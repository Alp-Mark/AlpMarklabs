#!/usr/bin/env python3
"""
Manually trigger recommendation generation for all active tenants.

This script bypasses the 24-hour Celery beat schedule and runs the
rule engine immediately. Useful for:
- Testing after seeding new data
- Debugging recommendation logic
- Forcing a refresh on demand

Usage:
    railway run python3 scripts/run_recommendations_now.py
    
Or locally with Railway database:
    export DATABASE_PUBLIC_URL="postgresql://..."
    python3 scripts/run_recommendations_now.py
"""

import os
import sys
from pathlib import Path

# CRITICAL: Override DATABASE_URL BEFORE any imports
# Railway CLI sets DATABASE_URL to internal address (postgres.railway.internal)
# which doesn't resolve from local machine. Use DATABASE_PUBLIC_URL instead.
db_url = os.getenv("DATABASE_PUBLIC_URL")
if not db_url:
    print("❌ Error: DATABASE_PUBLIC_URL not set")
    print("   Run this with: railway run python3 scripts/run_recommendations_now.py")
    sys.exit(1)

os.environ["DATABASE_URL"] = db_url

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the rule engine job (AFTER setting DATABASE_URL)
from worker.app.tasks import run_rule_engine_job


def main():
    """Run the recommendation engine immediately."""
    
    print("🔄 Running recommendation engine now...")
    print(f"   Database: {db_url.split('@')[1] if '@' in db_url else 'unknown'}")
    print()
    
    try:
        # Call the worker task function directly (without Celery)
        result = run_rule_engine_job()
        
        print("✅ Recommendation engine complete!")
        print(f"   Tenants processed: {result['tenants_processed']}")
        print(f"   Recommendations created: {result['recommendations_created']}")
        print()
        
        if result['recommendations_created'] == 0:
            print("⚠️  No recommendations generated. This could mean:")
            print("   • All metrics are within acceptable thresholds")
            print("   • Tenant alert configurations need adjustment")
            print("   • Rule conditions are too strict")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error running recommendation engine: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
