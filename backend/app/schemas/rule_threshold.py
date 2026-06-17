"""FR-071 / T-054: Pydantic schemas for the rule-threshold API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RuleThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    rule_id: str
    threshold_value: float
    threshold_unit: str
    description: str
    suggested_value: float | None
    is_customised: bool
    created_at: datetime
    updated_at: datetime


class RuleThresholdUpdateRequest(BaseModel):
    threshold_value: float


class RuleThresholdListResponse(BaseModel):
    items: list[RuleThresholdResponse]
    total: int
