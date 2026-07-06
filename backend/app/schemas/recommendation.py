"""FR-071 / T-053: Pydantic schemas for Recommendation API responses.

E1 extensions: confidence_score (numeric), data_sources (connector list),
and support for expired/archived states.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

# ── Computed field helpers ─────────────────────────────────────────────────────

def _rec_title(rule_id: str, affected_area: str, meta: dict | None) -> str:
    """Catchy one-line heading for the recommendation card."""
    if rule_id == "OPT-BUDGET-001" and meta:
        meta_alloc = meta.get("meta_allocation", {})
        g_alloc    = meta.get("google_allocation", {})
        meta_eff   = meta_alloc.get("current_efficiency", 0)
        g_eff      = g_alloc.get("current_efficiency", 0)
        change     = meta.get("daily_revenue_impact", 0)
        shift_to   = "Google" if g_eff > meta_eff else "Meta"
        shift_amt  = abs(
            meta_alloc.get("spend_change", 0) or g_alloc.get("spend_change", 0)
        )
        return (
            f"Shift ₹{shift_amt:,.0f}/day to {shift_to}"
            f" — +₹{change:,.0f}/day revenue"
        )
    # Threshold-based: humanise rule_id  (e.g. RET-REPEAT-001 → "Repeat Purchase Rate")
    parts = rule_id.replace("-", " ").title().split()
    # Drop trailing numeric IDs (001, 002 …)
    label = " ".join(p for p in parts if not p.isdigit())
    if affected_area and affected_area not in ("Meta Ads, Google Ads",):
        return affected_area
    return label


def _rec_short_description(
    rule_id: str,
    signal_summary: str,
    meta: dict | None,
    estimated_impact: float | None,
) -> str:
    """One-sentence description shown below the heading."""
    if rule_id == "OPT-BUDGET-001" and meta:
        meta_alloc = meta.get("meta_allocation", {})
        g_alloc    = meta.get("google_allocation", {})
        meta_eff   = meta_alloc.get("current_efficiency", 0)
        g_eff      = g_alloc.get("current_efficiency", 0)
        lift       = meta.get("lift_pct", 0)
        saturating = "Meta" if meta_eff < g_eff else "Google"
        growing    = "Google" if saturating == "Meta" else "Meta"
        return (
            f"{saturating} is saturating at current spend while {growing} has"
            f" headroom. Reallocation lifts conversions {lift:.1f}%"
            + (f" (+₹{estimated_impact:,.0f}/day)." if estimated_impact else ".")
        )
    # Fall back to first sentence of signal_summary
    first = signal_summary.split(".")[0].strip()
    return first + "." if first and not first.endswith(".") else first


def _rec_supporting_signals(
    rule_id: str,
    evidence: dict | None,
    meta: dict | None,
    confidence_score: float,
    confidence_level: str,
) -> list[dict]:
    """Structured evidence signals shown in the 'How we got here' section."""
    signals: list[dict] = []

    if rule_id == "OPT-BUDGET-001" and meta:
        meta_alloc = meta.get("meta_allocation", {})
        g_alloc    = meta.get("google_allocation", {})
        acc        = meta.get("model_accuracy", {})

        signals.append({
            "label": "Meta efficiency",
            "value": f"{meta_alloc.get('current_efficiency', 0):.2f}× per ₹1k",
            "context": (
                "declining — nearing saturation"
                if meta_alloc.get("current_efficiency", 1)
                < meta_alloc.get("optimal_efficiency", 1)
                else "at optimal level"
            ),
        })
        signals.append({
            "label": "Google efficiency",
            "value": f"{g_alloc.get('current_efficiency', 0):.2f}× per ₹1k",
            "context": (
                "underutilised — room to grow"
                if g_alloc.get("current_efficiency", 0)
                < g_alloc.get("optimal_efficiency", 0)
                else "at optimal level"
            ),
        })
        signals.append({
            "label": "Proposed reallocation",
            "value": (
                f"₹{abs(meta_alloc.get('spend_change', 0)):,.0f}/day"
                f" Meta → Google"
                if meta_alloc.get("spend_change", 0) < 0
                else f"₹{abs(g_alloc.get('spend_change', 0)):,.0f}/day"
                f" Google → Meta"
            ),
            "context": None,
        })
        signals.append({
            "label": "Model accuracy",
            "value": (
                f"Meta R²={acc.get('meta_r2', 0):.0%},"
                f" Google R²={acc.get('google_r2', 0):.0%}"
            ),
            "context": "Hill curve fit on last 90 days of spend/conversion data",
        })
        signals.append({
            "label": "Confidence",
            "value": f"{confidence_score:.0%} ({confidence_level.replace('_', ' ').title()})",
            "context": None,
        })
        return signals

    # Threshold-based: pull from evidence dict
    ev = evidence or {}
    for key, val in ev.items():
        if key in ("rule_id",):
            continue
        label = key.replace("_", " ").title()
        signals.append({"label": label, "value": str(val), "context": None})
    signals.append({
        "label": "Confidence",
        "value": f"{confidence_score:.0%} ({confidence_level.replace('_', ' ').title()})",
        "context": None,
    })
    return signals


class RecommendationResponse(BaseModel):
    """Recommendation response with E1 confidence and data source tracking."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    rule_id: str
    domain: str
    snapshot_date: date
    affected_area: str
    signal_summary: str
    suggested_action: str
    estimated_impact: float | None
    confidence_level: str = Field(
        ...,
        description="5-level enum: very_low, low, medium, high, very_high",
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Numeric confidence (0-1 scale)"
    )
    data_sources: list[str] = Field(
        default_factory=list,
        description="Connectors used: ['shopify', 'meta', 'google_ads']",
    )
    source: str = Field(
        default="threshold",
        description="Source: 'threshold' (rule-based) or 'optimization' (ML-based)",
    )
    optimization_metadata: dict | None = Field(
        default=None,
        description=(
            "Optimization details: conversions, lift_pct, model R²"
        ),
    )
    fitted_model_id: UUID | None = Field(
        default=None,
        description="FK to fitted model (for ML-based recommendations)",
    )
    data_freshness_context: str
    status: str = Field(
        ...,
        description=(
            "Lifecycle: new, reviewed, approved, rejected, "
            "implemented_externally, outcome_observed, expired, archived"
        ),
    )
    priority: int
    impact_score: float | None = Field(
        default=None,
        description="Impact score used for prioritization",
    )
    evidence: dict | None = Field(
        default=None,
        description="Supporting evidence and detailed metrics for the recommendation",
    )
    review_note: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def title(self) -> str:
        """Catchy heading for the recommendation card."""
        return _rec_title(self.rule_id, self.affected_area, self.optimization_metadata)

    @computed_field
    @property
    def short_description(self) -> str:
        """One-sentence summary shown below the heading."""
        return _rec_short_description(
            self.rule_id, self.signal_summary,
            self.optimization_metadata, self.estimated_impact,
        )

    @computed_field
    @property
    def supporting_signals(self) -> list[dict]:
        """Structured evidence signals for 'How we got here'."""
        return _rec_supporting_signals(
            self.rule_id, self.evidence,
            self.optimization_metadata, self.confidence_score, self.confidence_level,
        )

    @field_validator("confidence_score", mode="before")
    @classmethod
    def clamp_confidence_score(cls, v: float) -> float:
        """Clamp confidence_score to valid range [0.0, 1.0] to handle legacy data."""
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v


class RecommendationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[RecommendationResponse]
    total: int


class RecommendationDetailResponse(BaseModel):
    """E6: Recommendation with full provenance of spawned simulations.

    FR-126: When viewing a recommendation detail, show all simulations
    that were launched from this recommendation, allowing users to compare
    different scenario attempts and revisit past analysis.
    """

    model_config = ConfigDict(from_attributes=True)

    recommendation: RecommendationResponse
    simulations: list[dict] = Field(
        default_factory=list,
        description="All simulations spawned from this recommendation",
    )
    simulation_count: int = Field(
        default=0, description="Total number of simulations"
    )


class RecommendationStatusUpdateRequest(BaseModel):
    """FR-073 / T-059: Body for PATCH status endpoint."""

    to_status: str
    note: str | None = None
