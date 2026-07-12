"""
Daily Data Simulator for One8 Tenant

Simulates continuous Shopify and ad platform data ingestion by generating
realistic daily data. Runs as a scheduled Celery task.

This allows testing the optimization engine with a growing, realistic dataset
without needing actual platform connections.

ℹ️  NOTE: Generates simulated data for One8 test tenant for demo/testing purposes.
"""

import json
import logging
import math
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.app.db.session import SessionLocal
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# One8 tenant configuration (test/demo tenant)
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# ── Load product catalog (same as seed script) ─────────────────────────────────
_CATALOG: list[tuple[str, str, str, int, int, int]] | None = None

def _load_product_catalog() -> list[tuple[str, str, str, int, int, int]]:
    """Load One8 product catalog: (sku, title, variant, price, cost, stock)"""
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    
    products_file = Path(__file__).parent.parent.parent / "data" / "one8_products.json"
    with open(products_file) as f:
        catalog_data = json.load(f)
    
    COGS_PCT: dict[str, float] = {
        "T-Shirt": 28.0, "Polo": 30.0, "Tank Top": 28.0, "Shorts": 30.0,
        "Leggings": 30.0, "Sweatshirt": 32.0, "Pants": 32.0, "Jacket": 34.0,
        "Caps": 26.0, "Sneakers": 36.0, "Cricket Shoes": 36.0,
    }
    DEFAULT_COGS_PCT = 32.0
    
    catalog = []
    for prod in catalog_data["products"]:
        ptype = prod.get("product_type", "")
        cogs_pct = COGS_PCT.get(ptype, DEFAULT_COGS_PCT)
        title = prod["title"]
        for v in prod["variants"]:
            price = int(v["price"]) if v.get("price") else 0
            if price == 0:
                continue
            cost = max(1, int(price * cogs_pct / 100))
            sku = v.get("sku") or f"ONE8-{v['variant_id']}"
            variant_title = v.get("title", "")
            stock = max(0, v.get("inventory_quantity") or 0)
            catalog.append((sku, title, variant_title, price, cost, stock))
    
    _CATALOG = catalog
    logger.info(f"Loaded {len(catalog)} product variants")
    return catalog

# ── One8 brand business parameters (must match scripts/seed_one8_realistic.py) ────
# Observable business KPIs only — no Hill curve parameters.
# The optimizer discovers the saturation curves from the data we generate here.
ONE8_BRAND = {
    "meta_base_spend":   180_000,
    "google_base_spend": 110_000,
    "meta_base_cac":   920,
    "google_base_cac": 650,
    "meta_cac_at_2x_spend_increase_pct":   30,
    "google_cac_at_2x_spend_increase_pct": 45,
    "organic_orders_per_day": 50,
    "base_aov":        6_500,
    "aov_std_dev":     2_500,
    "return_rate":     0.12,
    "refund_min_days": 3,
    "refund_max_days": 10,
    "loyal_pool_size":    2_000,
    "repeat_order_share": 0.25,
}

# Multi-channel configuration (influencer, email, TV, affiliate)
MULTI_CHANNELS = {
    "influencer": {
        "base_spend": 25_000,
        "base_cac": 1_100,
        "cac_at_2x_pct": 50,
        "campaigns": ["Nano Influencers", "Micro Influencers", "Macro Influencers"],
    },
    "email": {
        "base_spend": 15_000,
        "base_cac": 380,
        "cac_at_2x_pct": 20,
        "campaigns": ["Win-Back", "Abandoned Cart", "Product Launch"],
    },
    "tv_streaming": {
        "base_spend": 50_000,
        "base_cac": 1_500,
        "cac_at_2x_pct": 65,
        "campaigns": ["IPL Sponsorship", "World Cup Ads", "Brand Films"],
    },
    "affiliate": {
        "base_spend": 20_000,
        "base_cac": 750,
        "cac_at_2x_pct": 35,
        "campaigns": ["Cashback Networks", "Coupon Sites", "Rewards Programs"],
    },
}

# Campaign cycle epochs — same as seed script so daily data continues the pattern
_META_EPOCH   = date(2026, 1, 1)
_GOOGLE_EPOCH = date(2026, 1, 10)

# Loyal customer pool — same ID format as seed
_LOYAL_POOL = [f"loyal_{i:05d}" for i in range(1, int(ONE8_BRAND["loyal_pool_size"]) + 1)]


# ── Helpers (identical logic to seed script) ───────────────────────────────────

def _get_seasonality_multiplier(d: date) -> float:
    month, day = d.month, d.day
    if (month == 10 and day >= 24) or (month == 11 and day <= 15):
        gap = abs((datetime(d.year, 11, 1).date() - d).days)
        if gap <= 3:
            return 2.0
        if gap <= 10:
            return 1.6
        return 1.3
    if month in (3, 4, 5):
        return 1.5
    if month == 10 and day < 24:
        return 1.4
    if (month == 12 and day >= 20) or (month == 1 and day <= 10):
        return 1.3
    if month == 2 and 10 <= day <= 15:
        return 1.2
    if month in (6, 7, 8):
        return 0.85
    return 1.0


def _get_weekend_multiplier(d: date) -> float:
    wd = d.weekday()
    if wd == 4:
        return 1.25
    if wd == 5:
        return 1.40
    if wd == 6:
        return 1.35
    return 1.0


def _meta_campaign_phase(d: date) -> float:
    phase = (d - _META_EPOCH).days % 45
    if 3 <= phase <= 16:
        return 1.9
    if phase <= 22:
        return 1.3
    return 1.0


def _google_campaign_phase(d: date) -> float:
    phase = (d - _GOOGLE_EPOCH).days % 33
    if 12 <= phase <= 21:
        return 1.6
    if phase <= 26:
        return 1.15
    return 1.0


def _paid_conversions(spend: int | float, base_spend: int | float,
                      base_cac: int | float,
                      cac_increase_at_2x_pct: int | float) -> int:
    """CAC-driven conversions with diminishing returns. No Hill curve params."""
    if spend <= 0:
        return 0
    cac_at_2x     = 1.0 + cac_increase_at_2x_pct / 100.0
    exponent      = math.log(cac_at_2x) / math.log(2)
    effective_cac = base_cac * (spend / base_spend) ** exponent
    return max(0, int(spend / effective_cac))


def _pick_customer_id() -> str:
    if random.random() < ONE8_BRAND["repeat_order_share"]:
        return random.choice(_LOYAL_POOL)
    return f"new_{uuid.uuid4().hex[:10]}"


def _seasonal_aov(d: date) -> int:
    season = _get_seasonality_multiplier(d)
    if season >= 2.0:
        mult = 1.30
    elif season >= 1.5:
        mult = 1.10
    elif season <= 0.85:
        mult = 0.92
    else:
        mult = 1.0
    return max(
        1_000,
        int(random.gauss(ONE8_BRAND["base_aov"] * mult, ONE8_BRAND["aov_std_dev"])),
    )

# Campaign names (consistent with seed data)
META_CAMPAIGNS = [
    "TOF_Prospecting_Lookalike",
    "MOF_Retargeting_Engagement",
    "BOF_Conversion_Purchase",
]

GOOGLE_CAMPAIGNS = [
    "Search_Brand_One8",
    "Search_Generic_Sportswear",
    "Display_Prospecting_Sports",
]


def get_connector_id(db: Session) -> str:
    """Get the Shopify connector ID for One8 tenant."""
    result = db.execute(
        text(
            """
        SELECT id FROM connector_integrations 
        WHERE tenant_id = :tid 
        LIMIT 1
        """
        ),
        {"tid": ONE8_TENANT_ID},
    ).fetchone()

    if not result:
        raise ValueError(f"No connector found for tenant {ONE8_TENANT_ID}")

    return str(result[0])


