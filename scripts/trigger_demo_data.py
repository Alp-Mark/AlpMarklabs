#!/usr/bin/env python3
"""
Manually trigger the 6-hour demo data generation task immediately.

This is useful for:
- Testing the data generation
- Populating the dashboard with fresh data
- Simulating activity without waiting 6 hours

Usage:
    python3 scripts/trigger_demo_data.py
"""

import os
import sys

# Set environment
os.environ.setdefault("DATABASE_URL", "postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.app.tasks_demo_data import generate_demo_data_one8


def main():
    print("🎯 Manually triggering demo data generation for One8...")
    print()
    
    try:
        result = generate_demo_data_one8()
        
        print()
        print("✅ Demo Data Generation Complete!")
        print()
        print("📊 Summary:")
        print(f"   • Orders created: {result['orders_created']}")
        print(f"   • Line items created: {result['line_items_created']}")
        print(f"   • Ad spend records: {result['ad_spend_records']}")
        print(f"   • Snapshots updated: {', '.join(result['snapshots_updated'])}")
        print()
        print("🔄 Refresh your dashboard to see the new data!")
        print("   URL: https://your-replit-url.replit.dev/executive/home")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
