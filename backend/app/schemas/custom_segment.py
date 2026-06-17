"""Pydantic schemas for custom segments (FR-044 / T-071)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomSegmentCreate(BaseModel):
    """Request body for creating a custom segment."""

    name: str = Field(..., min_length=1, max_length=255, description="Segment name")
    description: str | None = Field(
        None, max_length=1000, description="Optional description"
    )
    definition: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Flexible JSON filter definition "
            "(e.g., aov_min, aov_max, segment_type)"
        ),
    )


class CustomSegmentUpdate(BaseModel):
    """Request body for updating a custom segment."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Segment name (optional)"
    )
    description: str | None = Field(
        None, max_length=1000, description="Optional description"
    )
    definition: dict[str, Any] | None = Field(
        None, description="Flexible JSON filter definition (optional)"
    )
    is_active: bool | None = Field(None, description="Active/inactive flag (optional)")


class CustomSegmentResponse(BaseModel):
    """Response body for a custom segment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    definition: dict[str, Any]
    is_active: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CustomSegmentListResponse(BaseModel):
    """Response body for list of custom segments."""

    segments: list[CustomSegmentResponse]
    total: int
