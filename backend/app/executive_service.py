"""Executive overview business logic and calculations."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ConnectorIntegration,
    CostInput,
    GoogleAdSpend,
    MetaAdSpend,
    Recommendation,
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

    # Read COGS% and shipping from cost_inputs; fall back to 42% / ₹100 if not set
    _cogs_input = db.scalar(
        select(CostInput).where(
            CostInput.tenant_id == tenant_id,
            CostInput.input_type == "cogs",
            CostInput.is_active.is_(True),
        )
    )
    _cogs_pct: float = (
        _cogs_input.amount
        if _cogs_input is not None and _cogs_input.unit == "pct_of_revenue"
        else 42.0
    )
    _ship_input = db.scalar(
        select(CostInput).where(
            CostInput.tenant_id == tenant_id,
            CostInput.input_type == "shipping",
            CostInput.is_active.is_(True),
        )
    )
    _ship_per_order: float = (
        _ship_input.amount
        if _ship_input is not None and _ship_input.unit == "per_order"
        else 100.0
    )
    est_cogs = net_revenue * _cogs_pct / 100.0
    est_shipping = order_count * _ship_per_order
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
        # No prior-period data – no meaningful comparison available
        revenue_growth_rate = None
        revenue_growth_absolute = None
        # Use prior period dates for comparison (even though empty)
        # so delta calculations return None consistently
        comp_start = prior_period_start
        comp_end = prior_period_end

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
        "tenant_id": str(tenant_id),
        "start": period_start,
        "end": period_end
    }) or 0.0

    # Fallback: no line items (e.g. seed data) — use cost_inputs or 42% estimate
    if real_cogs == 0.0:
        _cogs_input = db.scalar(
            select(CostInput).where(
                CostInput.tenant_id == tenant_id,
                CostInput.input_type == "cogs",
                CostInput.is_active.is_(True),
            )
        )
        if _cogs_input is not None and _cogs_input.unit == "pct_of_revenue":
            real_cogs = net_revenue * _cogs_input.amount / 100.0
        else:
            real_cogs = net_revenue * 0.42

    # Count orders in period for shipping calc
    order_count = db.scalar(
        select(func.count(ShopifyOrder.id))
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .where(ShopifyOrder.is_refunded == False)  # noqa: E712
    ) or 0

    # Read shipping cost from cost_inputs; fall back to ₹100/order if not configured
    _ship_input = db.scalar(
        select(CostInput).where(
            CostInput.tenant_id == tenant_id,
            CostInput.input_type == "shipping",
            CostInput.is_active.is_(True),
        )
    )
    _ship_per_order: float = (
        _ship_input.amount
        if _ship_input is not None and _ship_input.unit == "per_order"
        else 100.0
    )
    estimated_shipping = order_count * _ship_per_order
    
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
        blended_roas=blended_roas,
        contribution_margin_pct=contribution_margin_pct,
        repeat_purchase_rate=repeat_purchase_rate,
        return_rate_pct=return_rate_pct,
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
        db=db,
        tenant_id=tenant_id,
        blended_roas=blended_roas,
        contribution_margin_pct=contribution_margin_pct,
        repeat_purchase_rate=repeat_purchase_rate,
        return_rate_pct=return_rate_pct,
        cac_payback_days=cac_payback_days,
        comp=comp,
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
    blended_roas: float | None,
    contribution_margin_pct: float,
    repeat_purchase_rate: float | None,
    return_rate_pct: float | None,
) -> list[BusinessHealthIndicator]:
    """
    Calculate business health indicators across 4 functional areas.
    
    Always returns exactly 4 indicators: growth, retention, finance, operations.
    """
    indicators: list[BusinessHealthIndicator] = []

    # 1. Growth health (ROAS-based)
    if blended_roas is not None and blended_roas > 0:
        if blended_roas >= 3.0:
            growth_status = "healthy"
            growth_message = f"Blended ROAS at {blended_roas:.1f}x (target: 3.0x+)"
        elif blended_roas >= 2.0:
            growth_status = "warning"
            growth_message = f"Blended ROAS at {blended_roas:.1f}x (below target)"
        else:
            growth_status = "critical"
            growth_message = f"Blended ROAS critically low at {blended_roas:.1f}x"
        
        indicators.append(
            BusinessHealthIndicator(
                area="growth",
                status=growth_status,
                status_message=growth_message,
                primary_metric="blended_roas",
                metric_value=blended_roas,
                metric_target=3.0,
                metric_unit="ratio",
            )
        )
    else:
        # No ROAS data available
        indicators.append(
            BusinessHealthIndicator(
                area="growth",
                status="warning",
                status_message="No ROAS data available for this area",
                primary_metric="blended_roas",
                metric_value=0.0,
                metric_target=3.0,
                metric_unit="ratio",
            )
        )

    # 2. Retention health (repeat purchase rate)
    if repeat_purchase_rate is not None and repeat_purchase_rate > 0:
        if repeat_purchase_rate >= 30.0:
            retention_status = "healthy"
            retention_message = (
                f"Repeat rate at {repeat_purchase_rate:.1f}% (target: 30%+)"
            )
        elif repeat_purchase_rate >= 20.0:
            retention_status = "warning"
            retention_message = (
                f"Repeat rate at {repeat_purchase_rate:.1f}% (below target)"
            )
        else:
            retention_status = "critical"
            retention_message = (
                f"Repeat rate critically low at {repeat_purchase_rate:.1f}%"
            )
        
        indicators.append(
            BusinessHealthIndicator(
                area="retention",
                status=retention_status,
                status_message=retention_message,
                primary_metric="repeat_purchase_rate",
                metric_value=repeat_purchase_rate,
                metric_target=30.0,
                metric_unit="percent",
            )
        )
    else:
        # No retention data available
        indicators.append(
            BusinessHealthIndicator(
                area="retention",
                status="warning",
                status_message="No data available for this area",
                primary_metric="repeat_purchase_rate",
                metric_value=0.0,
                metric_target=30.0,
                metric_unit="percent",
            )
        )

    # 3. Finance health (contribution margin)
    if contribution_margin_pct >= 35:
        finance_status = "healthy"
        finance_message = (
            f"Contribution margin at {contribution_margin_pct:.1f}% (target: 35%+)"
        )
    elif contribution_margin_pct >= 25:
        finance_status = "warning"
        finance_message = (
            f"Contribution margin at {contribution_margin_pct:.1f}% (below target)"
        )
    else:
        finance_status = "critical"
        finance_message = (
            f"Contribution margin critically low at {contribution_margin_pct:.1f}%"
        )

    indicators.append(
        BusinessHealthIndicator(
            area="finance",
            status=finance_status,
            status_message=finance_message,
            primary_metric="contribution_margin_pct",
            metric_value=contribution_margin_pct,
            metric_target=35.0,
            metric_unit="percent",
        )
    )

    # 4. Operations health (return rate - lower is better)
    if return_rate_pct is not None and return_rate_pct >= 0:
        if return_rate_pct <= 3.0:
            operations_status = "healthy"
            operations_message = (
                f"Return rate at {return_rate_pct:.1f}% (target: <3%)"
            )
        elif return_rate_pct <= 5.0:
            operations_status = "warning"
            operations_message = (
                f"Return rate at {return_rate_pct:.1f}% (above target)"
            )
        else:
            operations_status = "critical"
            operations_message = (
                f"Return rate critically high at {return_rate_pct:.1f}%"
            )
        
        indicators.append(
            BusinessHealthIndicator(
                area="operations",
                status=operations_status,
                status_message=operations_message,
                primary_metric="return_rate_pct",
                metric_value=return_rate_pct,
                metric_target=3.0,
                metric_unit="percent",
            )
        )
    else:
        # No operations data available
        indicators.append(
            BusinessHealthIndicator(
                area="operations",
                status="warning",
                status_message="No data available for this area",
                primary_metric="return_rate_pct",
                metric_value=0.0,
                metric_target=3.0,
                metric_unit="percent",
            )
        )

    return indicators


def _calculate_team_performance(
    db: Session,
    tenant_id: UUID,
    blended_roas: float | None,
    contribution_margin_pct: float,
    repeat_purchase_rate: float | None,
    return_rate_pct: float | None,
    cac_payback_days: float | None,
    comp: dict[str, Any],
) -> list[TeamPerformanceSummary]:
    """Calculate team performance summaries with real metrics and trends."""
    teams: list[TeamPerformanceSummary] = []

    # Helper to determine trend
    def _trend(current: float | None, previous: float | None) -> str:
        if current is None or previous is None or previous == 0:
            return "stable"
        change_pct = ((current - previous) / previous) * 100.0
        if change_pct > 5.0:
            return "improving"
        elif change_pct < -5.0:
            return "declining"
        else:
            return "stable"

    # Query recommendation counts by domain
    growth_recs = db.scalar(
        select(func.count(Recommendation.id))
        .where(Recommendation.tenant_id == tenant_id)
        .where(Recommendation.domain == "growth")
        .where(Recommendation.status.in_(["new", "reviewed"]))
    ) or 0

    retention_recs = db.scalar(
        select(func.count(Recommendation.id))
        .where(Recommendation.tenant_id == tenant_id)
        .where(Recommendation.domain == "retention")
        .where(Recommendation.status.in_(["new", "reviewed"]))
    ) or 0

    finance_recs = db.scalar(
        select(func.count(Recommendation.id))
        .where(Recommendation.tenant_id == tenant_id)
        .where(Recommendation.domain == "finance")
        .where(Recommendation.status.in_(["new", "reviewed"]))
    ) or 0

    operations_recs = db.scalar(
        select(func.count(Recommendation.id))
        .where(Recommendation.tenant_id == tenant_id)
        .where(Recommendation.domain == "operations")
        .where(Recommendation.status.in_(["new", "reviewed"]))
    ) or 0

    # Growth team
    growth_trend = _trend(blended_roas, comp.get("blended_roas"))
    teams.append(
        TeamPerformanceSummary(
            team="growth",
            key_metrics={
                "blended_roas": blended_roas,
                "cac_payback_days": cac_payback_days,
            },
            trend=growth_trend,
            alert_count=0,  # TODO: Implement alert counting when alert system is built
            recommendation_count=growth_recs,
        )
    )

    # Retention team
    retention_trend = _trend(
        repeat_purchase_rate, comp.get("repeat_purchase_rate")
    )
    teams.append(
        TeamPerformanceSummary(
            team="retention",
            key_metrics={
                "repeat_purchase_rate": repeat_purchase_rate,
            },
            trend=retention_trend,
            alert_count=0,  # TODO: Implement alert counting
            recommendation_count=retention_recs,
        )
    )

    # Finance team
    finance_trend = _trend(
        contribution_margin_pct, comp.get("contribution_margin_pct")
    )
    teams.append(
        TeamPerformanceSummary(
            team="finance",
            key_metrics={
                "contribution_margin_pct": contribution_margin_pct,
            },
            trend=finance_trend,
            alert_count=0,  # TODO: Implement alert counting
            recommendation_count=finance_recs,
        )
    )

    # Operations team
    # For return rate, lower is better, so invert the trend logic
    ops_trend = "stable"
    comp_return_rate = comp.get("return_rate_pct")
    if return_rate_pct is not None and comp_return_rate:
        change_pct = (
            (return_rate_pct - comp_return_rate) / comp_return_rate
        ) * 100.0
        if change_pct < -5.0:  # Return rate going down is good
            ops_trend = "improving"
        elif change_pct > 5.0:  # Return rate going up is bad
            ops_trend = "declining"

    teams.append(
        TeamPerformanceSummary(
            team="operations",
            key_metrics={
                "return_rate_pct": return_rate_pct,
            },
            trend=ops_trend,
            alert_count=0,  # TODO: Implement alert counting
            recommendation_count=operations_recs,
        )
    )

    return teams
