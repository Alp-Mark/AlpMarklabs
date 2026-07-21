"""Pydantic schemas for tenant goals (Goals & Targets widget)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

VALID_METRIC_KEYS = Literal[
    "monthly_revenue",
    "daily_orders",
    "monthly_orders",
    "aov",
    "blended_roas",
    "contribution_margin_pct",
    "cac_payback_days",
    "repeat_purchase_rate_pct",
    "return_rate_pct",
]

METRIC_LABELS: dict[str, str] = {
    "monthly_revenue": "Monthly Revenue",
    "daily_orders": "Orders / Day",
    "monthly_orders": "Orders / Month",
    "aov": "Average Order Value",
    "blended_roas": "Blended ROAS",
    "contribution_margin_pct": "Contribution Margin %",
    "cac_payback_days": "CAC Payback (days)",
    "repeat_purchase_rate_pct": "Repeat Purchase Rate %",
    "return_rate_pct": "Return Rate %",
}


class TenantGoalCreate(BaseModel):
    metric_key: VALID_METRIC_KEYS
    target_value: float = Field(..., gt=0)
    target_date: date
    label: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_pinned: bool = True


class TenantGoalUpdate(BaseModel):
    target_value: float | None = Field(default=None, gt=0)
    target_date: date | None = None
    label: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_pinned: bool | None = None


class TenantGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    metric_key: str
    label: str
    target_value: float
    target_date: date
    is_pinned: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # Computed live fields (populated by endpoint, not from DB)
    current_value: float | None = None
    progress_pct: float | None = None
    status: str | None = None  # on_track | at_risk | behind | achieved
    unit: str | None = None    # ₹ | x | % | days


class TenantGoalsResponse(BaseModel):
    goals: list[TenantGoalResponse]
    total: int
