"""Executive overview business logic and calculations."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    GoogleAdSpend,
    MetaAdSpend,
    ShopifyOrder,
)
from backend.app.schemas.executive import (
    BusinessHealthIndicator,
    ExecutiveOverviewResponse,
    TeamPerformanceSummary,
)

if TYPE_CHECKING:
    from uuid import UUID


def calculate_executive_overview(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> ExecutiveOverviewResponse:
    """Calculate executive overview metrics for a tenant and date range.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        period_start: Start of analysis period (inclusive)
        period_end: End of analysis period (inclusive)

    Returns:
        ExecutiveOverviewResponse with calculated metrics
    """
    # Query revenue from Shopify orders
    revenue_query = (
        select(
            func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label(
                "total_revenue"
            ),
            func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label(
                "total_refunds"
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
    last_synced = revenue_result.last_synced

    # Net revenue after refunds
    net_revenue = total_revenue - total_refunds

    # Query Meta ad spend
    meta_spend_query = (
        select(func.coalesce(func.sum(MetaAdSpend.spend_amount), 0.0))
        .where(MetaAdSpend.tenant_id == tenant_id)
        .where(MetaAdSpend.spend_date >= period_start)
        .where(MetaAdSpend.spend_date <= period_end)
    )
    meta_spend = float(db.scalar(meta_spend_query) or 0.0)

    # Query Google ad spend
    google_spend_query = (
        select(func.coalesce(func.sum(GoogleAdSpend.spend_amount), 0.0))
        .where(GoogleAdSpend.tenant_id == tenant_id)
        .where(GoogleAdSpend.spend_date >= period_start)
        .where(GoogleAdSpend.spend_date <= period_end)
    )
    google_spend = float(db.scalar(google_spend_query) or 0.0)

    total_ad_spend = meta_spend + google_spend

    # Calculate ROAS if we have ad spend
    blended_roas = net_revenue / total_ad_spend if total_ad_spend > 0 else None

    # Calculate prior period for growth comparison
    period_days = (period_end - period_start).days + 1
    prior_period_start = period_start - timedelta(days=period_days)
    prior_period_end = period_start - timedelta(days=1)

    prior_revenue_query = (
        select(
            func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label(
                "total_revenue"
            ),
            func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label(
                "total_refunds"
            ),
        )
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= prior_period_start)
        .where(ShopifyOrder.order_created_at <= prior_period_end)
    )
    prior_result = db.execute(prior_revenue_query).one()
    prior_revenue = float(prior_result.total_revenue or 0.0) - float(
        prior_result.total_refunds or 0.0
    )

    # Calculate growth rate
    if prior_revenue > 0:
        revenue_growth_rate = ((net_revenue - prior_revenue) / prior_revenue) * 100.0
        revenue_growth_absolute = net_revenue - prior_revenue
    else:
        revenue_growth_rate = None
        revenue_growth_absolute = None

    # For now, use simplified calculations without full cost data
    # In production, these would query CostInput and apply tiered logic
    gross_profit = net_revenue * 0.6  # Placeholder: 60% gross margin assumption
    contribution_margin = (
        net_revenue * 0.4
    )  # Placeholder: 40% contribution margin assumption
    contribution_margin_pct = 40.0  # Placeholder percentage

    # Business health indicators (simplified logic)
    health_indicators = _calculate_health_indicators(
        net_revenue=net_revenue,
        blended_roas=blended_roas,
        contribution_margin_pct=contribution_margin_pct,
        revenue_growth_rate=revenue_growth_rate,
    )

    # Determine overall health
    critical_count = sum(1 for h in health_indicators if h.status == "critical")
    warning_count = sum(1 for h in health_indicators if h.status == "warning")

    if critical_count > 0:
        overall_health = "critical"
    elif warning_count > 1:
        overall_health = "warning"
    else:
        overall_health = "healthy"

    # Team performance summaries (placeholder data for now)
    team_performance = _calculate_team_performance(
        blended_roas=blended_roas,
        contribution_margin_pct=contribution_margin_pct,
    )

    return ExecutiveOverviewResponse(
        total_revenue=net_revenue,
        gross_profit=gross_profit,
        contribution_margin=contribution_margin,
        contribution_margin_pct=contribution_margin_pct,
        revenue_growth_rate=revenue_growth_rate,
        revenue_growth_absolute=revenue_growth_absolute,
        blended_roas=blended_roas,
        cac_payback_days=None,  # Would need customer-level cohort data
        repeat_purchase_rate=None,  # Would need customer repeat purchase analysis
        return_rate_pct=None,  # Would need return-specific data
        overall_health_status=overall_health,
        health_indicators=health_indicators,
        team_performance=team_performance,
        period_start=period_start,
        period_end=period_end,
        data_last_synced_at=last_synced.isoformat() if last_synced else None,
        currency="USD",
    )


def _calculate_health_indicators(
    net_revenue: float,
    blended_roas: float | None,
    contribution_margin_pct: float,
    revenue_growth_rate: float | None,
) -> list[BusinessHealthIndicator]:
    """Calculate business health indicators across key areas."""
    indicators: list[BusinessHealthIndicator] = []

    # Growth health
    if revenue_growth_rate is not None:
        if revenue_growth_rate >= 10:
            growth_status = "healthy"
            growth_message = (
                f"Revenue growing at {revenue_growth_rate:.1f}% "
                "period-over-period"
            )
        elif revenue_growth_rate >= 0:
            growth_status = "warning"
            growth_message = f"Revenue growth slowing ({revenue_growth_rate:.1f}%)"
        else:
            growth_status = "critical"
            growth_message = (
                f"Revenue declining ({revenue_growth_rate:.1f}% period-over-period)"
            )

        indicators.append(
            BusinessHealthIndicator(
                area="growth",
                status=growth_status,
                status_message=growth_message,
                primary_metric="revenue_growth_rate",
                metric_value=revenue_growth_rate,
                metric_target=10.0,
                metric_unit="percent",
            )
        )

    # Profitability health
    if contribution_margin_pct >= 35:
        profit_status = "healthy"
        profit_message = (
            f"Contribution margin at {contribution_margin_pct:.1f}% (target: 35%+)"
        )
    elif contribution_margin_pct >= 25:
        profit_status = "warning"
        profit_message = (
            f"Contribution margin at {contribution_margin_pct:.1f}% (below target)"
        )
    else:
        profit_status = "critical"
        profit_message = (
            f"Contribution margin critically low at {contribution_margin_pct:.1f}%"
        )

    indicators.append(
        BusinessHealthIndicator(
            area="finance",
            status=profit_status,
            status_message=profit_message,
            primary_metric="contribution_margin_pct",
            metric_value=contribution_margin_pct,
            metric_target=35.0,
            metric_unit="percent",
        )
    )

    # Marketing efficiency health
    if blended_roas is not None:
        if blended_roas >= 3.0:
            roas_status = "healthy"
            roas_message = f"Blended ROAS at {blended_roas:.2f}x (target: 3.0x+)"
        elif blended_roas >= 2.0:
            roas_status = "warning"
            roas_message = f"Blended ROAS at {blended_roas:.2f}x (below target)"
        else:
            roas_status = "critical"
            roas_message = f"Blended ROAS critically low at {blended_roas:.2f}x"

        indicators.append(
            BusinessHealthIndicator(
                area="growth",
                status=roas_status,
                status_message=roas_message,
                primary_metric="blended_roas",
                metric_value=blended_roas,
                metric_target=3.0,
                metric_unit="ratio",
            )
        )

    return indicators


def _calculate_team_performance(
    blended_roas: float | None,
    contribution_margin_pct: float,
) -> list[TeamPerformanceSummary]:
    """Calculate team performance summaries (placeholder implementation)."""
    teams: list[TeamPerformanceSummary] = []

    # Growth team
    teams.append(
        TeamPerformanceSummary(
            team="growth",
            key_metrics={
                "blended_roas": blended_roas,
                "cac_payback_days": None,
            },
            trend="stable",
            alert_count=0,
            recommendation_count=0,
        )
    )

    # Retention team
    teams.append(
        TeamPerformanceSummary(
            team="retention",
            key_metrics={
                "repeat_purchase_rate": None,
                "ltv": None,
            },
            trend="stable",
            alert_count=0,
            recommendation_count=0,
        )
    )

    # Finance team
    teams.append(
        TeamPerformanceSummary(
            team="finance",
            key_metrics={
                "contribution_margin_pct": contribution_margin_pct,
                "gross_profit_margin": 60.0,  # Placeholder
            },
            trend="stable",
            alert_count=0,
            recommendation_count=0,
        )
    )

    # Operations team
    teams.append(
        TeamPerformanceSummary(
            team="operations",
            key_metrics={
                "inventory_turnover": None,
                "return_rate_pct": None,
            },
            trend="stable",
            alert_count=0,
            recommendation_count=0,
        )
    )

    return teams
