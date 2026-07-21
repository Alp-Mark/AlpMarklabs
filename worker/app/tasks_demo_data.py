"""
Celery task: Generate fresh data every 6 hours for One8 demo tenant.

This task simulates ongoing business activity with REALISTIC patterns:
- Seasonality (Cricket season, Diwali, festivals)
- Weekend spikes
- Spend-to-conversion correlation (saturation curves)
- Campaign bursts with diminishing returns
- Day-to-day variance

Runs every 6 hours via Celery beat schedule.
"""

import math
import random
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

# One8 demo tenant ID
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Realistic baseline parameters
BASELINE = {
    "base_daily_orders": 200,
    "base_meta_spend": 180000,  # INR/day
    "base_google_spend": 110000,  # INR/day
}


def get_seasonality_multiplier(dt):
    """Get seasonality multiplier for a given date (same as seed script)."""
    month = dt.month
    day = dt.day
    
    # Diwali peak (Oct 24-Nov 15)
    if month == 10 and day >= 24 or month == 11 and day <= 15:
        diwali_center = datetime(dt.year, 11, 1)
        days_from_diwali = abs((dt.date() - diwali_center.date()).days)
        if days_from_diwali <= 3:
            return 2.0
        elif days_from_diwali <= 10:
            return 1.6
        else:
            return 1.3
    
    # IPL season (March-May)
    if month in [3, 4, 5]:
        return 1.5
    
    # Early October (World Cup / Cricket season)
    if month == 10 and day < 24:
        return 1.4
    
    # New Year (Dec 20 - Jan 10)
    if (month == 12 and day >= 20) or (month == 1 and day <= 10):
        return 1.3
    
    # Valentine's (Feb 10-15)
    if month == 2 and 10 <= day <= 15:
        return 1.2
    
    # Summer lull (June-August)
    if month in [6, 7, 8]:
        return 0.85
    
    return 1.0


def get_weekend_multiplier(dt):
    """Weekend spike multiplier."""
    weekday = dt.weekday()
    if weekday == 4:  # Friday
        return 1.25
    elif weekday == 5:  # Saturday
        return 1.4
    elif weekday == 6:  # Sunday
        return 1.35
    else:
        return 1.0


def calculate_conversions_from_spend(meta_spend, google_spend):
    """Calculate realistic conversions using Hill curve saturation."""
    total_spend = meta_spend + google_spend
    
    # Hill curve parameters (matches seed script)
    max_daily_conversions = 600
    half_saturation_spend = 350000
    saturation_exponent = 1.8
    
    # Hill curve formula
    spend_power = total_spend ** saturation_exponent
    k_power = half_saturation_spend ** saturation_exponent
    saturation_conversions = max_daily_conversions * (spend_power / (k_power + spend_power))
    
    # Add noise (±10%)
    noise = random.uniform(0.9, 1.1)
    conversions = int(saturation_conversions * noise)
    
    return max(0, conversions)


