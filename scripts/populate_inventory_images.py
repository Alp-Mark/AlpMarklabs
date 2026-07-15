#!/usr/bin/env python3
"""Populate image_url in ShopifyInventoryItem from one8_products.json.

This script:
1. Reads product image data from one8_products.json
2. Matches SKUs to products
3. Updates inventory items with image_url from the first product image

Does NOT re-seed—only updates image_url column on existing inventory items.
Safe to run on existing data; preserves all other fields.
"""

import json
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import urlencode
import os

# Railway DB from env
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/alpmark")
engine = create_engine(DATABASE_URL)

# Load one8_products.json
products_path = Path(__file__).parent.parent / "data" / "one8_products.json"
print(f"Loading products from {products_path}...")

with open(products_path) as f:
    data = json.load(f)

# Build sku → image_url mapping
sku_to_image: dict[str, str] = {}
for product in data["products"]:
    images = product.get("images", [])
    if not images:
        continue
    
    first_image = images[0]
    
    # Extract SKUs from variants
    for variant in product.get("variants", []):
        sku = variant.get("sku")
        if sku:
            sku_to_image[sku] = first_image

print(f"   Mapped {len(sku_to_image)} SKUs to images")

# Update inventory items with image_url
with engine.begin() as conn:
    # Get all current inventory items
    result = conn.execute(text("""
        SELECT id, sku FROM shopify_inventory_items
    """))
    inventory_items = result.fetchall()
    print(f"   Found {len(inventory_items)} inventory items")
    
    # Update each with image_url if SKU matches
    updated = 0
    skipped = 0
    for item_id, sku in inventory_items:
        if sku in sku_to_image:
            image_url = sku_to_image[sku]
            conn.execute(text("""
                UPDATE shopify_inventory_items
                SET image_url = :image_url
                WHERE id = :id
            """), {"image_url": image_url, "id": item_id})
            updated += 1
        else:
            skipped += 1
    
    print(f"   ✅ Updated {updated} inventory items with images")
    print(f"   ⚠️  {skipped} SKUs not found in one8_products.json")

print("Done! Images are now populated in the database.")
print("Test with: GET /tenants/{{tenant_id}}/analytics/products/{{product}}/variants")
