import uuid

from pydantic import BaseModel, Field


class MembershipRoleUpdateRequest(BaseModel):
    role: str = Field(min_length=3, max_length=50)


class MembershipResponse(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    role: str
    is_active: bool
