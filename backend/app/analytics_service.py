"""Analytics business logic for dashboard endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    GoogleAdSpend,
    MarketingChannelSpend,
    MetaAdSpend,
    ShopifyInventoryItem,
    ShopifyOrder,
    ShopifyOrderLineItem,
)
from backend.app.schemas.analytics import (
    ChannelBreakdownItem,
    ChannelBreakdownResponse,
    ProductVariantsResponse,
    TopProduct,
    TopProductsResponse,
)


def get_top_products(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
    limit: int = 10,
) -> TopProductsResponse:
    """Get top-selling products by revenue in a given period.

    Products are aggregated across all SKU variants (sizes, colors, etc).
    Ranks by total revenue, showing distinct products and their performance.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        period_start: Start date (inclusive)
        period_end: End date (inclusive)
        limit: Number of top products to return (default 10)

    Returns:
        TopProductsResponse with top products and metadata
    """
    # Get all line items in period, grouped by product (across all variants/sizes)
    period_end_inclusive = period_end + timedelta(days=1)

    stmt = select(
        ShopifyOrderLineItem.product_title,
        func.count(func.distinct(ShopifyOrderLineItem.sku)).label("variant_count"),
        func.sum(ShopifyOrderLineItem.quantity).label("quantity_sold"),
        func.sum(
            ShopifyOrderLineItem.quantity * ShopifyOrderLineItem.unit_price
        ).label("total_revenue"),
        func.avg(ShopifyOrderLineItem.unit_price).label("avg_unit_price"),
        func.avg(ShopifyOrderLineItem.quantity).label(
            "avg_quantity_per_order"
        ),
    ).where(
        ShopifyOrderLineItem.tenant_id == tenant_id,
        ShopifyOrderLineItem.order_created_at >= period_start,
        ShopifyOrderLineItem.order_created_at < period_end_inclusive,
    ).group_by(
        ShopifyOrderLineItem.product_title,
    ).order_by(
        func.sum(
            ShopifyOrderLineItem.quantity * ShopifyOrderLineItem.unit_price
        ).desc()
    ).limit(limit)

    results = db.execute(stmt).fetchall()

    products = [
        TopProduct(
            product_title=row.product_title,
            quantity_sold=int(row.quantity_sold or 0),
            total_revenue=float(row.total_revenue or 0),
            avg_unit_price=float(row.avg_unit_price or 0),
            avg_quantity_per_order=float(row.avg_quantity_per_order or 1),
            variant_count=int(row.variant_count or 0),
        )
        for row in results
    ]

    # Get total stats
    total_products_stmt = select(
        func.count(func.distinct(ShopifyOrderLineItem.product_title))
    ).where(
        ShopifyOrderLineItem.tenant_id == tenant_id,
        ShopifyOrderLineItem.order_created_at >= period_start,
        ShopifyOrderLineItem.order_created_at < period_end_inclusive,
    )

    total_products_count = db.execute(total_products_stmt).scalar() or 0

    total_orders_stmt = select(
        func.count(func.distinct(ShopifyOrder.id))
    ).where(
        ShopifyOrder.tenant_id == tenant_id,
        ShopifyOrder.order_created_at >= period_start,
        ShopifyOrder.order_created_at < period_end_inclusive,
    )

    total_orders_count = db.execute(total_orders_stmt).scalar() or 0

    return TopProductsResponse(
        products=products,
        period_start=period_start,
        period_end=period_end,
        total_products_count=int(total_products_count),
        total_orders=int(total_orders_count),
    )


def get_channel_breakdown(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> ChannelBreakdownResponse:
    """Get breakdown of orders and revenue by marketing channel.

    Channels include:
    - meta: Meta/Facebook ads
    - google: Google Ads
    - email: Email/SMS campaigns
    - influencer: Influencer partnerships
    - tv_streaming: TV/Streaming ads
    - affiliate: Affiliate marketing
    - organic: Non-paid traffic (inferred from orders without attributed spend)
    - direct: Direct traffic

    Args:
        db: Database session
        tenant_id: Tenant identifier
        period_start: Start date (inclusive)
        period_end: End date (inclusive)

    Returns:
        ChannelBreakdownResponse with channel breakdown and totals
    """
    period_end_inclusive = period_end + timedelta(days=1)

    # Get all orders in the period
    all_orders_stmt = select(
        ShopifyOrder.id,
        ShopifyOrder.total_amount,
    ).where(
        ShopifyOrder.tenant_id == tenant_id,
        ShopifyOrder.order_created_at >= period_start,
        ShopifyOrder.order_created_at < period_end_inclusive,
    )

    all_orders = {
        row[0]: row[1] for row in db.execute(all_orders_stmt).fetchall()
    }

    channels_breakdown: dict[str, dict] = {}
    total_orders = len(all_orders)

    # Initialize channels
    for channel in [
        "meta",
        "google",
        "email",
        "influencer",
        "tv_streaming",
        "affiliate",
        "direct",
        "organic",
    ]:
        channels_breakdown[channel] = {
            "order_count": 0,
            "revenue": 0.0,
            "conversion_count": 0,
        }

    # ── Real attribution from actual spend and conversion data ───────────────

    # 1. Meta and Google: proportional spend attribution
    meta_spend = db.scalar(
        select(func.sum(MetaAdSpend.spend_amount)).where(
            MetaAdSpend.tenant_id == tenant_id,
            MetaAdSpend.spend_date >= period_start,
            MetaAdSpend.spend_date <= period_end,
        )
    ) or 0.0

    google_spend = db.scalar(
        select(func.sum(GoogleAdSpend.spend_amount)).where(
            GoogleAdSpend.tenant_id == tenant_id,
            GoogleAdSpend.spend_date >= period_start,
            GoogleAdSpend.spend_date <= period_end,
        )
    ) or 0.0

    # 2. Influencer, email, affiliate: actual conversions from marketing_channel_spends
    TRACKED_CHANNELS = ("influencer", "email", "affiliate")
    mcs_rows = db.execute(
        select(
            MarketingChannelSpend.channel_name,
            func.sum(MarketingChannelSpend.conversions).label("total_conversions"),
            func.sum(MarketingChannelSpend.revenue).label("total_revenue"),
        )
        .where(
            MarketingChannelSpend.tenant_id == tenant_id,
            MarketingChannelSpend.channel_name.in_(TRACKED_CHANNELS),
            MarketingChannelSpend.spend_date >= period_start,
            MarketingChannelSpend.spend_date <= period_end,
        )
        .group_by(MarketingChannelSpend.channel_name)
    ).fetchall()

    mcs_conversions: dict[str, float] = {}
    mcs_revenue: dict[str, float] = {}
    for row in mcs_rows:
        mcs_conversions[row.channel_name] = float(row.total_conversions or 0)
        mcs_revenue[row.channel_name] = float(row.total_revenue or 0)

    # 3. Attribute orders: subtract mcs-attributed, split remainder by Meta/Google spend
    mcs_total_conv = sum(mcs_conversions.values())
    remaining_orders = max(0, total_orders - int(mcs_total_conv))
    total_revenue_val = sum(all_orders.values())
    remaining_revenue = max(0.0, total_revenue_val - sum(mcs_revenue.values()))

    paid_total = meta_spend + google_spend
    if paid_total > 0:
        meta_frac = meta_spend / paid_total
        google_frac = google_spend / paid_total
    else:
        meta_frac = 0.0
        google_frac = 0.0

    meta_orders = int(remaining_orders * meta_frac)
    google_orders = int(remaining_orders * google_frac)
    meta_rev = remaining_revenue * meta_frac
    google_rev = remaining_revenue * google_frac

    if meta_orders > 0 or meta_spend > 0:
        channels_breakdown["meta"]["order_count"] = meta_orders
        channels_breakdown["meta"]["revenue"] = meta_rev
        channels_breakdown["meta"]["conversion_count"] = meta_orders

    if google_orders > 0 or google_spend > 0:
        channels_breakdown["google"]["order_count"] = google_orders
        channels_breakdown["google"]["revenue"] = google_rev
        channels_breakdown["google"]["conversion_count"] = google_orders

    for ch in TRACKED_CHANNELS:
        conv = int(mcs_conversions.get(ch, 0))
        rev = mcs_revenue.get(ch, 0.0)
        if conv > 0 or rev > 0:
            channels_breakdown[ch]["order_count"] = conv
            channels_breakdown[ch]["revenue"] = rev
            channels_breakdown[ch]["conversion_count"] = conv

    # 4. Organic = whatever isn't attributed to paid/mcs channels
    attributed_orders = sum(
        c["order_count"]
        for ch, c in channels_breakdown.items()
        if ch != "organic"
    )
    organic_orders = max(0, total_orders - attributed_orders)

    attributed_revenue = sum(
        c["revenue"]
        for ch, c in channels_breakdown.items()
        if ch != "organic"
    )
    organic_revenue = max(0.0, total_revenue_val - attributed_revenue)

    channels_breakdown["organic"]["order_count"] = organic_orders
    channels_breakdown["organic"]["revenue"] = organic_revenue

    total_revenue = total_revenue_val

    # Build response
    channels = []
    for channel_name, data in channels_breakdown.items():
        if data["order_count"] > 0 or data["revenue"] > 0:
            revenue_pct = (
                (data["revenue"] / total_revenue * 100)
                if total_revenue > 0
                else 0
            )
            avg_order_value = (
                data["revenue"] / data["order_count"]
                if data["order_count"] > 0
                else 0
            )

            channels.append(
                ChannelBreakdownItem(
                    channel_name=channel_name,
                    order_count=data["order_count"],
                    revenue=data["revenue"],
                    revenue_pct=revenue_pct,
                    avg_order_value=avg_order_value,
                    conversion_count=data["conversion_count"],
                )
            )

    # Sort by revenue descending
    channels.sort(key=lambda x: x.revenue, reverse=True)

    return ChannelBreakdownResponse(
        channels=channels,
        total_revenue=total_revenue,
        total_orders=total_orders,
        period_start=period_start,
        period_end=period_end,
        currency="INR",
    )


def get_product_variants(
    db: Session,
    tenant_id: UUID,
    product_title: str,
    period_start: date,
    period_end: date,
) -> ProductVariantsResponse:
    """Get individual variants (SKUs) for a specific product.

    Shows revenue and quantity metrics for each size/color variant of a product.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        product_title: Product name to fetch variants for
        period_start: Start date (inclusive)
        period_end: End date (inclusive)

    Returns:
        ProductVariantsResponse with variant breakdown and totals
    """
    from backend.app.schemas.analytics import ProductVariant, ProductVariantsResponse

    period_end_inclusive = period_end + timedelta(days=1)

    # Get all variants of the product in the period
    stmt = select(
        ShopifyOrderLineItem.sku,
        ShopifyOrderLineItem.variant_title,
        ShopifyOrderLineItem.unit_price,
        func.sum(ShopifyOrderLineItem.quantity).label("quantity_sold"),
        func.sum(
            ShopifyOrderLineItem.quantity * ShopifyOrderLineItem.unit_price
        ).label("total_revenue"),
        func.avg(ShopifyOrderLineItem.unit_price).label("avg_unit_price"),
        func.max(ShopifyInventoryItem.image_url).label("image_url"),
    ).outerjoin(
        ShopifyInventoryItem,
        (ShopifyOrderLineItem.sku == ShopifyInventoryItem.sku)
        & (ShopifyInventoryItem.tenant_id == tenant_id),
    ).where(
        ShopifyOrderLineItem.tenant_id == tenant_id,
        ShopifyOrderLineItem.product_title == product_title,
        ShopifyOrderLineItem.order_created_at >= period_start,
        ShopifyOrderLineItem.order_created_at < period_end_inclusive,
    ).group_by(
        ShopifyOrderLineItem.sku,
        ShopifyOrderLineItem.variant_title,
        ShopifyOrderLineItem.unit_price,
    ).order_by(
        func.sum(
            ShopifyOrderLineItem.quantity * ShopifyOrderLineItem.unit_price
        ).desc()
    )

    results = db.execute(stmt).fetchall()

    variants = [
        ProductVariant(
            sku=row.sku or "unknown",
            variant_title=row.variant_title or "Standard",
            quantity_sold=int(row.quantity_sold or 0),
            total_revenue=float(row.total_revenue or 0),
            avg_unit_price=float(row.avg_unit_price or 0),
            unit_price=float(row.unit_price or 0),
            image_url=row.image_url,
        )
        for row in results
    ]

    total_revenue = sum(v.total_revenue for v in variants)
    total_quantity = sum(v.quantity_sold for v in variants)

    return ProductVariantsResponse(
        product_title=product_title,
        variants=variants,
        total_revenue=total_revenue,
        total_quantity=total_quantity,
        period_start=period_start,
        period_end=period_end,
        currency="INR",
    )
