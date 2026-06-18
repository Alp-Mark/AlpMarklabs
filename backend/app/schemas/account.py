import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountActivationRequest(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class AccountActivationResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    activated_at: datetime


class UserResponse(BaseModel):
    """Response for GET /users/me endpoint."""

    email: str
    platform_role: str
    tenant_id: str | None = None


class LoginRequest(BaseModel):
    """Request for POST /auth/login endpoint."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Response for POST /auth/login endpoint."""

    access_token: str
    token_type: str = "bearer"
