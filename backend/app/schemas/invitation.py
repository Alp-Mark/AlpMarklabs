import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserInviteRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    role: str = Field(min_length=3, max_length=50)


class UserInviteResponse(BaseModel):
    invitation_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    token: str
    expires_at: datetime
