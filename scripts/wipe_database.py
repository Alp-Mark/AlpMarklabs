#!/usr/bin/env python3
"""
Clean all user data from the Railway PostgreSQL database.

This script deletes all tenants and users EXCEPT the super admin account
(support@alpmarklabs.com). The database schema remains intact.

Usage:
    railway run python3 scripts/wipe_database.py
"""

import os
import sys
from pathlib import Path

# Add backend to path so we can import from app
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text


def clean_database():
    """Delete all tenant and user data except super admin."""
    
    # Get database URL from environment (Railway provides this)
    # Try public URL first (for local execution), fall back to internal URL
    database_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not found")
        print("   Run this script with: railway run python3 scripts/wipe_database.py")
        sys.exit(1)
    
    print(f"🔌 Connecting to database...")
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("\n⚠️  WARNING: This will DELETE ALL USER DATA!")
            print("   - All tenants will be deleted")
            print("   - All users except support@alpmarklabs.com will be deleted")
            print("   - All tenant-related data will be permanently deleted")
            print("   - Super admin (support@alpmarklabs.com) will be preserved")
            
            # Count current data
            tenant_count = conn.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
            user_count = conn.execute(text("SELECT COUNT(*) FROM users WHERE email != 'support@alpmarklabs.com'")).scalar()
            
            print(f"\n📊 Current data:")
            print(f"   - Tenants: {tenant_count}")
            print(f"   - Users (excluding super admin): {user_count}")
            
            # Get all table names from the database
            tables_query = text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT IN ('alembic_version', 'users', 'subscription_plans', 'feature_flags')
                ORDER BY tablename
            """)
            all_tables = [row[0] for row in conn.execute(tables_query)]
            
            print(f"\n🗑️  Clearing {len(all_tables)} tables...")
            total_deleted = 0
            
            # Try to delete from all tables, handling foreign key constraints
            # Keep trying until no more rows can be deleted
            max_iterations = 10
            iteration = 0
            
            while all_tables and iteration < max_iterations:
                iteration += 1
                tables_still_referenced = []
                
                for table in all_tables:
                    try:
                        result = conn.execute(text(f"DELETE FROM {table}"))
                        conn.commit()
                        if result.rowcount > 0:
                            print(f"   ✅ {table}: {result.rowcount} rows")
                            total_deleted += result.rowcount
                    except Exception as e:
                        conn.rollback()
                        # If foreign key constraint, try again later
                        if "ForeignKeyViolation" in str(e) or "violates foreign key constraint" in str(e):
                            tables_still_referenced.append(table)
                        elif "does not exist" not in str(e) and "UndefinedTable" not in str(e):
                            print(f"   ⚠️  {table}: {str(e)[:80]}...")
                
                # Update the list with tables that still have foreign key issues
                if len(tables_still_referenced) == len(all_tables):
                    # No progress made, break to avoid infinite loop
                    print(f"   ⚠️  Could not delete from {len(tables_still_referenced)} tables due to circular references")
                    break
                all_tables = tables_still_referenced
            
            print(f"   Total rows deleted: {total_deleted}")
            
            # Now try to delete tenants one more time
            print("\n🗑️  Deleting all tenants...")
            result = conn.execute(text("DELETE FROM tenants"))
            conn.commit()
            print(f"   ✅ Deleted {result.rowcount} tenants (and all related data)")
            
            # Delete all users except super admin
            print("\n🗑️  Deleting all users except super admin...")
            result = conn.execute(text("DELETE FROM users WHERE email != 'support@alpmarklabs.com'"))
            conn.commit()
            print(f"   ✅ Deleted {result.rowcount} users")
            
            # Verify super admin still exists
            super_admin = conn.execute(text("SELECT email, is_platform_admin FROM users WHERE email = 'support@alpmarklabs.com'")).fetchone()
            
            if super_admin:
                print(f"\n✅ Super admin preserved:")
                print(f"   - Email: {super_admin[0]}")
                print(f"   - Platform Admin: {super_admin[1]}")
            else:
                print("\n⚠️  WARNING: Super admin account not found!")
                print("   You may need to recreate it manually.")
        
        print("\n✅ Database cleaned successfully!")
        print("\n📋 Current state:")
        print("   - Schema: intact")
        print("   - Migrations: intact")
        print("   - Super admin: preserved")
        print("   - All other data: deleted")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to clean database")
        print(f"   {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clean_database()