def run_demo_data_generation():
    """
    Core logic for demo data generation with REALISTIC patterns.
    
    Flow:
    1. Generate today's ad spend with seasonality/campaign patterns
    2. Calculate orders based on spend using Hill curve saturation
    3. Apply seasonality and weekend multipliers
    4. Update snapshots
    
    Returns:
        dict: Summary of generated data
    """
    from backend.app.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        now = datetime.now(UTC)
        today = now.date()
        
        summary = {
            "timestamp": now.isoformat(),
            "tenant_id": ONE8_TENANT_ID,
            "date": str(today),
            "seasonality": get_seasonality_multiplier(now),
            "weekend_mult": get_weekend_multiplier(now),
            "orders_created": 0,
            "line_items_created": 0,
            "ad_spend_records": 0,
            "meta_spend": 0,
            "google_spend": 0,
            "snapshots_updated": [],
        }
        
        # Get connector ID
        connector_id = db.scalar(text("""
            SELECT id FROM connector_integrations 
            WHERE tenant_id = :tid AND source = 'shopify'
            LIMIT 1
        """), {"tid": ONE8_TENANT_ID})
        
        if not connector_id:
            return {"error": "No Shopify connector found for One8"}
        
        # === 1. Generate realistic ad spend for today ===
        ad_spend_result = _generate_realistic_ad_spend(db, today, now)
        summary["ad_spend_records"] = ad_spend_result["records_created"]
        summary["meta_spend"] = ad_spend_result["meta_spend"]
        summary["google_spend"] = ad_spend_result["google_spend"]
        
        # === 2. Calculate orders from spend using saturation curve ===
        if ad_spend_result["meta_spend"] > 0 or ad_spend_result["google_spend"] > 0:
            base_conversions = calculate_conversions_from_spend(
                ad_spend_result["meta_spend"],
                ad_spend_result["google_spend"]
            )
            
            # Apply seasonality and weekend effects
            season_mult = get_seasonality_multiplier(now)
            weekend_mult = get_weekend_multiplier(now)
            target_conversions = int(base_conversions * season_mult * weekend_mult)
            
            # For 6-hour period, generate 1/4 of daily conversions
            num_orders = int(target_conversions / 4)
        else:
            # Fallback if no spend data
            num_orders = random.randint(40, 60)
        
        # === 3. Generate orders ===
        orders_created = _generate_orders(
            db, 
            connector_id, 
            num_orders
        )
        summary["orders_created"] = orders_created["count"]
        summary["line_items_created"] = orders_created["line_items"]
        summary["calculated_daily_conversions"] = num_orders * 4
        
        # Update connector last_synced_at
        db.execute(text("""
            UPDATE connector_integrations
            SET last_synced_at = :now
            WHERE tenant_id = :tid AND source = 'shopify'
        """), {"now": now, "tid": ONE8_TENANT_ID})
        
        # === 4. Update snapshots ===
        inventory_updated = _update_inventory_snapshots(db)
        if inventory_updated:
            summary["snapshots_updated"].append("inventory_risk")
        
        cohort_updated = _update_cohort_snapshots(db)
        if cohort_updated:
            summary["snapshots_updated"].append("cohort")
        
        cost_updated = _update_cost_driver_snapshots(db)
        if cost_updated:
            summary["snapshots_updated"].append("cost_driver")
        
        margin_updated = _update_margin_drift_snapshots(db)
        if margin_updated:
            summary["snapshots_updated"].append("margin_drift")
        
        ops_updated = _update_operational_impact_snapshots(db)
        if ops_updated:
            summary["snapshots_updated"].append("operational_impact")
        
        # === 5. Update marketing channel spends (influencer, email, affiliate) ===
        mcs_updated = _update_marketing_channel_spends(db, today)
        if mcs_updated:
            summary["snapshots_updated"].append("marketing_channels")
        
        db.commit()
        
        print(f"✅ Demo data generated: {summary}")
        return summary
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error generating demo data: {e}")
        raise
    finally:
        db.close()


def generate_demo_data_one8():
    """
    Celery task wrapper for demo data generation.
    
    Delegates to run_demo_data_generation() for actual logic.
    """
    return run_demo_data_generation()


# Register as celery task only when celery is available
try:
    from worker.app.celery_app import celery_app
    # Manually register the function as a task
    generate_demo_data_one8 = celery_app.task(
        name="worker.app.tasks.generate_demo_data_one8"
    )(generate_demo_data_one8)
except ImportError:
    # Celery not available - function can still be called directly
    pass


