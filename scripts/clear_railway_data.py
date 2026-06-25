"""Clear all seeded data from Railway database.

Run this to reset the database before letting Replit build the UI from scratch.
This keeps the schema (tables/migrations) but removes all data.

Usage:
    DATABASE_URL="your-railway-url" python3 scripts/clear_railway_data.py
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.app.db.session import SessionLocal
from sqlalchemy import text


def clear_all_data():
    """Delete all data from all tables (keeps schema intact)."""
    db = SessionLocal()
    try:
        print("Clearing all data from Railway database...")
        
        # Get all table names
        result = db.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename != 'alembic_version'
            ORDER BY tablename
        """))
        
        tables = [row[0] for row in result]
        
        # Disable triggers and foreign key checks
        db.execute(text("SET session_replication_role = 'replica';"))
        
        # Delete from all tables
        for table in tables:
            print(f"  Deleting from {table}...")
            db.execute(text(f"DELETE FROM {table}"))
        
        # Re-enable triggers and foreign key checks
        db.execute(text("SET session_replication_role = 'origin';"))
        
        db.commit()
        print("\n✅ All data cleared successfully!")
        print("   Schema (tables/migrations) preserved.")
        print("   Ready for fresh Super Admin → Tenant creation → Seeding workflow.")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_data()
