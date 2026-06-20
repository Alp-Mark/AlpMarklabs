"""Growth dashboard business logic and calculations."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import GoogleAdSpend, MetaAdSpend, ShopifyOrder
from backend.app.schemas.growth import (
    CampaignPerformance,
    ChannelPerformance,
    GrowthDashboardResponse,
)

if TYPE_CHECKING:
    from uuid import UUID


def calculate_growth_dashboard(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> GrowthDashboardResponse:
    """Calculate growth dashboard metrics for a tenant and date range.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        period_start: Start of analysis period (inclusive)
        period_end: End of analysis period (inclusive)

    Returns:
        GrowthDashboardResponse with channel and campaign performance
    """
    # Query Meta ad spend
    meta_campaigns_query = (
        select(
            MetaAdSpend.external_campaign_id,
            MetaAdSpend.campaign_name,
            func.sum(MetaAdSpend.spend_amount).label("total_spend"),
        )
        .where(MetaAdSpend.tenant_id == tenant_id)
        .where(MetaAdSpend.spend_date >= period_start)
        .where(MetaAdSpend.spend_date <= period_end)
        .group_by(MetaAdSpend.external_campaign_id, MetaAdSpend.campaign_name)
    )
    meta_campaigns = list(db.execute(meta_campaigns_query).all())

    # Query Google ad spend
    google_campaigns_query = (
        select(
            GoogleAdSpend.external_campaign_id,
            GoogleAdSpend.campaign_name,
            func.sum(GoogleAdSpend.spend_amount).label("total_spend"),
        )
        .where(GoogleAdSpend.tenant_id == tenant_id)
        .where(GoogleAdSpend.spend_date >= period_start)
        .where(GoogleAdSpend.spend_date <= period_end)
        .group_by(GoogleAdSpend.external_campaign_id, GoogleAdSpend.campaign_name)
    )
    google_campaigns = list(db.execute(google_campaigns_query).all())

    # Calculate total spend per channel
    meta_total_spend = sum(c.total_spend for c in meta_campaigns)
    google_total_spend = sum(c.total_spend for c in google_campaigns)
    total_spend = meta_total_spend + google_total_spend

    # Query revenue and orders
    revenue_query = (
        select(
            func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label(
                "total_revenue"
            ),
            func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label(
                "total_refunds"
            ),
            func.count(ShopifyOrder.id).label("order_count"),
            func.count(func.distinct(ShopifyOrder.customer_id)).label(
                "unique_customers"
            ),
            func.max(ShopifyOrder.synced_at).label("last_synced"),
        )
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
    )
    revenue_result = db.execute(revenue_query).one()
    total_revenue = float(revenue_result.total_revenue or 0.0)
    total_refunds = float(revenue_result.total_refunds or 0.0)
    net_revenue = total_revenue - total_refunds
    order_count = int(revenue_result.order_count or 0)
    unique_customers = int(revenue_result.unique_customers or 0)
    last_synced = revenue_result.last_synced

    # Calculate new customers (first order in this period)
    # For simplicity, we'll use unique customers as proxy for new customers
    # In production, this would check if customer_id appears in prior periods
    new_customers = unique_customers

    # Calculate blended metrics
    blended_roas = net_revenue / total_spend if total_spend > 0 else None
    blended_cac = total_spend / new_customers if new_customers > 0 else None

    # Placeholder contribution margin (40%)
    blended_contribution_margin_pct = 40.0

    # Build channel performance
    channel_performance = _calculate_channel_performance(
        meta_spend=meta_total_spend,
        google_spend=google_total_spend,
        total_revenue=net_revenue,
        total_orders=order_count,
        new_customers=new_customers,
    )

    # Build campaign performance
    campaign_list = _build_campaign_list(
        meta_campaigns=meta_campaigns,
        google_campaigns=google_campaigns,
        total_revenue=net_revenue,
        total_orders=order_count,
    )

    # Sort campaigns by ROAS and identify top/underperforming
    campaigns_with_roas = [c for c in campaign_list if c.roas is not None]
    campaigns_with_roas.sort(key=lambda c: c.roas or 0.0, reverse=True)

    top_campaigns = campaigns_with_roas[:5]

    # Underperforming: ROAS < 2.0
    underperforming_campaigns = [
        c for c in campaign_list if c.roas is not None and c.roas < 2.0
    ]

    return GrowthDashboardResponse(
        total_spend=total_spend,
        total_revenue=net_revenue,
        blended_roas=blended_roas,
        total_orders=order_count,
        total_new_customers=new_customers,
        blended_cac=blended_cac,
        blended_contribution_margin_pct=blended_contribution_margin_pct,
        channel_performance=channel_performance,
        top_campaigns=top_campaigns,
        underperforming_campaigns=underperforming_campaigns,
        period_start=period_start,
        period_end=period_end,
        data_last_synced_at=last_synced.isoformat() if last_synced else None,
        currency="USD",
    )


def _calculate_channel_performance(
    meta_spend: float,
    google_spend: float,
    total_revenue: float,
    total_orders: int,
    new_customers: int,
) -> list[ChannelPerformance]:
    """Calculate per-channel performance metrics.

    For simplicity, we split revenue proportionally by spend.
    In production, this would use actual attribution data.
    """
    channels: list[ChannelPerformance] = []
    total_spend = meta_spend + google_spend

    if total_spend == 0:
        return channels

    # Meta channel
    if meta_spend > 0:
        meta_revenue_share = (meta_spend / total_spend) * total_revenue
        meta_orders = int((meta_spend / total_spend) * total_orders)
        meta_new_customers = int((meta_spend / total_spend) * new_customers)
        meta_roas = meta_revenue_share / meta_spend if meta_spend > 0 else None
        meta_cac = meta_spend / meta_new_customers if meta_new_customers > 0 else None
        meta_contribution_margin = meta_revenue_share * 0.4  # Placeholder 40%
        meta_contribution_margin_pct = 40.0

        channels.append(
            ChannelPerformance(
                channel="meta",
                total_spend=meta_spend,
                total_revenue=meta_revenue_share,
                roas=meta_roas,
                orders_count=meta_orders,
                new_customers=meta_new_customers,
                cac=meta_cac,
                cac_payback_days=None,  # Would need margin data
                contribution_margin=meta_contribution_margin,
                contribution_margin_pct=meta_contribution_margin_pct,
                trend="stable",
            )
        )

    # Google Ads channel
    if google_spend > 0:
        google_revenue_share = (google_spend / total_spend) * total_revenue
        google_orders = int((google_spend / total_spend) * total_orders)
        google_new_customers = int((google_spend / total_spend) * new_customers)
        google_roas = (
            google_revenue_share / google_spend if google_spend > 0 else None
        )
        google_cac = (
            google_spend / google_new_customers if google_new_customers > 0 else None
        )
        google_contribution_margin = google_revenue_share * 0.4
        google_contribution_margin_pct = 40.0

        channels.append(
            ChannelPerformance(
                channel="google_ads",
                total_spend=google_spend,
                total_revenue=google_revenue_share,
                roas=google_roas,
                orders_count=google_orders,
                new_customers=google_new_customers,
                cac=google_cac,
                cac_payback_days=None,
                contribution_margin=google_contribution_margin,
                contribution_margin_pct=google_contribution_margin_pct,
                trend="stable",
            )
        )

    return channels


def _build_campaign_list(
    meta_campaigns: list[Any],
    google_campaigns: list[Any],
    total_revenue: float,
    total_orders: int,
) -> list[CampaignPerformance]:
    """Build campaign performance list from Meta and Google campaigns."""
    campaigns: list[CampaignPerformance] = []

    # Meta campaigns
    total_meta_spend = sum(c.total_spend for c in meta_campaigns)
    for campaign in meta_campaigns:
        spend = float(campaign.total_spend)
        # Simple revenue attribution proportional to spend
        campaign_revenue = (
            (spend / total_meta_spend) * total_revenue * 0.5
            if total_meta_spend > 0
            else 0.0
        )
        campaign_orders = (
            int((spend / total_meta_spend) * total_orders * 0.5)
            if total_meta_spend > 0
            else 0
        )
        roas = campaign_revenue / spend if spend > 0 else None
        cac = spend / campaign_orders if campaign_orders > 0 else None

        campaigns.append(
            CampaignPerformance(
                campaign_id=campaign.external_campaign_id,
                campaign_name=campaign.campaign_name,
                channel="meta",
                spend=spend,
                revenue=campaign_revenue if campaign_revenue > 0 else None,
                roas=roas,
                orders_count=campaign_orders,
                cac=cac,
                is_underperforming=roas is not None and roas < 2.0,
            )
        )

    # Google campaigns
    total_google_spend = sum(c.total_spend for c in google_campaigns)
    for campaign in google_campaigns:
        spend = float(campaign.total_spend)
        campaign_revenue = (
            (spend / total_google_spend) * total_revenue * 0.5
            if total_google_spend > 0
            else 0.0
        )
        campaign_orders = (
            int((spend / total_google_spend) * total_orders * 0.5)
            if total_google_spend > 0
            else 0
        )
        roas = campaign_revenue / spend if spend > 0 else None
        cac = spend / campaign_orders if campaign_orders > 0 else None

        campaigns.append(
            CampaignPerformance(
                campaign_id=campaign.external_campaign_id,
                campaign_name=campaign.campaign_name,
                channel="google_ads",
                spend=spend,
                revenue=campaign_revenue if campaign_revenue > 0 else None,
                roas=roas,
                orders_count=campaign_orders,
                cac=cac,
                is_underperforming=roas is not None and roas < 2.0,
            )
        )

    return campaigns
