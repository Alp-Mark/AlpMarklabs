"""Schemas for admin audit log endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminAuditLogResponse(BaseModel):
    """Single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | None
    admin_user_id: UUID
    admin_user_email: str | None = None  # Populated via join or lookup
    action_type: str
    resource_type: str
    resource_id: str | None
    changes: dict[str, object]
    reason: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    logs: list[AdminAuditLogResponse]
    total: int
    page: int
    page_size: int


class AdminAuditLogFilters(BaseModel):
    """Optional filters for audit log query."""

    tenant_id: UUID | None = None
    admin_user_id: UUID | None = None
    action_type: str | None = None
    resource_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
