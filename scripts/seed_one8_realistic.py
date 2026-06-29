#!/usr/bin/env python3
"""
Seed One8 tenant with REALISTIC data patterns.

Virat Kohli's One8 brand - premium Indian lifestyle products.
Includes:
- Cricket season seasonality (IPL, World Cup)
- Festival peaks (Diwali, New Year)
- Weekend spikes
- Launch campaigns with diminishing returns
- Realistic spend-to-conversion correlation
- Day-to-day variance

Usage:
    railway run python3 scripts/seed_one8_realistic.py
"""

import json
import math
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text

# One8 tenant ID
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Realistic baseline parameters for One8 (premium brand)
BASELINE = {
    "base_daily_orders": 200,  # Normal weekday baseline
    "base_aov": 6500,  # INR - premium apparel/footwear
    "aov_std_dev": 2500,
    "base_meta_spend": 180000,  # INR/day
    "base_google_spend": 110000,  # INR/day
    "base_cac": 850,  # Cost per acquisition baseline
    "return_rate": 0.12,
}


def get_seasonality_multiplier(date):
    """
    Get seasonality multiplier for a given date.
    
    Real One8 patterns:
    - IPL season (Mar-May): 1.5x sales
    - World Cup / Cricket season (Oct-Nov): 1.4x sales  
    - Diwali (late Oct/early Nov): 2.0x peak
    - New Year (late Dec/early Jan): 1.3x
    - Valentine's (Feb 14): 1.2x
    - Summer lull (June-Aug): 0.85x
    - Normal months: 1.0x
    """
    month = date.month
    day = date.day
    
    # Diwali peak (Oct 24-Nov 15 typically)
    if month == 10 and day >= 24 or month == 11 and day <= 15:
        # Peak on Diwali day (Nov 1 ± 5 days), 2.0x at peak
        diwali_center = datetime(date.year, 11, 1)
        days_from_diwali = abs((date - diwali_center).days)
        if days_from_diwali <= 3:
            return 2.0
        elif days_from_diwali <= 10:
            return 1.6
        else:
            return 1.3
    
    # IPL season (March-May) - cricket hype
    if month in [3, 4, 5]:
        return 1.5
    
    # World Cup / Cricket season (Oct-Nov) - already covered by Diwali
    # but early October before Diwali
    if month == 10 and day < 24:
        return 1.4
    
    # New Year season (Dec 20 - Jan 10)
    if (month == 12 and day >= 20) or (month == 1 and day <= 10):
        return 1.3
    
    # Valentine's Day (Feb 10-15)
    if month == 2 and 10 <= day <= 15:
        return 1.2
    
    # Summer lull (June-August) - slower period
    if month in [6, 7, 8]:
        return 0.85
    
    # Normal months
    return 1.0


def get_weekend_multiplier(date):
    """Weekend spike - people shop more on Fri-Sun."""
    weekday = date.weekday()
    
    if weekday == 4:  # Friday
        return 1.25
    elif weekday == 5:  # Saturday
        return 1.4
    elif weekday == 6:  # Sunday
        return 1.35
    else:  # Monday-Thursday
        return 1.0


def calculate_conversions_from_spend(meta_spend, google_spend, base_cac, date):
    """
    Calculate realistic conversions using saturation curve.
    
    Hill curve saturation: conversions = (spend^n) / (k^n + spend^n)
    where:
    - n = saturation exponent (how quickly diminishing returns kick in)
    - k = half-saturation point (spend needed to reach 50% of max)
    
    This creates realistic patterns:
    - Low spend: linear returns
    - Medium spend: good ROI
    - High spend: diminishing returns (saturation)
    """
    total_spend = meta_spend + google_spend
    
    # Hill curve parameters (tuned for realistic One8 behavior)
    max_daily_conversions = 600  # Physical max capacity
    half_saturation_spend = 350000  # ₹3.5L spend → 50% of max conversions
    saturation_exponent = 1.8  # How steep the diminishing returns
    
    # Hill curve formula
    spend_power = total_spend ** saturation_exponent
    k_power = half_saturation_spend ** saturation_exponent
    saturation_conversions = max_daily_conversions * (spend_power / (k_power + spend_power))
    
    # Add realistic noise (±10%)
    noise = random.uniform(0.9, 1.1)
    conversions = int(saturation_conversions * noise)
    
    # Apply seasonality and weekend effects
    season_mult = get_seasonality_multiplier(date)
    weekend_mult = get_weekend_multiplier(date)
    
    conversions = int(conversions * season_mult * weekend_mult)
    
    return max(0, conversions)


