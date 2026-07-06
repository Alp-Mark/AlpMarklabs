#!/usr/bin/env python3
"""Verify One8 realistic data seeding results on Railway."""
import os
from sqlalchemy import create_engine, text

ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("❌ DATABASE_URL not set")
    raise SystemExit(1)

engine = create_engine(db_url)

with engine.connect() as conn:
    orders = conn.execute(text("""
        SELECT COUNT(*), MIN(order_created_at)::date, MAX(order_created_at)::date,
               SUM(total_amount), AVG(total_amount)
        FROM shopify_orders WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()

    meta = conn.execute(text("""
        SELECT COUNT(*), MIN(spend_date), MAX(spend_date), SUM(spend_amount)
        FROM meta_ad_spends WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()

    google = conn.execute(text("""
        SELECT COUNT(*), MIN(spend_date), MAX(spend_date), SUM(spend_amount)
        FROM google_ad_spends WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()

    # Check date spread (should be ~90 distinct days)
    distinct_days = conn.execute(text("""
        SELECT COUNT(DISTINCT order_created_at::date)
        FROM shopify_orders WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).scalar()

print("=" * 60)
print("📊 ONE8 DATA VERIFICATION")
print("=" * 60)
print(f"🛒 Orders:         {orders[0]:,} rows")
print(f"   Date range:     {orders[1]} → {orders[2]}")
print(f"   Distinct days:  {distinct_days}")
print(f"   Total revenue:  ₹{orders[3]:,.0f}" if orders[3] else "   Total revenue:  ₹0")
print(f"   Avg order:      ₹{orders[4]:,.0f}" if orders[4] else "   Avg order:      ₹0")
print()
print(f"📱 Meta ad spend:  {meta[0]:,} rows")
print(f"   Date range:     {meta[1]} → {meta[2]}")
print(f"   Total spend:    ₹{meta[3]:,.0f}" if meta[3] else "   Total spend:    ₹0")
print()
print(f"🔍 Google ad spend:{google[0]:,} rows")
print(f"   Date range:     {google[1]} → {google[2]}")
print(f"   Total spend:    ₹{google[3]:,.0f}" if google[3] else "   Total spend:    ₹0")
print("=" * 60)

if orders[0] == 0:
    print("❌ NO DATA INSERTED - seeding did not work!")
elif distinct_days < 80:
    print(f"⚠️  Only {distinct_days} distinct days — expected ~90")
else:
    print(f"✅ SEEDING CONFIRMED - {distinct_days} days of data looks good!")
