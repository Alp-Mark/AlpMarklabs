"""Pydantic schemas for activity log and system health endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ActivityLogEntry(BaseModel):
    """Single activity log entry with filtering metadata."""

    id: str
    timestamp: datetime
    severity: Literal["critical", "important", "info", "debug"]
    category: str  # user_action, data_sync, alert, recommendation, etc.
    action: str  # Action code (e.g., "user.invited")
    description: str  # Human-readable description with context
    actor: str | None  # User name or "System"
    actor_user_id: str | None
    entity_type: str
    entity_id: str
    details: dict[str, object]
    is_system_generated: bool

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    """Paginated activity log with filtering metadata."""

    entries: list[ActivityLogEntry]
    total_count: int
    page: int
    page_size: int
    filters_applied: dict[str, object]  # Shows what filters were used


class SystemHealthIssue(BaseModel):
    """Active system health issue (unresolved)."""

    id: str
    service_name: str
    event_type: str  # sync_failure, api_error, etc.
    severity: Literal["critical", "important", "info", "debug"]
    error_message: str
    error_details: dict[str, object] | None
    created_at: datetime
    time_since_failure: str  # Human-readable (e.g., "3h 24m")

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    """List of active system health issues."""

    issues: list[SystemHealthIssue]
    total_unresolved: int