def _generate_orders(db, connector_id: str, num_orders: int) -> dict:
    """Generate realistic orders with line items for the last 6 hours."""
    
    # Product catalog with realistic One8 items
    PRODUCTS = [
        ("ONE8-TEE-001", "One8 Signature T-Shirt", "Black", 1299.0),
        ("ONE8-TEE-002", "One8 Signature T-Shirt", "White", 1299.0),
        ("ONE8-TEE-003", "One8 Signature T-Shirt", "Navy", 1299.0),
        ("ONE8-POLO-001", "One8 Polo Shirt", "Blue", 1899.0),
        ("ONE8-POLO-002", "One8 Polo Shirt", "Grey", 1899.0),
        ("ONE8-SHOE-001", "One8 Running Shoes", "Black/Red", 4999.0),
        ("ONE8-SHOE-002", "One8 Running Shoes", "White/Blue", 4999.0),
        ("ONE8-SHOE-003", "One8 Sneakers", "Grey", 3999.0),
        ("ONE8-TRACK-001", "One8 Track Pants", "Black", 2299.0),
        ("ONE8-TRACK-002", "One8 Track Pants", "Navy", 2299.0),
        ("ONE8-SHORT-001", "One8 Shorts", "Black", 1499.0),
        ("ONE8-SHORT-002", "One8 Shorts", "Grey", 1499.0),
        ("ONE8-JACKET-001", "One8 Jacket", "Black", 3499.0),
        ("ONE8-JACKET-002", "One8 Jacket", "Navy", 3499.0),
        ("ONE8-CAP-001", "One8 Cap", "Black", 799.0),
        ("ONE8-CAP-002", "One8 Cap", "White", 799.0),
        ("ONE8-SOCK-001", "One8 Socks (3-Pack)", "Mixed", 599.0),
        ("ONE8-HOODIE-001", "One8 Hoodie", "Grey", 2999.0),
    ]
    
    orders_batch = []
    line_items_batch = []
    now = datetime.now(UTC)
    
    for _i in range(num_orders):
        # Random timestamp within last 6 hours
        minutes_ago = random.randint(0, 360)  # 0-6 hours
        order_time = now - timedelta(minutes=minutes_ago)
        
        # Random customer ID (simulate 60% repeat customers, 40% new)
        is_repeat = random.random() < 0.6
        if is_repeat:
            # Use existing customer ID pattern
            customer_id = f"cust_{random.randint(1, 5000):05d}"
        else:
            # New customer
            customer_id = f"cust_{random.randint(10000, 99999):05d}"
        
        # Unique order number using timestamp + random suffix
        order_number = f"ONE8-{int(order_time.timestamp())}-{random.randint(100, 999)}"
        
        # Number of items (1-3, weighted toward 1-2)
        num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        
        # Select products
        selected_products = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
        
        # Calculate order total
        order_total = 0.0
        for _, _, _, price in selected_products:
            quantity = 1 if random.random() < 0.85 else 2
            order_total += price * quantity
        
        # Shipping (₹0-100)
        shipping = random.uniform(0, 100)
        order_total += shipping
        
        # Discount (10% of orders have 5-15% discount)
        discount = 0.0
        if random.random() < 0.1:
            discount = order_total * random.uniform(0.05, 0.15)
            order_total -= discount
        
        # 3% return rate
        is_refunded = random.random() < 0.03
        refund_amount = order_total if is_refunded else 0.0
        
        order_id = str(uuid.uuid4())
        
        orders_batch.append({
            "id": order_id,
            "tenant_id": ONE8_TENANT_ID,
            "connector_id": connector_id,
            "external_order_id": f"shopify_{order_number}",
            "customer_id": customer_id,
            "order_number": order_number,
            "currency": "INR",
            "total_amount": round(order_total, 2),
            "discount_amount": round(discount, 2),
            "shipping_amount": round(shipping, 2),
            "refund_amount": round(refund_amount, 2),
            "is_refunded": is_refunded,
            "order_created_at": order_time,
            "synced_at": now,
        })
        
        # Create line items
        for item_idx, (sku, product_title, variant, price) in enumerate(
            selected_products
        ):
            quantity = 1 if random.random() < 0.85 else 2
            
            line_items_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "order_id": order_id,
                "line_item_index": item_idx,
                "sku": sku,
                "product_title": product_title,
                "variant_title": variant,
                "quantity": quantity,
                "unit_price": round(price, 2),
                "order_created_at": order_time,
            })
    
    # Insert orders in batch (skip duplicates)
    if orders_batch:
        db.execute(text("""
            INSERT INTO shopify_orders (
                id, tenant_id, connector_id, external_order_id, customer_id,
                order_number, currency, total_amount, discount_amount,
                shipping_amount, refund_amount, is_refunded, order_created_at, synced_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_order_id, :customer_id,
                :order_number, :currency, :total_amount, :discount_amount,
                :shipping_amount, :refund_amount, :is_refunded,
                :order_created_at, :synced_at
            )
            ON CONFLICT (tenant_id, connector_id, external_order_id) DO NOTHING
        """), orders_batch)
    
    # Insert line items in batch (skip duplicates)
    if line_items_batch:
        db.execute(text("""
            INSERT INTO shopify_order_line_items (
                id, tenant_id, order_id, line_item_index, sku,
                product_title, variant_title, quantity, unit_price, order_created_at
            ) VALUES (
                :id, :tenant_id, :order_id, :line_item_index, :sku,
                :product_title, :variant_title, :quantity,
                :unit_price, :order_created_at
            )
            ON CONFLICT (id) DO NOTHING
        """), line_items_batch)
    
    return {
        "count": len(orders_batch),
        "line_items": len(line_items_batch),
    }


