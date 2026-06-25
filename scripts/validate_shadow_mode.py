"""
Task 1.8: Validate Shadow Mode Results

Checks optimization_runs and fitted_models tables for the One8 test tenant
to verify shadow mode is producing reasonable results.
"""

import os

from sqlalchemy import create_engine, text

# One8 test tenant ID
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

def validate_shadow_mode():
    """Run validation queries and display results."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev"
    )
    engine = create_engine(database_url)
    
    print("=" * 70)
    print("Task 1.8: Validate Shadow Mode Results")
    print("=" * 70)
    print()
    
    with engine.connect() as conn:
        # Query 1: Recent successful optimization runs
        print("📊 RECENT OPTIMIZATION RUNS")
        print("-" * 70)
        
        query1 = text("""
        SELECT 
            started_at,
            run_status,
            (optimization_result->>'meta_pct')::float as meta_pct,
            (optimization_result->>'google_pct')::float as google_pct,
            (optimization_result->>'expected_conversions')::float as expected_conv,
            (optimization_result->>'lift_pct')::float as lift_pct,
            execution_time_seconds
        FROM optimization_runs
        WHERE tenant_id = :tenant_id
            AND run_status = 'success'
        ORDER BY started_at DESC
        LIMIT 5;
        """)
        
        result = conn.execute(query1, {"tenant_id": ONE8_TENANT_ID})
        rows = list(result)
        
        if rows:
            for i, row in enumerate(rows, 1):
                print(f"\n#{i} - {row[0].strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"   Status: {row[1]}")
                print(f"   Allocation: {row[2]:.1f}% Meta / {row[3]:.1f}% Google")
                print(f"   Expected Conversions: {row[4]:.1f}")
                print(f"   Lift vs Current: {row[5]:+.1f}%")
                print(f"   Execution Time: {row[6]:.2f}s")
        else:
            print("\n   ⚠️  No successful runs found yet")
        
        print()
        print()
        
        # Query 2: Model accuracy metrics (our "confidence" measure)
        print("🎯 MODEL ACCURACY (CONFIDENCE)")
        print("-" * 70)
        
        query2 = text("""
        SELECT 
            fm.model_type,
            fm.trained_at,
            (fm.accuracy_metrics->>'r2')::float as r2_score,
            (fm.accuracy_metrics->>'rmse')::float as rmse
        FROM fitted_models fm
        JOIN optimization_runs r ON fm.optimization_run_id = r.id
        WHERE fm.tenant_id = :tenant_id
            AND r.run_status = 'success'
        ORDER BY fm.trained_at DESC
        LIMIT 10;
        """)
        
        result2 = conn.execute(query2, {"tenant_id": ONE8_TENANT_ID})
        rows2 = list(result2)
        
        if rows2:
            print()
            print(f"{'Model Type':<30} {'R² Score':<12} {'RMSE':<12} {'Quality'}")
            print("-" * 70)
            
            for row in rows2:
                r2 = row[2]
                if r2 >= 0.7:
                    quality = "✓ GOOD"
                elif r2 >= 0.5:
                    quality = "⚠ POOR"
                else:
                    quality = "✗ BAD"
                
                print(f"{row[0]:<30} {r2:<12.3f} {row[3]:<12.1f} {quality}")
            
            # Summary
            avg_r2 = sum(row[2] for row in rows2) / len(rows2)
            print()
            print(f"Average R² Score: {avg_r2:.3f}")
            
            if avg_r2 >= 0.7:
                print("✅ Models have GOOD confidence (R² ≥ 0.7)")
            elif avg_r2 >= 0.5:
                print("⚠️  Models have POOR confidence (0.5 ≤ R² < 0.7)")
            else:
                print("❌ Models have BAD confidence (R² < 0.5)")
        else:
            print("\n   ⚠️  No fitted models found yet")
        
        print()
        print()
        
        # Query 3: Recent failures
        print("❌ RECENT FAILURES")
        print("-" * 70)
        
        query3 = text("""
        SELECT 
            started_at,
            error_message
        FROM optimization_runs
        WHERE tenant_id = :tenant_id
            AND run_status = 'failed'
        ORDER BY started_at DESC
        LIMIT 5;
        """)
        
        result3 = conn.execute(query3, {"tenant_id": ONE8_TENANT_ID})
        rows3 = list(result3)
        
        if rows3:
            print()
            for row in rows3:
                print(f"{row[0].strftime('%Y-%m-%d %H:%M')}: {row[1][:70]}")
        else:
            print("\n   ✅ No failures - all runs successful!")
        
        print()
        print()
        
        # Summary counts
        print("📈 SUMMARY")
        print("-" * 70)
        
        query_counts = text("""
        SELECT 
            run_status,
            COUNT(*) as count
        FROM optimization_runs
        WHERE tenant_id = :tenant_id
        GROUP BY run_status
        ORDER BY run_status;
        """)
        
        result_counts = conn.execute(query_counts, {"tenant_id": ONE8_TENANT_ID})
        rows_counts = list(result_counts)
        
        if rows_counts:
            print()
            total = sum(row[1] for row in rows_counts)
            for row in rows_counts:
                status = row[0]
                count = row[1]
                pct = (count / total * 100) if total > 0 else 0
                print(f"   {status.upper():<12} {count:>3} runs ({pct:>5.1f}%)")
            print(f"   {'TOTAL':<12} {total:>3} runs")
        else:
            print("\n   ⚠️  No optimization runs found")
        
        print()
        print("=" * 70)


if __name__ == "__main__":
    validate_shadow_mode()
