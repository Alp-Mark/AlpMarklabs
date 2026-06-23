#!/usr/bin/env python3
"""
Verify One8 seeded data in the database.
"""

import os
from sqlalchemy import create_engine, text

# One8 tenant ID
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Database connection
DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL environment variable not set")

engine = create_engine(DATABASE_URL)

print("="*60)
print("🏏 ONE8 DATA VERIFICATION")
print("="*60)
print(f"Tenant ID: {ONE8_TENANT_ID}")
print("="*60)

with engine.connect() as conn:
    # Check tenant
    tenant = conn.execute(text("""
        SELECT name, created_at FROM tenants WHERE id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    
    if tenant:
        print(f"\n✅ Tenant: {tenant[0]} (created: {tenant[1]})")
    else:
        print(f"\n❌ Tenant not found!")
        exit(1)
    
    # Check connector
    connector = conn.execute(text("""
        SELECT id, source, status FROM connector_integrations 
        WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    
    if connector:
        print(f"✅ Connector: {connector[1]} - {connector[2]}")
    else:
        print(f"❌ No connector found!")
    
    # Check products
    products = conn.execute(text("""
        SELECT COUNT(*) FROM shopify_inventory_items 
        WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).scalar()
    print(f"✅ Products: {products:,}")
    
    # Check orders
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue,
            MIN(order_created_at) as earliest_order,
            MAX(order_created_at) as latest_order
        FROM shopify_orders 
        WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID}).fetchone()
    
    if result and result[0] > 0:
        print(f"✅ Orders: {result[0]:,}")
        print(f"   💰 Revenue: ₹{result[1]:,.2f}")
        print(f"   📅 Date range: {result[2].date()} to {result[3].date()}")
    else:
        print(f"❌ No orders found!")
    
    # Check what tables exist
    print(f"\n📋 Checking optional data tables...")
    
    tables_to_check = [
        "shopify_refunds",
        "meta_ad_spends", 
        "google_ad_spends",
        "klaviyo_campaigns"
    ]
    
    for table in tables_to_check:
        try:
            count = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid
            """), {"tid": ONE8_TENANT_ID}).scalar()
            print(f"   ✅ {table}: {count:,} records")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"   ⚠️  {table}: table does not exist")
            else:
                print(f"   ❌ {table}: error - {e}")

print("\n" + "="*60)
print("✅ VERIFICATION COMPLETE")
print("="*60)
