#!/usr/bin/env python3
"""Check if One8 has any snapshot data for rule engine."""

import os
import sys
from pathlib import Path

# Override DATABASE_URL before imports  
db_url = os.getenv("DATABASE_PUBLIC_URL")
if db_url:
    os.environ["DATABASE_URL"] = db_url

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.db.session import SessionLocal
from sqlalchemy import text

ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

SNAPSHOT_TABLES = [
    "executive_kpi_snapshots",
    "acquisition_metrics_snapshots",
    "retention_daily_snapshots",
    "margin_drift_snapshots",
    "inventory_risk_snapshots",
    "operational_impact_snapshots",
]

db = SessionLocal()

print("📊 Checking snapshot data for One8 tenant:")
print()

has_any_data = False
for table in SNAPSHOT_TABLES:
    try:
        result = db.execute(text(f'''
            SELECT COUNT(*) 
            FROM {table}
            WHERE tenant_id = '{ONE8_TENANT_ID}'
        ''')).scalar()
        
        status = "✅" if result > 0 else "❌"
        print(f"{status} {table:40} {result:5} rows")
        if result > 0:
            has_any_data = True
    except Exception as e:
        print(f"❌ {table:40} ERROR: {str(e)[:60]}")

print()
if not has_any_data:
    print("⚠️  NO SNAPSHOT DATA FOUND")
    print()
    print("The recommendation engine needs snapshots to evaluate rules.")
    print("These are created by OTHER Celery beat tasks:")
    print("  • executive-kpi-computation-schedule (every 4 hours)")
    print("  • acquisition-metrics-computation-schedule (every 4 hours)")
    print("  • retention-cohort-computation-schedule (every 4 hours)")
    print("  • etc.")
    print()
    print("Solution: Deploy the worker to Railway so beat schedules run!")
else:
    print("✅ Snapshot data exists - rules should generate recommendations")
