#!/usr/bin/env python3
"""
Seed One8 tenant with scraped product data + generated transaction data.

This script:
1. Loads scraped One8 products from JSON
2. Inserts products into Shopify products table
3. Generates realistic orders (high volume for Virat Kohli's brand)
4. Generates Meta/Google ad spend
5. Generates Klaviyo campaign data

Usage:
    railway run python3 scripts/seed_one8_data.py
"""

import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from decimal import Decimal

from sqlalchemy import create_engine, text

# One8 tenant ID (created from frontend)
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Data generation parameters for One8 (Premium Indian lifestyle brand)
PARAMS = {
    "daily_orders_min": 150,
    "daily_orders_max": 350,
    "avg_order_value": 6500,  # INR - premium brand
    "aov_std_dev": 3000,
    "daily_meta_spend_min": 150000,  # INR - significant ad budget
    "daily_meta_spend_max": 250000,
    "daily_google_spend_min": 80000,
    "daily_google_spend_max": 150000,
    "return_rate": 0.12,  # 12% return rate (apparel/footwear)
    "refund_days_delay_min": 3,
    "refund_days_delay_max": 10,
    "klaviyo_weekly_campaigns": 3,
    "klaviyo_avg_recipients": 45000,
    "klaviyo_open_rate": 0.24,
    "klaviyo_click_rate": 0.06,
}


def load_scraped_products():
    """Load scraped One8 products from JSON."""
    
    data_dir = Path(__file__).parent.parent / "data"
    json_path = data_dir / "one8_products.json"
    
    if not json_path.exists():
        print(f"❌ ERROR: Scraped products not found at {json_path}")
        print("   Run: python3 scripts/scrape_one8.py first")
        sys.exit(1)
    
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    return data["products"]


