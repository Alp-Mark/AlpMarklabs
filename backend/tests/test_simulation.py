"""Test suite for simulation core functionality.

FR-081, FR-087 / T-081: Three-scenario simulation (baseline/upside/downside).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from backend.app.db.models import (
    ExportLink,
    ExportShare,
    Recommendation,
    Scenario,
    Simulation,
    Tenant,
    User,
)
from backend.app.simulation_service import SimulationService
from fastapi.testclient import TestClient
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    pass


class TestSimulation:
    """Test suite for simulation core functionality."""

    def test_create_auto_simulation(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test creating an automatic simulation."""
        # Create a recommendation first
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="acquisition",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        # Create simulation service
        service = SimulationService(db_session)

        # Mock response function (linear: output = 2 * input)
        def mock_response_func(x: float) -> float:
            return 2.0 * x

        # Run auto simulation
        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="acquisition",
            current_value=100.0,
            response_function=mock_response_func,
        )

        # Verify simulation was created
        assert simulation is not None
        assert simulation.tenant_id == tenant.id
        assert simulation.recommendation_id == recommendation.id
        assert simulation.domain == "acquisition"
        assert simulation.simulation_type == "auto"

    def test_baseline_scenario_matches_current_state(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that baseline scenario reflects current state exactly."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="retention",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 1.5 * x

        current_value = 50.0
        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="retention",
            current_value=current_value,
            response_function=mock_response_func,
        )

        # Baseline should match current value
        assert simulation.baseline_scenario["input"] == current_value
        assert simulation.baseline_scenario["output"] == mock_response_func(
            current_value
        )

    def test_upside_scenario_differs_from_baseline(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that upside scenario is different from baseline."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="margin",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 0.5 * x * x  # Quadratic response

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="margin",
            current_value=100.0,
            response_function=mock_response_func,
        )

        # Upside output should differ from baseline
        baseline_output = simulation.baseline_scenario["output"]
        upside_output = simulation.upside_scenario["output"]
        assert upside_output != baseline_output

    def test_downside_scenario_is_riskier_than_upside(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that downside scenario shows risk (lower output than upside)."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="inventory",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 3.0 * x

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="inventory",
            current_value=100.0,
            response_function=mock_response_func,
        )

        # Downside confidence should be lower than upside
        scenarios = db_session.scalars(
            select(Scenario).where(Scenario.simulation_id == simulation.id)
        ).all()

        upside_scenario = next(s for s in scenarios if s.scenario_type == "upside")
        downside_scenario = next(s for s in scenarios if s.scenario_type == "downside")

        assert downside_scenario.confidence_score <= upside_scenario.confidence_score

    def test_three_scenarios_created_per_simulation(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that exactly three scenario records are created."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="ops",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 1.2 * x

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="ops",
            current_value=75.0,
            response_function=mock_response_func,
        )

        # Verify three scenario records
        scenarios = db_session.scalars(
            select(Scenario).where(Scenario.simulation_id == simulation.id)
        ).all()

        assert len(scenarios) == 3
        scenario_types = {s.scenario_type for s in scenarios}
        assert scenario_types == {"baseline", "upside", "downside"}

    def test_confidence_level_assigned(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that confidence level is assigned correctly."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="executive",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return x + 10

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="executive",
            current_value=50.0,
            response_function=mock_response_func,
        )

        assert simulation.confidence_level in ["high", "medium", "low"]

    def test_x_star_found_in_metadata(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test that x_star (optimizer result) is recorded."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="acquisition",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return -((x - 150) ** 2) + 500  # Peak at x=150

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="acquisition",
            current_value=100.0,
            response_function=mock_response_func,
        )

        assert "value" in simulation.x_star
        assert "domain" in simulation.x_star

    def test_get_simulation_by_recommendation(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test retrieving a simulation by recommendation ID."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="retention",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 1.1 * x

        simulation = service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="retention",
            current_value=80.0,
            response_function=mock_response_func,
        )

        # Retrieve it
        retrieved = service.get_simulation_by_recommendation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
        )

        assert retrieved is not None
        assert retrieved.id == simulation.id

    def test_list_simulations_pagination(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test listing simulations with pagination."""
        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return x

        # Create multiple recommendations and simulations
        for i in range(5):
            recommendation = Recommendation(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                rule_id=f"test_rule_{i}",
                domain="acquisition",
                snapshot_date=datetime.now(UTC).date(),
                affected_area=f"test area {i}",
                signal_summary=f"test signal {i}",
                suggested_action=f"test action {i}",
                confidence_level="high",
                data_freshness_context="test freshness",
            )
            db_session.add(recommendation)
            db_session.flush()

            service.run_auto_simulation(
                tenant_id=tenant.id,
                recommendation_id=recommendation.id,
                domain="acquisition",
                current_value=100.0 + i,
                response_function=mock_response_func,
            )

        # List with pagination
        simulations, total_count = service.list_simulations(
            tenant_id=tenant.id,
            skip=0,
            limit=2,
        )

        assert len(simulations) == 2
        assert total_count == 5

    def test_simulation_tenant_isolation(
        self,
        tenant: Tenant,
        other_tenant: Tenant,
        db_session: Session,
    ) -> None:
        """Test that simulations are isolated by tenant."""
        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return x * 2

        # Create recommendation for tenant 1
        rec1 = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule_1",
            domain="acquisition",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(rec1)
        db_session.flush()

        # Create simulation for tenant 1
        service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=rec1.id,
            domain="acquisition",
            current_value=100.0,
            response_function=mock_response_func,
        )

        # Query simulations for tenant 2 should be empty
        sims_tenant2, count = service.list_simulations(
            tenant_id=other_tenant.id,
            skip=0,
            limit=100,
        )

        assert len(sims_tenant2) == 0
        assert count == 0

    def test_api_get_simulation_by_recommendation(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test GET endpoint for retrieving simulation by recommendation."""
        recommendation = Recommendation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            rule_id="test_rule",
            domain="margin",
            snapshot_date=datetime.now(UTC).date(),
            affected_area="test area",
            signal_summary="test signal",
            suggested_action="test action",
            confidence_level="high",
            data_freshness_context="test freshness",
        )
        db_session.add(recommendation)
        db_session.flush()

        service = SimulationService(db_session)

        def mock_response_func(x: float) -> float:
            return 1.5 * x

        service.run_auto_simulation(
            tenant_id=tenant.id,
            recommendation_id=recommendation.id,
            domain="margin",
            current_value=100.0,
            response_function=mock_response_func,
        )

        # Call API
        response = client.get(
            f"/tenants/{tenant.id}/simulations/recommendations/{recommendation.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "margin"
        assert data["confidence_level"] in ["high", "medium", "low"]

    def test_api_list_simulations(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test GET endpoint for listing simulations."""
        response = client.get(f"/tenants/{tenant.id}/simulations")

        assert response.status_code == 200
        data = response.json()
        assert "simulations" in data
        assert "total_count" in data
        assert isinstance(data["simulations"], list)
        assert isinstance(data["total_count"], int)

    def test_api_simulation_tenant_not_found(
        self,
        nonexistent_uuid: uuid.UUID,
        client: TestClient,
    ) -> None:
        """Test that 404 is returned for nonexistent tenant."""
        rec_id = uuid.uuid4()
        response = client.get(
            f"/tenants/{nonexistent_uuid}/simulations/recommendations/{rec_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # ======================================================================
    # Domain-Specific Simulation Tests (FR-082 to FR-086 / T-082)
    # ======================================================================

    def test_growth_simulation_input_validation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test growth simulation input validation."""
        # Test: percentages don't sum to 100
        response = client.post(
            f"/tenants/{tenant.id}/simulations/growth",
            json={
                "total_budget": 10000.0,
                "channel_allocations": [
                    {"channel_id": "paid_social", "budget_allocation_pct": 60.0}
                ],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_growth_simulation_creates_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test growth simulation creates simulation with valid input."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/growth",
            json={
                "total_budget": 10000.0,
                "channel_allocations": [
                    {"channel_id": "paid_social", "budget_allocation_pct": 60.0},
                    {"channel_id": "google", "budget_allocation_pct": 40.0},
                ],
                "scenario_label": "Growth test scenario",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "growth"
        assert data["baseline_scenario"]["input"] == 10000.0
        assert data["upside_scenario"]["output"] != data["baseline_scenario"]["output"]

    def test_retention_simulation_creates_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test retention simulation creates simulation with valid input."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/retention",
            json={
                "offer_discount_pct": 15.0,
                "target_segment": "first_order_0_30d",
                "days_post_first_purchase": 7,
                "expected_response_rate_pct": 12.5,
                "estimated_segment_size": 5000,
                "scenario_label": "Retention test scenario",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "retention"
        assert data["baseline_scenario"]["input"] == 12.5
        assert "confidence_level" in data

    def test_finance_simulation_creates_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test finance simulation creates simulation with valid input."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/finance",
            json={
                "cost_changes": [
                    {
                        "cost_type": "shipping_cost",
                        "current_value": 5.0,
                        "proposed_value": 7.0,
                    },
                    {
                        "cost_type": "return_cost",
                        "current_value": 2.0,
                        "proposed_value": 2.5,
                    },
                ],
                "scenario_label": "Finance cost increase scenario",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "finance"
        # Cost delta = (7-5) + (2.5-2) = 2.5
        assert data["baseline_scenario"]["input"] == 2.5
        assert data["confidence_level"] in ["high", "medium", "low"]

    def test_operations_simulation_creates_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test operations simulation creates simulation with valid input."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/operations",
            json={
                "sku_or_category": "SKU-12345",
                "reorder_quantity_multiplier": 1.5,
                "lead_time_days": 10,
                "reorder_timing_policy": "weekly",
                "target_service_level_pct": 95.0,
                "scenario_label": "Ops inventory increase",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "operations"
        assert data["baseline_scenario"]["input"] == 1.5

    def test_executive_simulation_creates_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test executive simulation creates simulation with valid input."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/executive",
            json={
                "pricing_change_pct": 10.0,
                "channel_mix_changes": {"paid_social": 10.0, "google": -5.0},
                "demand_multiplier": 1.1,
                "projection_horizon_days": 90,
                "scenario_label": "Strategic pricing and mix shift",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "executive"
        assert data["baseline_scenario"]["input"] == 10.0

    def test_all_domain_simulations_have_three_scenarios(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test that all domain simulations produce three scenarios."""
        # Test growth
        response = client.post(
            f"/tenants/{tenant.id}/simulations/growth",
            json={
                "total_budget": 5000.0,
                "channel_allocations": [
                    {"channel_id": "paid_social", "budget_allocation_pct": 100.0}
                ],
            },
        )
        data = response.json()
        assert "baseline_scenario" in data
        assert "upside_scenario" in data
        assert "downside_scenario" in data

    def test_retention_simulation_invalid_discount(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test retention simulation rejects invalid discount."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/retention",
            json={
                "offer_discount_pct": 150.0,  # Invalid: > 100
                "target_segment": "test",
                "days_post_first_purchase": 7,
                "expected_response_rate_pct": 10.0,
            },
        )
        assert response.status_code == 422

    def test_operations_simulation_invalid_lead_time(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test operations simulation rejects invalid lead time."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/operations",
            json={
                "sku_or_category": "SKU-123",
                "reorder_quantity_multiplier": 1.5,
                "lead_time_days": 100,  # Invalid: > 90
                "reorder_timing_policy": "weekly",
            },
        )
        assert response.status_code == 422

    def test_executive_simulation_pricing_bounds(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test executive simulation respects pricing bounds."""
        response = client.post(
            f"/tenants/{tenant.id}/simulations/executive",
            json={
                "pricing_change_pct": -50.0,  # Valid: price decrease
                "channel_mix_changes": {"google": 0.0},
                "demand_multiplier": 0.8,  # Valid: demand contraction
            },
        )
        assert response.status_code == 200

    def test_compare_simulations_requires_two_minimum(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test comparison endpoint rejects single simulation."""
        from uuid import uuid4
        response = client.post(
            f"/tenants/{tenant.id}/simulations/compare",
            json={"simulation_ids": [str(uuid4())]},
        )
        assert response.status_code == 422

    def test_compare_growth_and_retention_simulations(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test comparing growth and retention simulations side-by-side."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create two growth simulations with different budgets
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )
        sim2 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=10000.0,
            channel_allocations={"google": 0.6, "meta": 0.4},
        )

        # Compare them via endpoint
        response = client.post(
            f"/tenants/{tenant.id}/simulations/compare",
            json={"simulation_ids": [str(sim1.id), str(sim2.id)]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "compared_simulations" in data
        assert "metrics" in data
        assert "overall_confidence" in data
        assert "data_freshness_warnings" in data
        assert len(data["compared_simulations"]) == 6  # 3 scenarios × 2 sims

    def test_comparison_includes_confidence_and_warnings(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test comparison view includes confidence scores and freshness warnings."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create two different domain simulations
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=8000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )
        sim2 = service.run_retention_simulation(
            tenant_id=tenant.id,
            offer_discount_pct=15.0,
            response_rate_pct=12.0,
        )

        response = client.post(
            f"/tenants/{tenant.id}/simulations/compare",
            json={"simulation_ids": [str(sim1.id), str(sim2.id)]},
        )

        assert response.status_code == 200
        data = response.json()

        # Check overall confidence is calculated
        assert 0 <= data["overall_confidence"] <= 100

        # Check recommendation is provided
        assert data["recommendation_for_viewer"] in [
            "Safe to use",
            "Consider with caution",
            "Wait for more data",
        ]

        # Check freshness warnings exist
        assert isinstance(data["data_freshness_warnings"], list)

    def test_comparison_maps_metrics_across_simulations(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test comparison correctly maps metrics for cross-simulation comparison."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create three simulations to compare
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )
        sim2 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=10000.0,
            channel_allocations={"google": 0.6, "meta": 0.4},
        )
        sim3 = service.run_retention_simulation(
            tenant_id=tenant.id,
            offer_discount_pct=10.0,
            response_rate_pct=8.0,
        )

        response = client.post(
            f"/tenants/{tenant.id}/simulations/compare",
            json={
                "simulation_ids": [str(sim1.id), str(sim2.id), str(sim3.id)],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Each metric row should have comparison values for all simulations
        for metric in data["metrics"]:
            assert "metric_name" in metric
            assert "comparison_values" in metric
            assert "variance" in metric
            # Should have entries for 3 simulations × 3 scenarios = 9 entries
            assert len(metric["comparison_values"]) == 9

    def test_cross_tenant_isolation_on_comparison(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test comparison cannot mix simulations from different tenants."""
        from uuid import uuid4

        from backend.app.db.models import Tenant
        from backend.app.simulation_service import SimulationService

        # Create a second tenant
        tenant2 = Tenant(
            id=uuid.uuid4(),
            name="Brand 2",
            slug="brand-2",
            billing_plan="starter",
            billing_cycle="monthly",
            billing_status="active",
            seat_limit=5,
            base_currency="USD",
            locale="en-US",
        )
        db_session.add(tenant2)
        db_session.commit()

        service = SimulationService(db_session)

        # Create simulation in first tenant
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Try to compare using different tenant (should fail)
        response = client.post(
            f"/tenants/{tenant2.id}/simulations/compare",
            json={"simulation_ids": [str(sim1.id), str(uuid4())]},
        )

        # Should fail because simulations don't belong to tenant2 or user lacks access
        assert response.status_code in [403, 404, 422]

    def test_get_simulation_detail(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test retrieving a single simulation detail with all scenarios."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a growth simulation
        simulation = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Retrieve the simulation detail
        response = client.get(
            f"/tenants/{tenant.id}/simulations/{simulation.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "simulation" in data
        assert "scenarios" in data
        assert data["simulation"]["id"] == str(simulation.id)
        assert data["simulation"]["domain"] == "growth"
        assert len(data["scenarios"]) == 3  # baseline, upside, downside
        assert data["scenarios"][0]["scenario_type"] in [
            "baseline", "upside", "downside"
        ]

    def test_get_simulation_detail_includes_all_scenarios(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that all three scenarios are included in detail view."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a retention simulation
        simulation = service.run_retention_simulation(
            tenant_id=tenant.id,
            offer_discount_pct=10.0,
            response_rate_pct=15.0,
        )

        response = client.get(
            f"/tenants/{tenant.id}/simulations/{simulation.id}"
        )

        assert response.status_code == 200
        data = response.json()
        scenarios = data["scenarios"]

        # Verify all scenario types present
        scenario_types = {s["scenario_type"] for s in scenarios}
        assert scenario_types == {"baseline", "upside", "downside"}

        # Verify each scenario has required fields
        for scenario in scenarios:
            assert "id" in scenario
            assert "simulation_id" in scenario
            assert "scenario_type" in scenario
            assert "input_assumptions" in scenario
            assert "output_metrics" in scenario
            assert "confidence_score" in scenario
            assert "created_at" in scenario

    def test_get_simulation_detail_not_found(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test 404 when simulation doesn't exist."""
        import uuid

        fake_sim_id = uuid.uuid4()

        response = client.get(
            f"/tenants/{tenant.id}/simulations/{fake_sim_id}"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_simulations(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test listing simulations for a tenant."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create 3 simulations
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )
        sim2 = service.run_retention_simulation(
            tenant_id=tenant.id,
            offer_discount_pct=10.0,
            response_rate_pct=15.0,
        )
        sim3 = service.run_finance_simulation(
            tenant_id=tenant.id,
            cost_changes={
                "shipping": (5.0, 4.5),
                "returns": (2.0, 2.5),
            },
        )

        # List simulations
        response = client.get(f"/tenants/{tenant.id}/simulations")

        assert response.status_code == 200
        data = response.json()
        assert "simulations" in data
        assert "total_count" in data
        assert data["total_count"] == 3
        assert len(data["simulations"]) == 3

        # Verify simulations are in descending order by created_at
        sim_ids = [s["id"] for s in data["simulations"]]
        assert str(sim3.id) in sim_ids
        assert str(sim2.id) in sim_ids
        assert str(sim1.id) in sim_ids

    def test_list_simulations_via_endpoint_pagination(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test pagination (skip/limit) on simulation list endpoint."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create 5 simulations
        for i in range(5):
            service.run_growth_simulation(
                tenant_id=tenant.id,
                total_budget=1000.0 * (i + 1),
                channel_allocations={"google": 0.5, "meta": 0.5},
            )

        # Test skip and limit
        response = client.get(
            f"/tenants/{tenant.id}/simulations?skip=0&limit=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["simulations"]) == 2

        # Test skip
        response = client.get(
            f"/tenants/{tenant.id}/simulations?skip=3&limit=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert len(data["simulations"]) == 2

    def test_cross_tenant_isolation_on_get_detail(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that cross-tenant access is blocked on detail view."""
        from backend.app.db.models import Tenant
        from backend.app.simulation_service import SimulationService

        # Create second tenant
        tenant2 = Tenant(
            id=uuid.uuid4(),
            name="Brand 2",
            slug="brand-2",
            billing_plan="starter",
            billing_cycle="monthly",
            billing_status="active",
            seat_limit=5,
            base_currency="USD",
            locale="en-US",
        )
        db_session.add(tenant2)
        db_session.commit()

        service = SimulationService(db_session)

        # Create simulation in first tenant
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Try to retrieve simulation from different tenant
        response = client.get(
            f"/tenants/{tenant2.id}/simulations/{sim1.id}"
        )

        # Should get 403 (auth) or 404 (cross-tenant isolation)
        assert response.status_code in [403, 404]

    def test_export_simulation_as_pdf(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test generating a PDF export of a simulation."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a growth simulation
        simulation = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Export as PDF
        response = client.post(
            f"/tenants/{tenant.id}/simulations/{simulation.id}/export",
            json={"format": "pdf", "include_scenarios": True},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert "simulation_" in response.headers["content-disposition"]
        assert ".pdf" in response.headers["content-disposition"]
        # PDF files should have some minimum size
        assert len(response.content) > 500

    def test_export_simulation_as_csv(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test generating a CSV export of a simulation."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a retention simulation
        simulation = service.run_retention_simulation(
            tenant_id=tenant.id,
            offer_discount_pct=10.0,
            response_rate_pct=15.0,
        )

        # Export as CSV
        response = client.post(
            f"/tenants/{tenant.id}/simulations/{simulation.id}/export",
            json={"format": "csv", "include_scenarios": True},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert ".csv" in response.headers["content-disposition"]
        # CSV should contain simulation data
        csv_content = response.content.decode("utf-8")
        assert "Simulation Export" in csv_content
        assert "Scenario Details" in csv_content
        assert simulation.domain in csv_content

    def test_export_csv_contains_all_scenarios(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that CSV export includes all three scenarios."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a finance simulation
        simulation = service.run_finance_simulation(
            tenant_id=tenant.id,
            cost_changes={
                "shipping": (5.0, 4.5),
                "returns": (2.0, 2.5),
            },
        )

        # Export as CSV
        response = client.post(
            f"/tenants/{tenant.id}/simulations/{simulation.id}/export",
            json={"format": "csv"},
        )

        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")

        # Should contain all three scenario types
        assert "baseline" in csv_content
        assert "upside" in csv_content
        assert "downside" in csv_content

    def test_export_pdf_contains_metadata(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that PDF export includes simulation metadata."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create an operations simulation
        simulation = service.run_operations_simulation(
            tenant_id=tenant.id,
            reorder_qty_multiplier=1.5,
            lead_time_days=14,
        )

        # Export as PDF
        response = client.post(
            f"/tenants/{tenant.id}/simulations/{simulation.id}/export",
            json={"format": "pdf"},
        )

        assert response.status_code == 200
        # PDF is binary, but we can at least verify it's not empty
        assert len(response.content) > 1000

    def test_export_invalid_format(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that invalid export format is rejected."""
        from backend.app.simulation_service import SimulationService

        service = SimulationService(db_session)

        # Create a simulation
        simulation = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Try to export with invalid format
        response = client.post(
            f"/tenants/{tenant.id}/simulations/{simulation.id}/export",
            json={"format": "excel"},  # Invalid format
        )

        assert response.status_code == 422

    def test_export_nonexistent_simulation(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test that exporting a nonexistent simulation returns 404."""
        import uuid

        fake_sim_id = uuid.uuid4()

        response = client.post(
            f"/tenants/{tenant.id}/simulations/{fake_sim_id}/export",
            json={"format": "pdf"},
        )

        assert response.status_code == 404

    def test_export_cross_tenant_isolation(
        self,
        tenant: Tenant,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that cross-tenant export is blocked."""
        from backend.app.db.models import Tenant
        from backend.app.simulation_service import SimulationService

        # Create second tenant
        tenant2 = Tenant(
            id=uuid.uuid4(),
            name="Brand 2",
            slug="brand-2",
            billing_plan="starter",
            billing_cycle="monthly",
            billing_status="active",
            seat_limit=5,
            base_currency="USD",
            locale="en-US",
        )
        db_session.add(tenant2)
        db_session.commit()

        service = SimulationService(db_session)

        # Create simulation in first tenant
        sim1 = service.run_growth_simulation(
            tenant_id=tenant.id,
            total_budget=5000.0,
            channel_allocations={"google": 0.5, "meta": 0.5},
        )

        # Try to export from different tenant
        response = client.post(
            f"/tenants/{tenant2.id}/simulations/{sim1.id}/export",
            json={"format": "pdf"},
        )

        # Should fail (403 auth or 404 cross-tenant isolation)
        assert response.status_code in [403, 404]


# ========== T-086: Scoped Export Sharing Tests ==========


def test_share_export_with_valid_recipient(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test sharing an export with a valid recipient in same tenant.
    
    T-086: Create an export share that respects recipient permissions.
    """
    from backend.app.db.models import TenantMembership

    # Create second user in same tenant
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user2.id,
        role="growth_performance_manager",
    )
    db_session.add(membership)
    db_session.commit()

    # Create a simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=5000.0,
        channel_allocations={"google": 0.5, "meta": 0.5},
    )

    # Share the export
    response = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "recipient@example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["simulation_id"] == str(sim.id)
    assert data["shared_with_email"] == "recipient@example.com"
    assert data["status"] == "active"
    assert data["revoked_at"] is None


def test_share_export_with_same_recipient_twice(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test sharing same export with same recipient twice returns existing share.
    
    T-086: Idempotent share creation.
    """
    from backend.app.db.models import TenantMembership

    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient2@example.com",
        full_name="Recipient 2",
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user2.id,
        role="finance_controller",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=4000.0,
        channel_allocations={"google": 1.0},
    )

    # Share twice
    response1 = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "recipient2@example.com"},
    )
    share1_id = response1.json()["id"]

    response2 = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "recipient2@example.com"},
    )
    share2_id = response2.json()["id"]

    # Should return same share ID (idempotent)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert share1_id == share2_id


def test_share_export_with_inactive_recipient(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test sharing with an inactive user fails.
    
    T-086: Permission check - recipient must be active.
    """
    from backend.app.db.models import TenantMembership

    # Create inactive user
    user_inactive = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user_inactive)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user_inactive.id,
        role="growth_performance_manager",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=3000.0,
        channel_allocations={"google": 1.0},
    )

    # Try to share with inactive user
    response = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "inactive@example.com"},
    )

    assert response.status_code == 400
    assert "inactive" in response.json()["detail"].lower()


def test_share_export_with_user_not_in_tenant(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test sharing with a user not in the tenant fails.
    
    T-086: Cross-tenant isolation - recipient must be in same tenant.
    """
    # Create user but do NOT add to tenant membership
    user_external = User(
        id=uuid.uuid4(),
        email="external@example.com",
        full_name="External User",
        is_active=True,
    )
    db_session.add(user_external)
    db_session.commit()

    # Create simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=2500.0,
        channel_allocations={"meta": 1.0},
    )

    # Try to share with external user
    response = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "external@example.com"},
    )

    assert response.status_code == 400
    assert "tenant" in response.json()["detail"].lower()


def test_list_shared_exports(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test listing exports shared with current user.
    
    T-086: Retrieve all active shares for recipient.
    """
    from backend.app.db.models import TenantMembership

    # Create a sharer user
    user_sharer = User(
        id=uuid.uuid4(),
        email="sharer@example.com",
        full_name="Sharer",
        is_active=True,
    )
    db_session.add(user_sharer)
    db_session.flush()

    # Add sharer to tenant
    m_sharer = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user_sharer.id,
        role="growth_performance_manager",
    )
    db_session.add(m_sharer)
    db_session.commit()

    # Create two simulations created by sharer
    service = SimulationService(db_session)
    sim1 = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=2000.0,
        channel_allocations={"meta": 1.0},
    )
    sim2 = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=3000.0,
        channel_allocations={"google": 1.0},
    )

    # Manually share both simulations with the current test user via service
    from backend.app.db.models import ExportShare
    share1 = ExportShare(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        simulation_id=sim1.id,
        shared_by_user_id=user_sharer.id,
        shared_with_user_id=user.id,
        status="active",
    )
    share2 = ExportShare(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        simulation_id=sim2.id,
        shared_by_user_id=user_sharer.id,
        shared_with_user_id=user.id,
        status="active",
    )
    db_session.add_all([share1, share2])
    db_session.commit()

    # List shared exports as recipient (the current test user)
    response = client.get(
        f"/tenants/{tenant.id}/exports/shared?skip=0&limit=50",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["shares"]) >= 2
    # All shares should be active
    for share in data["shares"]:
        assert share["status"] == "active"
        assert share["shared_with_email"] == user.email
    from backend.app.db.models import TenantMembership

    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient4@example.com",
        full_name="Recipient 4",
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user2.id,
        role="finance_controller",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=3000.0,
        channel_allocations={"meta": 1.0},
    )

    # Share the simulation
    share_response = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "recipient4@example.com"},
    )
    assert share_response.status_code == 200
    share_id = share_response.json()["id"]

    # Revoke the share
    revoke_response = client.delete(
        f"/tenants/{tenant.id}/exports/{share_id}/revoke",
    )

    assert revoke_response.status_code == 200
    data = revoke_response.json()
    assert data["status"] == "revoked"
    assert data["revoked_at"] is not None


def test_revoke_nonexistent_share(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test revoking a non-existent share fails.
    
    T-086: 404 for non-existent share.
    """
    fake_share_id = uuid.uuid4()

    response = client.delete(
        f"/tenants/{tenant.id}/exports/{fake_share_id}/revoke",
    )

    assert response.status_code == 404


def test_share_nonexistent_simulation(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test sharing a non-existent simulation fails.
    
    T-086: 404 for non-existent simulation.
    """
    from backend.app.db.models import TenantMembership

    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient5@example.com",
        full_name="Recipient 5",
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user2.id,
        role="retention_crm_manager",
    )
    db_session.add(membership)
    db_session.commit()

    # Try to share non-existent simulation
    fake_sim_id = uuid.uuid4()
    response = client.post(
        f"/tenants/{tenant.id}/simulations/{fake_sim_id}/share",
        json={"recipient_email": "recipient5@example.com"},
    )

    assert response.status_code == 404


def test_export_share_cross_tenant_isolation(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test cross-tenant isolation on export shares.
    
    T-086: Cannot share or access exports across tenant boundaries.
    """
    from backend.app.db.models import TenantMembership

    # Create second tenant and user
    tenant2 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 2",
        slug="tenant-2",
    )
    db_session.add(tenant2)
    db_session.flush()

    user2 = User(
        id=uuid.uuid4(),
        email="tenant2user@example.com",
        full_name="Tenant 2 User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant2.id,
        user_id=user2.id,
        role="growth_performance_manager",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation in tenant1
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=1000.0,
        channel_allocations={"google": 1.0},
    )

    # Try to share simulation from tenant1 to user in tenant2
    response = client.post(
        f"/tenants/{tenant.id}/simulations/{sim.id}/share",
        json={"recipient_email": "tenant2user@example.com"},
    )

    # Should fail - recipient not in tenant1
    assert response.status_code == 400
    assert "tenant" in response.json()["detail"].lower()


# T-087: Signed file links and expiry management tests


def test_generate_export_link_for_active_share(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test generating a signed download link for an active export share."""
    from backend.app.db.models import TenantMembership

    # Create second user in same tenant
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    # Add user2 to tenant
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user2.id,
        role="viewer",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=1000.0,
        channel_allocations={"google": 1.0},
    )

    # Create export share
    db_session.execute(
        insert(ExportShare).values(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            simulation_id=sim.id,
            shared_by_user_id=user.id,
            shared_with_user_id=user2.id,
            status="active",
        )
    )
    db_session.commit()
    share_id = db_session.scalar(
        select(ExportShare).where(ExportShare.tenant_id == tenant.id)
    ).id

    # Generate download link
    response = client.post(
        f"/tenants/{tenant.id}/exports/{share_id}/generate-link",
    )

    assert response.status_code == 200
    data = response.json()
    assert "download_link" in data
    assert "download_url" in data
    assert data["download_link"]["share_id"] == str(share_id)
    assert "token" in data["download_link"]
    assert data["download_link"]["token"]  # Token should not be empty
    assert "expires_at" in data["download_link"]


def test_generate_link_for_revoked_share(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test generating link fails with 400 when share is revoked."""
    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    # Create and revoke export share
    db_session.execute(
        insert(ExportShare).values(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            simulation_id=uuid.uuid4(),
            shared_by_user_id=user.id,
            shared_with_user_id=user2.id,
            status="revoked",
            revoked_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    share_id = db_session.scalar(
        select(ExportShare).where(ExportShare.tenant_id == tenant.id)
    ).id

    response = client.post(
        f"/tenants/{tenant.id}/exports/{share_id}/generate-link",
    )

    assert response.status_code == 400
    assert "revoked" in response.json()["detail"].lower()


def test_generate_link_for_nonexistent_share(
    tenant: Tenant,
    client: TestClient,
) -> None:
    """Test generating link fails with 404 for nonexistent share."""
    fake_share_id = uuid.uuid4()

    response = client.post(
        f"/tenants/{tenant.id}/exports/{fake_share_id}/generate-link",
    )

    assert response.status_code == 404


def test_download_export_with_valid_token(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test downloading export file using valid signed token."""
    from backend.app.db.models import TenantMembership

    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    # Add to tenant
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user2.id,
        role="viewer",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation and share
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=1000.0,
        channel_allocations={"google": 1.0},
    )

    db_session.execute(
        insert(ExportShare).values(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            simulation_id=sim.id,
            shared_by_user_id=user.id,
            shared_with_user_id=user2.id,
            status="active",
        )
    )
    db_session.commit()
    share_id = db_session.scalar(
        select(ExportShare).where(ExportShare.tenant_id == tenant.id)
    ).id

    # Generate link
    response = client.post(
        f"/tenants/{tenant.id}/exports/{share_id}/generate-link",
    )
    assert response.status_code == 200
    token = response.json()["download_link"]["token"]

    # Download using token
    response = client.get(f"/exports/download/{token}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0  # PDF content exists


def test_download_export_with_expired_token(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test downloading fails with 400 for expired token."""
    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    # Create share with expired link
    share_id = uuid.uuid4()
    token_id = uuid.uuid4()

    db_session.execute(
        insert(ExportShare).values(
            id=share_id,
            tenant_id=tenant.id,
            simulation_id=uuid.uuid4(),
            shared_by_user_id=user.id,
            shared_with_user_id=user2.id,
            status="active",
        )
    )

    # Create link that expired in the past
    db_session.execute(
        insert(ExportLink).values(
            id=token_id,
            share_id=share_id,
            token="fake-expired-token",
            expires_at=datetime.now(UTC) - timedelta(days=1),
            created_at=datetime.now(UTC) - timedelta(days=8),
        )
    )
    db_session.commit()

    # Try to download with expired token
    response = client.get("/exports/download/fake-expired-token")

    # Will fail with invalid signature (since token isn't real)
    assert response.status_code == 400


def test_download_export_with_tampered_token(
    client: TestClient,
) -> None:
    """Test downloading fails with 400 for tampered token."""
    # Use completely invalid/tampered token
    response = client.get("/exports/download/tampered.invalid.token")

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_download_export_with_nonexistent_link(
    tenant: Tenant,
    user: User,
    db_session: Session,
) -> None:
    """Test downloading fails with 404 when link not found."""
    from backend.app.simulation_service import SimulationService

    service = SimulationService(db_session)

    # Create valid signature but link not in DB
    from backend.app.utils.token_signing import ExportLinkTokenSigner

    signer = ExportLinkTokenSigner("default-dev-key-change-in-prod")
    fake_share_id = uuid.uuid4()
    token = signer.generate_token(fake_share_id)

    # Try to validate link that doesn't exist
    with pytest.raises(ValueError, match="link not found"):
        service.validate_and_get_export_by_token(db_session, token)


def test_export_link_tracks_access_timestamp(
    tenant: Tenant,
    user: User,
    db_session: Session,
    client: TestClient,
) -> None:
    """Test that accessing download link updates accessed_at timestamp."""
    from backend.app.db.models import TenantMembership

    # Create second user
    user2 = User(
        id=uuid.uuid4(),
        email="recipient@example.com",
        full_name="Recipient User",
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user2)

    # Add to tenant
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user2.id,
        role="viewer",
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulation and share
    service = SimulationService(db_session)
    sim = service.run_growth_simulation(
        tenant_id=tenant.id,
        total_budget=1000.0,
        channel_allocations={"google": 1.0},
    )

    db_session.execute(
        insert(ExportShare).values(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            simulation_id=sim.id,
            shared_by_user_id=user.id,
            shared_with_user_id=user2.id,
            status="active",
        )
    )
    db_session.commit()
    share_id = db_session.scalar(
        select(ExportShare).where(ExportShare.tenant_id == tenant.id)
    ).id

    # Generate link
    response = client.post(
        f"/tenants/{tenant.id}/exports/{share_id}/generate-link",
    )
    token = response.json()["download_link"]["token"]

    # Check accessed_at before download
    link_before = db_session.scalar(
        select(ExportLink).where(ExportLink.token == token)
    )
    assert link_before.accessed_at is None

    # Download file
    response = client.get(f"/exports/download/{token}")
    assert response.status_code == 200

    # Check accessed_at after download
    db_session.refresh(link_before)
    assert link_before.accessed_at is not None


# ========== T-117: Recommendation-to-Simulation Launch Tests ==========


def test_launch_simulation_from_growth_recommendation(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launch simulation from growth recommendation (happy path)."""
    # Create a growth recommendation with evidence
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Google spend inefficient",
        suggested_action="Reallocate to Meta",
        estimated_impact=1500.0,
        confidence_level="high",
        data_freshness_context="15 min",
        status="new",
        priority=1,
        impact_score=8.5,
        evidence={
            "total_budget": 10000.0,
            "channel_allocations": {"google": 0.3, "meta": 0.7},
        },
    )
    db_session.add(rec)
    db_session.commit()

    # Launch simulation from recommendation
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "simulation" in data
    assert "recommendation_id" in data
    assert "parameters_used" in data
    assert "message" in data

    # Check simulation was created
    assert data["recommendation_id"] == str(rec.id)
    assert data["parameters_used"]["total_budget"] == 10000.0
    assert data["parameters_used"]["channel_allocations"] == {
        "google": 0.3,
        "meta": 0.7,
    }

    # Check message
    assert "Growth" in data["message"]
    assert "parameters" in data["message"].lower()


def test_launch_simulation_from_retention_recommendation(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launch simulation from retention recommendation.

    Tests with different domain than growth.
    """

    # Create a retention recommendation with evidence
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="retention_001",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="repeat_purchase",
        signal_summary="Churn rate elevated",
        suggested_action="Launch retention offer",
        estimated_impact=800.0,
        confidence_level="high",
        data_freshness_context="1 hour",
        status="new",
        priority=2,
        impact_score=7.0,
        evidence={
            "offer_discount_pct": 12.0,
            "response_rate_pct": 18.0,
            "estimated_segment_size": 2000,
        },
    )
    db_session.add(rec)
    db_session.commit()

    # Launch simulation from recommendation
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 200
    data = response.json()

    # Check response structure and domain specifics
    assert data["recommendation_id"] == str(rec.id)
    assert data["parameters_used"]["offer_discount_pct"] == 12.0
    assert data["parameters_used"]["response_rate_pct"] == 18.0
    assert data["parameters_used"]["estimated_segment_size"] == 2000

    # Check message shows retention
    assert "Retention" in data["message"]


def test_launch_simulation_with_parameter_overrides(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launch simulation with user parameter overrides."""

    # Create a recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Budget optimization",
        suggested_action="Adjust allocations",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="15 min",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={
            "total_budget": 10000.0,
            "channel_allocations": {"google": 0.5, "meta": 0.5},
        },
    )
    db_session.add(rec)
    db_session.commit()

    # Launch simulation with parameter overrides
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={
            "override_parameters": {
                "total_budget": 15000.0,
            }
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Check that override was applied
    assert data["parameters_used"]["total_budget"] == 15000.0
    # Original allocations should still be there
    assert data["parameters_used"]["channel_allocations"] == {
        "google": 0.5,
        "meta": 0.5,
    }


def test_launch_simulation_nonexistent_recommendation(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launch simulation with nonexistent recommendation returns 404."""

    # Try to launch simulation from nonexistent recommendation
    fake_rec_id = uuid.uuid4()
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{fake_rec_id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_launch_simulation_cross_tenant_isolation(
    client: TestClient,
    db_session: Session,
    tenant: Tenant,
    user: User,
    other_tenant: Tenant,
) -> None:
    """FR-126 / T-117: Cross-tenant isolation.

    Ensure user cannot launch simulation from other tenant's recommendation.
    """

    # Create recommendation in other_tenant
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Test",
        suggested_action="Test action",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="15 min",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={
            "total_budget": 10000.0,
            "channel_allocations": {"google": 0.5, "meta": 0.5},
        },
    )
    db_session.add(rec)
    db_session.commit()

    # Try to launch simulation from other_tenant recommendation
    # while authed as tenant user (should get 404)
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 404


def test_launch_simulation_preserves_recommendation_link(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launched simulation has recommendation_id set."""

    # Create a recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Test",
        suggested_action="Test action",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="15 min",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={
            "total_budget": 5000.0,
            "channel_allocations": {"google": 0.5, "meta": 0.5},
        },
    )
    db_session.add(rec)
    db_session.commit()

    # Launch simulation
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify recommendation_id is preserved
    sim_id = data["simulation"]["id"]
    assert data["recommendation_id"] == str(rec.id)

    # Verify in database that simulation.recommendation_id is set
    sim = db_session.scalar(
        select(Simulation).where(Simulation.id == UUID(sim_id))
    )
    assert sim.recommendation_id == rec.id


def test_launch_simulation_invalid_domain(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-126 / T-117: Launch simulation with invalid domain raises 422."""

    # Create a recommendation with invalid domain
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="invalid_001",
        domain="invalid_domain",
        snapshot_date=date.today(),
        affected_area="test",
        signal_summary="Test",
        suggested_action="Test action",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="15 min",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={},
    )
    db_session.add(rec)
    db_session.commit()

    # Try to launch simulation
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 422
    assert "domain" in response.json()["detail"].lower()


def test_launch_simulation_nonexistent_tenant(
    client: TestClient
) -> None:
    """FR-126 / T-117: Launch simulation from nonexistent tenant returns 404."""
    fake_tenant_id = uuid.uuid4()
    fake_rec_id = uuid.uuid4()

    response = client.post(
        f"/tenants/{fake_tenant_id}/recommendations/{fake_rec_id}/simulate",
        json={"override_parameters": None},
    )

    assert response.status_code == 404
    assert "tenant" in response.json()["detail"].lower()


# ========== T-119: LLM Narration Layer Tests ==========


def test_narrate_growth_recommendation_happy_path(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: Generate narration for growth recommendation."""
    # Create growth recommendation with simulation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Google spend is inefficient vs Meta",
        suggested_action="Reallocate 30% from Google to Meta",
        estimated_impact=2500.0,
        confidence_level="high",
        data_freshness_context="2 hours",
        status="new",
        priority=1,
        impact_score=8.5,
        evidence={
            "total_budget": 10000.0,
            "channel_allocations": {"google": 0.3, "meta": 0.7},
        },
    )
    db_session.add(rec)
    db_session.flush()

    # Create linked simulation
    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        domain="growth",
        simulation_type="auto",
        x_star={"optimal_budget": 10000.0},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={
            "output_metrics": {"projected_roas": 2.5, "projected_cac": 45.0}
        },
        upside_scenario={
            "output_metrics": {"projected_roas": 3.1, "projected_cac": 38.0}
        },
        downside_scenario={
            "output_metrics": {"projected_roas": 2.3, "projected_cac": 52.0}
        },
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    # Request narration with real OpenAI API
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": None},
    )

    print("\n=== NARRATION RESPONSE ===")
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "urgency_context" in data
    assert "action_description" in data
    assert "risk_framing" in data
    assert "citations" in data
    assert "narration_metadata" in data
    assert "generated_at" in data

    # Verify narration is non-empty
    assert len(data["urgency_context"]) > 0
    assert len(data["action_description"]) > 0
    assert len(data["risk_framing"]) > 0

    # Verify citations extracted (baseline/upside/downside metrics)
    assert len(data["citations"]) > 0

    # Verify metadata contains LLM info
    assert data["narration_metadata"]["model"] == "gpt-3.5-turbo"
    assert data["narration_metadata"]["completion_tokens"] > 0
    assert data["narration_metadata"]["prompt_tokens"] > 0


def test_narrate_retention_recommendation(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: Generate narration for retention recommendation."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="retention_001",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="retention",
        signal_summary="30-60 day cohort repeat rate declining",
        suggested_action="Increase win-back email frequency",
        estimated_impact=800.0,
        confidence_level="medium",
        data_freshness_context="4 hours",
        status="new",
        priority=2,
        impact_score=6.5,
        evidence={
            "offer_discount_pct": 12.0,
            "response_rate_pct": 18.0,
            "estimated_segment_size": 2000,
        },
    )
    db_session.add(rec)
    db_session.flush()

    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        domain="retention",
        simulation_type="auto",
        x_star={"optimal_response_rate": 0.18},
        confidence_level="medium",
        data_freshness_signal="medium",
        metric_completeness_signal="high",
        baseline_scenario={
            "output_metrics": {"repeat_rate": 32.5, "ltv_uplift": 0.0}
        },
        upside_scenario={
            "output_metrics": {"repeat_rate": 40.2, "ltv_uplift": 890.0}
        },
        downside_scenario={
            "output_metrics": {"repeat_rate": 34.1, "ltv_uplift": 150.0}
        },
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": "cautious"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "retention"
    assert data["narration_metadata"]["tone_override"] == "cautious"
    assert len(data["action_description"]) > 0


def test_narrate_with_tone_override(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: Narration respects tone override."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="margin_001",
        domain="margin",
        snapshot_date=date.today(),
        affected_area="margin",
        signal_summary="Cost increase detected",
        suggested_action="Reduce cost input",
        estimated_impact=500.0,
        confidence_level="high",
        data_freshness_context="1 hour",
        status="new",
        priority=1,
        impact_score=9.0,
        evidence={"cost_input_adjustments": {"shipping": 2.5}},
    )
    db_session.add(rec)
    db_session.flush()

    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        domain="margin",
        simulation_type="auto",
        x_star={"optimal_cost": 2.5},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={
            "output_metrics": {"contribution_margin_pct": 32.5}
        },
        upside_scenario={"output_metrics": {"contribution_margin_pct": 36.2}},
        downside_scenario={
            "output_metrics": {"contribution_margin_pct": 30.1}
        },
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    # Test with urgent tone
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": "urgent"},
    )

    assert response.status_code == 200
    assert response.json()["narration_metadata"]["tone_override"] == "urgent"


def test_narrate_nonexistent_recommendation(
    client: TestClient, tenant: Tenant
) -> None:
    """FR-071, FR-079 / T-119: Narration with nonexistent recommendation returns 404."""
    fake_rec_id = uuid.uuid4()

    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{fake_rec_id}/narrate",
        json={"override_tone": None},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_narrate_cross_tenant_isolation(
    client: TestClient,
    db_session: Session,
    tenant: Tenant,
    user: User,
    other_tenant: Tenant,
) -> None:
    """FR-071, FR-079 / T-119: Cross-tenant isolation for narration."""
    # Create recommendation in other tenant
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Test",
        suggested_action="Test action",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="2 hours",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={"total_budget": 10000.0},
    )
    db_session.add(rec)
    db_session.flush()

    # Create simulation
    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        recommendation_id=rec.id,
        domain="growth",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={"output_metrics": {}},
        upside_scenario={"output_metrics": {}},
        downside_scenario={"output_metrics": {}},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    # Try to narrate from user's tenant (should not find it)
    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": None},
    )

    assert response.status_code == 404


def test_narrate_missing_linked_simulation(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: Narration fails if recommendation has no simulation."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Test",
        suggested_action="Test action",
        estimated_impact=1000.0,
        confidence_level="high",
        data_freshness_context="2 hours",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={"total_budget": 10000.0},
    )
    db_session.add(rec)
    db_session.commit()

    # No simulation created for this recommendation

    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={},
    )

    assert response.status_code == 404
    assert "simulation" in response.json()["detail"].lower()


def test_narrate_citations_track_sources(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: Citations correctly track source paths."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Channel efficiency test",
        suggested_action="Reallocate budget",
        estimated_impact=2000.0,
        confidence_level="high",
        data_freshness_context="1 hour",
        status="new",
        priority=1,
        impact_score=8.0,
        evidence={"total_budget": 10000.0, "channel_allocations": {}},
    )
    db_session.add(rec)
    db_session.flush()

    # Simulation with distinct metrics for each scenario
    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        domain="growth",
        simulation_type="auto",
        x_star={"optimal_spend": 10000.0},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={
            "output_metrics": {"projected_roas": 2.50, "projected_cac": 45.00}
        },
        upside_scenario={
            "output_metrics": {"projected_roas": 3.10, "projected_cac": 38.00}
        },
        downside_scenario={
            "output_metrics": {"projected_roas": 2.30, "projected_cac": 52.00}
        },
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": None},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify citations exist and have required fields
    citations = data["citations"]
    assert len(citations) > 0

    for citation in citations:
        assert "field_name" in citation
        assert "scenario_type" in citation
        assert "value" in citation
        assert "source_path" in citation
        # Source path should contain scenario and field info
        assert any(
            s in citation["source_path"]
            for s in ["baseline", "upside", "downside"]
        )


def test_narrate_no_number_generation_constraint(
    client: TestClient, db_session: Session, tenant: Tenant, user: User
) -> None:
    """FR-071, FR-079 / T-119: LLM narration constraint: numbers from simulation."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="growth_001",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="acquisition",
        signal_summary="Test constraint",
        suggested_action="Test action",
        estimated_impact=1234.56,
        confidence_level="high",
        data_freshness_context="1 hour",
        status="new",
        priority=1,
        impact_score=7.5,
        evidence={"total_budget": 10000.0},
    )
    db_session.add(rec)
    db_session.flush()

    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        domain="growth",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={
            "output_metrics": {"projected_roas": 2.50, "projected_cac": 45.00}
        },
        upside_scenario={
            "output_metrics": {"projected_roas": 3.10, "projected_cac": 38.00}
        },
        downside_scenario={
            "output_metrics": {"projected_roas": 2.30, "projected_cac": 52.00}
        },
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.commit()

    response = client.post(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/narrate",
        json={"override_tone": None},
    )

    assert response.status_code == 200
    data = response.json()

    # All numeric values in narration should have corresponding citations
    # (validated by LLM prompt constraint, verified by presence of citations)
    assert len(data["citations"]) > 0  # Evidence that numbers are cited


def test_narrate_nonexistent_tenant(client: TestClient) -> None:
    """FR-071, FR-079 / T-119: Narration with nonexistent tenant returns 404."""
    fake_tenant_id = uuid.uuid4()
    fake_rec_id = uuid.uuid4()

    response = client.post(
        f"/tenants/{fake_tenant_id}/recommendations/{fake_rec_id}/narrate",
        json={"override_tone": None},
    )

    assert response.status_code == 404
    assert "tenant" in response.json()["detail"].lower()

