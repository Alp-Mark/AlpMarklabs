from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CostDriverSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_type: str
    snapshot_date: date
    period_start_date: date
    period_end_date: date
    absolute_amount: float
    revenue: float
    pct_of_revenue: float
    margin_impact_amount: float
    source: str
    source_platform: str
    last_updated_at: datetime
    confidence_score: float
    confidence_label: str


class CostDriverListResponse(BaseModel):
    snapshot_date: date
    drivers: list[CostDriverSnapshotResponse]


class MarginDriftThresholdCreateRequest(BaseModel):
    channel: str
    category: str
    threshold_pct: float
    effective_date: date


class MarginDriftThresholdUpdateRequest(BaseModel):
    threshold_pct: float | None = None
    is_active: bool | None = None
    effective_date: date | None = None


class MarginDriftThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    category: str
    threshold_pct: float
    is_active: bool
    effective_date: date
    created_at: datetime
    updated_at: datetime


class MarginDriftThresholdListResponse(BaseModel):
    thresholds: list[MarginDriftThresholdResponse]


class MarginDriftSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_date: date
    channel: str
    category: str
    actual_margin_pct: float
    expected_margin_pct: float | None
    drift_pct: float | None
    threshold_exceeded: bool
    variance_reason: str
    data_completeness: str


class MarginDriftListResponse(BaseModel):
    snapshot_date: date
    snapshots: list[MarginDriftSnapshotResponse]


# ---------------------------------------------------------------------------
# T-048: Tiered cost inputs (FR-050 / FR-051)
# ---------------------------------------------------------------------------

_VALID_INPUT_TYPES = {"shipping", "cogs", "ad_spend_vat", "return_processing"}
_VALID_UNITS = {"per_order", "per_kg", "flat", "pct"}
_VALID_ZONES = {"domestic", "eu", "international"}


class CostInputCreateRequest(BaseModel):
    input_type: str
    tier_label: str
    weight_min_kg: float | None = None
    weight_max_kg: float | None = None
    destination_zone: str | None = None
    amount: float
    unit: str
    effective_date: date
    variance_reason: str | None = None


class CostInputUpdateRequest(BaseModel):
    tier_label: str | None = None
    weight_min_kg: float | None = None
    weight_max_kg: float | None = None
    destination_zone: str | None = None
    amount: float | None = None
    unit: str | None = None
    effective_date: date | None = None
    is_active: bool | None = None
    variance_reason: str | None = None


class CostInputRejectRequest(BaseModel):
    reason: str


class CostInputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    input_type: str
    tier_label: str
    weight_min_kg: float | None
    weight_max_kg: float | None
    destination_zone: str | None
    amount: float
    unit: str
    is_active: bool
    effective_date: date
    confirmation_required: bool
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CostInputListResponse(BaseModel):
    cost_inputs: list[CostInputResponse]


class CostInputVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cost_input_id: uuid.UUID
    version_number: int
    action: str
    prior_amount: float | None
    new_amount: float
    prior_unit: str | None
    new_unit: str
    effective_date: date
    variance_reason: str | None
    created_at: datetime


class CostInputHistoryResponse(BaseModel):
    cost_input_id: uuid.UUID
    versions: list[CostInputVersionResponse]


# ---------------------------------------------------------------------------
# T-068: Historical restatement engine (FR-056)
# ---------------------------------------------------------------------------

class HistoricalRestatementRequest(BaseModel):
    """Request to restate margin for a historical period under different cost inputs."""

    period_start: date
    period_end: date
    cost_input_id: uuid.UUID
    prior_version_number: int
    new_version_number: int


class HistoricalRestatementResponse(BaseModel):
    """Response showing margin comparison under prior vs new cost scenarios."""

    period_start: date
    period_end: date
    cost_input_id: uuid.UUID
    cost_input_type: str
    cost_input_label: str
    prior_version_number: int
    new_version_number: int
    prior_amount: float
    new_amount: float
    prior_unit: str
    new_unit: str
    # Margin impact under prior scenario
    prior_margin_total: float
    # Margin impact under new scenario
    new_margin_total: float
    # Delta in absolute terms
    margin_delta_absolute: float
    # Delta as percentage change
    margin_delta_pct: float
    # Explanation for finance review
    variance_note: str
    created_at: datetime
