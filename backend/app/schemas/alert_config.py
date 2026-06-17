"""Pydantic schemas for alert configuration APIs (T-072).

Supports CRUD operations on alert thresholds and alert recipients.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertThresholdCreate(BaseModel):
    """Request body to create a new alert threshold."""

    alert_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Alert type (e.g., 'kpi', 'margin', 'inventory')",
    )
    metric_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Metric name (e.g., 'roas', 'margin_pct', 'stockout_risk')",
    )
    threshold_value: float = Field(
        ...,
        description="Threshold value for comparison",
    )
    comparison_operator: Literal["<", ">", "<=", ">=", "==", "!="] = Field(
        default="<",
        description="Comparison operator for threshold",
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether this threshold is active",
    )


class AlertThresholdUpdate(BaseModel):
    """Request body to update an alert threshold (all fields optional)."""

    threshold_value: float | None = Field(
        None,
        description="Threshold value for comparison",
    )
    comparison_operator: Literal["<", ">", "<=", ">=", "==", "!="] | None = Field(
        None,
        description="Comparison operator for threshold",
    )
    is_enabled: bool | None = Field(
        None,
        description="Whether this threshold is active",
    )


class AlertThresholdResponse(BaseModel):
    """Response body for alert threshold."""

    id: UUID
    tenant_id: UUID
    alert_type: str
    metric_name: str
    threshold_value: float
    comparison_operator: str
    is_enabled: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertThresholdListResponse(BaseModel):
    """Response body for list of alert thresholds."""

    thresholds: list[AlertThresholdResponse]
    total: int


class AlertRecipientCreate(BaseModel):
    """Request body to create a new alert recipient."""

    user_id: UUID = Field(
        ...,
        description="User ID to receive alerts",
    )
    channel: Literal["email", "slack", "sms"] = Field(
        ...,
        description="Delivery channel",
    )
    destination: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Delivery destination (email, Slack webhook, phone number)",
    )


class AlertRecipientUpdate(BaseModel):
    """Request body to update an alert recipient (all fields optional)."""

    destination: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Delivery destination",
    )
    is_verified: bool | None = Field(
        None,
        description="Whether this recipient has been verified",
    )


class AlertRecipientResponse(BaseModel):
    """Response body for alert recipient."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    channel: str
    destination: str
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRecipientListResponse(BaseModel):
    """Response body for list of alert recipients."""

    recipients: list[AlertRecipientResponse]
    total: int
