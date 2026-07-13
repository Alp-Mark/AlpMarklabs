#!/usr/bin/env python3
"""Delete today's ONE8 data and regenerate cleanly."""
import sys
import os

# Set Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/worker')

from datetime import date
from sqlalchemy import text, create_engine

# Use PUBLIC database URL for external access
DB_URL = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    print("❌ DATABASE_PUBLIC_URL not set")
    sys.exit(1)

# Transform URL for psycopg v3
if DB_URL.startswith("postgresql://") and "+psycopg" not in DB_URL:
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgresql://"):]
elif DB_URL.startswith("postgres://"):
    DB_URL = "postgresql+psycopg://" + DB_URL[len("postgres://"):]

engine = create_engine(DB_URL, pool_pre_ping=True)

TODAY = date(2026, 7, 13)
TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

print(f"\n{'='*60}")
print(f"🗑️  Deleting ONE8 data from {TODAY}...")
print(f"{'='*60}\n")

try:
    with engine.begin() as conn:
        # Delete in correct order (foreign keys)
        tables = ["shopify_order_line_items", "shopify_orders", "meta_ad_spends", "google_ad_spends"]
        total = 0
        for table in tables:
            result = conn.execute(text(f"""
                DELETE FROM {table}
                WHERE tenant_id = :tid 
                AND DATE(created_at AT TIME ZONE 'UTC') = :date
            """), {"tid": TENANT_ID, "date": TODAY})
            count = result.rowcount
            total += count
            if count > 0:
                print(f"   ✓ Deleted {count:,} {table} records")
        
        if total == 0:
            print("   (No records found)")
except Exception as e:
    print(f"❌ Deletion failed: {e}")
    sys.exit(1)

print(f"\n🔄 Generating fresh demo data...\n")

try:
    from worker.app.tasks_demo_data import run_demo_data_generation
    result = run_demo_data_generation()
    
    print(f"✅ Demo data generated!\n")
    print(f"   📦 Orders:        {result['orders_created']:,}")
    print(f"   📋 Line items:    {result['line_items_created']:,}")
    print(f"   💰 Ad spend:      {result['ad_spend_records']:,}")
    print(f"   📊 Snapshots:     {len(result['snapshots_updated'])}")
    
    if result['ad_spend_records'] == 0:
        print(f"\n⚠️  Ad spend = 0 (unexpected)")
    else:
        print(f"\n✅ SUCCESS!")
        
except Exception as e:
    print(f"❌ Generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*60}\n")
