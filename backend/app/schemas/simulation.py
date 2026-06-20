"""Pydantic schemas for simulation and scenario responses.

FR-081, FR-087 / T-081: Three-scenario simulation (baseline/upside/downside).
FR-083 / T-083: Simulation side-by-side comparison with confidence warnings.
FR-090 / T-084: Save and revisit simulation scenarios.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScenarioResponse(BaseModel):
    """Single scenario within a simulation.

    Contains input assumptions, computed outputs, and confidence score
    for one of: baseline, upside, or downside.
    """

    id: UUID
    simulation_id: UUID
    scenario_type: str
    input_assumptions: dict
    output_metrics: dict
    impact_deltas: dict
    confidence_score: float
    rationale: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationResponse(BaseModel):
    """Complete simulation with all three scenarios.

    Returned when retrieving a simulation run. Contains baseline, upside,
    and downside scenarios along with metadata about the simulation.
    
    E2 additions: name, description, is_deleted, updated_at for
    rename/duplicate/delete operations.
    """

    id: UUID
    tenant_id: UUID
    recommendation_id: UUID | None
    name: str | None = Field(None, description="User-provided simulation name")
    description: str | None = Field(None, description="User notes about simulation")
    domain: str
    simulation_type: str
    x_star: dict
    confidence_level: str
    data_freshness_signal: str
    metric_completeness_signal: str
    baseline_scenario: dict
    upside_scenario: dict
    downside_scenario: dict
    simulation_metadata: dict
    is_deleted: bool = Field(default=False, description="Soft delete flag")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationListResponse(BaseModel):
    """Paginated list of simulations."""

    simulations: list[SimulationResponse]
    total_count: int


class SimulationDetailResponse(BaseModel):
    """Complete simulation detail view with all related scenarios.

    Returned when retrieving a saved simulation. Includes the simulation record
    plus all three scenario records from the scenarios table for full context.
    """

    simulation: SimulationResponse
    scenarios: list[ScenarioResponse] = Field(
        description="List of scenario records (baseline, upside, downside)"
    )

    model_config = ConfigDict(from_attributes=True)


class DataFreshnessWarning(BaseModel):
    """Warning about stale or incomplete data affecting simulation confidence."""

    source_name: str = Field(
        description="Name of data source (e.g., 'Shopify', 'Google Ads')"
    )
    last_synced_at: datetime = Field(description="Timestamp of last successful sync")
    hours_stale: int = Field(description="How many hours since last sync")
    confidence_impact: str = Field(
        description="How stale data affects confidence: 'low', 'medium', 'high'"
    )
    recommendation: str = Field(
        description="Action to take (e.g., 'Wait for next sync')"
    )

    model_config = ConfigDict(from_attributes=True)


class ScenarioComparisonColumn(BaseModel):
    """One simulation's scenario within a side-by-side comparison."""

    simulation_id: UUID
    simulation_domain: str
    scenario_type: str  # baseline, upside, downside
    input_assumptions: dict = Field(description="Key assumptions for this scenario")
    output_metrics: dict = Field(description="Projected metric values")
    impact_deltas: dict = Field(description="Change vs baseline")
    confidence_score: float = Field(ge=0, le=100, description="Confidence % (0-100)")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationComparisonMetricRow(BaseModel):
    """One metric compared across all simulations in a comparison."""

    metric_name: str = Field(description="e.g., 'ROAS', 'Margin %', 'CAC'")
    metric_unit: str = Field(description="e.g., '%', '$', 'days'")
    comparison_values: dict[str, float | None] = Field(
        description="Map of simulation_id → metric value, None if not applicable"
    )
    variance: dict[str, float | None] = Field(
        description="Map of simulation_id -> change from baseline, None if missing"
    )

    model_config = ConfigDict(from_attributes=True)