def generate_daily_orders(
    db: Session, connector_id: str, target_date: date
) -> dict[str, Any]:
    """
    Generate realistic orders for target_date using the CAC-driven model.

    Paid conversions are derived from today's ad spend via the same CAC model
    as the seed script so the optimizer sees a consistent data-generating process.
    Seasonality lives in the organic channel only, keeping paid curves clean.
    """
    # Spend for today (same campaign-phase logic as seed)
    meta_spend   = max(0, int(
        ONE8_BRAND["meta_base_spend"]
        * _meta_campaign_phase(target_date)
        * random.uniform(0.85, 1.15)
        * (0.88 if target_date.weekday() in (5, 6) else 1.0)
    ))
    google_spend = max(0, int(
        ONE8_BRAND["google_base_spend"]
        * _google_campaign_phase(target_date)
        * random.uniform(0.88, 1.12)
        * (0.92 if target_date.weekday() in (5, 6) else 1.0)
    ))

    # Paid conversions from CAC model (no Hill curve parameters)
    meta_paid   = _paid_conversions(
        meta_spend,
        ONE8_BRAND["meta_base_spend"],
        ONE8_BRAND["meta_base_cac"],
        ONE8_BRAND["meta_cac_at_2x_spend_increase_pct"],
    )
    google_paid = _paid_conversions(
        google_spend,
        ONE8_BRAND["google_base_spend"],
        ONE8_BRAND["google_base_cac"],
        ONE8_BRAND["google_cac_at_2x_spend_increase_pct"],
    )

    # Organic: ALL seasonality and weekend uplift lives here
    organic = max(0, int(
        ONE8_BRAND["organic_orders_per_day"]
        * _get_seasonality_multiplier(target_date)
        * _get_weekend_multiplier(target_date)
        * random.uniform(0.85, 1.15)
    ))

    num_orders = max(
        0,
        int((meta_paid + google_paid + organic) * random.uniform(0.94, 1.06)),
    )

    m_phase = _meta_campaign_phase(target_date)
    g_phase = _google_campaign_phase(target_date)

    orders_batch = []
    total_revenue = Decimal("0")

    for _ in range(num_orders):
        order_value = _seasonal_aov(target_date)

        # Discount during campaign bursts
        if m_phase >= 1.9:
            discount = int(order_value * 0.15)
        elif g_phase >= 1.6:
            discount = int(order_value * 0.08)
        else:
            discount = 0

        net_value = max(500, order_value - discount)

        order_datetime = datetime.combine(target_date, datetime.min.time()).replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )

        ext_id = str(random.randint(10_000_000, 99_999_999))
        orders_batch.append({
            "id":                str(uuid.uuid4()),
            "tenant_id":         ONE8_TENANT_ID,
            "connector_id":      connector_id,
            "external_order_id": ext_id,
            "customer_id":       _pick_customer_id(),
            "order_number":      ext_id,
            "currency":          "INR",
            "total_amount":      float(net_value),
            "discount_amount":   float(discount),
            "shipping_amount":   0.0,
            "refund_amount":     0.0,
            "is_refunded":       False,
            "order_created_at":  order_datetime,
            "synced_at":         datetime.utcnow(),
        })
        total_revenue += Decimal(str(net_value))

    if orders_batch:
        db.execute(
            text("""
                INSERT INTO shopify_orders (
                    id, tenant_id, connector_id, external_order_id, customer_id,
                    order_number, currency, total_amount, discount_amount,
                    shipping_amount, refund_amount, is_refunded,
                    order_created_at, synced_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_order_id, :customer_id,
                    :order_number, :currency, :total_amount, :discount_amount,
                    :shipping_amount, :refund_amount, :is_refunded,
                    :order_created_at, :synced_at
                )
            """),
            orders_batch,
        )
        db.commit()

    return {
        "orders_created": len(orders_batch),
        "revenue":        float(total_revenue),
        "meta_spend":     meta_spend,
        "google_spend":   google_spend,
    }


