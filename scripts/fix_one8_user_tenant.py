#!/usr/bin/env python3
"""
Fix owner@one8commune.com to point to the correct One8 tenant with seeded data.
"""

import os
from sqlalchemy import create_engine, text

# The correct One8 tenant with seeded data
CORRECT_ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"
WRONG_TENANT_ID = "bd51a725-febd-4411-a7c4-3ae7afa08068"
ONE8_USER_EMAIL = "owner@one8commune.com"

DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL not set")

engine = create_engine(DATABASE_URL)

print("="*60)
print("🔧 FIXING ONE8 USER → TENANT MAPPING")
print("="*60)

with engine.connect() as conn:
    # Verify the user exists
    user = conn.execute(text("""
        SELECT id, email FROM users WHERE email = :email
    """), {"email": ONE8_USER_EMAIL}).fetchone()
    
    if not user:
        print(f"❌ User {ONE8_USER_EMAIL} not found!")
        exit(1)
    
    user_id = user[0]
    
    print(f"\n👤 User: {user[1]}")
    print(f"   User ID: {user_id}")
    
    # Check current memberships
    current_memberships = conn.execute(text("""
        SELECT tm.tenant_id, t.name
        FROM tenant_memberships tm
        JOIN tenants t ON tm.tenant_id = t.id
        WHERE tm.user_id = :user_id
    """), {"user_id": user_id}).fetchall()
    
    print(f"\n📋 Current memberships:")
    has_correct_tenant = False
    has_wrong_tenant = False
    for tenant_id, tenant_name in current_memberships:
        tenant_id_str = str(tenant_id)
        if tenant_id_str == CORRECT_ONE8_TENANT_ID:
            has_correct_tenant = True
            print(f"   ✅ {tenant_name} ({tenant_id}) - CORRECT")
        elif tenant_id_str == WRONG_TENANT_ID:
            has_wrong_tenant = True
            print(f"   ❌ {tenant_name} ({tenant_id}) - WRONG (will remove)")
        else:
            print(f"   ⚪ {tenant_name} ({tenant_id})")
    
    if has_correct_tenant and not has_wrong_tenant:
        print("\n✅ Already correctly configured!")
    else:
        # Remove membership from wrong tenant if it exists
        if has_wrong_tenant:
            print(f"\n🗑️  Removing membership from wrong tenant...")
            conn.execute(text("""
                DELETE FROM tenant_memberships 
                WHERE user_id = :user_id AND tenant_id = :wrong_tenant_id
            """), {
                "user_id": user_id,
                "wrong_tenant_id": WRONG_TENANT_ID
            })
        
        # Add membership to correct tenant if not exists
        if not has_correct_tenant:
            # Get executive_owner role
            role = conn.execute(text("""
                SELECT id FROM roles WHERE name = 'executive_owner'
            """)).fetchone()
            
            if role:
                print(f"➕ Creating membership in correct tenant with executive_owner role...")
                conn.execute(text("""
                    INSERT INTO tenant_memberships (id, tenant_id, user_id, role, role_id, created_at)
                    VALUES (gen_random_uuid(), :tenant_id, :user_id, 'executive_owner', :role_id, NOW())
                """), {
                    "tenant_id": CORRECT_ONE8_TENANT_ID,
                    "user_id": user_id,
                    "role_id": role[0]
                })
            else:
                print("⚠️  executive_owner role not found, membership not created")
        
        conn.commit()
        print("\n✅ Memberships updated successfully!")
    
    # Verify the fix
    print("\n📊 Verification:")
    memberships = conn.execute(text("""
        SELECT tm.tenant_id, t.name, r.name as role_name
        FROM tenant_memberships tm
        JOIN tenants t ON tm.tenant_id = t.id
        LEFT JOIN roles r ON tm.role_id = r.id
        WHERE tm.user_id = :user_id
    """), {"user_id": user_id}).fetchall()
    
    print(f"   Final memberships for {ONE8_USER_EMAIL}:")
    for tenant_id, tenant_name, role_name in memberships:
        marker = "✅" if str(tenant_id) == CORRECT_ONE8_TENANT_ID else "⚪"
        print(f"     {marker} {tenant_name} ({tenant_id}) - {role_name}")

print("\n" + "="*60)
print("✅ FIX COMPLETE")
print("="*60)
print("\n💡 Next steps:")
print("   1. Log out and log back in on the frontend")
print("   2. The dashboard should now show ₹261M revenue!")
print("="*60)