class SimulationComparisonView(BaseModel):
    """Side-by-side comparison of multiple simulations with confidence context."""

    comparison_id: str = Field(
        description="Unique ID for this comparison (e.g., 'sim123_sim456_comparison')"
    )
    tenant_id: UUID
    compared_simulations: list[ScenarioComparisonColumn] = Field(
        min_length=2, description="Must compare at least 2 simulations"
    )
    metrics: list[SimulationComparisonMetricRow] = Field(
        description="All metrics with values across simulations"
    )
    data_freshness_warnings: list[DataFreshnessWarning] = Field(
        description="Warnings about stale data that affects these simulations"
    )
    overall_confidence: float = Field(
        ge=0, le=100, description="Overall confidence % considering all data freshness"
    )
    recommendation_for_viewer: str = Field(
        description="Guidance on whether to act on these simulations "
        "(e.g., 'Safe to use', 'Wait for sync')"
    )
    comparison_created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulationComparisonRequest(BaseModel):
    """Request body for comparing multiple simulations."""

    simulation_ids: list[UUID] = Field(
        min_length=2, description="List of simulation IDs to compare (minimum 2)"
    )

    model_config = ConfigDict(from_attributes=True)


class SimulationExportRequest(BaseModel):
    """Request body for exporting a simulation."""

    format: str = Field(
        description="Export format: 'pdf' or 'csv'",
        pattern="^(pdf|csv)$"
    )
    include_scenarios: bool = Field(
        default=True,
        description="Whether to include detailed scenario data"
    )

    model_config = ConfigDict(from_attributes=True)


class SimulationExportResponse(BaseModel):
    """Response for export generation."""

    export_id: str = Field(description="Unique ID for this export")
    simulation_id: UUID
    format: str = Field(description="Export format (pdf or csv)")
    file_name: str = Field(description="Generated file name")
    file_size_bytes: int = Field(description="Size of generated file in bytes")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportShareRequest(BaseModel):
    """Request body for sharing an export with a recipient."""

    recipient_email: str = Field(
        description="Email address of recipient (must be active user in same tenant)"
    )

    model_config = ConfigDict(from_attributes=True)


class ExportShareResponse(BaseModel):
    """Response for export share creation/retrieval."""

    id: UUID = Field(description="Share record ID")
    simulation_id: UUID = Field(description="Simulation ID being shared")
    shared_by_email: str = Field(description="Email of user who shared the export")
    shared_with_email: str = Field(description="Email of recipient user")
    status: str = Field(description="Share status (active or revoked)")
    created_at: datetime = Field(description="When the share was created")
    revoked_at: datetime | None = Field(
        description="When the share was revoked (if applicable)"
    )

    model_config = ConfigDict(from_attributes=True)


class ExportShareListResponse(BaseModel):
    """Response for listing shared exports."""

    shares: list[ExportShareResponse] = Field(description="List of export shares")
    total: int = Field(description="Total number of shares")

    model_config = ConfigDict(from_attributes=True)


class ExportLinkResponse(BaseModel):
    """Response for export download link."""

    id: UUID = Field(description="Download link ID")
    share_id: UUID = Field(description="Associated export share ID")
    token: str = Field(description="Signed download token (URL-safe)")
    expires_at: datetime = Field(description="When this link expires")
    created_at: datetime = Field(description="When the link was created")
    accessed_at: datetime | None = Field(
        description="When the link was last used (if accessed)"
    )

    model_config = ConfigDict(from_attributes=True)


