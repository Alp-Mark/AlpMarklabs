#!/usr/bin/env python3
"""Check current migration status on Railway database."""
import os
from sqlalchemy import create_engine, inspect, text

# Get Railway database URL from environment
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    exit(1)

engine = create_engine(db_url)

# Check current migration version
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.scalar()
    print(f"Current migration version: {version}")

# Check if columns exist
insp = inspect(engine)
cols = [c["name"] for c in insp.get_columns("recommendations")]
print(f"\nColumns in recommendations table:")
print(f"  - impact_score exists: {'impact_score' in cols}")
print(f"  - evidence exists: {'evidence' in cols}")

if "impact_score" in cols and "evidence" in cols:
    print("\n✅ Both columns exist! Migrations have run successfully.")
else:
    print("\n⚠️  Columns missing! Need to run migrations 0034 and 0035.")
