"""FR-074 / T-060: Pydantic schemas for recommendation suppression endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SuppressionStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_id: str
    rejection_count: int
    suppressed_until: date | None
    is_overridden: bool
    rejection_threshold: int
    suppression_window_days: int
    created_at: datetime
    updated_at: datetime


class SuppressionStateListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[SuppressionStateResponse]
    total: int