class GeneratedExportLinkResponse(BaseModel):
    """Response with generated download link."""

    download_link: ExportLinkResponse = Field(description="Download link details")
    download_url: str = Field(
        description="Full URL for download (includes token parameter)"
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# E2: Simulation rename/duplicate/delete schemas
# ---------------------------------------------------------------------------


class SimulationUpdateRequest(BaseModel):
    """Request body for updating simulation name/description (E2 rename)."""

    name: str | None = Field(None, max_length=255, description="Simulation name")
    description: str | None = Field(None, description="Simulation description/notes")


class SimulationDuplicateRequest(BaseModel):
    """Request body for duplicating a simulation (E2 duplicate)."""

    name: str | None = Field(
        None,
        max_length=255,
        description="Name for duplicated simulation (defaults to 'Copy of <original>')",
    )
    description: str | None = Field(
        None, description="Description for duplicated simulation"
    )


class SimulationDuplicateResponse(BaseModel):
    """Response for simulation duplication."""

    original_id: UUID = Field(description="ID of original simulation")
    duplicate_id: UUID = Field(description="ID of newly created duplicate")
    duplicate: SimulationResponse = Field(description="Full duplicated simulation")

    model_config = ConfigDict(from_attributes=True)


# ========== T-117: Recommendation-to-Simulation Launch ==========


class RecommendationSimulationLaunchRequest(BaseModel):
    """Request to launch a simulation pre-populated from recommendation parameters.

    FR-126 / T-117: When user clicks "Simulate" on a recommendation,
    this captures any user overrides or confirmations of the parameters
    that will be passed to the simulation engine.
    """

    override_parameters: dict | None = Field(
        default=None,
        description=(
            "Optional parameter overrides "
            "(user can adjust suggestions before simulating)"
        ),
    )

    model_config = ConfigDict(from_attributes=True)


class RecommendationSimulationLaunchResponse(BaseModel):
    """Response when launching simulation from a recommendation.

    Returns the newly created simulation with all three scenarios,
    showing the projected impact if the recommended action is taken.
    """

    simulation: SimulationResponse = Field(
        description="Newly created simulation with all three scenarios"
    )
    recommendation_id: UUID = Field(
        description="Original recommendation that was simulated"
    )
    parameters_used: dict = Field(
        description="The actual parameters that were passed to the simulator "
        "(after applying user overrides)"
    )
    message: str = Field(
        description="Human-readable message summarizing the launch "
        "(e.g., 'Simulation launched with Growth parameters')"
    )

    model_config = ConfigDict(from_attributes=True)


# ========== T-119: LLM Narration Layer for Recommendations ==========


class Citation(BaseModel):
    """Reference to a specific value in the simulation output.

    Used to track which numerical values in the narration come from where
    in the simulation payload, enabling audit trail and source verification.
    """

    field_name: str = Field(
        description="Name of the field being cited "
        "(e.g., 'baseline_margin_pct', 'upside_roas', 'downside_roi')"
    )
    scenario_type: str = Field(
        description="Scenario type: 'baseline', 'upside', or 'downside'"
    )
    value: float | str | None = Field(
        description="The actual numerical or string value being cited"
    )
    source_path: str = Field(
        description=(
            "JSON path to this value in simulation payload "
            "(e.g., 'upside_scenario.output_metrics.projected_roas')"
        )
    )
    confidence_note: str | None = Field(
        default=None,
        description=(
            "Optional note about confidence or data freshness "
            "affecting this value"
        ),
    )

    model_config = ConfigDict(from_attributes=True)


class NarrationRequest(BaseModel):
    """Request to generate LLM narration for a recommendation.

    FR-071, FR-079 / T-119: Takes simulation output and generates
    human-readable narrative framing, action description, and risk context.
    
    Note: tenant_id and recommendation_id are provided in the URL path,
    not in the request body.
    """

    override_tone: str | None = Field(
        default=None,
        description="Optional tone override: 'urgent', 'balanced', 'cautious' "
        "(default: inferred from confidence and impact)"
    )

    model_config = ConfigDict(from_attributes=True)


class NarrationResponse(BaseModel):
    """AI-generated narrative framing for a recommendation.

    Contains three text components generated by LLM:
    - urgency_context: Why this matters now
    - action_description: What to do in plain language
    - risk_framing: What could go wrong (downside scenario)

    All numerical values are cited back to simulation payload.
    """

    recommendation_id: UUID = Field(description="Recommendation being narrated")
    simulation_id: UUID = Field(
        description="Simulation that was narrated "
        "(linked to recommendation)"
    )
    domain: str = Field(
        description="Recommendation domain (growth, retention, margin, etc.)"
    )
    urgency_context: str = Field(
        description="Why-now framing: current signals and trend context "
        "(e.g., 'Return rates accelerating week-over-week')"
    )
    action_description: str = Field(
        description="Plain-language action: what to do and why "
        "(e.g., 'Offer 15% discount to high-risk cohort to recover 8% repeat rate')"
    )
    risk_framing: str = Field(
        description=(
            "Downside scenario implications: what could go wrong if action "
            "is taken (e.g., 'Margin impact is -2% if offer doesn't drive uptake')"
        )
    )
    citations: list[Citation] = Field(
        description="References to all numerical values in the narration "
        "(enables audit trail of where numbers came from)"
    )
    narration_metadata: dict = Field(
        default_factory=dict,
        description="LLM details: model name, tokens used, generation time, etc."
    )
    generated_at: datetime = Field(
        description="Timestamp when narration was generated"
    )

    model_config = ConfigDict(from_attributes=True)


# ========== E7: Simulation Chart-Ready Data ==========


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time-series chart.

    E7: Provides structured data for time-series projections across scenarios.
    Frontend can render line charts showing baseline/upside/downside trends
    over projected time periods.
    """

    period_index: int = Field(
        description="Time period index (0=now, 1=period 1, etc.)"
    )
    period_label: str = Field(
        description="Human-readable period label (e.g., 'Week 1', 'Day 7')"
    )
    baseline_value: float | None = Field(
        description="Metric value in baseline scenario"
    )
    upside_value: float | None = Field(
        description="Metric value in upside scenario"
    )
    downside_value: float | None = Field(
        description="Metric value in downside scenario"
    )

    model_config = ConfigDict(from_attributes=True)


class WaterfallSegment(BaseModel):
    """Single segment in a waterfall chart.

    E7: Shows how baseline value changes through intermediate steps to reach
    final value. Useful for showing contribution breakdown (e.g., baseline → 
    channel reallocation → pricing change → final outcome).
    """

    segment_label: str = Field(
        description="Segment name (e.g., 'Baseline', 'Channel shift', 'Final')"
    )
    segment_type: str = Field(
        description="Type: 'start', 'increase', 'decrease', 'end'"
    )
    value: float = Field(
        description="Segment value (absolute or delta depending on type)"
    )
    cumulative_value: float = Field(
        description="Running total after this segment"
    )

    model_config = ConfigDict(from_attributes=True)


class MetricDeltaBar(BaseModel):
    """Single metric comparison bar across scenarios.

    E7: Shows side-by-side comparison of a metric across baseline/upside/downside.
    Frontend can render grouped bar charts or delta visualizations.
    """

    metric_name: str = Field(
        description="Metric being compared (e.g., 'ROAS', 'Margin %', 'CAC')"
    )
    metric_unit: str = Field(
        description="Unit for display (e.g., '%', '$', 'days')"
    )
    baseline_value: float | None = Field(
        description="Baseline scenario value"
    )
    upside_value: float | None = Field(
        description="Upside scenario value"
    )
    upside_delta: float | None = Field(
        description="Change from baseline to upside (upside - baseline)"
    )
    upside_delta_pct: float | None = Field(
        description="Percentage change from baseline to upside"
    )
    downside_value: float | None = Field(
        description="Downside scenario value"
    )
    downside_delta: float | None = Field(
        description="Change from baseline to downside (downside - baseline)"
    )
    downside_delta_pct: float | None = Field(
        description="Percentage change from baseline to downside"
    )

    model_config = ConfigDict(from_attributes=True)


class SimulationChartDataResponse(BaseModel):
    """Chart-ready data for frontend visualization of a simulation.

    E7: Provides three structured data formats optimized for chart libraries:
    - time_series: Line charts showing metric trends over time
    - waterfall: Waterfall charts showing contribution breakdown
    - metric_deltas: Bar charts comparing metrics across scenarios
    
    All data pre-calculated and formatted for direct consumption by frontend
    chart components (Chart.js, Recharts, D3, etc.).
    """

    simulation_id: UUID = Field(
        description="Simulation being visualized"
    )
    domain: str = Field(
        description="Simulation domain (growth, retention, finance, etc.)"
    )
    time_series: dict[str, list[TimeSeriesDataPoint]] = Field(
        description=(
            "Time-series data per metric. "
            "Keys are metric names, values are arrays of time points."
        )
    )
    waterfall: dict[str, list[WaterfallSegment]] = Field(
        description=(
            "Waterfall data per metric. "
            "Keys are metric names, values are arrays of segments."
        )
    )
    metric_deltas: list[MetricDeltaBar] = Field(
        description="Side-by-side metric comparison across all scenarios"
    )
    confidence_level: str = Field(
        description="Overall simulation confidence: 'high', 'medium', 'low'"
    )
    data_freshness_signal: str = Field(
        description="Data freshness indicator: 'high', 'medium', 'low'"
    )

    model_config = ConfigDict(from_attributes=True)