def generate_daily_refunds(db: Session, connector_id: str) -> dict[str, Any]:
    """
    Generate refunds for orders from 3-10 days ago.
    
    Simulates the natural delay in returns.
    """
    # Get eligible orders (paid, not refunded, 3-10 days old)
    min_age = datetime.utcnow() - timedelta(days=ONE8_BRAND["refund_max_days"])
    max_age = datetime.utcnow() - timedelta(days=ONE8_BRAND["refund_min_days"])

    eligible_orders = db.execute(
        text(
            """
        SELECT id, external_order_id, total_amount, order_created_at
        FROM shopify_orders
        WHERE tenant_id = :tid
        AND is_refunded = false
        AND order_created_at BETWEEN :min_age AND :max_age
        ORDER BY RANDOM()
        LIMIT 100
        """
        ),
        {"tid": ONE8_TENANT_ID, "min_age": min_age, "max_age": max_age},
    ).fetchall()

    if not eligible_orders:
        return {"refunds_created": 0, "refund_amount": 0.0}

    # Select orders for refund based on return rate
    num_refunds = int(len(eligible_orders) * ONE8_BRAND["return_rate"])
    refund_orders = random.sample(
        list(eligible_orders), min(num_refunds, len(eligible_orders))
    )

    refunds_batch = []
    total_refund_amount = Decimal("0")

    for order in refund_orders:
        refund_date = datetime.utcnow()
        external_refund_id = f"refund_{random.randint(1000000, 9999999)}"

        refunds_batch.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_refund_id": external_refund_id,
                "order_id": order[0],
                "external_order_id": order[1],
                "refund_amount": order[2],
                "reason": random.choice(
                    ["customer_request", "defective", "size_issue", "changed_mind"]
                ),
                "refund_created_at": refund_date,
                "synced_at": refund_date,
                "created_at": refund_date,
            }
        )

        total_refund_amount += Decimal(str(order[2]))

    # Mark orders as refunded directly on shopify_orders
    # (there is no separate shopify_refunds table — refunds are tracked
    # via is_refunded + refund_amount on the orders row)
    if refunds_batch:
        for r in refunds_batch:
            db.execute(
                text(
                    """
                UPDATE shopify_orders
                SET is_refunded = true,
                    refund_amount = :refund_amount
                WHERE id = :order_id
                  AND tenant_id = :tenant_id
                """
                ),
                {
                    "refund_amount": r["refund_amount"],
                    "order_id": r["order_id"],
                    "tenant_id": ONE8_TENANT_ID,
                },
            )
        db.commit()

    return {
        "refunds_created": len(refunds_batch),
        "refund_amount": float(total_refund_amount),
    }


def generate_daily_ad_spend(
    db: Session, connector_id: str, target_date: date
) -> dict[str, Any]:
    """
    Generate daily ad spend for Meta and Google.
    Uses the same independent campaign cycles as the seed script.
    """
    meta_batch   = []
    google_batch = []

    # Spend derived from campaign phase (same logic as seed)
    daily_meta_total = max(0, int(
        ONE8_BRAND["meta_base_spend"]
        * _meta_campaign_phase(target_date)
        * random.uniform(0.85, 1.15)
        * (0.88 if target_date.weekday() in (5, 6) else 1.0)
    ))
    daily_google_total = max(0, int(
        ONE8_BRAND["google_base_spend"]
        * _google_campaign_phase(target_date)
        * random.uniform(0.88, 1.12)
        * (0.92 if target_date.weekday() in (5, 6) else 1.0)
    ))

    for campaign in META_CAMPAIGNS:
        meta_batch.append({
            "id":                   str(uuid.uuid4()),
            "tenant_id":            ONE8_TENANT_ID,
            "connector_id":         connector_id,
            "external_campaign_id": f"meta_{campaign}_{target_date.strftime('%Y%m%d')}",
            "campaign_name":        campaign,
            "spend_date":           target_date,
            "currency":             "INR",
            "spend_amount":         float(daily_meta_total / len(META_CAMPAIGNS)),
            "synced_at":            datetime.utcnow(),
            "created_at":           datetime.utcnow(),
            "updated_at":           datetime.utcnow(),
        })

    for campaign in GOOGLE_CAMPAIGNS:
        google_batch.append({
            "id":                   str(uuid.uuid4()),
            "tenant_id":            ONE8_TENANT_ID,
            "connector_id":         connector_id,
            "external_campaign_id": (
                    f"google_{campaign}_{target_date.strftime('%Y%m%d')}"
                ),
            "campaign_name":        campaign,
            "spend_date":           target_date,
            "currency":             "INR",
            "spend_amount":         float(daily_google_total / len(GOOGLE_CAMPAIGNS)),
            "synced_at":            datetime.utcnow(),
            "created_at":           datetime.utcnow(),
            "updated_at":           datetime.utcnow(),
        })

    # Insert ad spend
    if meta_batch:
        db.execute(
            text(
                """
            INSERT INTO meta_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount,
                :synced_at, :created_at, :updated_at
            )
            """
            ),
            meta_batch,
        )

    if google_batch:
        db.execute(
            text(
                """
            INSERT INTO google_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount,
                :synced_at, :created_at, :updated_at
            )
            """
            ),
            google_batch,
        )

    db.commit()

    return {
        "meta_spend":   daily_meta_total,
        "google_spend": daily_google_total,
        "total_spend":  daily_meta_total + daily_google_total,
    }


