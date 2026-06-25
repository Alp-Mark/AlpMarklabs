"""Clean up database - keep only One8 tenant with owner@one8commune.com."""

from sqlalchemy import create_engine, text

# Railway database URL
DATABASE_URL = "postgresql://postgres:sVlAqXfHqRANxxSPsBOBbhceeONfWXEe@thomas.proxy.rlwy.net:38395/railway"

engine = create_engine(DATABASE_URL)

KEEP_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"  # One8
KEEP_TENANT_MEMBER = "owner@one8commune.com"  # Only member of One8 tenant
SUPER_ADMIN_EMAIL = "support@alpmarklabs.com"  # Super admin (not a tenant member)

print("=" * 80)
print("🧹 CLEANUP: KEEP ONLY ONE8 TENANT WITH OWNER@ONE8COMMUNE.COM")
print("=" * 80)

with engine.connect() as conn:
    # Get the user ID for owner@one8commune.com
    user = conn.execute(text("""
        SELECT id FROM users WHERE email = :email
    """), {"email": KEEP_TENANT_MEMBER}).fetchone()
    
    if not user:
        print(f"❌ User {KEEP_TENANT_MEMBER} not found!")
        exit(1)
    
    keep_user_id = str(user[0])
    print(f"\n✅ Found tenant member: {KEEP_TENANT_MEMBER}")
    print(f"   User ID: {keep_user_id}")
    
    # Verify super admin exists (but we won't add them to tenant)
    super_admin = conn.execute(text("""
        SELECT id FROM users WHERE email = :email
    """), {"email": SUPER_ADMIN_EMAIL}).fetchone()
    
    if super_admin:
        print(f"\n👑 Super admin exists: {SUPER_ADMIN_EMAIL}")
        print(f"   User ID: {super_admin[0]}")
        print("   (Will NOT be added to tenant - super admin accesses all tenants)")
    else:
        print(f"\n⚠️  Super admin {SUPER_ADMIN_EMAIL} not found in database!")
    
    # Verify One8 tenant exists
    tenant = conn.execute(text("""
        SELECT id, name FROM tenants WHERE id = :tenant_id
    """), {"tenant_id": KEEP_TENANT_ID}).fetchone()
    
    if not tenant:
        print(f"❌ One8 tenant {KEEP_TENANT_ID} not found!")
        exit(1)
    
    print(f"\n✅ Found tenant: {tenant[1]}")
    print(f"   Tenant ID: {KEEP_TENANT_ID}")
    
    # Count what we're about to delete
    print("\n" + "=" * 80)
    print("📊 CURRENT STATE")
    print("=" * 80)
    
    total_tenants = conn.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
    total_memberships = conn.execute(text("SELECT COUNT(*) FROM tenant_memberships")).scalar()
    
    print(f"\nTotal tenants: {total_tenants}")
    print(f"Total tenant memberships: {total_memberships}")
    
    # List all tenants
    all_tenants = conn.execute(text("""
        SELECT id, name, created_at FROM tenants ORDER BY created_at
    """)).fetchall()
    
    print("\n📋 All tenants:")
    for tid, name, created_at in all_tenants:
        marker = "✅ KEEP" if str(tid) == KEEP_TENANT_ID else "❌ DELETE"
        print(f"   {marker} {name} ({tid})")
    
    # List all memberships for One8
    one8_memberships = conn.execute(text("""
        SELECT tm.id, u.email, tm.role
        FROM tenant_memberships tm
        JOIN users u ON tm.user_id = u.id
        WHERE tm.tenant_id = :tenant_id
    """), {"tenant_id": KEEP_TENANT_ID}).fetchall()
    
    print("\n📋 One8 tenant memberships:")
    for mid, email, role in one8_memberships:
        marker = "✅ KEEP" if email == KEEP_TENANT_MEMBER else "❌ DELETE"
        print(f"   {marker} {email} - {role}")
    
    # Confirm deletion
    print("\n" + "=" * 80)
    print("⚠️  WARNING: THIS WILL DELETE")
    print("=" * 80)
    tenants_to_delete = total_tenants - 1
    one8_memberships_to_delete = len(one8_memberships) - 1
    other_tenant_memberships = total_memberships - len(one8_memberships)
    
    print(f"\n   • {tenants_to_delete} tenant(s) (all except One8)")
    print(f"   • {one8_memberships_to_delete} One8 membership(s) (keep only owner@one8commune.com)")
    print(f"   • {other_tenant_memberships} membership(s) from other tenants")
    print("   • All data (orders, products, etc.) from deleted tenants")
    print(f"\n   ✅ WILL KEEP: {KEEP_TENANT_MEMBER} on One8 tenant")
    print(f"   👑 WILL KEEP: {SUPER_ADMIN_EMAIL} as super admin (not tenant member)")
    
    print("\n" + "=" * 80)
    response = input("Type 'DELETE' to proceed: ")
    
    if response != "DELETE":
        print("\n❌ Cancelled")
        exit(0)
    
    print("\n" + "=" * 80)
    print("🗑️  DELETING...")
    print("=" * 80)
    
    # Step 1: Delete all tenant_memberships EXCEPT owner@one8commune.com on One8
    print("\n1️⃣ Deleting unwanted tenant memberships...")
    deleted_memberships = conn.execute(text("""
        DELETE FROM tenant_memberships 
        WHERE NOT (tenant_id = :tenant_id AND user_id = :user_id)
        RETURNING id
    """), {
        "tenant_id": KEEP_TENANT_ID,
        "user_id": keep_user_id
    }).rowcount
    
    print(f"   ✅ Deleted {deleted_memberships} membership(s)")
    
    # Step 2: Delete data from other tenants
    # Query all tables with tenant_id column and delete from other tenants
    
    print("\n2️⃣ Finding all tables with tenant_id column...")
    
    tables_with_tenant_id = conn.execute(text("""
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
        AND table_schema = 'public'
        AND table_name != 'tenants'
        ORDER BY table_name
    """)).fetchall()
    
    table_names = [row[0] for row in tables_with_tenant_id]
    print(f"   Found {len(table_names)} tables with tenant_id")
    
    print("\n3️⃣ Deleting data from other tenants...")
    total_deleted = 0
    
    for table_name in table_names:
        try:
            deleted = conn.execute(text(f"""
                DELETE FROM {table_name} WHERE tenant_id != :tenant_id
            """), {"tenant_id": KEEP_TENANT_ID}).rowcount
            
            if deleted > 0:
                print(f"   ✅ Deleted {deleted} row(s) from {table_name}")
                total_deleted += deleted
        except Exception as e:
            print(f"   ⚠️  Skipped {table_name}: {str(e)[:80]}")
    
    print(f"\n   Total rows deleted: {total_deleted}")
    
    # Step 3: Delete other tenants
    print("\n4️⃣ Deleting other tenants...")
    deleted_tenants = conn.execute(text("""
        DELETE FROM tenants WHERE id != :tenant_id RETURNING id
    """), {"tenant_id": KEEP_TENANT_ID}).rowcount
    
    print(f"   ✅ Deleted {deleted_tenants} tenant(s)")
    
    # Commit all changes
    conn.commit()
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE")
    print("=" * 80)
    
    # Verify final state
    final_tenants = conn.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
    final_memberships = conn.execute(text("SELECT COUNT(*) FROM tenant_memberships")).scalar()
    final_orders = conn.execute(text("SELECT COUNT(*) FROM shopify_orders")).scalar()
    
    print("\n📊 Final state:")
    print(f"   Tenants: {final_tenants} (should be 1)")
    print(f"   Memberships: {final_memberships} (should be 1)")
    print(f"   Orders: {final_orders:,}")
    
    print("\n✅ Cleanup complete!")
    print(f"   One8 tenant: {KEEP_TENANT_MEMBER}")
    print(f"   Super admin: {SUPER_ADMIN_EMAIL} (can access all tenants)")
    print("=" * 80)
