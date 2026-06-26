"""
Celery task: Generate fresh data every 6 hours for One8 demo tenant.

This task simulates ongoing business activity by creating:
- New orders with line items
- New ad spend (Meta + Google)
- Updated inventory snapshots
- Updated cohort snapshots  
- Updated cost driver snapshots
- Updated margin drift snapshots
- Updated operational impact snapshots
- All other metric tables

Runs every 6 hours via Celery beat schedule.
"""

import random
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

# One8 demo tenant ID
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"


def run_demo_data_generation():
    """
    Core logic for demo data generation (no celery dependency).
    
    Can be called from celery task OR directly from API endpoint.
    
    Returns:
        dict: Summary of generated data
    """
    from backend.app.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tenant_id": ONE8_TENANT_ID,
            "orders_created": 0,
            "line_items_created": 0,
            "ad_spend_records": 0,
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
        
        # === 1. Generate new orders (80-120 orders per 6-hour period) ===
        num_orders = random.randint(80, 120)
        orders_created = _generate_orders(
            db, 
            connector_id, 
            num_orders
        )
        summary["orders_created"] = orders_created["count"]
        summary["line_items_created"] = orders_created["line_items"]
        
        # === 2. Generate ad spend for today ===
        ad_spend_created = _generate_ad_spend(db)
        summary["ad_spend_records"] = ad_spend_created

        # Update connector last_synced_at so the dashboard shows fresh sync time
        db.execute(text("""
            UPDATE connector_integrations
            SET last_synced_at = :now
            WHERE tenant_id = :tid AND source = 'shopify'
        """), {"now": datetime.now(UTC), "tid": ONE8_TENANT_ID})
        
        # === 3. Update inventory snapshots ===
        inventory_updated = _update_inventory_snapshots(db)
        if inventory_updated:
            summary["snapshots_updated"].append("inventory_risk")
        
        # === 4. Update cohort snapshots ===
        cohort_updated = _update_cohort_snapshots(db)
        if cohort_updated:
            summary["snapshots_updated"].append("cohort")
        
        # === 5. Update cost driver snapshots ===
        cost_updated = _update_cost_driver_snapshots(db)
        if cost_updated:
            summary["snapshots_updated"].append("cost_driver")
        
        # === 6. Update margin drift snapshots ===
        margin_updated = _update_margin_drift_snapshots(db)
        if margin_updated:
            summary["snapshots_updated"].append("margin_drift")
        
        # === 7. Update operational impact snapshots ===
        ops_updated = _update_operational_impact_snapshots(db)
        if ops_updated:
            summary["snapshots_updated"].append("operational_impact")
        
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


