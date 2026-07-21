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
    """Clear, plain-English heading for the recommendation card."""
    if rule_id == "OPT-BUDGET-001" and meta:
        meta_alloc = meta.get("meta_allocation", {})
        g_alloc    = meta.get("google_allocation", {})
        meta_eff   = meta_alloc.get("current_efficiency", 0)
        g_eff      = g_alloc.get("current_efficiency", 0)
        shift_to   = "Google" if g_eff > meta_eff else "Meta"
        shift_from = "Meta" if shift_to == "Google" else "Google"
        # Use absolute spend_change; fall back to computing from current vs optimal
        shift_amt = abs(meta_alloc.get("spend_change", 0) or 0)
        if shift_amt == 0:
            cur = meta_alloc.get("current_spend", 0)
            opt = meta_alloc.get("optimal_spend", 0)
            shift_amt = abs(opt - cur)
        if shift_amt < 1000:
            return f"Rebalance Meta and Google ad budget"
        return f"Shift ₹{shift_amt / 1000:.0f}K/day from {shift_from} to {shift_to}"

    if rule_id == "OPT-MULTICHANNEL-001" and meta:
        channels = meta.get("channels", [])
        if channels:
            sorted_ch = sorted(channels, key=lambda c: c.get("spend_change", 0))
            top_inc = next(
                (c for c in reversed(sorted_ch) if c.get("spend_change", 0) > 500),
                None,
            )
            top_dec = next(
                (c for c in sorted_ch if c.get("spend_change", 0) < -500),
                None,
            )
            if top_inc and top_dec:
                inc = top_inc["name"].replace("_", " ").title()
                dec = top_dec["name"].replace("_", " ").title()
                shift = abs(top_dec.get("spend_change", 0))
                return (
                    f"Shift \u20b9{shift / 1000:.0f}K/day from {dec} to {inc}"
                )
        return "Rebalance influencer, email and affiliate budget"

    if rule_id.startswith("OPT-SATURATION-") and meta:
        channel = meta.get("channel", "").title() or rule_id.split("-")[-1].title()
        saturated = meta.get("saturated", False)
        knee = meta.get("knee_spend", 0)
        if saturated and knee:
            return f"Cap {channel} spend. Diminishing returns past \u20b9{knee / 1000:.0f}K/day"
        return f"{channel} only. Consider testing a second ad channel"

    # Humanise rule_id (e.g. RET-REPEAT-001 → "Repeat Purchase Rate")
    parts = rule_id.replace("-", " ").title().split()
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
        saturating = "Meta" if meta_eff < g_eff else "Google"
        growing    = "Google" if saturating == "Meta" else "Meta"
        return (
            f"{saturating} audiences are saturating."
            f" {growing} can convert that budget better right now."
        )
    if rule_id == "OPT-MULTICHANNEL-001" and meta:
        channels = meta.get("channels", [])
        lift = meta.get("lift_pct", 0)
        return (
            f"{len(channels)} channels analysed."
            f" Rebalancing adds +{lift:.1f}% conversions without changing total budget."
        )
    if rule_id.startswith("OPT-SATURATION-") and meta:
        channel = meta.get("channel", "").title() or rule_id.split("-")[-1].title()
        saturated = meta.get("saturated", False)
        eff_change = meta.get("efficiency_change_pct", 0)
        if saturated:
            return (
                f"{channel} efficiency has dropped {abs(eff_change):.0f}%."
                f" Each extra rupee spent is returning less than before."
            )
        return (
            f"You're running on {channel} only. Adding a second channel "
            f"reduces risk and unlocks more conversion volume."
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
        meta_eff   = meta_alloc.get("current_efficiency", 0)
        g_eff      = g_alloc.get("current_efficiency", 0)
        meta_opt   = meta_alloc.get("optimal_efficiency", 0)
        g_opt      = g_alloc.get("optimal_efficiency", 0)
        shift_amt  = abs(
            meta_alloc.get("spend_change", 0) or g_alloc.get("spend_change", 0)
        )
        direction  = (
            "Meta \u2192 Google" if meta_alloc.get("spend_change", 0) < 0
            else "Google \u2192 Meta"
        )
        meta_r2    = acc.get("meta_r2", 0)
        g_r2       = acc.get("google_r2", 0)
        conf_pct   = round(confidence_score * 100)

        signals.append({
            "label": "What’s happening with Meta",
            "value": (
                f"Every ₹1,000 spent on Meta is generating {meta_eff:.2f} conversions."
                + (
                    " Spending more is producing fewer additional results."
                    " The audience is getting saturated."
                    if meta_eff < meta_opt
                    else " Meta is performing well and has room for more spend."
                )
            ),
            "context": None,
        })
        signals.append({
            "label": "What’s happening with Google",
            "value": (
                f"Every ₹1,000 spent on Google is generating {g_eff:.2f} conversions."
                + (
                    " There is room to grow here. Adding more budget"
                    " should improve results before hitting a ceiling."
                    if g_eff < g_opt
                    else " Google is already at its most efficient."
                )
            ),
            "context": None,
        })
        signals.append({
            "label": "What we’re suggesting",
            "value": (
                f"Move ₹{shift_amt / 1000:.0f}K/day ({direction})"
                " without changing the total budget."
                " The money is already being spent. It just performs better"
                " on a different channel right now."
            ),
            "context": None,
        })
        signals.append({
            "label": "How confident are we",
            "value": (
                f"{conf_pct}% confidence, based on real spend and conversion data"
                f" from both channels."
                + (
                    " The data fits the model well."
                    if min(meta_r2, g_r2) > 0.7
                    else " More data would make this signal stronger."
                )
            ),
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
        "value": (
            f"{confidence_score:.0%}"
            f" ({confidence_level.replace('_', ' ').title()})"
        ),
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