def generate_realistic_spend_pattern(base_spend, date, days_in_range, current_day_offset):
    """
    Generate realistic ad spend with variance and campaign patterns.
    
    Patterns:
    - Normal days: ±20% variance around baseline
    - Campaign bursts: 2-3 week periods with 1.8x spend
    - Budget cuts: occasional 1 week periods with 0.6x spend
    - Gradual budget increases over time (brand growth)
    """
    # Growth trend: 5% increase over 90 days
    growth_factor = 1.0 + (current_day_offset / days_in_range) * 0.05
    
    # Campaign burst pattern (simulate new collection launches)
    # Happens every ~40 days for 2 weeks
    campaign_cycle_day = current_day_offset % 40
    if 5 <= campaign_cycle_day <= 18:  # 2-week campaign burst
        campaign_mult = 1.8
    elif campaign_cycle_day <= 25:  # Wind-down week
        campaign_mult = 1.2
    else:
        campaign_mult = 1.0
    
    # Random daily variance (realistic fluctuations)
    daily_variance = random.uniform(0.85, 1.15)
    
    # Weekend optimization: reduce spend slightly on weekends (better organic traffic)
    if date.weekday() in [5, 6]:  # Sat-Sun
        weekend_mult = 0.9
    else:
        weekend_mult = 1.0
    
    # Combine all factors
    final_spend = base_spend * growth_factor * campaign_mult * daily_variance * weekend_mult
    
    return int(final_spend)


