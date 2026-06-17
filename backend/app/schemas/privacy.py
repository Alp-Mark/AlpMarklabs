import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PrivacyRequestCreateRequest(BaseModel):
    request_type: str = Field(min_length=6, max_length=20)
    subject_email: str = Field(min_length=5, max_length=320)
    reason: str | None = Field(default=None, min_length=3, max_length=500)


class PrivacyRequestStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=7, max_length=20)
    resolution_note: str | None = Field(default=None, min_length=3, max_length=500)


class PrivacyRequestResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    request_type: str
    subject_email: str
    status: str
    reason: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime