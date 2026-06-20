"""Pydantic schemas for retention endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CohortRetention(BaseModel):
    """Retention metrics for a customer cohort."""

    cohort_month: str = Field(..., description="Cohort month (YYYY-MM)")
    cohort_size: int = Field(..., description="Number of customers in cohort")
    month_0_retained: int = Field(..., description="Customers retained in month 0")
    month_1_retained: int | None = Field(
        None, description="Customers retained in month 1"
    )
    month_2_retained: int | None = Field(
        None, description="Customers retained in month 2"
    )
    month_3_retained: int | None = Field(
        None, description="Customers retained in month 3"
    )
    retention_rate_month_1: float | None = Field(
        None, description="Month 1 retention rate (%)"
    )
    retention_rate_month_2: float | None = Field(
        None, description="Month 2 retention rate (%)"
    )
    retention_rate_month_3: float | None = Field(
        None, description="Month 3 retention rate (%)"
    )


class CustomerSegment(BaseModel):
    """Customer segment with behavioral characteristics."""

    segment_name: str = Field(..., description="Segment identifier")
    customer_count: int = Field(..., description="Number of customers in segment")
    avg_order_value: float | None = Field(
        None, description="Average order value (USD)"
    )
    avg_order_frequency: float | None = Field(
        None, description="Average orders per customer"
    )
    total_revenue: float = Field(..., description="Total revenue from segment (USD)")
    is_at_risk: bool = Field(
        False, description="Whether segment shows churn risk"
    )


class RetentionDashboardResponse(BaseModel):
    """Complete retention dashboard response."""

    total_customers: int = Field(..., description="Total unique customers in period")
    repeat_customers: int = Field(
        ..., description="Customers with 2+ orders in period"
    )
    repeat_purchase_rate: float | None = Field(
        None, description="Repeat purchase rate (%)"
    )
    avg_orders_per_customer: float | None = Field(
        None, description="Average orders per customer"
    )
    avg_customer_lifetime_value: float | None = Field(
        None, description="Average customer lifetime value (USD)"
    )
    avg_days_between_purchases: float | None = Field(
        None, description="Average days between repeat purchases"
    )
    churn_risk_customers: int = Field(
        0, description="Customers showing churn risk indicators"
    )
    cohort_retention: list[CohortRetention] = Field(
        default_factory=list, description="Cohort retention analysis"
    )
    customer_segments: list[CustomerSegment] = Field(
        default_factory=list, description="Customer segment breakdown"
    )
    period_start: date = Field(..., description="Analysis period start date")
    period_end: date = Field(..., description="Analysis period end date")
    data_last_synced_at: str | None = Field(
        None, description="Last data sync timestamp (ISO 8601)"
    )
    currency: str = Field("USD", description="Currency code")