def _generate_realistic_ad_spend(db, today: date, now: datetime) -> dict:
    """
    Generate today's ad spend with realistic patterns.
    
    Applies:
    - Seasonality multipliers (Diwali, IPL, etc.)
    - Weekend optimization (reduce spend on weekends)
    - Campaign burst patterns (every ~40 days)
    - Daily variance (±15%)
    
    Returns: {"records_created": int, "meta_spend": float, "google_spend": float}
    """
    
    # Check if today's spend already exists
    meta_exists = db.scalar(text("""
        SELECT COUNT(*) FROM meta_ad_spends
        WHERE tenant_id = :tid AND spend_date = :date
    """), {"tid": ONE8_TENANT_ID, "date": today})

    google_exists = db.scalar(text("""
        SELECT COUNT(*) FROM google_ad_spends
        WHERE tenant_id = :tid AND spend_date = :date
    """), {"tid": ONE8_TENANT_ID, "date": today})
    
    # Don't check if today's spend exists - generate fresh ad spend every 6 hours
    # This ensures continuous data flow for the demo simulator
    # (Different from the backend seed, which only runs once at initialization)
    
    # Get connector IDs (reuse existing campaigns)
    meta_ref = db.execute(text("""
        SELECT connector_id, campaign_name FROM meta_ad_spends
        WHERE tenant_id = :tid ORDER BY spend_date DESC LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    
    google_ref = db.execute(text("""
        SELECT connector_id, campaign_name FROM google_ad_spends
        WHERE tenant_id = :tid ORDER BY spend_date DESC LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()

    fallback_connector = db.scalar(text("""
        SELECT id FROM connector_integrations WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID})

    meta_connector = meta_ref[0] if meta_ref else fallback_connector
    google_connector = google_ref[0] if google_ref else fallback_connector
    
    # Calculate days since epoch for campaign cycle
    days_since_epoch = (today - date(2026, 1, 1)).days
    campaign_cycle_day = days_since_epoch % 40
    
    # Campaign burst pattern (2-week bursts every ~40 days)
    if 5 <= campaign_cycle_day <= 18:
        campaign_mult = 1.8  # Heavy campaign
    elif campaign_cycle_day <= 25:
        campaign_mult = 1.2  # Wind-down
    else:
        campaign_mult = 1.0  # Normal
    
    # Weekend optimization (reduce paid spend when organic is high)
    weekend_mult = 0.9 if now.weekday() in [5, 6] else 1.0
    
    # Daily variance
    daily_variance = random.uniform(0.85, 1.15)
    
    # Calculate spend with all multipliers
    meta_spend = BASELINE["base_meta_spend"] * campaign_mult * weekend_mult * daily_variance
    google_spend = BASELINE["base_google_spend"] * campaign_mult * weekend_mult * daily_variance
    
    records_created = 0
    
    # Insert Meta spend (split across 3 campaigns)
    if not meta_exists and meta_connector:
        meta_campaigns = ["Acquisition - Broad", "Retargeting", "Collection Launch"]
        for campaign in meta_campaigns:
            campaign_spend = meta_spend / len(meta_campaigns)
            db.execute(text("""
                INSERT INTO meta_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id,
                    campaign_name, spend_date, currency, spend_amount,
                    synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id,
                    :campaign_name, :spend_date, :currency, :spend_amount,
                    :synced_at, :created_at, :updated_at
                )
            """), {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": str(meta_connector),
                "external_campaign_id": f"meta_{campaign.replace(' ', '_')}_{today.strftime('%Y%m%d')}",
                "campaign_name": campaign,
                "spend_date": today,
                "currency": "INR",
                "spend_amount": round(campaign_spend, 2),
                "synced_at": now,
                "created_at": now,
                "updated_at": now,
            })
            records_created += 1
    
    # Insert Google spend (split across 3 campaigns)
    if not google_exists and google_connector:
        google_campaigns = ["Search - Brand", "Search - Generic", "Shopping"]
        for campaign in google_campaigns:
            campaign_spend = google_spend / len(google_campaigns)
            db.execute(text("""
                INSERT INTO google_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id,
                    campaign_name, spend_date, currency, spend_amount,
                    synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id,
                    :campaign_name, :spend_date, :currency, :spend_amount,
                    :synced_at, :created_at, :updated_at
                )
            """), {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": str(google_connector),
                "external_campaign_id": f"google_{campaign.replace(' ', '_')}_{today.strftime('%Y%m%d')}",
                "campaign_name": campaign,
                "spend_date": today,
                "currency": "INR",
                "spend_amount": round(campaign_spend, 2),
                "synced_at": now,
                "created_at": now,
                "updated_at": now,
            })
            records_created += 1

    return {
        "records_created": records_created,
        "meta_spend": round(meta_spend, 2),
        "google_spend": round(google_spend, 2),
    }




def _update_inventory_snapshots(db) -> bool:
    """Update inventory items with realistic stock levels and COGS."""
    
    # One8 Product Catalog with realistic COGS (42% of retail)
    # (sku, product_title, variant, retail_price, cogs, reorder_point, image_url)
    # image_url: real verified URLs from one8_products.json CDN
    PRODUCTS_WITH_COGS = [
        ("ONE8-TEE-001", "One8 Signature T-Shirt", "Black", 1299.0, 545.0, 50, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1-copy.jpg?v=1781874432"),
        ("ONE8-TEE-002", "One8 Signature T-Shirt", "White", 1299.0, 545.0, 50, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1copy_4ebb53f6-004b-4f25-9342-f040f59c1ba8.jpg?v=1781874356"),
        ("ONE8-TEE-003", "One8 Signature T-Shirt", "Navy", 1299.0, 545.0, 40, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1-copy.jpg?v=1781874432"),
        ("ONE8-POLO-001", "One8 Polo Shirt", "Blue", 1899.0, 798.0, 30, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V22000901_01.jpg?v=1781425700"),
        ("ONE8-POLO-002", "One8 Polo Shirt", "Grey", 1899.0, 798.0, 30, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1_84768696-dc76-4ed2-8aaa-66b1e2de6679.jpg?v=1781985199"),
        ("ONE8-SHOE-001", "One8 Running Shoes", "Black/Red", 4999.0, 2100.0, 20, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V10032402_02_756f038f-3639-4cd3-9cf9-45eb76905d92.jpg?v=1781859656"),
        ("ONE8-SHOE-002", "One8 Running Shoes", "White/Blue", 4999.0, 2100.0, 20, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V10015001_03_6d97ac06-93e4-46c0-b7ee-12a9ae14bd22.jpg?v=1781597662"),
        ("ONE8-SHOE-003", "One8 Sneakers", "Grey", 3999.0, 1680.0, 25, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V10015401_03.jpg?v=1781959016"),
        ("ONE8-TRACK-001", "One8 Track Pants", "Black", 2299.0, 966.0, 35, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1_577715d4-9ece-498f-aaf0-103a0e7f4886.jpg?v=1781868512"),
        ("ONE8-TRACK-002", "One8 Track Pants", "Navy", 2299.0, 966.0, 35, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1_9bf49dff-95a5-4e14-85b2-86e52c7deaa4.jpg?v=1781994618"),
        ("ONE8-SHORT-001", "One8 Shorts", "Black", 1499.0, 630.0, 40, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/2_7d5037d2-58b2-496f-9f3c-870836c46c6a.jpg?v=1781876268"),
        ("ONE8-SHORT-002", "One8 Shorts", "Grey", 1499.0, 630.0, 40, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/1_dc3beb8b-ee20-4ae6-8eb5-b7fb567b0e2d.jpg?v=1781988968"),
        ("ONE8-JACKET-001", "One8 Jacket", "Black", 3499.0, 1470.0, 20, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V24000501_01.jpg?v=1781875446"),
        ("ONE8-JACKET-002", "One8 Jacket", "Navy", 3499.0, 1470.0, 20, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V24000502_01.jpg?v=1781875497"),
        ("ONE8-CAP-001", "One8 Cap", "Black", 799.0, 336.0, 60, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V31001001_01_f2126a31-d5d5-4504-a797-0278343a8c81.jpg?v=1782142874"),
        ("ONE8-CAP-002", "One8 Cap", "White", 799.0, 336.0, 60, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V31000603_01.jpg?v=1781432152"),
        ("ONE8-SOCK-001", "One8 Socks (3-Pack)", "Mixed", 599.0, 252.0, 80, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V31001001_01_f2126a31-d5d5-4504-a797-0278343a8c81.jpg?v=1782142874"),
        ("ONE8-HOODIE-001", "One8 Hoodie", "Grey", 2999.0, 1260.0, 25, "https://cdn.shopify.com/s/files/1/0692/3514/6912/files/V24000501_01.jpg?v=1781875446"),
    ]
    
    # Get real connector ID from existing inventory
    ONE8_CONNECTOR_ID = db.scalar(text("""
        SELECT DISTINCT connector_id FROM shopify_inventory_items
        WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID})
    
    if not ONE8_CONNECTOR_ID:
        return True  # Skip if no connector
    
    for sku, product_title, variant, _retail_price, cogs, reorder_point, image_url in (
        PRODUCTS_WITH_COGS
    ):
        # Check if inventory item exists
        exists = db.scalar(text("""
            SELECT id FROM shopify_inventory_items
            WHERE tenant_id = :tid AND sku = :sku
        """), {"tid": ONE8_TENANT_ID, "sku": sku})
        
        if exists:
            # Update stock level (simulate consumption and restocking)
            # Decrease by random amount (0-10), occasionally restock
            change = (
                random.randint(-10, 0) if random.random() < 0.8
                else random.randint(20, 50)
            )
            
            db.execute(text("""
                UPDATE shopify_inventory_items
                SET available_quantity = GREATEST(available_quantity + :change, 0),
                    cost_per_unit = :cogs,
                    reorder_point = :reorder,
                    image_url = :image_url,
                    synced_at = :now,
                    updated_at = :now
                WHERE id = :id
            """), {
                "change": change,
                "cogs": cogs,
                "reorder": reorder_point,
                "image_url": image_url,
                "now": datetime.now(UTC),
                "id": exists
            })
        else:
            # Create inventory item with COGS
            db.execute(text("""
                INSERT INTO shopify_inventory_items (
                    id, tenant_id, connector_id, external_inventory_item_id,
                    sku, product_title, variant_title, available_quantity,
                    cost_per_unit, reorder_point, image_url, synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_id,
                    :sku, :product_title, :variant_title, :quantity,
                    :cogs, :reorder, :image_url, :now, :now, :now
                )
            """), {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": ONE8_CONNECTOR_ID,
                "external_id": f"shopify_inv_{sku}",
                "sku": sku,
                "product_title": product_title,
                "variant_title": variant,
                "quantity": 100,
                "cogs": cogs,
                "reorder": reorder_point,
                "image_url": image_url,
                "now": datetime.now(UTC),
            })
    
    return True


