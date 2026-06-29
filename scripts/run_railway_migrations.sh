#!/bin/bash
# Script to manually run Alembic migrations on Railway
# 
# Usage:
#   1. Install Railway CLI: npm install -g @railway/cli
#   2. Login to Railway: railway login
#   3. Link to project: railway link
#   4. Run this script: ./scripts/run_railway_migrations.sh

set -e

echo "Running Alembic migrations on Railway..."
railway run alembic -c backend/alembic.ini upgrade head

echo "✅ Migrations completed successfully!"