def generate_daily_multi_channel_spend(
    db: Session, connector_id: str, target_date: date
) -> dict[str, Any]:
    """
    Generate multi-channel spend (influencer, email, TV, affiliate).
    Uses same CAC-driven model as seed script.
    """
    multi_channel_batch = []
    total_by_channel = {}

    for channel_name, config in MULTI_CHANNELS.items():
        # Simple multiplier for day-to-day variance
        daily_mult = random.uniform(0.85, 1.15)
        
        # Calculate daily spend
        daily_spend = max(0, int(config["base_spend"] * daily_mult))
        
        # Calculate conversions from spend using CAC model
        spend_ratio = daily_spend / config["base_spend"]
        cac_at_2x = 1.0 + config["cac_at_2x_pct"] / 100.0
        exponent = math.log(cac_at_2x) / math.log(2)
        effective_cac = config["base_cac"] * (spend_ratio ** exponent)
        conversions = max(0, int(daily_spend / effective_cac)) if effective_cac > 0 else 0
        
        # Revenue estimation (assume similar AOV to organic)
        avg_revenue_per_conv = ONE8_BRAND["base_aov"]
        estimated_revenue = conversions * avg_revenue_per_conv * random.uniform(0.9, 1.1)
        
        # Split across campaigns
        for campaign_name in config["campaigns"]:
            campaign_spend = daily_spend / len(config["campaigns"])
            campaign_conversions = conversions // len(config["campaigns"])
            campaign_revenue = estimated_revenue / len(config["campaigns"])
            
            multi_channel_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "channel_name": channel_name,
                "external_campaign_id": f"{channel_name}_{campaign_name.replace(' ', '_')}_{target_date.strftime('%Y%m%d')}",
                "campaign_name": campaign_name,
                "spend_date": target_date,
                "currency": "INR",
                "spend_amount": float(campaign_spend),
                "conversions": campaign_conversions,
                "revenue": float(campaign_revenue),
                "impressions": None,
                "clicks": None,
                "synced_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        
        total_by_channel[channel_name] = daily_spend

    # Insert multi-channel spend
    if multi_channel_batch:
        db.execute(
            text("""
                INSERT INTO marketing_channel_spends (
                    id, tenant_id, connector_id, channel_name,
                    external_campaign_id, campaign_name,
                    spend_date, currency, spend_amount,
                    conversions, revenue, impressions, clicks,
                    synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :channel_name,
                    :external_campaign_id, :campaign_name,
                    :spend_date, :currency, :spend_amount,
                    :conversions, :revenue, :impressions, :clicks,
                    :synced_at, :created_at, :updated_at
                )
            """),
            multi_channel_batch,
        )
        db.commit()

    return {
        "records_created": len(multi_channel_batch),
        "by_channel": total_by_channel,
        "total_spend": sum(total_by_channel.values()),
    }


