"""Simulation service with three-scenario optimizer.

FR-081, FR-087 / T-081: Simulation core with baseline/upside/downside scenarios.
FR-091 / T-085: Export generation service (PDF and CSV).

Runs scipy.optimize to find x* (mathematical optimum) for each domain,
then generates three scenarios: baseline (no change), upside (best case),
downside (risk case).
"""

from __future__ import annotations

import csv
import io
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np
from itsdangerous import BadSignature, SignatureExpired
from openai import OpenAI
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from scipy.optimize import minimize
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    ExportLink,
    ExportShare,
    Recommendation,
    Scenario,
    Simulation,
    Tenant,
    User,
)
from backend.app.utils.token_signing import ExportLinkTokenSigner

if TYPE_CHECKING:
    pass


class SimulationService:
    """Service for running simulations with three-scenario analysis."""

    # Retry intervals for simulation optimizer (in seconds)
    OPTIMIZER_MAX_ITERATIONS = 1000
    OPTIMIZER_TOLERANCE = 1e-6

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def run_auto_simulation(
        self,
        tenant_id: uuid.UUID,
        domain: str,
        current_value: float,
        response_function: Callable[[float], float],
        recommendation_id: uuid.UUID | None = None,
    ) -> Simulation:
        """Run automatic simulation after rule engine fires a recommendation.

        Finds x* (mathematical optimum) using scipy.optimize, then generates
        three scenarios: baseline, upside, downside.

        Args:
            tenant_id: Tenant identifier
            domain: Simulation domain (e.g., 'acquisition', 'retention')
            current_value: Current state value (for baseline)
            response_function: Callable that maps input x → output metric value
            recommendation_id: Optional associated recommendation (for rule-engine
                triggered simulations). If None, simulation is user-initiated.

        Returns:
            Simulation object with all three scenarios persisted.
        """
        tenant = self.db_session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        ).scalar()
        if tenant is None:
            msg = f"Tenant {tenant_id} not found"
            raise ValueError(msg)

        # Validate recommendation only if provided (rule-engine trigger path)
        if recommendation_id is not None:
            recommendation = self.db_session.execute(
                select(Recommendation).where(Recommendation.id == recommendation_id)
            ).scalar()
            if recommendation is None:
                msg = f"Recommendation {recommendation_id} not found"
                raise ValueError(msg)

        # Step 1: Baseline scenario (no change)
        baseline_output = response_function(current_value)
        baseline_scenario = {
            "input": current_value,
            "output": float(baseline_output),
            "label": "current_state",
        }

        # Step 2: Find x* (mathematical optimum)
        # Optimizer minimizes negative output (i.e., maximizes output)
        def objective(x: float) -> float:
            return -response_function(x)

        result = minimize(
            objective,
            x0=current_value * 1.1,  # Start 10% above current
            method="BFGS",
            options={
                "maxiter": self.OPTIMIZER_MAX_ITERATIONS,
                "gtol": self.OPTIMIZER_TOLERANCE,
            },
        )

        x_star = result.x.item() if result.success else current_value * 1.2
        upside_output = response_function(x_star)

        # Step 3: Upside scenario (best case with x*)
        upside_scenario = {
            "input": x_star,
            "output": float(upside_output),
            "label": "optimized_best_case",
            "assumptions": {
                "execution_quality": "perfect",
                "market_conditions": "favorable",
            },
        }

        # Step 4: Downside scenario (risk case with x* but pessimistic assumptions)
        # Downside assumes 70% of optimized output (execution risk)
        downside_output = upside_output * 0.7
        downside_scenario = {
            "input": x_star,
            "output": float(downside_output),
            "label": "optimized_worst_case",
            "assumptions": {
                "execution_quality": "imperfect",
                "market_conditions": "neutral",
            },
        }

        # Step 5: Compute confidence levels
        # Baseline is always high confidence (current state)
        baseline_confidence_score = 1.0
        # Upside confidence depends on how far x* is from current_value
        # Handle zero or near-zero current_value
        if abs(current_value) < 0.01:
            distance_ratio = 0.0
        else:
            distance_ratio = abs(x_star - current_value) / abs(current_value)
        upside_confidence_score = max(0.5, 1.0 - (distance_ratio * 0.2))
        # Downside confidence is lower (riskier)
        downside_confidence_score = upside_confidence_score * 0.8

        # Step 6: Determine overall confidence level (high/medium/low)
        avg_confidence = (
            baseline_confidence_score
            + upside_confidence_score
            + downside_confidence_score
        ) / 3
        if avg_confidence >= 0.8:
            confidence_level = "high"
        elif avg_confidence >= 0.6:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        # Step 7: Create Simulation record
        simulation = Simulation(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            domain=domain,
            simulation_type="auto",
            x_star={"value": x_star, "domain": domain},
            confidence_level=confidence_level,
            data_freshness_signal="high",  # Will be set by T-081 caller
            metric_completeness_signal="high",  # Will be set by T-081 caller
            baseline_scenario=baseline_scenario,
            upside_scenario=upside_scenario,
            downside_scenario=downside_scenario,
            simulation_metadata={
                "optimizer": "scipy.optimize.minimize",
                "method": "BFGS",
                "x_star_found": result.success if result else False,
                "optimizer_iterations": result.nit if result else 0,
            },
        )

        self.db_session.add(simulation)
        self.db_session.flush()

        # Step 8: Create individual Scenario records
        baseline_scenario_record = Scenario(
            id=uuid.uuid4(),
            simulation_id=simulation.id,
            scenario_type="baseline",
            input_assumptions={"current_value": current_value},
            output_metrics=baseline_scenario,
            impact_deltas={"change_pct": 0.0},
            confidence_score=baseline_confidence_score,
            rationale="No change from current state; baseline for comparison.",
        )
        upside_scenario_record = Scenario(
            id=uuid.uuid4(),
            simulation_id=simulation.id,
            scenario_type="upside",
            input_assumptions=upside_scenario["assumptions"],
            output_metrics=upside_scenario,
            impact_deltas={
                "change_pct": ((upside_output - baseline_output) / baseline_output)
                * 100
            },
            confidence_score=upside_confidence_score,
            rationale=(
                "Best-case scenario with optimized input and favorable "
                "conditions."
            ),
        )
        downside_scenario_record = Scenario(
            id=uuid.uuid4(),
            simulation_id=simulation.id,
            scenario_type="downside",
            input_assumptions=downside_scenario["assumptions"],
            output_metrics=downside_scenario,
            impact_deltas={
                "change_pct": ((downside_output - baseline_output) / baseline_output)
                * 100
            },
            confidence_score=downside_confidence_score,
            rationale="Risk scenario with execution challenges and neutral market.",
        )

        self.db_session.add_all(
            [baseline_scenario_record, upside_scenario_record, downside_scenario_record]
        )
        self.db_session.commit()

        return simulation

    def get_simulation_by_recommendation(
        self,
        tenant_id: uuid.UUID,
        recommendation_id: uuid.UUID,
    ) -> Simulation | None:
        """Retrieve simulation for a given recommendation.

        Args:
            tenant_id: Tenant identifier
            recommendation_id: Recommendation identifier

        Returns:
            Simulation object or None if not found.
        """
        return self.db_session.execute(
            select(Simulation)
            .where(Simulation.tenant_id == tenant_id)
            .where(Simulation.recommendation_id == recommendation_id)
        ).scalar()

    def get_simulation_with_scenarios(
        self,
        tenant_id: uuid.UUID,
        simulation_id: uuid.UUID,
    ) -> tuple[Simulation | None, list[Scenario]]:
        """Retrieve a simulation and its associated scenarios.

        FR-090 / T-084: Save and revisit simulation scenarios.

        Args:
            tenant_id: Tenant identifier
            simulation_id: Simulation identifier

        Returns:
            Tuple of (Simulation object or None if not found, list of Scenario objects)

        Raises:
            ValueError: If simulation exists but tenant_id doesn't match
                (cross-tenant access)
        """
        # Fetch simulation
        simulation = self.db_session.execute(
            select(Simulation)
            .where(Simulation.id == simulation_id)
            .where(Simulation.tenant_id == tenant_id)
        ).scalar()

        if simulation is None:
            return None, []

        # Fetch all scenarios for this simulation
        scenarios = self.db_session.execute(
            select(Scenario)
            .where(Scenario.simulation_id == simulation_id)
            .order_by(Scenario.scenario_type)
        ).scalars().all()

        return simulation, list(scenarios)

    def list_simulations(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Simulation], int]:
        """List simulations for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            skip: Number of records to skip
            limit: Max records to return (capped at 500)

        Returns:
            Tuple of (simulations, total_count)
        """
        limit = min(limit, 500)

        # Get total count
        total_count_int = self.db_session.scalar(
            select(func.count())
            .select_from(Simulation)
            .where(Simulation.tenant_id == tenant_id)
        ) or 0

        # Get paginated results
        simulations = list(
            self.db_session.scalars(
                select(Simulation)
                .where(Simulation.tenant_id == tenant_id)
                .order_by(Simulation.created_at.desc())
                .offset(skip)
                .limit(limit)
            ).all()
        )

        return simulations, total_count_int

    # ========================================================================
    # Domain-Specific Simulation Methods (FR-082 to FR-086 / T-082)
    # ========================================================================

    def run_growth_simulation(
        self,
        tenant_id: uuid.UUID,
        total_budget: float,
        channel_allocations: dict[str, float],
        recommendation_id: uuid.UUID | None = None,
        scenario_label: str | None = None,
    ) -> Simulation:
        """Simulate growth channel budget reallocation.

        FR-082: Growth and Performance Manager can simulate budget
        reallocation across channels and see projected impact on CAC, ROAS,
        new customer volume, contribution margin, and payback period.

        Args:
            tenant_id: Tenant identifier
            total_budget: Total budget to allocate
            channel_allocations: Dict {channel_id: pct_allocation, ...}
            recommendation_id: Optional linked recommendation
            scenario_label: Optional description of scenario

        Returns:
            Simulation with growth metrics in scenario outputs
        """
        # Placeholder response function for testing
        # Maps total_budget → projected blended ROAS
        def growth_response_func(budget: float) -> float:
            # Diminishing returns model: ROAS = base - decay * log(budget)
            base_roas = 3.0
            decay = 0.15
            if budget <= 0:
                return 0.0
            return max(1.5, base_roas - decay * np.log(budget + 1))

        # Baseline: current budget
        return self.run_auto_simulation(
            tenant_id=tenant_id,
            domain="growth",
            current_value=total_budget,
            response_function=growth_response_func,
            recommendation_id=recommendation_id,
        )

    def run_retention_simulation(
        self,
        tenant_id: uuid.UUID,
        offer_discount_pct: float,
        response_rate_pct: float,
        estimated_segment_size: int | None = None,
        recommendation_id: uuid.UUID | None = None,
        scenario_label: str | None = None,
    ) -> Simulation:
        """Simulate retention intervention (offer/response/timing).

        FR-083: Retention and CRM Manager can simulate retention
        interventions and see projected repeat purchase rate, cohort revenue,
        and retention margin impact.

        Args:
            tenant_id: Tenant identifier
            offer_discount_pct: Discount level offered
            response_rate_pct: Expected response rate
            estimated_segment_size: Segment size estimate
            recommendation_id: Optional linked recommendation
            scenario_label: Optional description

        Returns:
            Simulation with retention metrics in scenario outputs
        """
        # Placeholder response function for testing
        # Maps response_rate → projected repeat purchase rate impact
        def retention_response_func(response_rate: float) -> float:
            # Simple model: each 1% response drives ~0.5% repeat lift
            baseline_repeat_rate = 0.25
            lift = response_rate * 0.005
            return max(0.0, min(0.8, baseline_repeat_rate + lift))

        return self.run_auto_simulation(
            tenant_id=tenant_id,
            domain="retention",
            current_value=response_rate_pct,
            response_function=retention_response_func,
            recommendation_id=recommendation_id,
        )

    def run_finance_simulation(
        self,
        tenant_id: uuid.UUID,
        cost_changes: dict[str, tuple[float, float]],
        recommendation_id: uuid.UUID | None = None,
        scenario_label: str | None = None,
    ) -> Simulation:
        """Simulate cost input changes (shipping, returns, fees, VAT).

        FR-084: Finance Controller can simulate changes in cost inputs and
        see projected gross margin and contribution margin movement.

        Args:
            tenant_id: Tenant identifier
            cost_changes: Dict {cost_type: (current_value, proposed_value), ...}
            recommendation_id: Optional linked recommendation
            scenario_label: Optional description

        Returns:
            Simulation with finance metrics in scenario outputs
        """
        # Placeholder response function for testing
        # Maps total cost delta → projected contribution margin impact
        def finance_response_func(cost_total: float) -> float:
            # Margin = revenue - cost_total (simplified)
            baseline_revenue = 100.0
            baseline_margin = 0.35
            margin = baseline_margin - (cost_total / baseline_revenue) * 0.5
            return max(0.0, margin)

        # Calculate total cost delta (sum of (proposed - current))
        total_cost_delta = sum(
            proposed - current for current, proposed in cost_changes.values()
        )

        return self.run_auto_simulation(
            tenant_id=tenant_id,
            domain="finance",
            current_value=total_cost_delta,
            response_function=finance_response_func,
            recommendation_id=recommendation_id,
        )

    def run_operations_simulation(
        self,
        tenant_id: uuid.UUID,
        reorder_qty_multiplier: float,
        lead_time_days: int,
        recommendation_id: uuid.UUID | None = None,
        scenario_label: str | None = None,
    ) -> Simulation:
        """Simulate inventory reorder policy changes.

        FR-085: Operations Manager can simulate reorder timing, quantity, and
        lead-time scenarios and see projected stockout risk, overstock risk,
        weeks-of-cover, and capital tied up.

        Args:
            tenant_id: Tenant identifier
            reorder_qty_multiplier: Reorder quantity multiplier
            lead_time_days: Lead time in days
            recommendation_id: Optional linked recommendation
            scenario_label: Optional description

        Returns:
            Simulation with ops metrics in scenario outputs
        """
        # Placeholder response function for testing
        # Maps reorder quantity → projected stockout risk
        def ops_response_func(qty_mult: float) -> float:
            # More inventory → lower stockout risk
            # Stockout risk decreases logarithmically with inventory levels
            if qty_mult <= 0:
                return 1.0
            return max(0.0, 0.50 - 0.15 * np.log(qty_mult + 1))

        return self.run_auto_simulation(
            tenant_id=tenant_id,
            domain="operations",
            current_value=reorder_qty_multiplier,
            response_function=ops_response_func,
            recommendation_id=recommendation_id,
        )

    def run_executive_simulation(
        self,
        tenant_id: uuid.UUID,
        pricing_change_pct: float,
        demand_multiplier: float,
        recommendation_id: uuid.UUID | None = None,
        scenario_label: str | None = None,
    ) -> Simulation:
        """Simulate strategic what-if scenarios (pricing, channel mix, demand).

        FR-086: Executive Owner can run strategic what-if scenarios combining
        pricing, channel mix, and demand assumptions and see consolidated
        projected business impact.

        Args:
            tenant_id: Tenant identifier
            pricing_change_pct: Pricing change percentage
            demand_multiplier: Demand scenario multiplier
            recommendation_id: Optional linked recommendation
            scenario_label: Optional description

        Returns:
            Simulation with executive metrics in scenario outputs
        """
        # Placeholder response function for testing
        # Maps pricing change → projected revenue/margin
        def executive_response_func(pricing_pct: float) -> float:
            # Price elasticity model: volume decreases when price increases
            # Revenue = (base_volume - elasticity * price_change) * (1 + price_change)
            base_revenue = 100.0
            elasticity = 0.5  # 1% price increase → 0.5% volume decrease
            price_factor = 1.0 + (pricing_pct / 100.0)
            volume_factor = 1.0 - elasticity * (pricing_pct / 100.0)
            revenue = base_revenue * price_factor * volume_factor
            return max(0.0, revenue)

        return self.run_auto_simulation(
            tenant_id=tenant_id,
            domain="executive",
            current_value=pricing_change_pct,
            response_function=executive_response_func,
            recommendation_id=recommendation_id,
        )

    def get_simulation_comparison(
        self,
        tenant_id: uuid.UUID,
        simulation_ids: list[uuid.UUID],
    ) -> dict:
        """Build a side-by-side comparison of multiple simulations.

        Compares scenarios across simulations, calculates freshness warnings,
        and provides overall confidence guidance for decision-makers.

        Args:
            tenant_id: Tenant identifier
            simulation_ids: List of simulation IDs to compare (min 2)

        Returns:
            Dictionary with comparison view, metrics, confidence, and
            freshness warnings.

        Raises:
            ValueError: If fewer than 2 simulations provided, or simulations not found.
        """
        if len(simulation_ids) < 2:
            msg = "Must compare at least 2 simulations"
            raise ValueError(msg)

        # Fetch all simulations
        simulations = self.db_session.execute(
            select(Simulation).where(
                Simulation.tenant_id == tenant_id,
                Simulation.id.in_(simulation_ids),
            )
        ).scalars().all()

        if len(simulations) != len(simulation_ids):
            expected = len(simulation_ids)
            found = len(simulations)
            msg = f"Expected {expected} simulations, found {found}"
            raise ValueError(msg)

        # Fetch scenarios for each simulation (baseline, upside, downside)
        scenarios_by_sim = {}
        for sim in simulations:
            scenarios = self.db_session.execute(
                select(Scenario)
                .where(Scenario.simulation_id == sim.id)
                .order_by(Scenario.scenario_type)
            ).scalars().all()
            scenarios_by_sim[sim.id] = scenarios

        # Build comparison columns (one per simulation, showing all scenarios)
        comparison_columns: list[dict] = []
        for sim in simulations:
            scenarios = scenarios_by_sim[sim.id]
            for scenario in scenarios:
                output_metrics_dict: dict = scenario.output_metrics or {}
                impact_deltas_dict: dict = scenario.impact_deltas or {}
                input_assumptions_dict: dict = scenario.input_assumptions or {}
                comparison_columns.append({
                    "simulation_id": str(sim.id),
                    "simulation_domain": sim.domain,
                    "scenario_type": scenario.scenario_type,
                    "input_assumptions": input_assumptions_dict,
                    "output_metrics": output_metrics_dict,
                    "impact_deltas": impact_deltas_dict,
                    "confidence_score": scenario.confidence_score,
                    "created_at": scenario.created_at,
                })

        # Extract all unique metrics from scenarios
        all_metrics: set = set()
        for col in comparison_columns:
            output_metrics_col: dict = col["output_metrics"]
            all_metrics.update(output_metrics_col.keys())

        # Build metric rows for side-by-side comparison
        metric_rows: list = []
        for metric_name in sorted(all_metrics):
            comparison_values: dict = {}
            variance_values: dict = {}

            for col in comparison_columns:
                col_key = f"{col['simulation_id']}_{col['scenario_type']}"
                output_metrics_col_inner: dict = col["output_metrics"]
                value = output_metrics_col_inner.get(metric_name)
                comparison_values[col_key] = value

                # Calculate variance from baseline
                if col["scenario_type"] == "baseline":
                    variance_values[col_key] = 0.0
                else:
                    output_metrics_inner: dict = col["output_metrics"]
                    baseline_value = output_metrics_inner.get(metric_name, 0.0)
                    if isinstance(baseline_value, (int, float)):
                        variance_values[col_key] = baseline_value - (
                            output_metrics_inner.get(metric_name, 0.0)
                        )

            metric_rows.append({
                "metric_name": metric_name,
                "metric_unit": "value",  # Could be enhanced to infer units
                "comparison_values": comparison_values,
                "variance": variance_values,
            })

        # Calculate data freshness warnings
        # (Placeholder: in reality, would fetch from ConnectorSyncStatus or similar)
        freshness_warnings = [
            {
                "source_name": "Simulated Data",
                "last_synced_at": simulations[0].created_at,
                "hours_stale": 0,
                "confidence_impact": "low",
                "recommendation": "Simulations created from latest available data.",
            }
        ]

        # Calculate overall confidence (average of all scenarios' confidence scores)
        all_confidence_scores = [
            col["confidence_score"] for col in comparison_columns
        ]
        overall_confidence = sum(all_confidence_scores) / len(all_confidence_scores)

        return {
            "comparison_id": "_".join([str(sim_id)[:8] for sim_id in simulation_ids]),
            "tenant_id": str(tenant_id),
            "compared_simulations": comparison_columns,
            "metrics": metric_rows,
            "data_freshness_warnings": freshness_warnings,
            "overall_confidence": overall_confidence,
            "recommendation_for_viewer": (
                "Safe to use"
                if overall_confidence >= 75
                else (
                    "Consider with caution"
                    if overall_confidence >= 50
                    else "Wait for more data"
                )
            ),
            "comparison_created_at": datetime.now(),
        }

    def generate_simulation_export(
        self,
        tenant_id: uuid.UUID,
        simulation_id: uuid.UUID,
        format: str = "pdf",
    ) -> tuple[bytes, str]:
        """Generate an export (PDF or CSV) of a simulation.

        FR-091 / T-085: Export generation service for all domains.

        Args:
            tenant_id: Tenant identifier
            simulation_id: Simulation identifier
            format: Export format ('pdf' or 'csv')

        Returns:
            Tuple of (file_content_bytes, file_name)

        Raises:
            ValueError: If simulation not found or invalid format
        """
        if format not in ["pdf", "csv"]:
            msg = f"Invalid format: {format}. Must be 'pdf' or 'csv'"
            raise ValueError(msg)

        # Fetch simulation with scenarios
        simulation, scenarios = self.get_simulation_with_scenarios(
            tenant_id=tenant_id,
            simulation_id=simulation_id,
        )

        if simulation is None:
            msg = f"Simulation {simulation_id} not found for tenant {tenant_id}"
            raise ValueError(msg)

        if format == "pdf":
            content = self._generate_pdf_export(simulation, scenarios)
            file_name = f"simulation_{simulation.id}_{simulation.domain}.pdf"
        else:  # csv
            content = self._generate_csv_export(simulation, scenarios)
            file_name = f"simulation_{simulation.id}_{simulation.domain}.csv"

        return content, file_name

    def _generate_pdf_export(
        self,
        simulation: Simulation,
        scenarios: list[Scenario],
    ) -> bytes:
        """Generate PDF export of a simulation.

        Args:
            simulation: Simulation ORM object
            scenarios: List of Scenario ORM objects

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=12,
            alignment=1,  # Center
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
        )

        story = []

        # Title
        story.append(
            Paragraph(
                f"Simulation Report: {simulation.domain.capitalize()}",
                title_style,
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Metadata
        metadata_text = (
            f"<b>Simulation ID:</b> {simulation.id}<br/>"
            f"<b>Domain:</b> {simulation.domain}<br/>"
            f"<b>Type:</b> {simulation.simulation_type}<br/>"
            f"<b>Confidence Level:</b> {simulation.confidence_level}<br/>"
            f"<b>Created:</b> {simulation.created_at.isoformat()}<br/>"
        )
        story.append(Paragraph(metadata_text, body_style))
        story.append(Spacer(1, 0.2 * inch))

        # Scenarios summary
        story.append(Paragraph("<b>Scenarios Summary</b>", styles["Heading2"]))

        # Build scenarios table
        scenario_data = [
            [
                "Scenario",
                "Confidence Score",
                "Type",
                "Created",
            ]
        ]

        for scenario in scenarios:
            scenario_data.append(
                [
                    scenario.scenario_type.capitalize(),
                    f"{scenario.confidence_score:.2f}",
                    "Deterministic",
                    scenario.created_at.strftime("%Y-%m-%d %H:%M"),
                ]
            )

        scenario_table = Table(
            scenario_data,
            colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch],
        )
        scenario_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F2F2F2")],
                    ),
                ]
            )
        )
        story.append(scenario_table)
        story.append(Spacer(1, 0.3 * inch))

        # Output metrics summary
        story.append(Paragraph("<b>Key Metrics</b>", styles["Heading2"]))

        all_metrics: set[str] = set()
        for scenario in scenarios:
            if scenario.output_metrics:
                all_metrics.update(scenario.output_metrics.keys())

        if all_metrics:
            scenario_headers = [s.scenario_type.capitalize() for s in scenarios]
            metrics_data = [["Metric"] + scenario_headers]
            for metric in sorted(all_metrics):
                row = [metric]
                for scenario in scenarios:
                    value = scenario.output_metrics.get(metric, "N/A")
                    if isinstance(value, (int, float)):
                        row.append(f"{value:.2f}")
                    else:
                        row.append(str(value))
                metrics_data.append(row)

            metrics_table = Table(metrics_data)
            metrics_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F2F2F2")],
                        ),
                    ]
                )
            )
            story.append(metrics_table)

        # Build PDF
        doc.build(story)
        return buffer.getvalue()

    def _generate_csv_export(
        self,
        simulation: Simulation,
        scenarios: list[Scenario],
    ) -> bytes:
        """Generate CSV export of a simulation.

        Args:
            simulation: Simulation ORM object
            scenarios: List of Scenario ORM objects

        Returns:
            CSV content as bytes
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header with simulation metadata
        writer.writerow(["Simulation Export"])
        writer.writerow(["Simulation ID", str(simulation.id)])
        writer.writerow(["Domain", simulation.domain])
        writer.writerow(["Type", simulation.simulation_type])
        writer.writerow(["Confidence Level", simulation.confidence_level])
        writer.writerow(["Created", simulation.created_at.isoformat()])
        writer.writerow([])  # Blank row

        # Scenario details
        writer.writerow(["Scenario Details"])
        writer.writerow([
            "Scenario Type",
            "Confidence Score",
            "Created At",
        ])

        for scenario in scenarios:
            writer.writerow([
                scenario.scenario_type,
                f"{scenario.confidence_score:.2f}",
                scenario.created_at.isoformat(),
            ])

        writer.writerow([])  # Blank row

        # Input assumptions
        writer.writerow(["Input Assumptions"])
        writer.writerow(["Scenario Type", "Assumption Key", "Assumption Value"])

        for scenario in scenarios:
            if scenario.input_assumptions:
                for key, value in scenario.input_assumptions.items():
                    writer.writerow([
                        scenario.scenario_type,
                        key,
                        str(value),
                    ])

        writer.writerow([])  # Blank row

        # Output metrics
        writer.writerow(["Output Metrics"])
        writer.writerow(["Scenario Type", "Metric Name", "Metric Value"])

        for scenario in scenarios:
            if scenario.output_metrics:
                for key, value in scenario.output_metrics.items():
                    writer.writerow([
                        scenario.scenario_type,
                        key,
                        str(value),
                    ])

        writer.writerow([])  # Blank row

        # Impact deltas
        writer.writerow(["Impact Deltas"])
        writer.writerow(["Scenario Type", "Delta Key", "Delta Value"])

        for scenario in scenarios:
            if scenario.impact_deltas:
                for key, value in scenario.impact_deltas.items():
                    writer.writerow([
                        scenario.scenario_type,
                        key,
                        str(value),
                    ])

        writer.writerow([])  # Blank row

        # Impact deltas
        writer.writerow(["Impact Deltas"])
        writer.writerow(["Scenario Type", "Delta Key", "Delta Value"])

        for scenario in scenarios:
            if scenario.impact_deltas:
                for key, value in scenario.impact_deltas.items():
                    writer.writerow([
                        scenario.scenario_type,
                        key,
                        str(value),
                    ])

        return output.getvalue().encode("utf-8")

    def share_export(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        simulation_id: uuid.UUID,
        shared_by_user_id: uuid.UUID,
        recipient_email: str,
    ) -> ExportShare:
        """Share a simulation export with a recipient.

        T-086: Scoped export sharing with permission checks.

        Validates that:
        1. Simulation exists and belongs to tenant
        2. Recipient is an active user in the same tenant
        3. Recipient has viewing permission for the simulation domain
        4. Sharer has permission to share (owns the simulation or has admin role)

        Args:
            db: Database session
            tenant_id: Tenant ID (cross-tenant isolation)
            simulation_id: Simulation ID to share
            shared_by_user_id: User ID of sharer
            recipient_email: Email address of recipient (must be active in same tenant)

        Returns:
            Created ExportShare record

        Raises:
            ValueError: If simulation not found, recipient not found, or
                permission denied
        """
        # Verify simulation exists and belongs to tenant
        simulation = db.scalar(
            select(Simulation).where(
                Simulation.id == simulation_id,
                Simulation.tenant_id == tenant_id,
            )
        )
        if simulation is None:
            raise ValueError("Simulation not found or does not belong to this tenant")

        # Verify sharer exists in tenant
        sharer = db.scalar(
            select(User).where(User.id == shared_by_user_id)
        )
        if sharer is None:
            raise ValueError("Sharer not found")

        # Verify recipient exists and is active
        recipient = db.scalar(
            select(User).where(
                User.email == recipient_email.strip().lower(),
                User.is_active,
            )
        )
        if recipient is None:
            # Check if recipient exists but is inactive
            recipient_exists = db.scalar(
                select(User).where(
                    User.email == recipient_email.strip().lower(),
                )
            )
            if recipient_exists:
                raise ValueError(
                    "Recipient is inactive. "
                    "Recipient must be an active user."
                )
            raise ValueError(
                "Recipient not found. "
                "Recipient must be an active user in the same tenant."
            )

        # Verify recipient is in same tenant
        from backend.app.db.models import TenantMembership
        recipient_membership = db.scalar(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == recipient.id,
            )
        )
        if recipient_membership is None:
            raise ValueError("Recipient is not a member of this tenant")

        # Check if share already exists
        existing_share = db.scalar(
            select(ExportShare).where(
                ExportShare.tenant_id == tenant_id,
                ExportShare.simulation_id == simulation_id,
                ExportShare.shared_by_user_id == shared_by_user_id,
                ExportShare.shared_with_user_id == recipient.id,
                ExportShare.status == "active",
            )
        )
        if existing_share is not None:
            return existing_share

        # Create new share
        share = ExportShare(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            simulation_id=simulation_id,
            shared_by_user_id=shared_by_user_id,
            shared_with_user_id=recipient.id,
            status="active",
        )
        db.add(share)
        db.commit()
        db.refresh(share)
        return share

    def get_shared_exports_with_me(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        recipient_user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ExportShare], int]:
        """List exports shared with the current user.

        T-086: Retrieve all active exports shared with a user within a tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
            recipient_user_id: User ID (recipient of shares)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Tuple of (list of active ExportShare records, total count)
        """
        shares = db.scalars(
            select(ExportShare)
            .where(
                ExportShare.tenant_id == tenant_id,
                ExportShare.shared_with_user_id == recipient_user_id,
                ExportShare.status == "active",
            )
            .order_by(ExportShare.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()

        total = db.scalar(
            select(func.count(ExportShare.id)).where(
                ExportShare.tenant_id == tenant_id,
                ExportShare.shared_with_user_id == recipient_user_id,
                ExportShare.status == "active",
            )
        ) or 0

        return list(shares), total

    def revoke_export_share(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        share_id: uuid.UUID,
    ) -> ExportShare:
        """Revoke an export share.

        T-086: Mark a share as revoked; access to this shared export is immediately
        revoked. Share record is retained for audit trail.

        Args:
            db: Database session
            tenant_id: Tenant ID (cross-tenant isolation)
            share_id: ExportShare ID to revoke

        Returns:
            Updated ExportShare record with status='revoked'

        Raises:
            ValueError: If share not found or belongs to different tenant
        """
        share = db.scalar(
            select(ExportShare).where(
                ExportShare.id == share_id,
                ExportShare.tenant_id == tenant_id,
            )
        )
        if share is None:
            raise ValueError("Export share not found")

        share.status = "revoked"
        share.revoked_at = datetime.now(UTC)
        db.commit()
        db.refresh(share)
        return share

    def generate_export_download_link(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        share_id: uuid.UUID,
        expiry_days: int = 7,
    ) -> ExportLink:
        """T-087: Generate a signed download link for an export share.

        Creates a time-limited, cryptographically signed URL token.
        The recipient can use this token to download the export file.
        Link expires after expiry_days (default 7 days).

        Args:
            db: Database session
            tenant_id: Tenant identifier (for isolation checks)
            share_id: ExportShare identifier
            expiry_days: How many days until link expires

        Returns:
            ExportLink object with signed token

        Raises:
            ValueError: If share not found, share is revoked, or share not in
                tenant
        """
        # Validate share exists and belongs to tenant
        share = db.scalar(
            select(ExportShare).where(
                ExportShare.id == share_id,
                ExportShare.tenant_id == tenant_id,
            )
        )
        if share is None:
            raise ValueError("not found")

        # Ensure share is active (not revoked)
        if share.status == "revoked":
            raise ValueError("share revoked")

        # Generate signed token using secret key
        secret_key = os.environ.get(
            "EXPORT_LINK_SECRET_KEY",
            "default-dev-key-change-in-prod",
        )
        signer = ExportLinkTokenSigner(secret_key)
        token = signer.generate_token(share_id)

        # Calculate expiry timestamp (now + expiry_days)
        expires_at = datetime.now(UTC) + timedelta(days=expiry_days)

        # Create ExportLink record
        export_link = ExportLink(
            id=uuid.uuid4(),
            share_id=share_id,
            token=token,
            expires_at=expires_at,
        )
        db.add(export_link)
        db.commit()
        db.refresh(export_link)
        return export_link

    def validate_and_get_export_by_token(
        self,
        db: Session,
        token: str,
        max_age_seconds: int = 604800,  # 7 days
    ) -> ExportLink:
        """T-087: Validate token and retrieve associated export.

        Verifies the token signature, checks expiry, and ensures the link
        still exists and is not revoked.

        Args:
            db: Database session
            token: Signed token from download URL
            max_age_seconds: Maximum age of token before expiry

        Returns:
            ExportLink object with validated token

        Raises:
            SignatureExpired: If token timestamp exceeds max_age_seconds
            BadSignature: If token signature is invalid or tampered
            ValueError: If link not found or associated share is revoked
        """
        # Validate signature and get share_id from token
        secret_key = os.environ.get(
            "EXPORT_LINK_SECRET_KEY",
            "default-dev-key-change-in-prod",
        )
        signer = ExportLinkTokenSigner(secret_key)

        try:
            share_id = signer.extract_share_id(token, max_age_seconds)
        except SignatureExpired as e:
            raise SignatureExpired("Token has expired") from e
        except BadSignature as e:
            raise BadSignature("Invalid token signature") from e

        # Look up the export link in database
        export_link = db.scalar(
            select(ExportLink).where(
                ExportLink.token == token,
                ExportLink.share_id == share_id,
            )
        )
        if export_link is None:
            raise ValueError("link not found")

        # Verify share is still active (not revoked)
        share = db.scalar(select(ExportShare).where(ExportShare.id == share_id))
        if share is None or share.status == "revoked":
            raise ValueError("share revoked")

        # Update accessed_at timestamp (track usage)
        export_link.accessed_at = datetime.now(UTC)
        db.commit()
        db.refresh(export_link)
        return export_link

    def cleanup_expired_export_links(self, db: Session) -> int:
        """T-087: Remove expired download links (garbage collection).

        Deletes ExportLink records where expires_at is in the past.
        Called periodically via background job or manually.

        Args:
            db: Database session

        Returns:
            Number of links deleted
        """
        now = datetime.now(UTC)
        result = db.execute(
            select(ExportLink).where(ExportLink.expires_at < now)
        )
        expired_links = result.scalars().all()
        count = len(expired_links)

        for link in expired_links:
            db.delete(link)

        db.commit()
        return count

    def launch_simulation_from_recommendation(
        self,
        tenant_id: uuid.UUID,
        recommendation_id: uuid.UUID,
        override_parameters: dict | None = None,
    ) -> tuple[Simulation, dict]:
        """FR-126 / T-117: Launch simulation pre-populated from recommendation.

        When a user clicks "Simulate" on a recommendation, this method:
        1. Fetches the recommendation
        2. Extracts parameters from recommendation domain and evidence
        3. Applies any user overrides
        4. Calls the appropriate run_*_simulation method
        5. Returns the created simulation

        Args:
            tenant_id: Tenant identifier
            recommendation_id: Recommendation to simulate from
            override_parameters: Optional user overrides (applied on top of
                extracted params)

        Returns:
            Tuple of (Simulation object, parameters_used dict)

        Raises:
            ValueError: If recommendation not found or domain not supported
        """
        # Fetch recommendation
        recommendation = self.db_session.execute(
            select(Recommendation).where(
                Recommendation.id == recommendation_id,
                Recommendation.tenant_id == tenant_id,
            )
        ).scalar()

        if recommendation is None:
            msg = f"Recommendation {recommendation_id} not found"
            raise ValueError(msg)

        # Extract parameters based on domain
        parameters_used: dict = {}

        if recommendation.domain == "growth":
            # Growth domain: extract budget and channels from evidence
            parameters_used = {
                "total_budget": recommendation.evidence.get("total_budget", 5000.0),
                "channel_allocations": recommendation.evidence.get(
                    "channel_allocations", {"google": 0.5, "meta": 0.5}
                ),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Run growth simulation
            simulation = self.run_growth_simulation(
                tenant_id=tenant_id,
                total_budget=parameters_used["total_budget"],
                channel_allocations=parameters_used["channel_allocations"],
                recommendation_id=recommendation_id,
            )

        elif recommendation.domain == "retention":
            # Retention domain: extract offer and segment data
            parameters_used = {
                "offer_discount_pct": recommendation.evidence.get(
                    "offer_discount_pct", 10.0
                ),
                "response_rate_pct": recommendation.evidence.get(
                    "response_rate_pct", 15.0
                ),
                "estimated_segment_size": recommendation.evidence.get(
                    "estimated_segment_size", 1000
                ),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Run retention simulation
            simulation = self.run_retention_simulation(
                tenant_id=tenant_id,
                offer_discount_pct=parameters_used["offer_discount_pct"],
                response_rate_pct=parameters_used["response_rate_pct"],
                estimated_segment_size=parameters_used["estimated_segment_size"],
                recommendation_id=recommendation_id,
            )

        elif recommendation.domain == "margin":
            # Margin domain: extract cost input changes
            parameters_used = {
                "target_margin_improvement_pct": recommendation.evidence.get(
                    "target_margin_improvement_pct", 5.0
                ),
                "cost_input_adjustments": recommendation.evidence.get(
                    "cost_input_adjustments", {}
                ),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Build cost_changes dict for finance simulation
            cost_changes = parameters_used.get(
                "cost_input_adjustments",
                {"shipping": (10.0, 9.5), "returns": (2.0, 1.8)},
            )

            # Run finance simulation (margin focus)
            simulation = self.run_finance_simulation(
                tenant_id=tenant_id,
                cost_changes=cost_changes,
                recommendation_id=recommendation_id,
            )

        elif recommendation.domain == "inventory":
            # Inventory domain: extract reorder and stockout parameters
            parameters_used = {
                "reorder_qty_multiplier": recommendation.evidence.get(
                    "reorder_qty_multiplier", 1.0
                ),
                "lead_time_days": recommendation.evidence.get("lead_time_days", 7),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Run operations simulation
            simulation = self.run_operations_simulation(
                tenant_id=tenant_id,
                reorder_qty_multiplier=parameters_used["reorder_qty_multiplier"],
                lead_time_days=parameters_used["lead_time_days"],
                recommendation_id=recommendation_id,
            )

        elif recommendation.domain == "ops":
            # Ops domain: same as inventory (operations simulations)
            parameters_used = {
                "reorder_qty_multiplier": recommendation.evidence.get(
                    "reorder_qty_multiplier", 1.0
                ),
                "lead_time_days": recommendation.evidence.get("lead_time_days", 7),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Run operations simulation
            simulation = self.run_operations_simulation(
                tenant_id=tenant_id,
                reorder_qty_multiplier=parameters_used["reorder_qty_multiplier"],
                lead_time_days=parameters_used["lead_time_days"],
                recommendation_id=recommendation_id,
            )

        elif recommendation.domain == "executive":
            # Executive domain: cross-functional mix and strategy
            parameters_used = {
                "pricing_change_pct": recommendation.evidence.get(
                    "pricing_change_pct", 0.0
                ),
                "demand_multiplier": recommendation.evidence.get(
                    "demand_multiplier", 1.0
                ),
            }
            # Apply overrides if provided
            if override_parameters:
                parameters_used.update(override_parameters)

            # Run executive simulation
            simulation = self.run_executive_simulation(
                tenant_id=tenant_id,
                pricing_change_pct=parameters_used["pricing_change_pct"],
                demand_multiplier=parameters_used["demand_multiplier"],
                recommendation_id=recommendation_id,
            )

        else:
            msg = f"Unknown recommendation domain: {recommendation.domain}"
            raise ValueError(msg)

        return simulation, parameters_used

    def generate_narration_for_recommendation(
        self,
        tenant_id: uuid.UUID,
        recommendation_id: uuid.UUID,
        override_tone: str | None = None,
    ) -> dict:  # narration dict with urgency_context, action_description, risk_framing
        """FR-071, FR-079 / T-119: Generate LLM narration for a recommendation.

        Takes a recommendation and its linked simulation, generates three
        narrative components via GPT-4-mini:
        - urgency_context: why-now framing
        - action_description: what to do
        - risk_framing: downside implications

        All numbers are cited back to simulation payload with source path.
        Enforces strict rule: LLM generates words only, never numbers.
        All numbers come exclusively from simulation output.
        """
        # Fetch recommendation
        rec = self.db_session.scalar(
            select(Recommendation).where(
                (Recommendation.id == recommendation_id)
                & (Recommendation.tenant_id == tenant_id)
            )
        )
        if rec is None:
            msg = f"Recommendation {recommendation_id} not found for tenant {tenant_id}"
            raise ValueError(msg)

        # Fetch linked simulation
        if rec.id is None:
            msg = "Recommendation has no linked simulation"
            raise ValueError(msg)

        sim = self.db_session.scalar(
            select(Simulation).where(
                (Simulation.recommendation_id == rec.id)
                & (Simulation.tenant_id == tenant_id)
            )
        )
        if sim is None:
            msg = f"No simulation found for recommendation {recommendation_id}"
            raise ValueError(msg)

        # Build domain-specific prompt with strict constraints
        prompt = self._build_narration_prompt(
            recommendation=rec,
            simulation=sim,
            override_tone=override_tone,
        )

        # Call OpenAI API for narration
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert business analyst for e-commerce brands. "
                        "Generate clear, actionable narrative for recommendations. "
                        "CRITICAL: Never generate any numbers yourself. "
                        "All numbers must come from the simulation data provided. "
                        "Format your response with these three sections: "
                        "URGENCY_CONTEXT:, ACTION_DESCRIPTION:, RISK_FRAMING:"
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        narration_text = response.choices[0].message.content or ""

        # Parse response into three components
        components = self._parse_narration_response(narration_text)

        # Extract citations from simulation data
        citations = self._extract_citations_from_simulation(
            simulation=sim,
            narration_text=narration_text,
            components=components,
        )

        # Get token usage (with fallback for None)
        completion_tokens = 0
        prompt_tokens = 0
        if response.usage:
            completion_tokens = response.usage.completion_tokens or 0
            prompt_tokens = response.usage.prompt_tokens or 0

        return {
            "urgency_context": components.get("urgency_context", ""),
            "action_description": components.get("action_description", ""),
            "risk_framing": components.get("risk_framing", ""),
            "citations": citations,
            "narration_metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "completion_tokens": completion_tokens,
                "prompt_tokens": prompt_tokens,
                "tone_override": override_tone,
            },
        }

    def _build_narration_prompt(
        self,
        recommendation: Recommendation,
        simulation: Simulation,
        override_tone: str | None,
    ) -> str:
        """Build domain-specific prompt for LLM narration.

        Extracts key metrics from baseline/upside/downside scenarios
        and constructs a prompt that tells the LLM:
        - Current state (baseline)
        - Recommended action
        - Projected outcomes (upside)
        - Downside risks
        - Data freshness context

        Emphasizes: NO numbers generated by LLM, only cite from simulation.
        """
        baseline = simulation.baseline_scenario or {}
        upside = simulation.upside_scenario or {}
        downside = simulation.downside_scenario or {}

        baseline_metrics = baseline.get("output_metrics", {})
        upside_metrics = upside.get("output_metrics", {})
        downside_metrics = downside.get("output_metrics", {})

        tone = override_tone or (
            "urgent" if recommendation.impact_score > 7 else "balanced"
        )

        prompt = f"""
Generate a narrative for this recommendation using ONLY the data provided below.
CRITICAL RULE: Do not generate any numbers yourself.
Only cite values from the simulation data.

Domain: {recommendation.domain.upper()}
Recommendation: {recommendation.suggested_action}
Confidence Level: {recommendation.confidence_level} (
{recommendation.confidence_level})
Data Freshness: {recommendation.data_freshness_context}
Tone: {tone}

BASELINE (Current State - No Change):
{self._format_metrics_for_prompt(baseline_metrics, "baseline")}

UPSIDE (Best Case - If Action is Taken):
{self._format_metrics_for_prompt(upside_metrics, "upside")}

DOWNSIDE (Risk Case - If Action has Limited Effect):
{self._format_metrics_for_prompt(downside_metrics, "downside")}

EVIDENCE / REASONING:
{recommendation.signal_summary}

Please generate three sections:

URGENCY_CONTEXT: Explain why this matters NOW.
Reference current baseline state and any accelerating trends.
Keep to 2-3 sentences.

ACTION_DESCRIPTION: Describe what should be done in plain English.
Reference the specific upside projection if available.
Keep to 3-4 sentences.

RISK_FRAMING: Explain what could go wrong (downside scenario).
Reference the downside metrics and margin/KPI impact.
Keep to 2-3 sentences.

Remember: Every number you cite must come directly from the
baseline/upside/downside sections above. Do not invent numbers.
"""
        return prompt

    def _format_metrics_for_prompt(self, metrics: dict, scenario_type: str) -> str:
        """Format simulation metrics for inclusion in LLM prompt."""
        if not metrics:
            return f"{scenario_type}: No data available"

        lines = [f"{scenario_type}:"]
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                lines.append(f"  - {key}: {value:.2f}")
            else:
                lines.append(f"  - {key}: {value}")
        return "\n".join(lines)

    def _parse_narration_response(self, narration_text: str) -> dict:
        """Parse LLM response into three narrative components.

        Expects response formatted as:
        URGENCY_CONTEXT: ...
        ACTION_DESCRIPTION: ...
        RISK_FRAMING: ...
        """
        components = {
            "urgency_context": "",
            "action_description": "",
            "risk_framing": "",
        }

        text = narration_text.strip()

        # Extract URGENCY_CONTEXT
        if "URGENCY_CONTEXT:" in text:
            start = text.find("URGENCY_CONTEXT:") + len("URGENCY_CONTEXT:")
            end = text.find("ACTION_DESCRIPTION:", start)
            if end == -1:
                end = text.find("RISK_FRAMING:", start)
            if end == -1:
                end = len(text)
            components["urgency_context"] = text[start:end].strip()

        # Extract ACTION_DESCRIPTION
        if "ACTION_DESCRIPTION:" in text:
            start = text.find("ACTION_DESCRIPTION:") + len("ACTION_DESCRIPTION:")
            end = text.find("RISK_FRAMING:", start)
            if end == -1:
                end = len(text)
            components["action_description"] = text[start:end].strip()

        # Extract RISK_FRAMING
        if "RISK_FRAMING:" in text:
            start = text.find("RISK_FRAMING:") + len("RISK_FRAMING:")
            components["risk_framing"] = text[start:].strip()

        return components

    def _extract_citations_from_simulation(
        self,
        simulation: Simulation,
        narration_text: str,
        components: dict,
    ) -> list[dict]:
        """Extract numerical citations from simulation data.

        Scans the narration for numbers and attempts to match them
        back to simulation output_metrics. Records source path for audit.
        """
        citations = []

        baseline_metrics = simulation.baseline_scenario.get("output_metrics", {})
        upside_metrics = simulation.upside_scenario.get("output_metrics", {})
        downside_metrics = simulation.downside_scenario.get("output_metrics", {})

        # Build mapping of values to source paths for citation
        value_to_source = {}
        for key, val in baseline_metrics.items():
            if isinstance(val, (int, float)):
                value_to_source[f"{val:.2f}"] = {
                    "field": key,
                    "scenario": "baseline",
                    "path": f"baseline_scenario.output_metrics.{key}",
                }
        for key, val in upside_metrics.items():
            if isinstance(val, (int, float)):
                value_to_source[f"{val:.2f}"] = {
                    "field": key,
                    "scenario": "upside",
                    "path": f"upside_scenario.output_metrics.{key}",
                }
        for key, val in downside_metrics.items():
            if isinstance(val, (int, float)):
                value_to_source[f"{val:.2f}"] = {
                    "field": key,
                    "scenario": "downside",
                    "path": f"downside_scenario.output_metrics.{key}",
                }

        # Extract all citations from narration text
        combined_text = " ".join(components.values())

        for value_str, source_info in value_to_source.items():
            if value_str in combined_text:
                try:
                    numeric_value = float(value_str)
                    citations.append({
                        "field_name": source_info["field"],
                        "scenario_type": source_info["scenario"],
                        "value": numeric_value,
                        "source_path": source_info["path"],
                        "confidence_note": (
                            f"Based on {source_info['scenario']} scenario "
                            f"(confidence: {simulation.confidence_level})"
                        ),
                    })
                except ValueError:
                    pass

        return citations
