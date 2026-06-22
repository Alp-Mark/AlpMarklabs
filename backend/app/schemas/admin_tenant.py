"""Schemas for super-admin tenant management endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminTenantResponse(BaseModel):
    """Detailed tenant info for super-admin views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_active: bool
    status: str  # active, suspended, deleted
    status_reason: str | None
    suspended_at: datetime | None
    deleted_at: datetime | None
    billing_plan: str
    billing_cycle: str
    billing_status: str
    seat_limit: int
    base_currency: str
    locale: str
    created_at: datetime
    updated_at: datetime
    # Computed fields - user counts
    total_users: int
    active_users: int
    # Usage metrics
    total_logins: int | None = None
    last_activity_at: datetime | None = None
    active_users_30d: int | None = None


class AdminTenantListResponse(BaseModel):
    """List response with pagination."""

    tenants: list[AdminTenantResponse]
    total: int
    page: int
    page_size: int


class AdminTenantUpdateRequest(BaseModel):
    """Update tenant fields (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    billing_plan: str | None = Field(None, min_length=1, max_length=50)
    billing_cycle: str | None = Field(None, pattern=r"^(monthly|annual)$")
    billing_status: str | None = Field(
        None, pattern=r"^(active|past_due|suspended|cancelled)$"
    )
    seat_limit: int | None = Field(None, ge=1, le=1000)


class AdminTenantStatusUpdateRequest(BaseModel):
    """Request to suspend or activate a tenant."""

    is_active: bool
    reason: str | None = Field(
        None, max_length=1000, description="Optional reason for status change"
    )


class AdminTenantDeleteResponse(BaseModel):
    """Response after deleting a tenant."""

    message: str
    tenant_id: UUID
    deleted_at: datetime
