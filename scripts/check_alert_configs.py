#!/usr/bin/env python3
"""Check alert configurations for One8 tenant."""

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

db = SessionLocal()
result = db.execute(text(f'''
    SELECT 
        domain, 
        metric_name, 
        threshold_value, 
        threshold_unit,
        is_active
    FROM alert_configurations
    WHERE tenant_id = '{ONE8_TENANT_ID}'
    ORDER BY domain, metric_name
''')).fetchall()

if result:
    print(f'✅ Alert Configurations for One8 ({len(result)} total):')
    print()
    for row in result:
        status = "✓" if row[4] else "✗"
        print(f'  [{status}] {row[0]:12} | {row[1]:30} | {row[2]:10} {row[3]}')
else:
    print('❌ No alert configurations found for One8 tenant')
    print('   Recommendations require thresholds to be configured!')
    print()
    print('   The rule engine checks these configurations to determine if metrics')
    print('   are outside acceptable bounds and need recommendations.')