def generate_daily_line_items(
    db: Session, target_date: date
) -> dict[str, Any]:
    """
    Generate line items for orders created on target_date.
    Uses product catalog to create realistic line items matching order totals.
    """
    catalog = _load_product_catalog()
    
    # Group products by price tier for realistic order composition
    tier_low = [c for c in catalog if c[3] <= 2_500]
    tier_mid = [c for c in catalog if 2_501 <= c[3] <= 5_500]
    tier_high = [c for c in catalog if c[3] > 5_500]
    accessories = [c for c in catalog if c[3] <= 2_000]
    
    # Get orders for target date
    orders = db.execute(
        text("""
            SELECT id, total_amount, order_created_at
            FROM shopify_orders
            WHERE tenant_id = :tid
              AND order_created_at::date = :target_date
            ORDER BY order_created_at
        """),
        {"tid": ONE8_TENANT_ID, "target_date": target_date},
    ).fetchall()
    
    if not orders:
        return {"line_items_created": 0, "orders_processed": 0}
    
    line_items_batch = []
    
    for order in orders:
        order_id, order_total, order_created_at = order[0], order[1], order[2]
        
        # Select products based on order total
        if order_total <= 2_800:
            pool = tier_low or tier_mid
        elif order_total <= 6_000:
            pool = tier_mid or tier_high
        else:
            pool = tier_high or tier_mid
        
        if not pool:
            continue
        
        primary = random.choice(pool)
        items_for_order = [(primary, 1)]
        
        # 35% chance of adding an accessory
        if random.random() < 0.35 and accessories:
            acc = random.choice(accessories)
            if acc[0] != primary[0]:  # Different SKU
                items_for_order.append((acc, 1))
        
        for idx, (cat_row, qty) in enumerate(items_for_order):
            sku, title, variant, sell_price, _cost, _stock = cat_row
            line_items_batch.append({
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "order_id": order_id,
                "line_item_index": idx,
                "sku": sku,
                "product_title": title,
                "variant_title": variant,
                "quantity": qty,
                "unit_price": float(sell_price),
                "order_created_at": order_created_at,
            })
    
    # Insert line items
    if line_items_batch:
        db.execute(
            text("""
                INSERT INTO shopify_order_line_items (
                    id, tenant_id, order_id, line_item_index,
                    sku, product_title, variant_title,
                    quantity, unit_price, order_created_at
                ) VALUES (
                    :id, :tenant_id, :order_id, :line_item_index,
                    :sku, :product_title, :variant_title,
                    :quantity, :unit_price, :order_created_at
                )
            """),
            line_items_batch,
        )
        db.commit()
    
    avg_items = len(line_items_batch) / len(orders) if orders else 0
    
    return {
        "line_items_created": len(line_items_batch),
        "orders_processed": len(orders),
        "avg_items_per_order": round(avg_items, 2),
    }


def run_daily_simulation(target_date: date | None = None) -> dict[str, Any]:
    """
    Run daily data simulation for One8 tenant.
    
    Args:
        target_date: Date to generate data for. Defaults to today.
    
    Returns:
        Summary statistics
    """
    if target_date is None:
        target_date = date.today()

    db = SessionLocal()

    try:
        # Check if data already exists for this date
        existing_orders = db.execute(
            text(
                """
            SELECT COUNT(*) FROM shopify_orders
            WHERE tenant_id = :tid
            AND order_created_at::date = :target_date
            """
            ),
            {"tid": ONE8_TENANT_ID, "target_date": target_date},
        ).scalar()

        if existing_orders and existing_orders > 0:
            return {
                "status": "skipped",
                "reason": f"Data already exists for {target_date}",
                "existing_orders": existing_orders,
            }

        # Get connector
        connector_id = get_connector_id(db)

        # Log data generation
        logger.info(
            f"Generating simulated data for One8 test tenant ({ONE8_TENANT_ID}) "
            f"for date {target_date}"
        )

        # Generate data
        orders_stats = generate_daily_orders(db, connector_id, target_date)
        refunds_stats = generate_daily_refunds(db, connector_id)
        ad_spend_stats = generate_daily_ad_spend(db, connector_id, target_date)
        multi_channel_stats = generate_daily_multi_channel_spend(db, connector_id, target_date)
        line_items_stats = generate_daily_line_items(db, target_date)

        logger.info(
            f"Successfully generated: {orders_stats['orders_created']} orders, "
            f"{line_items_stats['line_items_created']} line items, "
            f"{refunds_stats['refunds_created']} refunds, "
            f"₹{ad_spend_stats['total_spend']:,.0f} ad spend, "
            f"₹{multi_channel_stats['total_spend']:,.0f} multi-channel spend"
        )

        return {
            "status": "success",
            "date": str(target_date),
            "orders": orders_stats,
            "line_items": line_items_stats,
            "refunds": refunds_stats,
            "ad_spend": ad_spend_stats,
            "multi_channel": multi_channel_stats,
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "date": str(target_date) if target_date else "unknown",
            "error": str(e),
        }

    finally:
        db.close()


# Convenience function for manual testing
def simulate_date_range(start_date: date, end_date: date) -> dict[str, Any]:
    """
    Simulate data for a range of dates.
    
    Useful for backfilling or testing.
    """
    current_date = start_date
    results = []

    while current_date <= end_date:
        result = run_daily_simulation(current_date)
        results.append(result)
        current_date += timedelta(days=1)

    return {
        "dates_processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }
