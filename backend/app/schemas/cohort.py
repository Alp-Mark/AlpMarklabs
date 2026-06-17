"""FR-037 / T-066: Pydantic schemas for cohort comparison."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CohortSnapshotCreateRequest(BaseModel):
    """Request to create a cohort snapshot."""

    cohort_start_date: date = Field(..., description="Cohort period start date")
    cohort_end_date: date = Field(..., description="Cohort period end date")
    cohort_grain: str = Field(
        ..., max_length=50, description="Grain: 'month', 'week', 'quarter'"
    )
    observation_window_days: int = Field(
        ..., description="Days after cohort start for metrics window"
    )
    customer_count: int = Field(..., ge=0, description="Count of customers in cohort")
    repeat_rate: float = Field(
        ..., ge=0, le=1, description="Repeat purchase rate [0..1]"
    )
    churn_rate: float = Field(..., ge=0, le=1, description="Churn rate [0..1]")
    avg_order_value: float = Field(..., ge=0, description="Average order value")
    total_revenue: float = Field(..., ge=0, description="Total cohort revenue")
    repeat_purchase_frequency: float = Field(
        ..., ge=0, description="Avg purchases per repeat customer"
    )


class CohortSnapshotResponse(BaseModel):
    """Cohort snapshot with all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    cohort_start_date: date
    cohort_end_date: date
    cohort_grain: str
    observation_window_days: int
    customer_count: int
    repeat_rate: float
    churn_rate: float
    avg_order_value: float
    total_revenue: float
    repeat_purchase_frequency: float
    created_at: datetime
    updated_at: datetime


class CohortComparisonRequest(BaseModel):
    """Request to compare cohorts."""

    cohort_grain: str = Field(..., description="'month', 'week', or 'quarter'")
    start_date: date = Field(..., description="Earliest cohort start date to include")
    end_date: date = Field(..., description="Latest cohort start date to include")
    observation_window_days: int = Field(
        ..., description="Observation window to filter cohorts by"
    )


class CohortComparisonResponse(BaseModel):
    """Side-by-side cohort comparison."""

    cohorts: list[CohortSnapshotResponse] = Field(
        ..., description="List of cohorts matching filter criteria"
    )
    total: int = Field(..., description="Total cohort snapshots returned")


class AcquisitionCohortResponse(BaseModel):
    """FR-043 / T-070: Acquisition metrics for a cohort and channel.

    Read-only view for retention managers to understand incoming customer
    quality: channel, CAC, AOV, and early repeat purchase signals.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    cohort_start_date: date
    cohort_end_date: date
    cohort_grain: str
    channel: str
    new_customer_count: int
    blended_cac: float = Field(..., description="Blended cost per acquisition")
    first_order_aov: float = Field(
        ..., description="Average first-order value for this cohort+channel"
    )
    total_acquisition_spend: float
    repeat_purchase_rate_90d: float | None = Field(
        None, description="Early indicator: repeat rate at 90 days post-acquisition"
    )
    synced_at: datetime
    created_at: datetime
    updated_at: datetime


class AcquisitionContextRequest(BaseModel):
    """Request to fetch acquisition context for retention analysis.

    Retention manager specifies date range to fetch cohorts for comparison.
    """

    start_date: date = Field(
        ..., description="Earliest cohort start date to include"
    )
    end_date: date = Field(..., description="Latest cohort end date to include")
    cohort_grain: str = Field(
        default="month", description="'week', 'month', or 'quarter'"
    )
    channel: str | None = Field(
        None, description="Filter to specific channel; if None, return all channels"
    )


class AcquisitionContextResponse(BaseModel):
    """Acquisition context for retention manager analysis.

    Groups acquisition metrics by cohort and channel, showing quality
    differences to inform retention strategy.
    """

    cohorts: list[AcquisitionCohortResponse] = Field(
        ..., description="Acquisition cohorts matching filter criteria"
    )
    total: int = Field(..., description="Total acquisition cohorts returned")
    data_freshness: str = Field(
        ..., description="'fresh' or 'stale' based on synced_at"
    )
    channels_included: list[str] = Field(
        ..., description="Unique channels in the result set"
    )

