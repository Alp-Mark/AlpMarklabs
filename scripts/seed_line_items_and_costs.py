#!/usr/bin/env python3
"""
Generate realistic line items and COGS/shipping costs for One8 orders.

This script:
1. Loads all One8 orders that don't have line items
2. Generates 1-3 realistic line items per order based on order total
3. Seeds COGS (40-50% of price) and shipping costs (₹50-200)
4. Updates executive metrics

Run:
    python3 scripts/seed_line_items_and_costs.py
"""

import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add repo root to path
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev')

from backend.app.db.session import SessionLocal
from sqlalchemy import text

# One8 tenant ID
ONE8_TENANT_ID = '23165fa5-150b-4b6c-a637-b3dd24532c4d'

# Realistic One8 product catalog (apparel/footwear)
PRODUCTS = [
    ("ONE8-TEE-001", "One8 Signature T-Shirt", "Black", 1299.0),
    ("ONE8-TEE-002", "One8 Signature T-Shirt", "White", 1299.0),
    ("ONE8-TEE-003", "One8 Signature T-Shirt", "Navy", 1299.0),
    ("ONE8-POLO-001", "One8 Polo Shirt", "Blue", 1899.0),
    ("ONE8-POLO-002", "One8 Polo Shirt", "Grey", 1899.0),
    ("ONE8-SHOE-001", "One8 Running Shoes", "Black/Red", 4999.0),
    ("ONE8-SHOE-002", "ONE8 Running Shoes", "White/Blue", 4999.0),
    ("ONE8-SHOE-003", "One8 Sneakers", "Grey", 3999.0),
    ("ONE8-TRACK-001", "One8 Track Pants", "Black", 2299.0),
    ("ONE8-TRACK-002", "One8 Track Pants", "Navy", 2299.0),
    ("ONE8-SHORT-001", "One8 Shorts", "Black", 1499.0),
    ("ONE8-SHORT-002", "One8 Shorts", "Grey", 1499.0),
    ("ONE8-JACKET-001", "One8 Jacket", "Black", 3499.0),
    ("ONE8-JACKET-002", "One8 Jacket", "Navy", 3499.0),
    ("ONE8-CAP-001", "One8 Cap", "Black", 799.0),
    ("ONE8-CAP-002", "One8 Cap", "White", 799.0),
    ("ONE8-SOCK-001", "One8 Socks (3-Pack)", "Mixed", 599.0),
    ("ONE8-TANK-001", "One8 Tank Top", "Black", 999.0),
    ("ONE8-TANK-002", "One8 Tank Top", "White", 999.0),
    ("ONE8-HOODIE-001", "One8 Hoodie", "Grey", 2999.0),
]


def generate_line_items_for_order(order_id, order_total, order_date, num_items=None):
    """Generate 1-3 realistic line items that sum close to order_total."""
    
    if num_items is None:
        # Most orders have 1-2 items, occasionally 3
        weights = [0.6, 0.3, 0.1]  # 60% single item, 30% two items, 10% three
        num_items = random.choices([1, 2, 3], weights=weights)[0]
    
    # Randomly select products
    selected_products = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
    
    line_items = []
    target_per_item = order_total / num_items
    
    for i, (sku, product_title, variant, base_price) in enumerate(selected_products):
        # Vary quantity slightly (mostly 1, occasionally 2)
        quantity = 1 if random.random() < 0.85 else 2
        
        # Adjust price to hit target (with some variation)
        if i == num_items - 1:
            # Last item: make total match exactly
            remaining = order_total - sum(item['unit_price'] * item['quantity'] for item in line_items)
            unit_price = max(100.0, remaining / quantity)  # Min ₹100
        else:
            # Scale product price to roughly match order total
            scale_factor = target_per_item / base_price
            unit_price = base_price * scale_factor * random.uniform(0.8, 1.2)
        
        line_items.append({
            'id': str(uuid.uuid4()),
            'tenant_id': ONE8_TENANT_ID,
            'order_id': order_id,
            'line_item_index': i,
            'sku': sku,
            'product_title': product_title,
            'variant_title': variant,
            'quantity': quantity,
            'unit_price': round(unit_price, 2),
            'order_created_at': order_date,
        })
    
    return line_items


def generate_costs_for_line_item(unit_price):
    """Generate realistic COGS and shipping for a product."""
    
    # COGS: 40-50% of retail price (varies by category)
    cogs_pct = random.uniform(0.40, 0.50)
    cogs = unit_price * cogs_pct
    
    # Shipping: ₹50-200 depending on product price (heavier/expensive = more)
    if unit_price < 1000:
        shipping = random.uniform(50, 100)
    elif unit_price < 3000:
        shipping = random.uniform(80, 150)
    else:
        shipping = random.uniform(120, 200)
    
    return round(cogs, 2), round(shipping, 2)


