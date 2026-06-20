"""Pydantic schemas for support ticket operations (E4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# E4: Support ticket CRUD schemas
# ---------------------------------------------------------------------------


class SupportTicketCreate(BaseModel):
    """Request schema for creating a support ticket."""

    tenant_id: uuid.UUID = Field(description="Tenant identifier")
    priority: str = Field(
        default="medium",
        description="Ticket priority: low, medium, high, urgent",
    )
    issue_type: str = Field(
        description="Issue type: integration_failure, sync_error, etc"
    )
    title: str = Field(max_length=200, description="Brief ticket title")
    description: str | None = Field(default=None, description="Detailed description")


class SupportTicketUpdate(BaseModel):
    """Request schema for updating a support ticket."""

    status: str | None = Field(
        default=None, description="Ticket status: open, in_progress, resolved, closed"
    )
    priority: str | None = Field(default=None, description="Ticket priority")
    assigned_to_user_id: uuid.UUID | None = Field(
        default=None, description="Assign to user ID"
    )
    due_date: date | None = Field(default=None, description="Due date")
    internal_notes: str | None = Field(
        default=None, description="Internal support notes (FR-099)"
    )


class SupportTicketClose(BaseModel):
    """Request schema for closing a support ticket (FR-100, FR-101)."""

    resolution_summary: str = Field(description="Summary of resolution (required)")
    resolution_category: str = Field(
        description="Root cause category (required): integration_auth, sync_config, etc"
    )


class SupportTicketResponse(BaseModel):
    """Response schema for a support ticket."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Ticket identifier")
    tenant_id: uuid.UUID = Field(description="Tenant identifier")
    status: str = Field(description="Ticket status")
    priority: str = Field(description="Ticket priority")
    issue_type: str = Field(description="Issue type")
    title: str = Field(description="Ticket title")
    description: str | None = Field(description="Ticket description")
    created_by_user_id: uuid.UUID = Field(description="Creator user ID")
    assigned_to_user_id: uuid.UUID | None = Field(description="Assigned user ID")
    due_date: date | None = Field(description="Due date")
    internal_notes: str | None = Field(description="Internal support notes")
    resolution_summary: str | None = Field(description="Resolution summary")
    resolution_category: str | None = Field(description="Resolution category")
    closed_at: datetime | None = Field(description="Closure timestamp")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class SupportTicketListResponse(BaseModel):
    """Response schema for listing support tickets."""

    tickets: list[SupportTicketResponse] = Field(description="List of tickets")
    total: int = Field(description="Total ticket count")
