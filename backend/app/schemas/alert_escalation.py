"""Pydantic schemas for alert escalation and acknowledgement APIs (T-078).

Supports acknowledgement, dismissal, and escalation rule management.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertAcknowledgementCreate(BaseModel):
    """Request body to acknowledge an alert."""

    alert_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the alert being acknowledged",
    )
    alert_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Alert type (e.g., 'early_warning', 'operational_anomaly')",
    )


class AlertAcknowledgementResponse(BaseModel):
    """Response when an alert is acknowledged."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    alert_id: str
    alert_type: str
    acknowledged_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertDismissalCreate(BaseModel):
    """Request body to dismiss an alert."""

    alert_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the alert being dismissed",
    )
    alert_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Alert type (e.g., 'early_warning', 'operational_anomaly')",
    )
    dismiss_reason: str | None = Field(
        None,
        max_length=500,
        description="Optional reason for dismissal",
    )


class AlertDismissalResponse(BaseModel):
    """Response when an alert is dismissed."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    alert_id: str
    alert_type: str
    dismiss_reason: str | None
    dismissed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    """Response for listing alerts with acknowledgement/dismissal status."""

    alert_id: str
    alert_type: str
    domain: str
    is_acknowledged: bool
    acknowledged_by_user_id: UUID | None
    acknowledged_at: datetime | None
    is_dismissed: bool
    dismissed_by_user_id: UUID | None
    dismissed_at: datetime | None
    dismiss_reason: str | None
    alert_fired_at: datetime


class EscalationRuleCreate(BaseModel):
    """Request body to create an escalation rule."""

    alert_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Alert type this rule applies to (e.g., 'early_warning')",
    )
    domain: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Domain (e.g., 'growth', 'retention', 'operations')",
    )
    unacknowledged_hours: float = Field(
        ...,
        gt=0,
        description="Hours before escalation fires if alert unacknowledged",
    )
    escalation_to_roles: list[str] | None = Field(
        None,
        description="Roles to escalate (e.g., executive_owner, growth_manager)",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this escalation rule is active",
    )


class EscalationRuleUpdate(BaseModel):
    """Request body to update an escalation rule (all fields optional)."""

    unacknowledged_hours: float | None = Field(
        None,
        gt=0,
        description="Hours before escalation fires if alert unacknowledged",
    )
    escalation_to_roles: list[str] | None = Field(
        None,
        description="List of roles to escalate to",
    )
    is_enabled: bool | None = Field(
        None,
        description="Whether this escalation rule is active",
    )


class EscalationRuleResponse(BaseModel):
    """Response for an escalation rule."""

    id: UUID
    tenant_id: UUID
    alert_type: str
    domain: str
    unacknowledged_hours: float
    escalation_to_roles: list[str] | None
    is_enabled: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EscalationRuleListResponse(BaseModel):
    """Response for listing escalation rules."""

    rules: list[EscalationRuleResponse]
    total_count: int