def main():
    print("🔧 Seeding Line Items and Costs for One8 Orders\n")
    
    db = SessionLocal()
    
    try:
        # Step 1: Count orders without line items
        print("📊 Checking existing data...")
        
        orders = db.execute(text("""
            SELECT o.id, o.total_amount, o.order_created_at, o.currency
            FROM shopify_orders o
            WHERE o.tenant_id = :tid
            AND NOT EXISTS (
                SELECT 1 FROM shopify_order_line_items li 
                WHERE li.order_id = o.id
            )
            ORDER BY o.order_created_at DESC
        """), {'tid': ONE8_TENANT_ID}).fetchall()
        
        print(f"   ✅ Found {len(orders):,} orders without line items\n")
        
        if not orders:
            print("   ✅ All orders already have line items!")
            return
        
        # Step 2: Generate and insert line items in batches
        print(f"🎯 Generating line items for {len(orders):,} orders...")
        
        all_line_items = []
        batch_size = 1000
        
        for i, (order_id, order_total, order_date, currency) in enumerate(orders, 1):
            line_items = generate_line_items_for_order(order_id, order_total, order_date)
            all_line_items.extend(line_items)
            
            if i % batch_size == 0 or i == len(orders):
                # Insert batch
                if all_line_items:
                    db.execute(text("""
                        INSERT INTO shopify_order_line_items (
                            id, tenant_id, order_id, line_item_index, sku,
                            product_title, variant_title, quantity, unit_price,
                            order_created_at
                        ) VALUES (
                            :id, :tenant_id, :order_id, :line_item_index, :sku,
                            :product_title, :variant_title, :quantity, :unit_price,
                            :order_created_at
                        )
                    """), all_line_items)
                    db.commit()
                    print(f"   ✅ Inserted {i:,} / {len(orders):,} orders ({len(all_line_items):,} line items)")
                    all_line_items = []  # Clear for next batch
        
        print("\n✅ Line items complete!\n")
        
        # Step 3: Seed COGS and shipping costs for all products
        print("💰 Seeding COGS and shipping costs...")
        
        # Get all unique SKUs with their average prices
        skus = db.execute(text("""
            SELECT DISTINCT sku, product_title, AVG(unit_price) as avg_price
            FROM shopify_order_line_items
            WHERE tenant_id = :tid
            AND sku IS NOT NULL
            GROUP BY sku, product_title
        """), {'tid': ONE8_TENANT_ID}).fetchall()
        
        print(f"   Found {len(skus):,} unique SKUs")
        
        # Check if CostInput table exists
        cost_inputs = []
        for sku, product_title, avg_price in skus:
            cogs, shipping = generate_costs_for_line_item(avg_price)
            
            cost_inputs.append({
                'id': str(uuid.uuid4()),
                'tenant_id': ONE8_TENANT_ID,
                'cost_driver': 'cogs',
                'source': 'manual',
                'value_amount': cogs,
                'unit': 'INR',
                'scope_dimension': 'sku',
                'scope_value': sku,
                'effective_date': datetime.now().date(),
                'is_active': True,
                'notes': f'Auto-generated COGS for {product_title}',
            })
            
            cost_inputs.append({
                'id': str(uuid.uuid4()),
                'tenant_id': ONE8_TENANT_ID,
                'cost_driver': 'shipping',
                'source': 'manual',
                'value_amount': shipping,
                'unit': 'INR',
                'scope_dimension': 'sku',
                'scope_value': sku,
                'effective_date': datetime.now().date(),
                'is_active': True,
                'notes': f'Auto-generated shipping cost for {product_title}',
            })
        
        # Insert costs in batch
        if cost_inputs:
            db.execute(text("""
                INSERT INTO cost_inputs (
                    id, tenant_id, cost_driver, source, value_amount, unit,
                    scope_dimension, scope_value, effective_date, is_active, notes
                ) VALUES (
                    :id, :tenant_id, :cost_driver, :source, :value_amount, :unit,
                    :scope_dimension, :scope_value, :effective_date, :is_active, :notes
                )
                ON CONFLICT DO NOTHING
            """), cost_inputs)
            db.commit()
            print(f"   ✅ Seeded {len(cost_inputs):,} cost inputs ({len(skus):,} SKUs × 2 types)\n")
        
        print("✨ Complete! Executive dashboard should now show real metrics.\n")
        
        # Show sample stats
        total_line_items = db.scalar(text("""
            SELECT COUNT(*) FROM shopify_order_line_items
            WHERE tenant_id = :tid
        """), {'tid': ONE8_TENANT_ID})
        
        total_revenue = db.scalar(text("""
            SELECT SUM(total_amount) FROM shopify_orders
            WHERE tenant_id = :tid AND is_refunded = false
        """), {'tid': ONE8_TENANT_ID})
        
        print("📊 Final Stats:")
        print(f"   Orders: {len(orders):,}")
        print(f"   Line Items: {total_line_items:,}")
        print(f"   Total Revenue: ₹{total_revenue:,.2f}\n")
        
    finally:
        db.close()


if __name__ == '__main__':
    main()
