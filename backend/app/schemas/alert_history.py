"""Pydantic schemas for alert event history responses (FR-125 / T-079)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertEventResponse(BaseModel):
    """Response for a single alert event from the immutable log."""

    id: UUID
    tenant_id: UUID
    alert_id: str
    alert_type: str
    event_type: str  # "created", "acknowledged", "dismissed", "escalation_rule_*", etc.
    actor_user_id: UUID | None
    event_data: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertEventListResponse(BaseModel):
    """Paginated list of alert events."""

    events: list[AlertEventResponse]
    total_count: int

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryResponse(BaseModel):
    """Complete immutable history for a specific alert."""

    alert_id: str
    alert_type: str
    events: list[AlertEventResponse]
    total_events: int
    first_event_at: datetime | None
    last_event_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