def seed_realistic_data(days=90):
    """Seed One8 with realistic data patterns."""
    
    # Connect to database (Railway production by default)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set. Run with: railway run python3 scripts/seed_one8_realistic.py")
        sys.exit(1)
    
    engine = create_engine(db_url)
    
    print("=" * 70)
    print("🏏 Seeding One8 (Virat Kohli Brand) - REALISTIC DATA")
    print("=" * 70)
    print(f"🗄️  Database: Railway Production")
    print(f"Tenant ID: {ONE8_TENANT_ID}")
    print(f"Days: {days}")
    print(f"Date range: {datetime.now().date() - timedelta(days=days)} to {datetime.now().date()}")
    print("")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        # Get connector_id
        connector = conn.execute(text("""
            SELECT id FROM connector_integrations 
            WHERE tenant_id = :tid AND source = 'shopify'
        """), {"tid": ONE8_TENANT_ID}).fetchone()
        
        if not connector:
            print("❌ No Shopify connector found. Run seed_one8_data.py first to create connector.")
            sys.exit(1)
        
        connector_id = connector[0]
        print(f"✅ Using connector: {connector_id}\n")
        
        # Clear ALL existing One8 data (complete wipe)
        print("🗑️  WIPING ALL One8 tenant data...")
        
        # Delete in correct order to avoid FK violations
        tables_to_clear = [
            "shopify_order_line_items",
            "shopify_orders",
            "shopify_refunds",
            "meta_ad_spends",
            "google_ad_spends",
            "klaviyo_campaigns",
            "recommendations",
            "optimization_runs",
            "fitted_models",
            "executive_kpi_snapshots",
            "acquisition_metrics_snapshots",
            "retention_daily_snapshots",
        ]
        
        deleted_counts = {}
        for table in tables_to_clear:
            try:
                result = conn.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                    {"tid": ONE8_TENANT_ID}
                )
                deleted_counts[table] = result.rowcount
                if result.rowcount > 0:
                    print(f"   🗑️  {table}: {result.rowcount:,} rows")
            except Exception as e:
                if "does not exist" in str(e):
                    continue
                else:
                    print(f"   ⚠️  {table}: {e}")
        
        total_deleted = sum(deleted_counts.values())
        print(f"   ✅ Total deleted: {total_deleted:,} rows\n")
        
        # Generate data day by day with realistic patterns
        meta_batch = []
        google_batch = []
        orders_batch = []
        
        end_date = datetime.now()
        
        total_meta_spend = 0
        total_google_spend = 0
        total_orders = 0
        total_revenue = Decimal("0")
        
        print("📊 Generating realistic daily data...")
        print("    Day | Date       | Season Mult | Meta Spend | Google Spend | Orders | Revenue")
        print("    " + "-" * 80)
        
        for day_offset in range(days):
            current_date = end_date - timedelta(days=day_offset)
            
            # Generate realistic spend with patterns
            meta_spend = generate_realistic_spend_pattern(
                BASELINE["base_meta_spend"], current_date, days, day_offset
            )
            google_spend = generate_realistic_spend_pattern(
                BASELINE["base_google_spend"], current_date, days, day_offset
            )
            
            # Calculate conversions from spend (with saturation)
            conversions = calculate_conversions_from_spend(
                meta_spend, google_spend, BASELINE["base_cac"], current_date
            )
            
            # Generate orders for this day
            daily_revenue = Decimal("0")
            for _ in range(conversions):
                # Order value with realistic variance
                order_value = max(
                    1000,  # Min order
                    int(random.gauss(BASELINE["base_aov"], BASELINE["aov_std_dev"]))
                )
                
                order_datetime = current_date.replace(
                    hour=random.randint(0, 23),
                    minute=random.randint(0, 59)
                )
                
                external_order_id = f"ONE8{random.randint(100000, 999999)}"
                
                orders_batch.append({
                    "id": str(uuid.uuid4()),
                    "tenant_id": ONE8_TENANT_ID,
                    "connector_id": connector_id,
                    "external_order_id": external_order_id,
                    "customer_id": f"cust_{random.randint(1000, 99999)}",
                    "order_number": external_order_id,
                    "currency": "INR",
                    "total_amount": float(order_value),
                    "discount_amount": 0.0,
                    "shipping_amount": 0.0,  # Free shipping for premium brand
                    "refund_amount": 0.0,
                    "is_refunded": False,
                    "order_created_at": order_datetime,
                    "synced_at": datetime.utcnow(),
                })
                
                daily_revenue += Decimal(str(order_value))
            
            # Store ad spend (split Meta/Google into campaigns)
            meta_campaigns = ["Acquisition - Broad", "Retargeting", "Collection Launch"]
            for i, campaign in enumerate(meta_campaigns):
                campaign_spend = meta_spend / len(meta_campaigns)
                meta_batch.append({
                    "id": str(uuid.uuid4()),
                    "tenant_id": ONE8_TENANT_ID,
                    "connector_id": connector_id,
                    "external_campaign_id": f"meta_{campaign.replace(' ', '_')}_{current_date.strftime('%Y%m%d')}",
                    "campaign_name": campaign,
                    "spend_date": current_date.date(),
                    "currency": "INR",
                    "spend_amount": float(campaign_spend),
                    "synced_at": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
            
            google_campaigns = ["Search - Brand", "Search - Generic", "Shopping"]
            for campaign in google_campaigns:
                campaign_spend = google_spend / len(google_campaigns)
                google_batch.append({
                    "id": str(uuid.uuid4()),
                    "tenant_id": ONE8_TENANT_ID,
                    "connector_id": connector_id,
                    "external_campaign_id": f"google_{campaign.replace(' ', '_')}_{current_date.strftime('%Y%m%d')}",
                    "campaign_name": campaign,
                    "spend_date": current_date.date(),
                    "currency": "INR",
                    "spend_amount": float(campaign_spend),
                    "synced_at": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
            
            total_meta_spend += meta_spend
            total_google_spend += google_spend
            total_orders += conversions
            total_revenue += daily_revenue
            
            # Print progress every 10 days
            if day_offset % 10 == 0 or day_offset < 5:
                season = get_seasonality_multiplier(current_date)
                print(f"    {day_offset:>3} | {current_date.date()} | {season:>5.2f}x      | "
                      f"₹{meta_spend:>7,.0f}  | ₹{google_spend:>7,.0f}   | {conversions:>4}   | "
                      f"₹{daily_revenue:>9,.0f}")
        
        print("    " + "-" * 80)
        print("")
        
        # Bulk insert
        print("💾 Inserting data into database...")
        
        if meta_batch:
            print(f"   📱 Meta ad spend: {len(meta_batch):,} records...")
            conn.execute(text("""
                INSERT INTO meta_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id, campaign_name,
                    spend_date, currency, spend_amount, synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                    :spend_date, :currency, :spend_amount, :synced_at, :created_at, :updated_at
                )
                ON CONFLICT DO NOTHING
            """), meta_batch)
        
        if google_batch:
            print(f"   🔍 Google ad spend: {len(google_batch):,} records...")
            conn.execute(text("""
                INSERT INTO google_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id, campaign_name,
                    spend_date, currency, spend_amount, synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                    :spend_date, :currency, :spend_amount, :synced_at, :created_at, :updated_at
                )
                ON CONFLICT DO NOTHING
            """), google_batch)
        
        if orders_batch:
            print(f"   🛒 Orders: {len(orders_batch):,} records in batches...")
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
                    ON CONFLICT (tenant_id, connector_id, external_order_id) DO NOTHING
                """), chunk)
        
        # Update connector last_synced_at
        conn.execute(text("""
            UPDATE connector_integrations
            SET last_synced_at = :now
            WHERE id = :cid
        """), {"cid": connector_id, "now": datetime.utcnow()})
        
        # Commit transaction
        trans.commit()
        print("   ✅ All data inserted\n")
        
        # Summary
        print("=" * 70)
        print("✅ SEEDING COMPLETE - REALISTIC DATA")
        print("=" * 70)
        print(f"📊 Total Meta Spend:   ₹{total_meta_spend:>12,.0f}")
        print(f"🔍 Total Google Spend: ₹{total_google_spend:>12,.0f}")
        print(f"💰 Total Spend:        ₹{total_meta_spend + total_google_spend:>12,.0f}")
        print(f"🛒 Total Orders:       {total_orders:>14,}")
        print(f"💵 Total Revenue:      ₹{total_revenue:>12,.0f}")
        print(f"📈 Blended ROAS:       {float(total_revenue) / (total_meta_spend + total_google_spend):>15.2f}x")
        print(f"💳 Avg Order Value:    ₹{float(total_revenue) / total_orders:>12,.0f}")
        print(f"💸 Blended CAC:        ₹{(total_meta_spend + total_google_spend) / total_orders:>12,.0f}")
        print("=" * 70)
        print("")
        print("🎯 Data includes:")
        print("   ✅ Cricket season spikes (IPL Mar-May, World Cup Oct-Nov)")
        print("   ✅ Diwali peak (2x sales)")
        print("   ✅ Weekend patterns (Fri-Sun +25-40%)")
        print("   ✅ Campaign bursts with diminishing returns")
        print("   ✅ Realistic spend-to-conversion saturation curves")
        print("   ✅ Day-to-day variance and noise")
        print("")
        print("🚀 Next: Trigger optimization to fit Hill curves on this data")
        print("   python3 scripts/trigger_railway_optimization.py")
        print("=" * 70)


if __name__ == "__main__":
    seed_realistic_data(days=90)