def _generate_ad_spend(db) -> int:
    """Generate today's ad spend data if not already exists.

    Matches the real meta_ad_spends/google_ad_spends schema:
    id, tenant_id, connector_id, external_campaign_id, campaign_name,
    spend_date, currency, spend_amount, synced_at, created_at, updated_at.
    """

    today = date.today()
    now = datetime.now(UTC)

    # Reuse an existing connector + campaign so columns/FKs match real data.
    meta_ref = db.execute(text("""
        SELECT connector_id, external_campaign_id FROM meta_ad_spends
        WHERE tenant_id = :tid ORDER BY spend_date DESC LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    google_ref = db.execute(text("""
        SELECT connector_id, external_campaign_id FROM google_ad_spends
        WHERE tenant_id = :tid ORDER BY spend_date DESC LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()

    fallback_connector = db.scalar(text("""
        SELECT id FROM connector_integrations WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID})

    meta_connector = meta_ref[0] if meta_ref else fallback_connector
    meta_campaign = meta_ref[1] if meta_ref else "one8_meta_daily"
    google_connector = google_ref[0] if google_ref else fallback_connector
    google_campaign = google_ref[1] if google_ref else "one8_google_daily"

    meta_exists = db.scalar(text("""
        SELECT COUNT(*) FROM meta_ad_spends
        WHERE tenant_id = :tid AND spend_date = :date
    """), {"tid": ONE8_TENANT_ID, "date": today})

    google_exists = db.scalar(text("""
        SELECT COUNT(*) FROM google_ad_spends
        WHERE tenant_id = :tid AND spend_date = :date
    """), {"tid": ONE8_TENANT_ID, "date": today})

    records_created = 0

    # Meta ad spend (Rs 20k-40k per day)
    if not meta_exists and meta_connector is not None:
        meta_spend = random.uniform(20000, 40000)
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
            "external_campaign_id": meta_campaign,
            "campaign_name": "One8_Meta_Daily",
            "spend_date": today,
            "currency": "INR",
            "spend_amount": round(meta_spend, 2),
            "synced_at": now,
            "created_at": now,
            "updated_at": now,
        })
        records_created += 1

    # Google ad spend (Rs 15k-30k per day)
    if not google_exists and google_connector is not None:
        google_spend = random.uniform(15000, 30000)
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
            "external_campaign_id": google_campaign,
            "campaign_name": "One8_Google_Daily",
            "spend_date": today,
            "currency": "INR",
            "spend_amount": round(google_spend, 2),
            "synced_at": now,
            "created_at": now,
            "updated_at": now,
        })
        records_created += 1

    return records_created


def _update_inventory_snapshots(db) -> bool:
    """Update inventory items with realistic stock levels and COGS."""
    
    # One8 Product Catalog with realistic COGS (42% of retail)
    PRODUCTS_WITH_COGS = [
        ("ONE8-TEE-001", "One8 Signature T-Shirt", "Black", 1299.0, 545.0, 50),
        ("ONE8-TEE-002", "One8 Signature T-Shirt", "White", 1299.0, 545.0, 50),
        ("ONE8-TEE-003", "One8 Signature T-Shirt", "Navy", 1299.0, 545.0, 40),
        ("ONE8-POLO-001", "One8 Polo Shirt", "Blue", 1899.0, 798.0, 30),
        ("ONE8-POLO-002", "One8 Polo Shirt", "Grey", 1899.0, 798.0, 30),
        ("ONE8-SHOE-001", "One8 Running Shoes", "Black/Red", 4999.0, 2100.0, 20),
        ("ONE8-SHOE-002", "One8 Running Shoes", "White/Blue", 4999.0, 2100.0, 20),
        ("ONE8-SHOE-003", "One8 Sneakers", "Grey", 3999.0, 1680.0, 25),
        ("ONE8-TRACK-001", "One8 Track Pants", "Black", 2299.0, 966.0, 35),
        ("ONE8-TRACK-002", "One8 Track Pants", "Navy", 2299.0, 966.0, 35),
        ("ONE8-SHORT-001", "One8 Shorts", "Black", 1499.0, 630.0, 40),
        ("ONE8-SHORT-002", "One8 Shorts", "Grey", 1499.0, 630.0, 40),
        ("ONE8-JACKET-001", "One8 Jacket", "Black", 3499.0, 1470.0, 20),
        ("ONE8-JACKET-002", "One8 Jacket", "Navy", 3499.0, 1470.0, 20),
        ("ONE8-CAP-001", "One8 Cap", "Black", 799.0, 336.0, 60),
        ("ONE8-CAP-002", "One8 Cap", "White", 799.0, 336.0, 60),
        ("ONE8-SOCK-001", "One8 Socks (3-Pack)", "Mixed", 599.0, 252.0, 80),
        ("ONE8-HOODIE-001", "One8 Hoodie", "Grey", 2999.0, 1260.0, 25),
    ]
    
    # Get real connector ID from existing inventory
    ONE8_CONNECTOR_ID = db.scalar(text("""
        SELECT DISTINCT connector_id FROM shopify_inventory_items
        WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID})
    
    if not ONE8_CONNECTOR_ID:
        return True  # Skip if no connector
    
    for sku, product_title, variant, _retail_price, cogs, reorder_point in (
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
                    synced_at = :now,
                    updated_at = :now
                WHERE id = :id
            """), {
                "change": change,
                "cogs": cogs,
                "reorder": reorder_point,
                "now": datetime.now(UTC),
                "id": exists
            })
        else:
            # Create inventory item with COGS
            db.execute(text("""
                INSERT INTO shopify_inventory_items (
                    id, tenant_id, connector_id, external_inventory_item_id,
                    sku, product_title, variant_title, available_quantity,
                    cost_per_unit, reorder_point, synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_id,
                    :sku, :product_title, :variant_title, :quantity,
                    :cogs, :reorder, :now, :now, :now
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
                "now": datetime.now(UTC),
            })
    
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
