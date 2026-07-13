#!/usr/bin/env python3
"""Delete today's ONE8 data cleanly."""
import sys
sys.path.insert(0, '/app/backend')

from datetime import date
from sqlalchemy import create_engine, text
import os

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DB_URL)
TODAY = date(2026, 7, 13)
TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

print(f"🗑️  Deleting ONE8 data from {TODAY}...")

with engine.begin() as conn:
    # Delete in correct order (foreign keys)
    for table in ["shopify_order_line_items", "shopify_orders", "meta_ad_spends", "google_ad_spends"]:
        result = conn.execute(text(f"""
            DELETE FROM {table}
            WHERE tenant_id = :tid 
            AND DATE(created_at AT TIME ZONE 'UTC') = :date
        """), {"tid": TENANT_ID, "date": TODAY})
        print(f"✓ Deleted {result.rowcount:,} {table} records")

print("✅ Done!")
