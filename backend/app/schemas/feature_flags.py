"""Pydantic schemas for feature flags."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FeatureFlagResponse(BaseModel):
    """Feature flag details."""

    id: uuid.UUID
    slug: str
    name: str
    description: str
    category: str
    is_available: bool
    default_enabled: bool


class FeatureFlagCreateRequest(BaseModel):
    """Create new feature flag (super-admin only)."""

    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    category: str = Field(..., min_length=2, max_length=50)
    is_available: bool = True
    default_enabled: bool = False


class FeatureFlagUpdateRequest(BaseModel):
    """Update feature flag (super-admin only)."""

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, min_length=10, max_length=500)
    category: str | None = Field(None, min_length=2, max_length=50)
    is_available: bool | None = None
    default_enabled: bool | None = None


class TenantFeatureResponse(BaseModel):
    """Feature flag status for a tenant."""

    slug: str
    name: str
    description: str
    category: str
    is_enabled: bool
    source: str  # "plan", "override", or "default"


class TenantFeatureFlagOverride(BaseModel):
    """Per-tenant feature flag override details."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    feature_flag_slug: str
    is_enabled: bool
    enabled_at: datetime | None
    disabled_at: datetime | None
    changed_by_user_id: uuid.UUID | None


class TenantFeatureToggleRequest(BaseModel):
    """Toggle feature flag for tenant (super-admin only)."""

    feature_slug: str
    is_enabled: bool
