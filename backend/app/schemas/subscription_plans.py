"""Pydantic schemas for subscription plans."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SubscriptionPlanLimits(BaseModel):
    """Plan resource limits."""

    seat_limit: int
    connector_limit: int
    recommendation_limit: int


class SubscriptionPlanResponse(BaseModel):
    """Public subscription plan details."""

    id: uuid.UUID
    slug: str
    name: str
    description: str
    price_monthly: float
    price_annual: float
    features: list[str]
    limits: SubscriptionPlanLimits
    is_active: bool
    sort_order: int


class SubscriptionPlanCreateRequest(BaseModel):
    """Create new subscription plan (super-admin only)."""

    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    price_monthly: float = Field(..., ge=0)
    price_annual: float = Field(..., ge=0)
    features: list[str] = Field(default_factory=list)
    limits: SubscriptionPlanLimits
    is_active: bool = True
    sort_order: int = 0


class SubscriptionPlanUpdateRequest(BaseModel):
    """Update existing subscription plan (super-admin only)."""

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, min_length=10, max_length=500)
    price_monthly: float | None = Field(None, ge=0)
    price_annual: float | None = Field(None, ge=0)
    features: list[str] | None = None
    limits: SubscriptionPlanLimits | None = None
    is_active: bool | None = None
    sort_order: int | None = None
