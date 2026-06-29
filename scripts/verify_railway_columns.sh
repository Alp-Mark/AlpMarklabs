#!/bin/bash
# Verify that impact_score and evidence columns exist on Railway database
# Run this AFTER migrations complete to confirm success

set -e

echo "Checking Railway database for impact_score and evidence columns..."
echo ""

railway run --service AlpMarklabs -- python3 -c "
from sqlalchemy import create_engine, inspect
import os

engine = create_engine(os.environ['DATABASE_URL'])
insp = inspect(engine)
cols = [c['name'] for c in insp.get_columns('recommendations')]

impact_exists = 'impact_score' in cols
evidence_exists = 'evidence' in cols

print(f'✓ impact_score column: {'EXISTS' if impact_exists else 'MISSING'}')
print(f'✓ evidence column: {'EXISTS' if evidence_exists else 'MISSING'}')
print('')

if impact_exists and evidence_exists:
    print('✅ SUCCESS! Both columns exist. Ready to uncomment code.')
    exit(0)
else:
    print('⚠️  Columns still missing. Run migrations on Railway.')
    exit(1)
"
