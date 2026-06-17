"""FR-032, FR-034 / T-064: Pydantic schemas for saved analysis views."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SavedAnalysisViewCreateRequest(BaseModel):
    name: str
    description: str | None = None
    filters_config: dict


class SavedAnalysisViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_id: UUID
    name: str
    description: str | None
    filters_config: dict
    created_at: datetime
    updated_at: datetime


class SavedAnalysisViewListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[SavedAnalysisViewResponse]
    total: int


class AnalysisViewShareRequest(BaseModel):
    recipient_emails: list[str]
    scope: str = "tenant"  # "tenant" or "one_time_link"


class AnalysisViewShareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    saved_view_id: UUID
    tenant_id: UUID
    shared_by_id: UUID
    recipient_email: str
    scope: str
    one_time_token: str | None
    shared_at: datetime


class AnalysisViewShareListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AnalysisViewShareResponse]
    total: int
