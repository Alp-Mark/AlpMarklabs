#!/usr/bin/env python3
"""
One-time script to cleanly regenerate demo data for today (2026-07-13).

Usage:
    railway run python3 scripts/regenerate_today.py

After this runs once, Celery will auto-generate data every 6 hours.
You won't need to run this again.
"""

import os
import sys
from datetime import date
from sqlalchemy import create_engine, text

# Must have DATABASE_URL from Railway
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("❌ DATABASE_URL not set.")
    print("   Run via: railway run python3 scripts/regenerate_today.py")
    sys.exit(1)

# Import after DB_URL check
from worker.app.tasks_demo_data import run_demo_data_generation

TODAY = date(2026, 7, 13)
TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

engine = create_engine(DB_URL, pool_pre_ping=True, connect_args={"connect_timeout": 10})

print(f"\n{'='*60}")
print(f"🔄 Regenerating demo data for {TODAY}")
print(f"{'='*60}\n")

# Step 1: Delete incomplete/stale today data
print(f"🗑️  Removing incomplete records from {TODAY}...\n")
try:
    with engine.begin() as conn:
        tables_to_clean = [
            "shopify_order_line_items",
            "shopify_orders",
            "meta_ad_spends",
            "google_ad_spends",
        ]
        
        total_deleted = 0
        for table in tables_to_clean:
            # Delete only ONE8 tenant data from today
            result = conn.execute(text(f"""
                DELETE FROM {table}
                WHERE tenant_id = :tid 
                AND DATE(created_at AT TIME ZONE 'UTC') = :date
            """), {"tid": TENANT_ID, "date": TODAY})
            
            deleted_count = result.rowcount
            total_deleted += deleted_count
            if deleted_count > 0:
                print(f"   ✓ Deleted {deleted_count:,} {table} records")
        
        if total_deleted == 0:
            print(f"   (No records found to delete)")
except Exception as e:
    print(f"❌ Cleanup failed: {e}")
    sys.exit(1)

# Step 2: Generate fresh data
print(f"\n🔄 Generating fresh demo data...\n")
try:
    result = run_demo_data_generation()
    
    print(f"✅ Demo data generated successfully!\n")
    print(f"   📦 Orders created:        {result['orders_created']:,}")
    print(f"   📋 Line items created:    {result['line_items_created']:,}")
    print(f"   💰 Ad spend records:      {result['ad_spend_records']:,}")
    print(f"   📊 Snapshots updated:     {len(result['snapshots_updated'])}")
    
    if result['ad_spend_records'] > 0:
        print(f"\n✅ SUCCESS! Ad spend is now being generated.")
    else:
        print(f"\n⚠️  WARNING: Ad spend records = 0 (check logs)")
        
except Exception as e:
    print(f"❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*60}")
print(f"✅ Done! Celery will auto-generate data every 6 hours.")
print(f"   You don't need to run this again.")
print(f"{'='*60}\n")
