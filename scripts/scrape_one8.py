#!/usr/bin/env python3
"""
Scrape One8 (Virat Kohli's brand) product catalog from their Shopify store.

This script fetches all products, variants, prices, and inventory information
from https://one8.com/ using Shopify's JSON API.

Usage:
    python3 scripts/scrape_one8.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests


def fetch_all_products():
    """Fetch all products from One8 Shopify store using pagination."""
    
    base_url = "https://one8.com"
    all_products = []
    page = 1
    
    print("🔍 Scraping One8 product catalog...")
    print(f"   Base URL: {base_url}")
    
    while True:
        # Shopify products.json endpoint with pagination
        url = f"{base_url}/products.json?page={page}&limit=250"
        
        print(f"\n📄 Fetching page {page}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            products = data.get("products", [])
            
            if not products:
                print(f"   ✅ No more products found. Total pages: {page - 1}")
                break
            
            print(f"   ✅ Found {len(products)} products on page {page}")
            all_products.extend(products)
            
            page += 1
            
            # Be polite to their server
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error fetching page {page}: {e}")
            break
    
    return all_products


def extract_product_info(raw_products):
    """Extract and structure product information."""
    
    products = []
    
    print(f"\n📊 Processing {len(raw_products)} products...")
    
    for raw_product in raw_products:
        # Extract variants (sizes, colors, etc.)
        variants = []
        for variant in raw_product.get("variants", []):
            variant_info = {
                "variant_id": variant.get("id"),
                "sku": variant.get("sku"),
                "title": variant.get("title"),
                "price": float(variant.get("price", 0)),
                "compare_at_price": float(variant.get("compare_at_price", 0)) if variant.get("compare_at_price") else None,
                "inventory_quantity": variant.get("inventory_quantity", 0),
                "inventory_policy": variant.get("inventory_policy"),
                "available": variant.get("available", False),
                "weight": variant.get("weight"),
                "weight_unit": variant.get("weight_unit"),
                "option1": variant.get("option1"),  # Usually size
                "option2": variant.get("option2"),  # Usually color
                "option3": variant.get("option3"),
            }
            variants.append(variant_info)
        
        # Extract main product info
        product = {
            "product_id": raw_product.get("id"),
            "handle": raw_product.get("handle"),
            "title": raw_product.get("title"),
            "product_type": raw_product.get("product_type"),
            "vendor": raw_product.get("vendor"),
            "tags": raw_product.get("tags", []),
            "published_at": raw_product.get("published_at"),
            "created_at": raw_product.get("created_at"),
            "updated_at": raw_product.get("updated_at"),
            "url": f"https://one8.com/products/{raw_product.get('handle')}",
            "description": raw_product.get("body_html"),
            "images": [img.get("src") for img in raw_product.get("images", [])],
            "variants": variants,
            "options": raw_product.get("options", []),
            "min_price": min([float(v.get("price", 0)) for v in raw_product.get("variants", [])], default=0),
            "max_price": max([float(v.get("price", 0)) for v in raw_product.get("variants", [])], default=0),
            "total_inventory": sum([v.get("inventory_quantity", 0) for v in raw_product.get("variants", [])]),
        }
        
        products.append(product)
    
    return products


def analyze_catalog(products):
    """Print catalog statistics."""
    
    print("\n" + "="*60)
    print("📊 ONE8 CATALOG ANALYSIS")
    print("="*60)
    
    print(f"\n🏷️  Total Products: {len(products)}")
    
    # Count by product type
    types = {}
    for p in products:
        ptype = p.get("product_type", "Unknown")
        types[ptype] = types.get(ptype, 0) + 1
    
    print("\n📦 Products by Type:")
    for ptype, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {ptype}: {count}")
    
    # Price analysis
    all_prices = [p["min_price"] for p in products if p["min_price"] > 0]
    if all_prices:
        print("\n💰 Price Range:")
        print(f"   - Lowest: ₹{min(all_prices):,.2f}")
        print(f"   - Highest: ₹{max(all_prices):,.2f}")
        print(f"   - Average: ₹{sum(all_prices) / len(all_prices):,.2f}")
    
    # Variant count
    total_variants = sum([len(p["variants"]) for p in products])
    print(f"\n🎨 Total Variants (SKUs): {total_variants}")
    
    # Inventory
    total_inventory = sum([p["total_inventory"] for p in products])
    print(f"\n📦 Total Inventory Units: {total_inventory:,}")
    
    # Top products by price
    print("\n🏆 Top 5 Most Expensive Products:")
    for p in sorted(products, key=lambda x: x["max_price"], reverse=True)[:5]:
        print(f"   - {p['title']}: ₹{p['max_price']:,.2f}")
    
    print("\n" + "="*60)


def save_to_json(products, filename="one8_products.json"):
    """Save products to JSON file."""
    
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / filename
    
    # Add metadata
    output_data = {
        "scrape_date": datetime.utcnow().isoformat(),
        "total_products": len(products),
        "total_variants": sum([len(p["variants"]) for p in products]),
        "source": "https://one8.com",
        "products": products,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(products)} products to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path


def main():
    """Main scraping workflow."""
    
    print("🏏 ONE8 PRODUCT SCRAPER")
    print("   Virat Kohli's Lifestyle Brand")
    print("   https://one8.com/\n")
    
    # Fetch raw product data from Shopify
    raw_products = fetch_all_products()
    
    if not raw_products:
        print("\n❌ No products found!")
        return
    
    # Extract and structure data
    products = extract_product_info(raw_products)
    
    # Analyze catalog
    analyze_catalog(products)
    
    # Save to JSON
    output_path = save_to_json(products)
    
    print("\n✅ Scraping complete!")
    print("\n📋 Next steps:")
    print(f"   1. Review: cat {output_path}")
    print("   2. Generate seed data with fake orders/ad spend")
    print("   3. Import into AlpMark database")


if __name__ == "__main__":
    main()
