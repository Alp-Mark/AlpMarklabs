#!/usr/bin/env python3
"""Check what tables exist in the database."""

import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL not set")

engine = create_engine(DATABASE_URL)

print("="*60)
print("📋 DATABASE TABLES CHECK")
print("="*60)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename
    """))
    
    tables = [row[0] for row in result]
    
    # Check for specific tables
    search_for = ['meta_ad_spends', 'google_ad_spends', 'shopify_refunds', 'klaviyo_campaigns']
    
    print("\n🔍 Looking for these tables:")
    for table in search_for:
        exists = table in tables
        status = "✅" if exists else "❌"
        print(f"   {status} {table}")
    
    print(f"\n📊 Total tables in database: {len(tables)}")
    print("\nAll tables:")
    for table in tables:
        print(f"   - {table}")

print("\n" + "="*60)
