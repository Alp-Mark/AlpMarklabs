"""Pydantic schemas for tenant goals (Goals & Targets widget)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_METRIC_KEYS = {
    "monthly_revenue",
    "daily_orders",
    "monthly_orders",
    "aov",
    "blended_roas",
    "contribution_margin_pct",
    "cac_payback_days",
    "repeat_purchase_rate_pct",
    "return_rate_pct",
}

# Map display labels → metric keys (handles what Replit might send)
_LABEL_TO_KEY: dict[str, str] = {
    "monthly revenue": "monthly_revenue",
    "orders / day": "daily_orders",
    "daily orders": "daily_orders",
    "orders / month": "monthly_orders",
    "monthly orders": "monthly_orders",
    "average order value": "aov",
    "blended roas": "blended_roas",
    "contribution margin %": "contribution_margin_pct",
    "contribution margin": "contribution_margin_pct",
    "cac payback (days)": "cac_payback_days",
    "cac payback": "cac_payback_days",
    "repeat purchase rate %": "repeat_purchase_rate_pct",
    "repeat purchase rate": "repeat_purchase_rate_pct",
    "return rate %": "return_rate_pct",
    "return rate": "return_rate_pct",
}

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


def _normalize_metric_key(v: str) -> str:
    """Accept snake_case keys or space-separated display labels."""
    normalized = v.strip().lower().replace(" ", "_")
    if normalized in VALID_METRIC_KEYS:
        return normalized
    # Try label lookup
    label_match = _LABEL_TO_KEY.get(v.strip().lower())
    if label_match:
        return label_match
    valid = ", ".join(sorted(VALID_METRIC_KEYS))
    raise ValueError(f"Invalid metric_key '{v}'. Valid values: {valid}")


class TenantGoalCreate(BaseModel):
    metric_key: str
    target_value: float = Field(..., gt=0)
    target_date: date
    label: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    is_pinned: bool = True

    @field_validator("metric_key", mode="before")
    @classmethod
    def validate_metric_key(cls, v: str) -> str:
        return _normalize_metric_key(v)


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
