"""FR-071 / T-053: Pydantic schemas for Recommendation API responses."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_id: str
    domain: str
    snapshot_date: date
    affected_area: str
    signal_summary: str
    suggested_action: str
    estimated_impact: float | None
    confidence_level: str
    data_freshness_context: str
    status: str
    priority: int
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class RecommendationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[RecommendationResponse]
    total: int


class RecommendationStatusUpdateRequest(BaseModel):
    """FR-073 / T-059: Body for PATCH status endpoint."""

    to_status: str
    note: str | None = None
