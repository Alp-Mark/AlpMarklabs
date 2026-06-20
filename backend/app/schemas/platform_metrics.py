"""Schemas for D5 - Platform metrics dashboard (super-admin only)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantMetrics(BaseModel):
    """Tenant-level aggregate metrics."""

    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    new_tenants_last_30_days: int
    new_tenants_last_7_days: int


class UserMetrics(BaseModel):
    """User-level aggregate metrics."""

    total_users: int
    active_users: int
    users_per_tenant_avg: float
    new_users_last_30_days: int
    new_users_last_7_days: int


class SubscriptionMetrics(BaseModel):
    """Subscription plan distribution."""

    starter_count: int
    professional_count: int
    enterprise_count: int
    total_seats_allocated: int
    total_seats_used: int


class FeatureFlagMetrics(BaseModel):
    """Feature flag adoption metrics."""

    total_flags: int
    total_overrides: int
    most_enabled_features: list[tuple[str, int]]  # (feature_slug, tenant_count)
    most_disabled_features: list[tuple[str, int]]


class IntegrationMetrics(BaseModel):
    """Integration health aggregate metrics."""

    total_connectors: int
    active_connectors: int
    connectors_with_errors: int
    total_sync_jobs_last_24h: int
    failed_sync_jobs_last_24h: int


class PlatformMetricsResponse(BaseModel):
    """Comprehensive platform metrics for super-admin dashboard."""

    model_config = ConfigDict(from_attributes=True)

    tenant_metrics: TenantMetrics
    user_metrics: UserMetrics
    subscription_metrics: SubscriptionMetrics
    feature_flag_metrics: FeatureFlagMetrics
    integration_metrics: IntegrationMetrics
    generated_at: datetime
    platform_version: str
