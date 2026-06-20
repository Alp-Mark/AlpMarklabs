"""Pydantic schemas for role and permission operations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PermissionInfo(BaseModel):
    """Information about a single permission."""

    permission: str
    description: str


class PermissionCatalogResponse(BaseModel):
    """Response for GET /permissions endpoint."""

    permissions: list[PermissionInfo]


class RoleCreateRequest(BaseModel):
    """Request to create a custom role."""

    name: str = Field(min_length=1, max_length=100)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    """Request to update a custom role."""

    name: str | None = Field(None, min_length=1, max_length=100)
    permissions: list[str] | None = None


class RoleResponse(BaseModel):
    """Response for role information."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    permissions: list[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """Response for GET /roles endpoint."""

    roles: list[RoleResponse]