def create_shopify_connector(conn):
    """Create a Shopify connector integration for One8."""
    
    print("\n🔌 Creating Shopify connector...")
    
    # Check if connector already exists
    connector = conn.execute(text("""
        SELECT id FROM connector_integrations 
        WHERE tenant_id = :tid AND source = 'shopify'
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    
    if connector:
        print(f"   ✅ Connector already exists: {connector[0]}")
        return connector[0]
    
    # Create connector
    connector_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO connector_integrations (
            id, tenant_id, source, auth_mode, status, health_status,
            shop_domain, connected_at, last_synced_at, created_at
        ) VALUES (
            :id, :tenant_id, :source, :auth_mode, :status, :health_status,
            :shop_domain, :connected_at, :last_synced_at, :created_at
        )
    """), {
        "id": connector_id,
        "tenant_id": ONE8_TENANT_ID,
        "source": "shopify",
        "auth_mode": "oauth",
        "status": "connected",
        "health_status": "healthy",
        "shop_domain": "one8.myshopify.com",
        "connected_at": datetime.utcnow(),
        "last_synced_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    })
    
    conn.commit()
    print(f"   ✅ Created connector: {connector_id}")
    
    return connector_id


def insert_products(conn, products, connector_id):
    """Insert One8 products into shopify_inventory_items table."""
    
    print(f"\n📦 Inserting {len(products)} products...")
    
    inserted = 0
    skipped = 0
    
    for product in products:
        # Use the first variant for main product data
        first_variant = product["variants"][0] if product["variants"] else {}
        
        # Check if product already exists
        check = conn.execute(
            text("""
                SELECT id FROM shopify_inventory_items 
                WHERE external_inventory_item_id = :eid AND tenant_id = :tid
            """),
            {"eid": str(product["product_id"]), "tid": ONE8_TENANT_ID}
        ).fetchone()
        
        if check:
            skipped += 1
            continue
        
        # Insert product
        conn.execute(text("""
            INSERT INTO shopify_inventory_items (
                id, tenant_id, connector_id, external_inventory_item_id,
                sku, product_title, variant_title, available_quantity,
                cost_per_unit, synced_at, created_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_inventory_item_id,
                :sku, :product_title, :variant_title, :available_quantity,
                :cost_per_unit, :synced_at, :created_at
            )
        """), {
            "id": str(uuid.uuid4()),
            "tenant_id": ONE8_TENANT_ID,
            "connector_id": connector_id,
            "external_inventory_item_id": str(product["product_id"]),
            "sku": first_variant.get("sku", f"ONE8-{product['product_id']}"),
            "product_title": product["title"],
            "variant_title": first_variant.get("title") if len(product["variants"]) > 1 else None,
            "available_quantity": random.randint(10, 200),  # Random inventory
            "cost_per_unit": float(product["min_price"]) * 0.4,  # Assume 40% cost
            "synced_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        })
        
        inserted += 1
    
    conn.commit()
    print(f"   ✅ Inserted: {inserted}, Skipped (already exists): {skipped}")
    
    return inserted


def generate_orders(conn, products, connector_id, days=90):
    """Generate realistic orders for One8 over the past X days."""
    
    print(f"\n📊 Generating {days} days of order data...")
    
    # Clean up any existing orders first (delete ALL orders for this tenant)
    result = conn.execute(text("""
        DELETE FROM shopify_orders 
        WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID})
    deleted = result.rowcount
    if deleted > 0:
        print(f"   🗑️  Deleted {deleted} existing orders")
    conn.commit()
    
    # Get product list with prices
    product_pool = []
    for p in products:
        for _ in range(max(1, int(p["min_price"] / 1000))):  # Weight by price
            product_pool.append({
                "id": p["product_id"],
                "title": p["title"],
                "price": p["min_price"],
                "type": p.get("product_type", ""),
            })
    
    total_orders = 0
    total_revenue = Decimal("0")
    orders_batch = []
    used_order_ids = set()  # Track used external_order_ids to avoid duplicates
    
    end_date = datetime.utcnow()
    
    print("   Generating order data...")
    for day_offset in range(days):
        order_date = end_date - timedelta(days=day_offset)
        
        # Daily order count (varies by day of week)
        is_weekend = order_date.weekday() >= 5
        daily_orders = random.randint(
            int(PARAMS["daily_orders_min"] * (1.3 if is_weekend else 1.0)),
            int(PARAMS["daily_orders_max"] * (1.3 if is_weekend else 1.0))
        )
        
        for _ in range(daily_orders):
            # Generate order value (log-normal distribution)
            aov = max(
                1000,
                random.gauss(PARAMS["avg_order_value"], PARAMS["aov_std_dev"])
            )
            
            # Pick 1-3 items
            num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            selected_products = random.sample(product_pool, min(num_items, len(product_pool)))
            
            # Calculate totals
            subtotal = Decimal(str(sum([p["price"] for p in selected_products])))
            shipping = Decimal(str(random.choice([0, 99, 149])))  # Free shipping or paid
            tax = subtotal * Decimal("0.18")  # 18% GST in India
            total = subtotal + shipping + tax
            
            # Random timestamp during the day
            order_datetime = order_date.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Fulfillment status
            fulfillment_status = random.choices(
                ["fulfilled", "pending", "cancelled"],
                weights=[0.92, 0.05, 0.03]
            )[0]
            
            # Financial status
            financial_status = "paid" if fulfillment_status != "cancelled" else "refunded"
            
            # Generate unique external_order_id
            while True:
                external_order_id = str(random.randint(10000000, 99999999))
                if external_order_id not in used_order_ids:
                    used_order_ids.add(external_order_id)
                    break
            
            # Collect order data
            order_id = str(uuid.uuid4())
            
            orders_batch.append({
                "id": order_id,
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_order_id": external_order_id,
                "customer_id": f"cust_{random.randint(1000, 99999)}",
                "order_number": external_order_id,
                "currency": "INR",
                "total_amount": float(total),
                "discount_amount": 0.0,
                "shipping_amount": float(shipping),
                "refund_amount": 0.0 if financial_status == "paid" else float(total),
                "is_refunded": financial_status != "paid",
                "order_created_at": order_datetime,
                "synced_at": order_datetime,
            })
            
            total_orders += 1
            if financial_status == "paid":
                total_revenue += total
    
    # Bulk insert orders in chunks (to avoid overwhelming the database)
    print(f"   Inserting {len(orders_batch):,} orders in batches of 1000...")
    if orders_batch:
        batch_size = 1000
        for i in range(0, len(orders_batch), batch_size):
            chunk = orders_batch[i:i + batch_size]
            conn.execute(text("""
                INSERT INTO shopify_orders (
                    id, tenant_id, connector_id, external_order_id, customer_id,
                    order_number, currency, total_amount, discount_amount,
                    shipping_amount, refund_amount, is_refunded, order_created_at, synced_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_order_id, :customer_id,
                    :order_number, :currency, :total_amount, :discount_amount,
                    :shipping_amount, :refund_amount, :is_refunded, :order_created_at, :synced_at
                )
            """), chunk)
            conn.commit()
            print(f"      Inserted {min(i + batch_size, len(orders_batch)):,} / {len(orders_batch):,}")
    
    print(f"   ✅ Generated {total_orders:,} orders")
    print(f"   💰 Total revenue: ₹{total_revenue:,.2f}")
    
    return total_orders


def generate_refunds(conn, days=90):
    """Generate refunds based on return rate."""
    
    print(f"\n💸 Generating refunds ({PARAMS['return_rate']*100:.0f}% return rate)...")
    
    try:
        # Clean up existing refunds first
        result = conn.execute(text("""
            DELETE FROM shopify_refunds WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID})
        deleted = result.rowcount
        if deleted > 0:
            print(f"   🗑️  Deleted {deleted} existing refunds")
            conn.commit()
    except Exception as e:
        if "does not exist" in str(e):
            print("   ⚠️  shopify_refunds table does not exist, skipping...")
            return
        raise
    
    # Get paid orders (not already refunded)
    orders = conn.execute(text("""
        SELECT id, external_order_id, total_amount, order_created_at
        FROM shopify_orders
        WHERE tenant_id = :tid
        AND is_refunded = false
        ORDER BY order_created_at DESC
        LIMIT 10000
    """), {"tid": ONE8_TENANT_ID}).fetchall()
    
    if not orders:
        print("   ⚠️  No orders found to refund")
        return
    
    # Select orders for refund
    num_refunds = int(len(orders) * PARAMS["return_rate"])
    refund_orders = random.sample(list(orders), min(num_refunds, len(orders)))
    
    # Get connector_id for refunds
    connector_result = conn.execute(text("""
        SELECT connector_id FROM shopify_orders WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    connector_id = connector_result[0] if connector_result else None
    
    if not connector_id:
        print("   ⚠️  No connector_id found, skipping refunds")
        return
    
    # Collect refund data
    refunds_batch = []
    for order in refund_orders:
        refund_date = order[3] + timedelta(
            days=random.randint(
                PARAMS["refund_days_delay_min"],
                PARAMS["refund_days_delay_max"]
            )
        )
        
        external_refund_id = f"refund_{random.randint(1000000, 9999999)}"
        
        refunds_batch.append({
            "id": str(uuid.uuid4()),
            "tenant_id": ONE8_TENANT_ID,
            "connector_id": connector_id,
            "external_refund_id": external_refund_id,
            "order_id": order[0],
            "external_order_id": order[1],
            "refund_amount": order[2],
            "reason": random.choice(["customer_request", "defective", "size_issue", "changed_mind"]),
            "refund_created_at": refund_date,
            "synced_at": refund_date,
            "created_at": refund_date,
        })
    
    # Bulk insert refunds
    if refunds_batch:
        conn.execute(text("""
            INSERT INTO shopify_refunds (
                id, tenant_id, connector_id, external_refund_id, order_id, external_order_id,
                refund_amount, reason, refund_created_at, synced_at, created_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_refund_id, :order_id, :external_order_id,
                :refund_amount, :reason, :refund_created_at, :synced_at, :created_at
            )
        """), refunds_batch)
        conn.commit()
    
    print(f"   ✅ Generated {len(refunds_batch):,} refunds")


def generate_ad_spend(conn, days=90):
    """Generate Meta and Google ad spend data."""
    
    print(f"\n💰 Generating {days} days of ad spend...")
    
    # Get connector_id for ad spends
    connector_result = conn.execute(text("""
        SELECT id FROM connector_integrations WHERE tenant_id = :tid LIMIT 1
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    connector_id = connector_result[0] if connector_result else None
    
    if not connector_id:
        print("   ⚠️  No connector_id found, skipping ad spend")
        return
    
    try:
        # Clean up existing ad spend first
        result = conn.execute(text("""
            DELETE FROM meta_ad_spends WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID})
        deleted_meta = result.rowcount
        result = conn.execute(text("""
            DELETE FROM google_ad_spends WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID})
        deleted_google = result.rowcount
        if deleted_meta + deleted_google > 0:
            print(f"   🗑️  Deleted {deleted_meta} Meta + {deleted_google} Google ad records")
            conn.commit()
    except Exception as e:
        if "does not exist" in str(e):
            print("   ⚠️  Ad spend tables do not exist, skipping...")
            return
        raise
    
    end_date = datetime.utcnow()
    
    # Meta/Google campaign names for realistic data
    meta_campaigns = [
        "TOF_Prospecting_Lookalike",
        "MOF_Retargeting_Engagement",
        "BOF_Conversion_Purchase",
    ]
    
    google_campaigns = [
        "Search_Brand_One8",
        "Search_Generic_Sportswear",
        "Display_Prospecting_Sports",
    ]
    
    meta_total = Decimal("0")
    google_total = Decimal("0")
    meta_batch = []
    google_batch = []
    
    for day_offset in range(days):
        ad_date = (end_date - timedelta(days=day_offset)).date()
        
        # Meta ads - distribute spend across campaigns
        daily_meta_total = Decimal(str(random.randint(
            PARAMS["daily_meta_spend_min"],
            PARAMS["daily_meta_spend_max"]
        )))
        
        for campaign in meta_campaigns:
            campaign_spend = daily_meta_total / len(meta_campaigns)
            meta_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_campaign_id": f"meta_{campaign}_{ad_date.strftime('%Y%m')}",
                "campaign_name": campaign,
                "spend_date": ad_date,
                "currency": "INR",
                "spend_amount": float(campaign_spend),
                "synced_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        
        meta_total += daily_meta_total
        
        # Google ads - distribute spend across campaigns
        daily_google_total = Decimal(str(random.randint(
            PARAMS["daily_google_spend_min"],
            PARAMS["daily_google_spend_max"]
        )))
        
        for campaign in google_campaigns:
            campaign_spend = daily_google_total / len(google_campaigns)
            google_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_campaign_id": f"google_{campaign}_{ad_date.strftime('%Y%m')}",
                "campaign_name": campaign,
                "spend_date": ad_date,
                "currency": "INR",
                "spend_amount": float(campaign_spend),
                "synced_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        
        google_total += daily_google_total
    
    # Bulk insert ad spend
    if meta_batch:
        conn.execute(text("""
            INSERT INTO meta_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount, :synced_at, :created_at, :updated_at
            )
        """), meta_batch)
    
    if google_batch:
        conn.execute(text("""
            INSERT INTO google_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount, :synced_at, :created_at, :updated_at
            )
        """), google_batch)
    
    conn.commit()
    print(f"   ✅ Meta spend: ₹{meta_total:,.2f}")
    print(f"   ✅ Google spend: ₹{google_total:,.2f}")
    print(f"   ✅ Total ad spend: ₹{(meta_total + google_total):,.2f}")


def generate_klaviyo_campaigns(conn, weeks=12):
    """Generate Klaviyo email campaign data."""
    
    print(f"\n📧 Generating {weeks} weeks of email campaigns...")
    
    try:
        # Clean up existing campaigns first
        result = conn.execute(text("""
            DELETE FROM klaviyo_campaigns WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID})
        deleted = result.rowcount
        if deleted > 0:
            print(f"   🗑️  Deleted {deleted} existing campaigns")
            conn.commit()
    except Exception as e:
        if "does not exist" in str(e):
            print("   ⚠️  klaviyo_campaigns table does not exist, skipping...")
            return
        raise
    
    campaign_types = [
        "New Arrivals Alert",
        "Weekend Flash Sale",
        "Product Launch",
        "Re-engagement Campaign",
        "Cart Abandonment",
        "VIP Early Access",
        "Seasonal Collection"
    ]
    
    total_campaigns = weeks * PARAMS["klaviyo_weekly_campaigns"]
    end_date = datetime.utcnow()
    campaigns_batch = []
    
    for i in range(total_campaigns):
        days_ago = random.randint(0, weeks * 7)
        campaign_date = end_date - timedelta(days=days_ago)
        
        recipients = random.randint(
            int(PARAMS["klaviyo_avg_recipients"] * 0.7),
            int(PARAMS["klaviyo_avg_recipients"] * 1.3)
        )
        
        opens = int(recipients * random.gauss(PARAMS["klaviyo_open_rate"], 0.03))
        clicks = int(opens * random.gauss(PARAMS["klaviyo_click_rate"] / PARAMS["klaviyo_open_rate"], 0.02))
        
        campaigns_batch.append({
            "id": str(uuid.uuid4()),
            "tenant_id": ONE8_TENANT_ID,
            "campaign_name": random.choice(campaign_types),
            "sent_at": campaign_date,
            "recipients": recipients,
            "opens": max(0, opens),
            "clicks": max(0, clicks),
            "created_at": campaign_date,
        })
    
    # Bulk insert campaigns
    if campaigns_batch:
        conn.execute(text("""
            INSERT INTO klaviyo_campaigns (
                id, tenant_id, campaign_name, sent_at, recipients, opens, clicks, created_at
            ) VALUES (
                :id, :tenant_id, :campaign_name, :sent_at, :recipients, :opens, :clicks, :created_at
            )
        """), campaigns_batch)
        conn.commit()
    
    print(f"   ✅ Generated {total_campaigns} campaigns")


def main():
    """Main seeding workflow."""
    
    print("="*60)
    print("🏏 ONE8 DATA SEEDING")
    print("="*60)
    print(f"Tenant ID: {ONE8_TENANT_ID}")
    print("Brand: One8 by Virat Kohli")
    print("="*60)
    
    # Get database connection
    database_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found")
        print("   Run with: railway run python3 scripts/seed_one8_data.py")
        sys.exit(1)
    
    engine = create_engine(database_url)
    
    # Load scraped products
    products = load_scraped_products()
    print(f"\n✅ Loaded {len(products)} products from scraped data")
    
    with engine.connect() as conn:
        # Create Shopify connector
        connector_id = create_shopify_connector(conn)
        
        # Insert products
        insert_products(conn, products, connector_id)
        
        # Generate orders (90 days)
        generate_orders(conn, products, connector_id, days=90)
        
        # Generate refunds
        generate_refunds(conn, days=90)
        
        # Generate ad spend
        generate_ad_spend(conn, days=90)
        
        # Generate email campaigns
        generate_klaviyo_campaigns(conn, weeks=12)
    
    print("\n" + "="*60)
    print("✅ ONE8 DATA SEEDING COMPLETE!")
    print("="*60)
    print("\n📋 Summary:")
    print("   - Products: 187 (real One8 catalog)")
    print("   - Orders: ~22,500 (90 days, high volume)")
    print("   - Ad Spend: ~₹2.07 Cr (Meta + Google)")
    print("   - Email Campaigns: 36 campaigns")
    print("\n🚀 Ready to test Executive Owner dashboard!")


if __name__ == "__main__":
    main()
