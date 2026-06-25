"""Check tenant mappings for both users."""

from sqlalchemy import create_engine, text

# Railway database URL
DATABASE_URL = "postgresql://postgres:sVlAqXfHqRANxxSPsBOBbhceeONfWXEe@thomas.proxy.rlwy.net:38395/railway"

engine = create_engine(DATABASE_URL)

USERS_TO_CHECK = [
    "owner@one8commune.com",
    "sudeeppemmaraju@gmail.com"
]

print("=" * 70)
print("CHECKING USER TENANT MAPPINGS")
print("=" * 70)

with engine.connect() as conn:
    for email in USERS_TO_CHECK:
        print(f"\n{'='*70}")
        print(f"📧 {email}")
        print(f"{'='*70}")
        
        # Check if user exists
        user = conn.execute(text("""
            SELECT id, email FROM users WHERE email = :email
        """), {"email": email}).fetchone()
        
        if not user:
            print("❌ User does NOT exist in database")
            continue
        
        user_id = user[0]
        
        print("✅ User exists")
        print(f"   User ID: {user_id}")
        
        # Check tenant memberships
        memberships = conn.execute(text("""
            SELECT 
                tm.tenant_id, 
                t.name as tenant_name,
                tm.role as membership_role,
                r.name as role_name
            FROM tenant_memberships tm
            JOIN tenants t ON tm.tenant_id = t.id
            LEFT JOIN roles r ON tm.role_id = r.id
            WHERE tm.user_id = :user_id
        """), {"user_id": user_id}).fetchall()
        
        if not memberships:
            print("\n⚠️  NO TENANT MEMBERSHIPS found")
        else:
            print(f"\n📋 Tenant Memberships ({len(memberships)}):")
            for tenant_id, tenant_name, membership_role, role_name in memberships:
                print(f"\n   Tenant: {tenant_name}")
                print(f"   Tenant ID: {tenant_id}")
                print(f"   Role (string): {membership_role}")
                print(f"   Role (FK): {role_name or 'None'}")
                
                # Check data counts for this tenant
                order_count = conn.execute(text("""
                    SELECT COUNT(*) FROM shopify_orders WHERE tenant_id = :tenant_id
                """), {"tenant_id": tenant_id}).scalar()
                
                print(f"   📊 Data: {order_count:,} orders")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
