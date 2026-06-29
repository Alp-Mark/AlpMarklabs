"""Pydantic schemas for trend/time-series endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ExecutiveTrendDataPoint(BaseModel):
    """Single data point in executive KPI trend."""

    snapshot_date: date
    revenue_amount: float
    order_count: int
    aov: float
    customer_count: int
    profit_amount: float
    ad_spend_amount: float
    blended_roas: float
    contribution_margin_pct: float


class ExecutiveTrendResponse(BaseModel):
    """Time-series trend data for executive dashboard."""

    data_points: list[ExecutiveTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class GrowthChannelTrendDataPoint(BaseModel):
    """Single data point in growth channel trend."""

    snapshot_date: date
    ad_spend_amount: float
    revenue_attributed: float
    order_count: int
    roas: float
    cac: float
    contribution_margin_pct: float
    payback_period_days: float


class GrowthChannelTrendResponse(BaseModel):
    """Time-series trend data for a single growth channel."""

    channel: str
    data_points: list[GrowthChannelTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class GrowthTrendResponse(BaseModel):
    """Time-series trend data for all growth channels."""

    channels: list[GrowthChannelTrendResponse]
    period_start: date
    period_end: date
    window_label: str


class RetentionTrendDataPoint(BaseModel):
    """Single data point in retention trend."""

    snapshot_date: date
    total_customers: int
    repeat_customers: int
    repeat_purchase_rate_pct: float


class RetentionTrendResponse(BaseModel):
    """Time-series trend data for retention dashboard."""

    data_points: list[RetentionTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class CostDriverTrendDataPoint(BaseModel):
    """Single data point in cost driver trend - aggregated across all drivers."""

    snapshot_date: date
    driver_type: str
    absolute_amount: float
    pct_of_revenue: float
    margin_impact_amount: float


class CostDriverTrendResponse(BaseModel):
    """Time-series trend data for cost drivers (grouped by driver_type)."""

    data_points: list[CostDriverTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class MarginDriftTrendDataPoint(BaseModel):
    """Single data point in margin drift trend."""

    snapshot_date: date
    channel: str
    category: str
    actual_margin_pct: float
    expected_margin_pct: float | None
    drift_pct: float | None


class MarginDriftTrendResponse(BaseModel):
    """Time-series trend data for margin drift."""

    data_points: list[MarginDriftTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class InventoryRiskTrendDataPoint(BaseModel):
    """Aggregated inventory risk metrics per snapshot_date."""

    snapshot_date: date
    total_skus: int
    stockout_risk_skus: int
    overstock_skus: int
    total_capital_at_risk: float


class InventoryRiskTrendResponse(BaseModel):
    """Time-series trend data for inventory risk (aggregated)."""

    data_points: list[InventoryRiskTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str


class OperationalImpactTrendDataPoint(BaseModel):
    """Aggregated operational impact metrics per snapshot_date."""

    snapshot_date: date
    total_skus: int
    avg_logistics_margin_impact_pct: float
    total_stockout_lost_revenue: float


class OperationalImpactTrendResponse(BaseModel):
    """Time-series trend data for operational impact (aggregated)."""

    data_points: list[OperationalImpactTrendDataPoint]
    period_start: date
    period_end: date
    window_label: str
