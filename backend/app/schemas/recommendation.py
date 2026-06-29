"""FR-071 / T-053: Pydantic schemas for Recommendation API responses.

E1 extensions: confidence_score (numeric), data_sources (connector list),
and support for expired/archived states.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
