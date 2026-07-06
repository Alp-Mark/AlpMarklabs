"""Check date range of One8 data in database."""

import os
from sqlalchemy import create_engine, text

ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    # Get date range
    result = conn.execute(text("""
        SELECT 
            MIN(DATE(order_created_at)) as first_order_date,
            MAX(DATE(order_created_at)) as last_order_date,
            COUNT(*) as total_orders,
            COUNT(DISTINCT DATE(order_created_at)) as days_with_data
        FROM shopify_orders 
        WHERE tenant_id = :tid
    """), {"tid": ONE8_TENANT_ID})
    
    summary = result.one()
    print("=" * 70)
    print("ONE8 DATA SUMMARY")
    print("=" * 70)
    print(f"First Order Date: {summary.first_order_date}")
    print(f"Last Order Date:  {summary.last_order_date}")
    print(f"Total Orders:     {summary.total_orders:,}")
    print(f"Days with Data:   {summary.days_with_data}")
    print()
    
    # Get daily breakdown
    result = conn.execute(text("""
        SELECT 
            DATE(order_created_at) as order_date,
            COUNT(*) as order_count,
            ROUND(SUM(total_amount - refund_amount)::numeric, 2) as revenue
        FROM shopify_orders 
        WHERE tenant_id = :tid
        GROUP BY DATE(order_created_at)
        ORDER BY order_date
    """), {"tid": ONE8_TENANT_ID})
    
    print("DAILY BREAKDOWN:")
    print("-" * 70)
    print(f"{'Date':<12} {'Orders':<10} {'Revenue':<20}")
    print("-" * 70)
    
    for row in result:
        print(f"{str(row.order_date):<12} {row.order_count:>6}    ₹{row.revenue:>15,.2f}")
    
    print("=" * 70)
