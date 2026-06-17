"""Domain-specific simulation input schemas.

FR-082 to FR-086 / T-082: User-provided assumptions for what-if simulations.

Each schema captures the assumptions a persona provides to run a simulation:
- GrowthSimulationInput: Channel budget allocation
- RetentionSimulationInput: Offer, segment, timing, response rate
- FinanceSimulationInput: Cost input changes
- OperationsSimulationInput: Reorder policy changes
- ExecutiveSimulationInput: Strategic what-if scenarios
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ChannelBudgetAllocation(BaseModel):
    """Channel budget allocation for growth simulation."""

    channel_id: str = Field(description="Channel identifier (e.g., paid_social)")
    budget_allocation_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Percentage of total budget for this channel (0-100)",
    )


class GrowthSimulationInput(BaseModel):
    """Growth Manager: Channel budget reallocation simulation.

    FR-082: Growth and Performance Manager can simulate budget reallocation
    across channels/campaign groups and see projected impact on CAC, ROAS,
    new customer volume, contribution margin, and payback period.

    Assumptions user provides:
    - Which channels to allocate budget to (e.g., paid_social, google, direct)
    - What percentage of total budget for each
    - Total budget to simulate (or use current total)

    Output impacts:
    - CAC per channel
    - ROAS per channel (blended)
    - New customer volume
    - Contribution margin
    - Payback period
    """

    total_budget: float = Field(
        gt=0,
        description="Total budget to allocate across channels (currency amount)",
    )
    channel_allocations: list[ChannelBudgetAllocation] = Field(
        min_length=1,
        description="List of channels with budget allocation percentages. "
        "Percentages must sum to 100.",
    )
    scenario_label: str | None = Field(
        None,
        max_length=200,
        description="Optional descriptive label for this scenario",
    )

    @field_validator("channel_allocations")
    @classmethod
    def validate_channel_allocations_sum(
        cls, value: list[ChannelBudgetAllocation]
    ) -> list[ChannelBudgetAllocation]:
        """Validate that channel allocations sum to 100%."""
        total_pct = sum(alloc.budget_allocation_pct for alloc in value)
        if abs(total_pct - 100.0) > 0.01:  # Allow 0.01% rounding error
            msg = f"Channel allocations must sum to 100%, got {total_pct}%"
            raise ValueError(msg)
        return value


class RetentionSimulationInput(BaseModel):
    """Retention Manager: Retention intervention simulation.

    FR-083: Retention and CRM Manager can simulate retention interventions
    (offer level, audience segment, send timing, expected response rate)
    and see projected repeat purchase rate, cohort revenue, and retention
    margin impact.

    Assumptions user provides:
    - Offer discount level (% off)
    - Target segment (cohort age range, purchase value range, etc.)
    - Send timing (days post first purchase)
    - Expected response rate (% of segment)

    Output impacts:
    - Repeat purchase rate
    - Cohort revenue
    - Retention margin
    - ROI of intervention
    """

    offer_discount_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Discount percentage offered to segment (0-100)",
    )
    target_segment: str = Field(
        max_length=100,
        description="Segment identifier or description "
        "(e.g., first_order_0_30d, high_value)",
    )
    days_post_first_purchase: int = Field(
        ge=0,
        le=365,
        description="Days after first purchase to send offer",
    )
    expected_response_rate_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Expected response rate to offer (0-100)",
    )
    estimated_segment_size: int | None = Field(
        None,
        ge=1,
        description=(
            "Estimated number of customers in segment (optional, for impact scale)"
        ),
    )
    scenario_label: str | None = Field(
        None,
        max_length=200,
        description="Optional descriptive label for this scenario",
    )


class CostInputChange(BaseModel):
    """Single cost input change for finance simulation."""

    cost_type: str = Field(
        description="Cost type identifier "
        "(e.g., shipping_cost, return_processing_cost, platform_fee_pct, "
        "ad_vat_pct)",
    )
    current_value: float = Field(description="Current value (currency or %)")
    proposed_value: float = Field(description="Proposed new value (currency or %)")


class FinanceSimulationInput(BaseModel):
    """Finance Controller: Cost input change simulation.

    FR-084: Finance Controller can simulate changes in cost inputs
    (shipping bands, return cost, platform fees, ad VAT, duties assumptions
    for Phase 1 treatment) and see projected gross margin and contribution
    margin movement.

    Assumptions user provides:
    - Changes to shipping costs
    - Changes to return processing costs
    - Changes to platform fees %
    - Changes to ad spend VAT/tax %
    - Changes to import duties (Phase 1 simplification)

    Output impacts:
    - Gross margin %
    - Contribution margin %
    - Margin delta ($ and %)
    - Cost driver impact breakdown
    """

    cost_changes: list[CostInputChange] = Field(
        min_length=1,
        description="List of cost inputs to change",
    )
    scenario_label: str | None = Field(
        None,
        max_length=200,
        description="Optional descriptive label for this scenario",
    )


class OperationsSimulationInput(BaseModel):
    """Operations Manager: Inventory reorder simulation.

    FR-085: Operations Manager can simulate reorder timing, reorder quantity,
    and lead-time scenarios and see projected stockout risk, overstock risk,
    weeks-of-cover, and capital tied up.

    Assumptions user provides:
    - Reorder quantity multiplier (% change from current)
    - Lead time in days
    - Reorder timing policy (e.g., weekly, every-7-days, on-demand)
    - Target service level (% in stock at all times)

    Output impacts:
    - Stockout risk %
    - Overstock risk %
    - Weeks of inventory cover
    - Capital tied up in inventory
    - Expected lost revenue from stockouts
    """

    sku_or_category: str = Field(
        max_length=100,
        description="SKU or category identifier to simulate",
    )
    reorder_quantity_multiplier: float = Field(
        gt=0.0,
        description="Multiplier for reorder quantity (e.g., 1.2 = 20% increase)",
    )
    lead_time_days: int = Field(
        ge=1,
        le=90,
        description="Lead time in days for new stock to arrive",
    )
    reorder_timing_policy: str = Field(
        description="Reorder timing policy "
        "(e.g., weekly, every_7_days, on_demand, threshold)",
    )
    target_service_level_pct: float = Field(
        default=95.0,
        ge=50.0,
        le=99.9,
        description="Target service level (% in stock)",
    )
    scenario_label: str | None = Field(
        None,
        max_length=200,
        description="Optional descriptive label for this scenario",
    )


class ExecutiveSimulationInput(BaseModel):
    """Executive Owner: Strategic what-if simulation.

    FR-086: Executive Owner can run strategic what-if scenarios combining
    pricing, channel mix, and demand assumptions and see consolidated
    projected business impact.

    Assumptions user provides:
    - Pricing change (%)
    - Channel mix shift (% budget change per channel)
    - Demand multiplier (growth or contraction scenario)
    - Time horizon for projection

    Output impacts:
    - Blended revenue
    - Blended contribution margin
    - Blended ROAS
    - CAC payback
    - Executive KPI impact (e.g., margin %, repeat rate, ROI)
    """

    pricing_change_pct: float = Field(
        ge=-100.0,
        le=100.0,
        description="Pricing change percentage (-100 to +100)",
    )
    channel_mix_changes: dict[str, float] = Field(
        description="Channel budget shift deltas (e.g., "
        '{"paid_social": 10, "google": -5} means +10% to paid social, '
        "-5% from google)",
    )
    demand_multiplier: float = Field(
        gt=0.0,
        description="Demand scenario multiplier (e.g., 1.2 = 20% growth, "
        "0.8 = 20% contraction)",
    )
    projection_horizon_days: int = Field(
        default=90,
        ge=7,
        le=365,
        description="Projection horizon in days",
    )
    scenario_label: str | None = Field(
        None,
        max_length=200,
        description="Optional descriptive label for this scenario",
    )
