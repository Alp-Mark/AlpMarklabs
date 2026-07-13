#!/usr/bin/env python3
"""Debug script to check order data."""

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

db = SessionLocal()

print("=== RECENT ORDERS ===")
result = db.execute(text('''
    SELECT id, order_number, total_price, created_at, items
    FROM orders
    ORDER BY created_at DESC
    LIMIT 10
''')).fetchall()

for row in result:
    print(f"Order {row[1]}: ₹{row[2]:.2f} on {row[3]} - {row[4]} items")

print("\n=== ORDER TOTAL STATS ===")
result = db.execute(text('''
    SELECT 
        COUNT(*) as order_count,
        SUM(total_price) as total_revenue,
        MIN(total_price) as min_order,
        MAX(total_price) as max_order,
        AVG(total_price) as avg_order
    FROM orders
''')).fetchone()

print(f"Total Orders: {result[0]}")
if result[1]:
    print(f"Total Revenue: ₹{result[1]:.2f}")
    print(f"Min Order: ₹{result[2]:.2f}")
    print(f"Max Order: ₹{result[3]:.2f}")
    print(f"Avg Order: ₹{result[4]:.2f}")
else:
    print("No orders found")

print("\n=== CHECKING ONE8 PRODUCTS ===")
result = db.execute(text('''
    SELECT COUNT(*), MIN(price), MAX(price), AVG(price)
    FROM products
''')).fetchone()

print(f"Total Products: {result[0]}")
if result[0] > 0:
    print(f"Min Price: ₹{result[1]:.2f}")
    print(f"Max Price: ₹{result[2]:.2f}")
    print(f"Avg Price: ₹{result[3]:.2f}")

print("\n=== SAMPLE PRODUCTS WITH ₹150 OR CLOSE ===")
result = db.execute(text('''
    SELECT sku, title, price
    FROM products
    WHERE price BETWEEN 100 AND 200
    ORDER BY price
    LIMIT 10
''')).fetchall()

for row in result:
    print(f"SKU {row[0]}: {row[1]} - ₹{row[2]:.2f}")

db.close()
