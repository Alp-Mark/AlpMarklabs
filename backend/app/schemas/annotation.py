from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnnotationCreateRequest(BaseModel):
    """Request to create an annotation on an analysis view."""

    text: str = Field(..., min_length=1, max_length=1000, description="Annotation text")
    event_date: date | None = Field(
        None, description="Optional date for lifecycle/operational events"
    )
    annotation_type: str | None = Field(
        None,
        max_length=50,
        description="Optional type tag (lifecycle, operational, context)",
    )


class AnnotationResponse(BaseModel):
    """Full annotation model with all fields."""

    id: UUID
    saved_view_id: UUID
    tenant_id: UUID
    created_by_id: UUID
    text: str
    event_date: date | None
    annotation_type: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnotationListResponse(BaseModel):
    """List of annotations with pagination."""

    items: list[AnnotationResponse]
    total: int
