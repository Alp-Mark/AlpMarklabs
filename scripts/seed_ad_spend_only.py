#!/usr/bin/env python3
"""
Quick seed script to generate ad spend data for optimization testing.
Creates 90 days of Meta and Google ad spend data.
"""

import os
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text

# Real tenant ID (from frontend)
TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Use existing connector (for testing, same connector for both is fine)
CONNECTOR_ID = "28b0368f-00ff-48e6-8f00-14a9cfe06412"


def main():
    # Database connection
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev"
    )
    
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:  # Auto-commit transaction
        print(f"Generating ad spend data for tenant {TENANT_ID}")
        print(f"Using connector: {CONNECTOR_ID}")
        print("=" * 60)
        
        # Generate 90 days of ad spend
        end_date = date.today()
        start_date = end_date - timedelta(days=89)
        
        meta_campaigns = ["TOF_Prospecting", "MOF_Retargeting", "BOF_Conversion"]
        google_campaigns = ["Search_Brand", "Search_Generic", "Display_Prospecting"]
        
        meta_records = []
        google_records = []
        
        current_date = start_date
        while current_date <= end_date:
            # Meta ad spend
            for campaign in meta_campaigns:
                daily_spend = random.uniform(3000, 7000)  # INR 3K-7K per campaign per day
                meta_records.append({
                    'id': str(uuid.uuid4()),
                    'tenant_id': TENANT_ID,
                    'connector_id': CONNECTOR_ID,
                    'external_campaign_id': f"meta_{campaign}_{current_date.strftime('%Y%m')}",
                    'campaign_name': campaign,
                    'spend_date': current_date,
                    'currency': 'INR',
                    'spend_amount': round(daily_spend, 2)
                })
            
            # Google ad spend
            for campaign in google_campaigns:
                daily_spend = random.uniform(2000, 5000)  # INR 2K-5K per campaign per day
                google_records.append({
                    'id': str(uuid.uuid4()),
                    'tenant_id': TENANT_ID,
                    'connector_id': CONNECTOR_ID,
                    'external_campaign_id': f"google_{campaign}_{current_date.strftime('%Y%m')}",
                    'campaign_name': campaign,
                    'spend_date': current_date,
                    'currency': 'INR',
                    'spend_amount': round(daily_spend, 2)
                })
            
            current_date += timedelta(days=1)
        
        # Insert Meta ad spend
        if meta_records:
            conn.execute(text('''
                INSERT INTO meta_ad_spends 
                (id, tenant_id, connector_id, external_campaign_id, campaign_name, 
                 spend_date, currency, spend_amount, synced_at, created_at, updated_at)
                VALUES 
                (:id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                 :spend_date, :currency, :spend_amount, NOW(), NOW(), NOW())
            '''), meta_records)
            print(f"\n✓ Created {len(meta_records)} Meta ad spend records")
        
        # Insert Google ad spend
        if google_records:
            conn.execute(text('''
                INSERT INTO google_ad_spends 
                (id, tenant_id, connector_id, external_campaign_id, campaign_name, 
                 spend_date, currency, spend_amount, synced_at, created_at, updated_at)
                VALUES 
                (:id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                 :spend_date, :currency, :spend_amount, NOW(), NOW(), NOW())
            '''), google_records)
            print(f"✓ Created {len(google_records)} Google ad spend records")
        
        print("\n✅ Ad spend data generated successfully!")
        print(f"Date range: {start_date} to {end_date} (90 days)")
        print("\nReady for optimization testing!")


if __name__ == "__main__":
    main()