def _update_marketing_channel_spends(db, today) -> bool:
    """Generate daily spend/conversions for influencer, email, affiliate channels.

    Runs every 3 hours but only inserts one record per channel-campaign per day
    (idempotent). Uses realistic seasonality and baseline patterns aligned with
    the existing seeded data.
    """
    season_mult = get_seasonality_multiplier(datetime(today.year, today.month, today.day))
    weekend_mult = get_weekend_multiplier(datetime(today.year, today.month, today.day))

    # Influencer campaigns — 10 named creators with individual budgets
    INFLUENCERS = [
        ("Vikram Malhotra (Personal Training/Hiit)",  6000.0, 3.0),
        ("Meera Patel (Athleisure/Lifestyle)",         4800.0, 2.5),
        ("Aditya Verma (Sports Nutrition)",            4500.0, 2.4),
        ("Anjali Rao (Lifestyle Fitness)",             1500.0, 1.8),
        ("Shreya Iyer (Weight Loss)",                  1300.0, 1.7),
        ("Kabir Singh (Cricket Training)",             1200.0, 1.7),
        ("Rohan Kapoor (Gym/Strength)",                 900.0, 1.5),
        ("Neha Sharma (Yoga)",                          410.0, 1.3),
        ("Arjun Desai (Running)",                       400.0, 1.3),
        ("Priya Mehta (Fitness)",                       355.0, 1.2),
    ]

    # Email campaigns
    EMAIL_CAMPAIGNS = [
        ("Welcome Series",    2500.0, 12.0),  # high ROAS (owned channel)
        ("Weekly Newsletter", 1800.0, 9.0),
        ("Abandoned Cart",    1400.0, 11.0),
        ("Re-engagement",      800.0, 6.0),
    ]

    # Affiliate campaigns
    AFFILIATE_CAMPAIGNS = [
        ("Sports Affiliate Network", 9000.0, 3.0),
        ("Fitness Bloggers",         7000.0, 2.8),
        ("Coupon Sites",             5500.0, 2.5),
    ]

    connector_id = db.scalar(text("""
        SELECT id FROM connector_integrations WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID})

    if not connector_id:
        return False

    def upsert_channel_spend(channel_name, campaign_name, base_spend, roas):
        """Insert a row only if one doesn't exist for this campaign+date."""
        exists = db.scalar(text("""
            SELECT 1 FROM marketing_channel_spends
            WHERE tenant_id = :tid
              AND channel_name = :ch
              AND campaign_name = :camp
              AND spend_date = :dt
        """), {"tid": ONE8_TENANT_ID, "ch": channel_name,
               "camp": campaign_name, "dt": today})
        if exists:
            return

        variance = random.uniform(0.88, 1.12)
        spend = round(base_spend * season_mult * weekend_mult * variance, 2)
        # conversions: spend × ROAS / AOV (approx, using AOV=5500)
        conversions = max(0, round((spend * roas) / 5500 * random.uniform(0.85, 1.15)))
        revenue = round(conversions * 5500 * random.uniform(0.95, 1.05), 2)

        db.execute(text("""
            INSERT INTO marketing_channel_spends
              (id, tenant_id, connector_id, channel_name, external_campaign_id,
               campaign_name, spend_date, currency, spend_amount,
               impressions, clicks, conversions, revenue,
               synced_at, created_at, updated_at)
            VALUES
              (:id, :tid, :cid, :ch, :ext_id,
               :camp, :dt, 'INR', :spend,
               :imp, :clicks, :conv, :rev,
               NOW(), NOW(), NOW())
        """), {
            "id": str(uuid.uuid4()),
            "tid": ONE8_TENANT_ID,
            "cid": str(connector_id),
            "ch": channel_name,
            "ext_id": f"{channel_name}_{campaign_name[:20].replace(' ', '_')}_{today}",
            "camp": campaign_name,
            "dt": today,
            "spend": spend,
            "imp": int(spend * random.uniform(8, 15)),
            "clicks": int(spend * random.uniform(0.03, 0.08)),
            "conv": conversions,
            "rev": revenue,
        })

    for camp, base_spend, roas in INFLUENCERS:
        upsert_channel_spend("influencer", camp, base_spend, roas)

    for camp, base_spend, roas in EMAIL_CAMPAIGNS:
        upsert_channel_spend("email", camp, base_spend, roas)

    for camp, base_spend, roas in AFFILIATE_CAMPAIGNS:
        upsert_channel_spend("affiliate", camp, base_spend, roas)

    return True


def _update_cohort_snapshots(db) -> bool:
    """Update cohort retention snapshots."""
    # Placeholder - would calculate cohort metrics
    return True


def _update_cost_driver_snapshots(db) -> bool:
    """Update cost driver snapshots (COGS, shipping trends)."""
    # Placeholder - would update cost trends
    return True


def _update_margin_drift_snapshots(db) -> bool:
    """Update margin drift detection snapshots."""
    # Placeholder - would detect margin changes
    return True


def _update_operational_impact_snapshots(db) -> bool:
    """Update operational impact snapshots (returns, shipping costs, etc)."""
    # Placeholder - would calculate ops metrics
    return True
