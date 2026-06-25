"""Executive overview business logic and calculations."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ConnectorIntegration,
    GoogleAdSpend,
    MetaAdSpend,
    ShopifyOrder,
)
from backend.app.schemas.executive import (
    BusinessHealthIndicator,
    ExecutiveOverviewResponse,
    TeamPerformanceSummary,
)


def _get_period_metrics(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """Return core KPI metrics for a given date range.

    Used for comparison-period delta calculations.  COGS uses a flat 42 %
    estimate here (consistent across both periods) rather than the heavy
    line-item join used for the primary period display.
    """
    rev_row = db.execute(
        select(
            func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label("total"),
            func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label("refunds"),
        )
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
    ).one()
    net_revenue = float(rev_row.total or 0.0) - float(rev_row.refunds or 0.0)

    meta = float(
        db.scalar(
            select(func.coalesce(func.sum(MetaAdSpend.spend_amount), 0.0))
            .where(MetaAdSpend.tenant_id == tenant_id)
            .where(MetaAdSpend.spend_date >= period_start)
            .where(MetaAdSpend.spend_date <= period_end)
        )
        or 0.0
    )
    google = float(
        db.scalar(
            select(func.coalesce(func.sum(GoogleAdSpend.spend_amount), 0.0))
            .where(GoogleAdSpend.tenant_id == tenant_id)
            .where(GoogleAdSpend.spend_date >= period_start)
            .where(GoogleAdSpend.spend_date <= period_end)
        )
        or 0.0
    )
    total_ad_spend = meta + google

    blended_roas = net_revenue / total_ad_spend if total_ad_spend > 0 else None

    order_count = db.scalar(
        select(func.count(ShopifyOrder.id))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == False)  # noqa: E712
    ) or 0

    est_cogs = net_revenue * 0.42
    est_shipping = order_count * 100.0
    cm = net_revenue - est_cogs - est_shipping - total_ad_spend
    cm_pct: float | None = (cm / net_revenue * 100.0) if net_revenue > 0 else None

    rr_row = db.execute(
        text("""
            WITH coc AS (
                SELECT customer_id, COUNT(*) AS order_count
                FROM shopify_orders
                WHERE tenant_id = :tid
                AND order_created_at >= :start
                AND order_created_at <= :end
                AND is_refunded = false
                AND customer_id IS NOT NULL
                GROUP BY customer_id
            )
            SELECT
                COUNT(*) FILTER (WHERE order_count >= 2) AS repeat_count,
                COUNT(*) AS total_count
            FROM coc
        """),
        {"tid": str(tenant_id), "start": period_start, "end": period_end},
    ).one()
    repeat_purchase_rate: float | None = (
        (rr_row.repeat_count / rr_row.total_count * 100.0)
        if (rr_row.total_count or 0) > 0
        else None
    )

    refunded = db.scalar(
        select(func.count(ShopifyOrder.id))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == True)  # noqa: E712
    ) or 0
    total_orders = order_count + refunded
    return_rate_pct: float | None = (
        (refunded / total_orders * 100.0) if total_orders > 0 else None
    )

    return {
        "net_revenue": net_revenue,
        "blended_roas": blended_roas,
        "contribution_margin_pct": cm_pct,
        "repeat_purchase_rate": repeat_purchase_rate,
        "return_rate_pct": return_rate_pct,
    }


def _pct_delta(current: float | None, prior: float | None) -> float | None:
    """Return % change from prior to current; None when either is unavailable."""
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100.0


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
            func.max(ShopifyOrder.currency).label("currency"),
        )
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
    )
    revenue_result = db.execute(revenue_query).one()
    total_revenue = float(revenue_result.total_revenue or 0.0)
    total_refunds = float(revenue_result.total_refunds or 0.0)
    currency = revenue_result.currency or "INR"  # Default to INR for One8

    # Use the Shopify connector's last_synced_at as the authoritative
    # "data last synced" timestamp (reflects when the sync job ran, not
    # the historical order date).
    last_synced = db.scalar(
        select(func.max(ConnectorIntegration.last_synced_at)).where(
            ConnectorIntegration.tenant_id == tenant_id,
            ConnectorIntegration.source == "shopify",
        )
    )

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

    # Always compute mid_date – used for intra-period fallback
    half_days = period_days // 2
    mid_date = period_start + timedelta(days=half_days)

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
        # Comparison period for all delta calculations = true prior period
        comp_start: date = prior_period_start
        comp_end: date = prior_period_end
    else:
        # No prior-period data – fall back to intra-period split (second half
        # vs first half of the current period).
        first_half_query = (
            select(
                func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label(
                    "total_revenue"
                ),
                func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label(
                    "total_refunds"
                ),
            )
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(ShopifyOrder.order_created_at >= period_start)
            .where(ShopifyOrder.order_created_at < mid_date)
        )
        first_half_result = db.execute(first_half_query).one()
        first_half_revenue = float(
            first_half_result.total_revenue or 0.0
        ) - float(first_half_result.total_refunds or 0.0)

        second_half_query = (
            select(
                func.coalesce(func.sum(ShopifyOrder.total_amount), 0.0).label(
                    "total_revenue"
                ),
                func.coalesce(func.sum(ShopifyOrder.refund_amount), 0.0).label(
                    "total_refunds"
                ),
            )
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(ShopifyOrder.order_created_at >= mid_date)
            .where(ShopifyOrder.order_created_at <= period_end)
        )
        second_half_result = db.execute(second_half_query).one()
        second_half_revenue = float(
            second_half_result.total_revenue or 0.0
        ) - float(second_half_result.total_refunds or 0.0)

        if first_half_revenue > 0:
            revenue_growth_rate = (
                (second_half_revenue - first_half_revenue)
                / first_half_revenue
                * 100.0
            )
            revenue_growth_absolute = second_half_revenue - first_half_revenue
        else:
            revenue_growth_rate = None
            revenue_growth_absolute = None
        # Comparison period for all delta calculations = first half
        comp_start = period_start
        comp_end = mid_date - timedelta(days=1)

    # Calculate REAL COGS from inventory items (not estimates!)
    # Join line items with inventory to get actual cost_per_unit
    # If inventory item missing COGS, fallback to 42% estimate
    
    cogs_query = text("""
        SELECT 
            COALESCE(
                SUM(li.quantity * COALESCE(inv.cost_per_unit, li.unit_price * 0.42)),
                0
            ) as total_cogs
        FROM shopify_order_line_items li
        JOIN shopify_orders o ON o.id = li.order_id
        LEFT JOIN shopify_inventory_items inv
            ON inv.sku = li.sku AND inv.tenant_id = :tenant_id
        WHERE o.tenant_id = :tenant_id
        AND o.order_created_at >= :start
        AND o.order_created_at <= :end
        AND o.is_refunded = false
    """)
    
    real_cogs = db.scalar(cogs_query, {
        "tenant_id": tenant_id,
        "start": period_start,
        "end": period_end
    }) or 0.0
    
    # Count orders in period for shipping calc
    order_count = db.scalar(
        select(func.count(ShopifyOrder.id))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == False)  # noqa: E712
    ) or 0
    
    estimated_shipping = order_count * 100.0  # ₹100 per order
    
    # Gross profit = Revenue - REAL COGS
    gross_profit = net_revenue - real_cogs
    
    # Contribution margin = Gross Profit - Shipping - Ad Spend
    contribution_margin = gross_profit - estimated_shipping - total_ad_spend
    contribution_margin_pct = (
        (contribution_margin / net_revenue * 100.0) if net_revenue > 0 else 0.0
    )
    
    # Calculate CAC Payback Days (for current period)
    # CAC Payback = Total Ad Spend / New Customers / 
    #               (Avg Order Value * Contribution Margin %)
    # Simplified: use period ad spend / period orders for CAC
    new_customer_count = db.scalar(
        select(func.count(func.distinct(ShopifyOrder.customer_id)))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == False)  # noqa: E712
    ) or 0
    
    if new_customer_count > 0 and net_revenue > 0 and contribution_margin > 0:
        cac = total_ad_spend / new_customer_count
        contribution_per_order = (
            contribution_margin / order_count if order_count > 0 else 0
        )
        # Payback days = CAC / (contribution per order / 30 days)
        # Assumes monthly purchase frequency
        cac_payback_days = (
            (cac / contribution_per_order * 30)
            if contribution_per_order > 0
            else None
        )
    else:
        cac_payback_days = None
    
    # Calculate Repeat Purchase Rate
    # Repeat Rate = (Customers with 2+ orders) / Total Customers
    # Need to use a subquery to count customers with 2+ orders
    
    repeat_rate_result = db.execute(text("""
        WITH customer_order_counts AS (
            SELECT customer_id, COUNT(*) as order_count
            FROM shopify_orders
            WHERE tenant_id = :tenant_id
            AND order_created_at >= :period_start
            AND order_created_at <= :period_end
            AND is_refunded = false
            AND customer_id IS NOT NULL
            GROUP BY customer_id
        )
        SELECT 
            COUNT(*) FILTER (WHERE order_count >= 2) as repeat_customers,
            COUNT(*) as total_customers
        FROM customer_order_counts
    """), {
        'tenant_id': str(tenant_id),
        'period_start': period_start,
        'period_end': period_end
    }).one()
    
    repeat_customers_count = repeat_rate_result.repeat_customers or 0
    total_customers = repeat_rate_result.total_customers or 0
    
    if total_customers > 0:
        repeat_purchase_rate = (repeat_customers_count / total_customers) * 100.0
    else:
        repeat_purchase_rate = None
    
    # Calculate Return Rate
    # Return Rate = (Refunded Orders) / Total Orders
    refunded_count = db.scalar(
        select(func.count(ShopifyOrder.id))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == True)  # noqa: E712
    ) or 0
    
    total_orders = order_count + refunded_count
    if total_orders > 0:
        return_rate_pct = (refunded_count / total_orders) * 100.0
    else:
        return_rate_pct = None

    # Compute comparison-period deltas for all KPI cards
    comp = _get_period_metrics(db, tenant_id, comp_start, comp_end)
    contribution_margin_pct_change = _pct_delta(
        contribution_margin_pct, comp["contribution_margin_pct"]
    )
    blended_roas_change = _pct_delta(blended_roas, comp["blended_roas"])
    repeat_purchase_rate_change = _pct_delta(
        repeat_purchase_rate, comp["repeat_purchase_rate"]
    )
    return_rate_pct_change = _pct_delta(return_rate_pct, comp["return_rate_pct"])

    # Business health indicators
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

    # Team performance summaries
    team_performance = _calculate_team_performance(
        blended_roas=blended_roas,
        contribution_margin_pct=contribution_margin_pct,
    )

    return ExecutiveOverviewResponse(
        total_revenue=net_revenue,
        gross_profit=gross_profit,
        contribution_margin=contribution_margin,
        contribution_margin_pct=contribution_margin_pct,
        contribution_margin_pct_change=contribution_margin_pct_change,
        revenue_growth_rate=revenue_growth_rate,
        revenue_growth_absolute=revenue_growth_absolute,
        blended_roas=blended_roas,
        blended_roas_change=blended_roas_change,
        cac_payback_days=cac_payback_days,
        repeat_purchase_rate=repeat_purchase_rate,
        repeat_purchase_rate_change=repeat_purchase_rate_change,
        return_rate_pct=return_rate_pct,
        return_rate_pct_change=return_rate_pct_change,
        overall_health_status=overall_health,
        health_indicators=health_indicators,
        team_performance=team_performance,
        period_start=period_start,
        period_end=period_end,
        data_last_synced_at=last_synced.isoformat() if last_synced else None,
        currency=currency,
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
