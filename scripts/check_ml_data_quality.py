#!/usr/bin/env python3
"""Check One8 tenant ML model quality."""
import sys
from sqlalchemy import create_engine, text

# Connect to database
engine = create_engine("postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev")

ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

print("Checking One8 tenant ML model quality...")
print(f"Tenant ID: {ONE8_TENANT_ID}\n")

with engine.connect() as conn:
    # Check ad spend data variance
    ad_spend = conn.execute(
        text(
            """
            SELECT 
                connector,
                COUNT(*) as days,
                MIN(spend) as min_spend,
                MAX(spend) as max_spend,
                AVG(spend) as avg_spend,
                STDDEV(spend) as stddev_spend
            FROM ad_spend
            WHERE tenant_id = :tid
            GROUP BY connector
            """
        ),
        {"tid": ONE8_TENANT_ID},
    ).fetchall()

    print(f"Ad Spend Data by Connector:")
    for row in ad_spend:
        variance_ratio = (row[5] or 0) / (row[4] or 1)  # stddev/mean
        print(
            f"  {row[0]}: {row[1]} days | "
            f"₹{row[2]:,.0f}-{row[3]:,.0f} (avg ₹{row[4]:,.0f}, CV={variance_ratio:.2f})"
        )
        if variance_ratio < 0.2:
            print(f"    ⚠️  LOW VARIANCE - spend is too consistent for ML to learn saturation curves")

    # Check fitted models
    models = conn.execute(
        text(
            """
            SELECT 
                model_type,
                connector,
                accuracy_metrics,
                created_at
            FROM fitted_models
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
            LIMIT 10
            """
        ),
        {"tid": ONE8_TENANT_ID},
    ).fetchall()

    print(f"\nFitted Models (R² = model quality, higher is better):")
    if not models:
        print("  ⚠️  No fitted models found!")
    else:
        for row in models:
            r2 = row[2].get('r2') if row[2] else None
            rmse = row[2].get('rmse') if row[2] else None
            print(f"  {row[0]} ({row[1]}): R²={r2:.4f if r2 is not None else 'N/A'}, RMSE={rmse:.2f if rmse else 'N/A'} | {row[3]}")
            if r2 is not None and r2 < 0.3:
                print(f"    ⚠️  POOR FIT - R² < 0.3 means model is unreliable")

    # Check recommendations by confidence
    recs = conn.execute(
        text(
            """
            SELECT 
                source,
                confidence_level,
                COUNT(*) as count,
                AVG(confidence_score) as avg_score
            FROM recommendations
            WHERE tenant_id = :tid
            GROUP BY source, confidence_level
            ORDER BY source, avg_score DESC
            """
        ),
        {"tid": ONE8_TENANT_ID},
    ).fetchall()

    print(f"\nRecommendations by Confidence Level:")
    for row in recs:
        print(f"  {row[0]:<12} | {row[1]:<10} | count={row[2]:>3} | avg_score={row[3]:.2%}")

print("\n" + "=" * 70)
print("ML Quality Thresholds:")
print("  - Coefficient of Variation (CV) should be > 0.3 for good learning")
print("  - R² should be > 0.5 for production use (0.7+ for high confidence)")
print("  - Below 0.3 R² → model is worse than random guessing")
print("=" * 70)
