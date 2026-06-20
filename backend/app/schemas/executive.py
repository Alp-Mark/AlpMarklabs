"""Pydantic schemas for Executive Overview endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class BusinessHealthIndicator(BaseModel):
    """Business health status for a specific area."""

    model_config = ConfigDict(from_attributes=True)

    area: str  # e.g. "growth", "retention", "finance", "operations"
    status: str  # "healthy", "warning", "critical"
    status_message: str  # Human-readable explanation
    primary_metric: str  # The key metric driving this status
    metric_value: float | None  # Current value
    metric_target: float | None  # Target/threshold value
    metric_unit: str  # "percent", "dollars", "ratio", etc.


class TeamPerformanceSummary(BaseModel):
    """Performance summary for a functional team."""

    model_config = ConfigDict(from_attributes=True)

    team: str  # "growth", "retention", "finance", "operations"
    key_metrics: dict[str, float | None]  # Top 2-3 metrics for this team
    trend: str  # "improving", "stable", "declining"
    alert_count: int  # Number of active alerts for this team
    recommendation_count: int  # Number of pending recommendations


class ExecutiveOverviewResponse(BaseModel):
    """Executive overview dashboard response."""

    model_config = ConfigDict(from_attributes=True)

    # Primary Financial Metrics
    total_revenue: float  # Total revenue in period
    gross_profit: float  # Revenue - COGS
    contribution_margin: float  # Revenue - COGS - Shipping - Fulfillment - Ad Spend
    contribution_margin_pct: float  # Contribution margin as % of revenue

    # Growth Metrics
    revenue_growth_rate: float | None  # MoM or period-over-period growth %
    revenue_growth_absolute: float | None  # Absolute $ change

    # Key Performance Indicators
    blended_roas: float | None  # Total revenue / total ad spend
    cac_payback_days: float | None  # Average CAC payback period
    repeat_purchase_rate: float | None  # % customers with 2+ orders
    return_rate_pct: float | None  # % orders returned

    # Business Health
    overall_health_status: str  # "healthy", "warning", "critical"
    health_indicators: list[BusinessHealthIndicator]

    # Cross-Team Rollup
    team_performance: list[TeamPerformanceSummary]

    # Metadata
    period_start: date
    period_end: date
    data_last_synced_at: str | None  # ISO timestamp of most recent sync
    currency: str  # e.g. "USD"
