import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AccountActivationRequest(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)


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


class ForgotPasswordRequest(BaseModel):
    """Request for POST /auth/forgot-password endpoint."""

    email: str = Field(min_length=3, max_length=320)


class ForgotPasswordResponse(BaseModel):
    """Response for POST /auth/forgot-password endpoint."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Request for POST /auth/reset-password endpoint."""

    token: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)


class ResetPasswordResponse(BaseModel):
    """Response for POST /auth/reset-password endpoint."""

    message: str


class UserSessionResponse(BaseModel):
    """Response for user session information."""

    id: uuid.UUID
    jti: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime | None
    expires_at: datetime
    is_current: bool


class SessionListResponse(BaseModel):
    """Response for GET /me/sessions endpoint."""

    sessions: list[UserSessionResponse]


class LogoutResponse(BaseModel):
    """Response for logout endpoints."""

    message: str


class BootstrapSuperAdminRequest(BaseModel):
    """Request for POST /auth/bootstrap/super-admin endpoint."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)


class BootstrapSuperAdminResponse(BaseModel):
    """Response for POST /auth/bootstrap/super-admin endpoint."""

    id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool
    tenant_id: uuid.UUID | None
    created_at: datetime

