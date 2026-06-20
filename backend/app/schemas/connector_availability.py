"""Schemas for D6 - Connector availability tracking (super-admin only)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConnectorSourceBreakdown(BaseModel):
    """Per-source connector statistics."""

    source: str
    total_connectors: int
    connected_count: int
    disconnected_count: int
    error_count: int
    tenants_using: int


class ConnectorAvailabilityResponse(BaseModel):
    """Platform-wide connector availability statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_connectors: int
    active_connectors: int
    disconnected_connectors: int
    connectors_with_errors: int
    recent_sync_failures_24h: int
    tenants_with_connectors: int
    tenants_without_connectors: int
    by_source: list[ConnectorSourceBreakdown]
    generated_at: datetime
