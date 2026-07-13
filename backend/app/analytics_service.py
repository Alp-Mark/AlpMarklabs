"""Analytics business logic for dashboard endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    GoogleAdSpend,
    MetaAdSpend,
    ShopifyOrder,
    ShopifyOrderLineItem,
)
from backend.app.schemas.analytics import (
    ChannelBreakdownItem,
    ChannelBreakdownResponse,
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
    """Get top-selling products by quantity and revenue.

    Aggregates across all line items in the period, ranking by revenue.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        period_start: Start date (inclusive)
        period_end: End date (inclusive)
        limit: Number of top products to return (default 10)

    Returns:
        TopProductsResponse with top products and metadata
    """
    # Get all line items in period, grouped by SKU
    period_end_inclusive = period_end + timedelta(days=1)

    stmt = select(
        ShopifyOrderLineItem.sku,
        ShopifyOrderLineItem.product_title,
        ShopifyOrderLineItem.variant_title,
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
        ShopifyOrderLineItem.sku,
        ShopifyOrderLineItem.product_title,
        ShopifyOrderLineItem.variant_title,
    ).order_by(
        func.sum(
            ShopifyOrderLineItem.quantity * ShopifyOrderLineItem.unit_price
        ).desc()
    ).limit(limit)

    results = db.execute(stmt).fetchall()

    products = [
        TopProduct(
            sku=row.sku or "unknown",
            product_title=row.product_title,
            variant_title=row.variant_title,
            quantity_sold=int(row.quantity_sold or 0),
            total_revenue=float(row.total_revenue or 0),
            avg_unit_price=float(row.avg_unit_price or 0),
            avg_quantity_per_order=float(row.avg_quantity_per_order or 1),
        )
        for row in results
    ]

    # Get total stats
    total_products_stmt = select(
        func.count(func.distinct(ShopifyOrderLineItem.sku))
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

    # Meta spend attribution
    meta_stmt = select(
        func.count().label("count"),
        func.sum(MetaAdSpend.spend_amount).label("total_spend"),
    ).where(
        MetaAdSpend.tenant_id == tenant_id,
        MetaAdSpend.spend_date >= period_start,
        MetaAdSpend.spend_date <= period_end,
    )

    meta_result = db.execute(meta_stmt).first()
    if meta_result and meta_result[1]:  # If there's spend
        # Simple attribution: assume proportion based on spend
        # In a real system, you'd have explicit attribution data
        meta_orders_count = int(total_orders * 0.25) if total_orders > 0 else 0
        meta_revenue = (
            sum(all_orders.values()) * 0.25 if all_orders else 0.0
        )
        channels_breakdown["meta"]["order_count"] = meta_orders_count
        channels_breakdown["meta"]["revenue"] = meta_revenue
        channels_breakdown["meta"]["conversion_count"] = meta_orders_count

    # Google spend attribution
    google_stmt = select(
        func.count().label("count"),
        func.sum(GoogleAdSpend.spend_amount).label("total_spend"),
    ).where(
        GoogleAdSpend.tenant_id == tenant_id,
        GoogleAdSpend.spend_date >= period_start,
        GoogleAdSpend.spend_date <= period_end,
    )

    google_result = db.execute(google_stmt).first()
    if google_result and google_result[1]:  # If there's spend
        google_orders_count = (
            int(total_orders * 0.20) if total_orders > 0 else 0
        )
        google_revenue = (
            sum(all_orders.values()) * 0.20 if all_orders else 0.0
        )
        channels_breakdown["google"]["order_count"] = google_orders_count
        channels_breakdown["google"]["revenue"] = google_revenue
        channels_breakdown["google"]["conversion_count"] = google_orders_count

    # Note: Marketing channel spends (influencer, email, tv_streaming, affiliate)
    # will be integrated in Steps 4-10 when MarketingChannelSpend model is available.
    # For now, leave these channels with zero values.

    # Calculate organic = total - attributed
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
    organic_revenue = max(0.0, sum(all_orders.values()) - attributed_revenue)

    channels_breakdown["organic"]["order_count"] = organic_orders
    channels_breakdown["organic"]["revenue"] = organic_revenue

    total_revenue = sum(all_orders.values())

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
