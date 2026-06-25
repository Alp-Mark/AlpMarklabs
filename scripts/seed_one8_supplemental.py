#!/usr/bin/env python3
"""
Seed One8 tenant with refunds, ad spend, and email campaigns data.
This script ONLY generates refunds/ad spend/campaigns, NOT orders.
"""

import os
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text

# One8 tenant ID and connector ID (from previous seeding)
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"
ONE8_CONNECTOR_ID = "828071d8-86ae-4d5b-b3af-77c9600400a6"

# Seeding parameters
PARAMS = {
    "return_rate": 0.12,  # 12% return rate
    "refund_days_delay_min": 3,
    "refund_days_delay_max": 10,
    "daily_meta_spend_min": 150000,  # ₹150k
    "daily_meta_spend_max": 250000,  # ₹250k
    "daily_google_spend_min": 80000,  # ₹80k
    "daily_google_spend_max": 150000,  # ₹150k
    "klaviyo_weekly_campaigns": 3,
    "klaviyo_avg_recipients": 8500,
    "klaviyo_open_rate": 0.32,
    "klaviyo_click_rate": 0.08,
}

# Database connection
DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL environment variable not set")

engine = create_engine(DATABASE_URL)


def generate_refunds(conn, days=90):
    """Generate refunds based on return rate."""
    
    print(f"\n💸 Generating refunds ({PARAMS['return_rate']*100:.0f}% return rate)...")
    
    # Clean up existing refunds first
    result = conn.execute(text("""
        DELETE FROM shopify_refunds WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID})
    deleted = result.rowcount
    if deleted > 0:
        print(f"   🗑️  Deleted {deleted} existing refunds")
        conn.commit()
    
    # Get paid orders (not already refunded)
    orders = conn.execute(text("""
        SELECT id, external_order_id, total_amount, order_created_at
        FROM shopify_orders
        WHERE tenant_id = :tid
        AND is_refunded = false
        ORDER BY order_created_at DESC
    """), {"tid": ONE8_TENANT_ID}).fetchall()
    
    if not orders:
        print("   ⚠️  No orders found to refund")
        return
    
    # Select orders for refund
    num_refunds = int(len(orders) * PARAMS["return_rate"])
    refund_orders = random.sample(list(orders), min(num_refunds, len(orders)))
    
    # Collect refund data. external_refund_id is derived from the order's
    # unique external_order_id so it is guaranteed collision-free against the
    # uq_shopify_refund_per_connector unique constraint (one refund per order).
    refunds_batch = []
    for order in refund_orders:
        refund_date = order[3] + timedelta(
            days=random.randint(
                PARAMS["refund_days_delay_min"],
                PARAMS["refund_days_delay_max"]
            )
        )
        
        refunds_batch.append({
            "id": str(uuid.uuid4()),
            "tenant_id": ONE8_TENANT_ID,
            "connector_id": ONE8_CONNECTOR_ID,
            "external_refund_id": f"refund_{order[1]}",
            "order_id": str(order[0]),
            "external_order_id": order[1],
            "refund_amount": order[2],
            "reason": random.choice([
                "Customer request",
                "Size issue",
                "Quality concern",
                "Wrong item received",
                "Damaged in transit",
                None
            ]),
            "refund_created_at": refund_date,
            "synced_at": refund_date,
        })
    
    # Bulk insert refunds in chunks (a single 2,800-row insert overwhelms the
    # Railway connection and hangs; chunking is the same fix used for orders).
    if refunds_batch:
        print(f"   Inserting {len(refunds_batch):,} refunds in batches of 500...")
        batch_size = 500
        for i in range(0, len(refunds_batch), batch_size):
            chunk = refunds_batch[i:i + batch_size]
            conn.execute(text("""
                INSERT INTO shopify_refunds (
                    id, tenant_id, connector_id, external_refund_id, order_id,
                    external_order_id, refund_amount, reason, refund_created_at, synced_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_refund_id, :order_id,
                    :external_order_id, :refund_amount, :reason, :refund_created_at, :synced_at
                )
            """), chunk)
            conn.commit()
            print(f"      Inserted {min(i + batch_size, len(refunds_batch)):,} / {len(refunds_batch):,}")
    
    total_refund_amount = sum(r["refund_amount"] for r in refunds_batch)
    print(f"   ✅ Generated {len(refunds_batch):,} refunds")
    print(f"   💰 Total refund amount: ₹{total_refund_amount:,.2f}")


def generate_ad_spend(conn, days=90):
    """Generate Meta and Google ad spend data."""
    
    print(f"\n💰 Generating {days} days of ad spend...")
    
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
    
    end_date = datetime.utcnow()
    
    meta_total = Decimal("0")
    google_total = Decimal("0")
    meta_batch = []
    google_batch = []
    
    # Generate campaigns (we'll spread spend across a few campaigns per platform)
    meta_campaigns = [
        ("camp_meta_001", "One8 Brand Awareness"),
        ("camp_meta_002", "One8 Performance Max"),
        ("camp_meta_003", "One8 Retargeting"),
    ]
    
    google_campaigns = [
        ("camp_google_001", "One8 Search - Brand"),
        ("camp_google_002", "One8 Search - Generic"),
        ("camp_google_003", "One8 Shopping"),
    ]
    
    for day_offset in range(days):
        ad_date = (end_date - timedelta(days=day_offset)).date()
        
        # Meta ads (split spend across campaigns)
        daily_meta_spend = random.randint(
            PARAMS["daily_meta_spend_min"],
            PARAMS["daily_meta_spend_max"]
        )
        
        # Distribute spend across campaigns
        for ext_campaign_id, campaign_name in meta_campaigns:
            campaign_fraction = random.uniform(0.25, 0.40)
            campaign_spend = daily_meta_spend * campaign_fraction
            
            meta_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": ONE8_CONNECTOR_ID,
                "external_campaign_id": ext_campaign_id,
                "campaign_name": campaign_name,
                "spend_date": ad_date,
                "currency": "INR",
                "spend_amount": campaign_spend,
                "synced_at": datetime.utcnow(),
            })
            
            meta_total += Decimal(str(campaign_spend))
        
        # Google ads (split spend across campaigns)
        daily_google_spend = random.randint(
            PARAMS["daily_google_spend_min"],
            PARAMS["daily_google_spend_max"]
        )
        
        for ext_campaign_id, campaign_name in google_campaigns:
            campaign_fraction = random.uniform(0.25, 0.40)
            campaign_spend = daily_google_spend * campaign_fraction
            
            google_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": ONE8_CONNECTOR_ID,
                "external_campaign_id": ext_campaign_id,
                "campaign_name": campaign_name,
                "spend_date": ad_date,
                "currency": "INR",
                "spend_amount": campaign_spend,
                "synced_at": datetime.utcnow(),
            })
            
            google_total += Decimal(str(campaign_spend))
    
    # Bulk insert ad spend
    if meta_batch:
        conn.execute(text("""
            INSERT INTO meta_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount, :synced_at
            )
        """), meta_batch)
    
    if google_batch:
        conn.execute(text("""
            INSERT INTO google_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount, :synced_at
            )
        """), google_batch)
    
    conn.commit()
    print(f"   ✅ Meta spend: ₹{meta_total:,.2f} ({len(meta_batch):,} records)")
    print(f"   ✅ Google spend: ₹{google_total:,.2f} ({len(google_batch):,} records)")
    print(f"   ✅ Total ad spend: ₹{(meta_total + google_total):,.2f}")


def generate_klaviyo_campaigns(conn, weeks=12):
    """Generate Klaviyo email campaign data."""
    
    print(f"\n📧 Generating {weeks} weeks of email campaigns...")
    
    # Clean up existing campaigns first
    result = conn.execute(text("""
        DELETE FROM klaviyo_campaigns WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID})
    deleted = result.rowcount
    if deleted > 0:
        print(f"   🗑️  Deleted {deleted} existing campaigns")
        conn.commit()
    
    campaign_types = [
        "New Arrivals Alert",
        "Weekend Flash Sale",
        "Product Launch",
        "Re-engagement Campaign",
        "Cart Abandonment",
        "VIP Early Access",
        "Seasonal Collection",
        "Customer Winback",
        "Limited Edition Drop",
    ]
    
    total_campaigns = weeks * PARAMS["klaviyo_weekly_campaigns"]
    end_date = datetime.utcnow()
    campaigns_batch = []
    
    for i in range(total_campaigns):
        days_ago = random.randint(0, weeks * 7)
        campaign_date = end_date - timedelta(days=days_ago)
        
        campaign_name = random.choice(campaign_types)
        
        recipients = random.randint(
            int(PARAMS["klaviyo_avg_recipients"] * 0.7),
            int(PARAMS["klaviyo_avg_recipients"] * 1.3)
        )
        
        opens = int(recipients * random.gauss(PARAMS["klaviyo_open_rate"], 0.03))
        clicks = int(opens * random.gauss(PARAMS["klaviyo_click_rate"] / PARAMS["klaviyo_open_rate"], 0.02))
        
        campaigns_batch.append({
            "id": str(uuid.uuid4()),
            "tenant_id": ONE8_TENANT_ID,
            "connector_id": ONE8_CONNECTOR_ID,
            "external_campaign_id": f"klav_{random.randint(100000, 999999)}",
            "campaign_name": campaign_name,
            "subject": f"{campaign_name} - One8 Lifestyle",
            "sent_at": campaign_date,
            "recipients": recipients,
            "opens": max(0, opens),
            "clicks": max(0, clicks),
            "synced_at": campaign_date,
        })
    
    # Bulk insert campaigns
    if campaigns_batch:
        conn.execute(text("""
            INSERT INTO klaviyo_campaigns (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                subject, sent_at, recipients, opens, clicks, synced_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :subject, :sent_at, :recipients, :opens, :clicks, :synced_at
            )
        """), campaigns_batch)
        conn.commit()
    
    total_recipients = sum(c["recipients"] for c in campaigns_batch)
    total_opens = sum(c["opens"] for c in campaigns_batch)
    total_clicks = sum(c["clicks"] for c in campaigns_batch)
    
    print(f"   ✅ Generated {total_campaigns} campaigns")
    print(f"   📊 Total recipients: {total_recipients:,}")
    print(f"   📧 Total opens: {total_opens:,} ({total_opens/total_recipients*100:.1f}%)")
    print(f"   🖱️  Total clicks: {total_clicks:,} ({total_clicks/total_recipients*100:.1f}%)")


def main():
    """Main seeding workflow."""
    
    print("="*60)
    print("🏏 ONE8 SUPPLEMENTAL DATA SEEDING")
    print("="*60)
    print(f"Tenant ID: {ONE8_TENANT_ID}")
    print(f"Connector ID: {ONE8_CONNECTOR_ID}")
    print("="*60)
    
    with engine.connect() as conn:
        # Verify tenant exists
        tenant = conn.execute(text("""
            SELECT name FROM tenants WHERE id = :tid
        """), {"tid": ONE8_TENANT_ID}).fetchone()
        
        if not tenant:
            print(f"\n❌ ERROR: Tenant {ONE8_TENANT_ID} not found!")
            return
        
        print(f"\n✅ Tenant: {tenant[0]}")
        
        # Verify orders exist
        order_count = conn.execute(text("""
            SELECT COUNT(*) FROM shopify_orders WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID}).scalar()
        
        if order_count == 0:
            print("\n❌ ERROR: No orders found! Run seed_one8_data.py first to seed products and orders.")
            return
        
        print(f"✅ Found {order_count:,} existing orders")
        
        # Generate supplemental data
        generate_refunds(conn, days=90)
        generate_ad_spend(conn, days=90)
        generate_klaviyo_campaigns(conn, weeks=12)
    
    print("\n" + "="*60)
    print("✅ SUPPLEMENTAL DATA SEEDING COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()
