"""
Fix one8commune tenant to have only owner@one8commune.com as executive owner.
Removes sudeeppemmaraju@gmail.com and cleans up audit events.
"""
import os
import sys
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.db.models import User, TenantMembership, Tenant, AuditEvent

# Connect to database
db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
if not db_url:
    print("ERROR: DATABASE_URL or DATABASE_PUBLIC_URL environment variable not set")
    sys.exit(1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Find the one8commune tenant
    tenant = db.scalar(select(Tenant).where(Tenant.slug == '18'))
    if not tenant:
        print("ERROR: one8commune tenant not found")
        sys.exit(1)
    
    print(f"Found tenant: {tenant.name} (ID: {tenant.id})")
    print(f"Tenant status: {tenant.status}\n")
    
    # Find owner@one8commune.com user
    owner_user = db.scalar(select(User).where(User.email == 'owner@one8commune.com'))
    if not owner_user:
        print("ERROR: owner@one8commune.com user not found")
        print("You need to create this user first")
        sys.exit(1)
    
    print(f"Found owner user: {owner_user.email} (ID: {owner_user.id})")
    
    # Find sudeep user
    sudeep_user = db.scalar(select(User).where(User.email == 'sudeeppemmaraju@gmail.com'))
    
    # Get current members
    members = db.scalars(
        select(TenantMembership)
        .where(TenantMembership.tenant_id == tenant.id)
    ).all()
    
    print(f"\nCurrent members ({len(members)}):")
    for m in members:
        user = db.scalar(select(User).where(User.id == m.user_id))
        if user:
            print(f"  - {user.email} (role: {m.role})")
    
    # Check if owner@one8commune.com is already a member with executive_owner role
    owner_membership = db.scalar(
        select(TenantMembership)
        .where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == owner_user.id
        )
    )
    
    if owner_membership:
        if owner_membership.role != 'executive_owner':
            print(f"\nUpdating {owner_user.email} role to executive_owner...")
            owner_membership.role = 'executive_owner'
        else:
            print(f"\n{owner_user.email} is already executive_owner")
    else:
        print(f"\nAdding {owner_user.email} as executive_owner...")
        new_membership = TenantMembership(
            tenant_id=tenant.id,
            user_id=owner_user.id,
            role='executive_owner'
        )
        db.add(new_membership)
    
    # Remove sudeep if they exist
    if sudeep_user:
        print(f"\nRemoving {sudeep_user.email} from tenant...")
        db.execute(
            delete(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant.id,
                TenantMembership.user_id == sudeep_user.id
            )
        )
        
        # Clean up audit events created by sudeep
        print(f"Cleaning up audit events for {sudeep_user.email}...")
        deleted_count = db.execute(
            delete(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant.id,
                AuditEvent.actor_user_id == sudeep_user.id
            )
        ).rowcount
        print(f"  Deleted {deleted_count} audit events")
    
    # Commit changes
    db.commit()
    
    print("\n✅ SUCCESS!")
    print(f"\nFinal members for {tenant.name}:")
    members = db.scalars(
        select(TenantMembership)
        .where(TenantMembership.tenant_id == tenant.id)
    ).all()
    for m in members:
        user = db.scalar(select(User).where(User.id == m.user_id))
        if user:
            print(f"  - {user.email} (role: {m.role})")

finally:
    db.close()
