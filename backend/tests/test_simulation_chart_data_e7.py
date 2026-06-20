"""E7: Simulation chart-ready data tests.

Tests for GET /tenants/{tenant_id}/simulations/{simulation_id}/chart-data endpoint
that returns structured data optimized for frontend chart libraries.
"""

from typing import Any

import jwt
import pytest
from backend.app.db.models import Scenario, Simulation
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_token(email: str) -> str:
    """Create a test JWT token."""

    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "user"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


@pytest.fixture
def client() -> Any:
    """Test client fixture."""
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_get_chart_data_with_all_scenarios(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Chart data includes time_series, waterfall, and metric_deltas."""
    # Create simulation with all three scenarios
    sim = Simulation(
        tenant_id=tenant.id,
        domain="growth",
        simulation_type="auto",
        x_star={"optimal_spend": 10000},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={"roas": 2.5},
        upside_scenario={"roas": 3.0},
        downside_scenario={"roas": 2.0},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    # Create scenario records
    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={"spend": 10000},
        output_metrics={"roas": 2.5, "cac": 50.0, "revenue": 25000},
        impact_deltas={},
        confidence_score=85.0,
    )
    upside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="upside",
        input_assumptions={"spend": 12000},
        output_metrics={"roas": 3.0, "cac": 45.0, "revenue": 36000},
        impact_deltas={"roas": 0.5, "cac": -5.0, "revenue": 11000},
        confidence_score=75.0,
    )
    downside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="downside",
        input_assumptions={"spend": 8000},
        output_metrics={"roas": 2.0, "cac": 55.0, "revenue": 16000},
        impact_deltas={"roas": -0.5, "cac": 5.0, "revenue": -9000},
        confidence_score=80.0,
    )
    db_session.add_all([baseline_scenario, upside_scenario, downside_scenario])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Validate structure
    assert data["simulation_id"] == str(sim.id)
    assert data["domain"] == "growth"
    assert data["confidence_level"] == "high"
    assert data["data_freshness_signal"] == "high"

    # Validate time_series structure
    assert "time_series" in data
    assert "roas" in data["time_series"]
    assert "cac" in data["time_series"]
    assert "revenue" in data["time_series"]

    # Each metric should have 4 time periods (current + 3 projections)
    roas_series = data["time_series"]["roas"]
    assert len(roas_series) == 4
    assert roas_series[0]["period_label"] == "Current"
    assert roas_series[0]["baseline_value"] == 2.5
    assert roas_series[3]["period_label"] == "Period 3"

    # Validate waterfall structure
    assert "waterfall" in data
    assert "roas" in data["waterfall"]
    roas_waterfall = data["waterfall"]["roas"]
    assert len(roas_waterfall) == 3  # Baseline, Upside change, Downside change
    assert roas_waterfall[0]["segment_label"] == "Baseline"
    assert roas_waterfall[0]["segment_type"] == "start"
    assert roas_waterfall[1]["segment_label"] == "Upside Change"
    assert roas_waterfall[2]["segment_label"] == "Downside Change"

    # Validate metric_deltas structure
    assert "metric_deltas" in data
    assert len(data["metric_deltas"]) == 3  # roas, cac, revenue

    # Find ROAS delta
    roas_delta = next(m for m in data["metric_deltas"] if m["metric_name"] == "cac")
    assert roas_delta["baseline_value"] == 50.0
    assert roas_delta["upside_value"] == 45.0
    assert roas_delta["downside_value"] == 55.0
    assert roas_delta["upside_delta"] == -5.0
    assert roas_delta["downside_delta"] == 5.0


def test_get_chart_data_time_series_interpolation(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Time series shows gradual interpolation from baseline to target."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="growth",
        simulation_type="auto",
        x_star={},
        confidence_level="medium",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"revenue": 100000},
        impact_deltas={},
        confidence_score=80.0,
    )
    upside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="upside",
        input_assumptions={},
        output_metrics={"revenue": 130000},  # +30k from baseline
        impact_deltas={},
        confidence_score=70.0,
    )
    downside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="downside",
        input_assumptions={},
        output_metrics={"revenue": 70000},  # -30k from baseline
        impact_deltas={},
        confidence_score=75.0,
    )
    db_session.add_all([baseline_scenario, upside_scenario, downside_scenario])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    revenue_series = data["time_series"]["revenue"]
    assert len(revenue_series) == 4

    # Period 0: all scenarios start at baseline
    assert revenue_series[0]["baseline_value"] == 100000
    assert revenue_series[0]["upside_value"] == 100000
    assert revenue_series[0]["downside_value"] == 100000

    # Period 1: 33% progress
    assert revenue_series[1]["baseline_value"] == 100000
    assert 109000 < revenue_series[1]["upside_value"] < 111000  # ~110k (33% of 30k)
    assert 89000 < revenue_series[1]["downside_value"] < 91000  # ~90k

    # Period 3: 100% progress (final values)
    assert revenue_series[3]["baseline_value"] == 100000
    assert revenue_series[3]["upside_value"] == 130000
    assert revenue_series[3]["downside_value"] == 70000


def test_get_chart_data_waterfall_segment_types(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Waterfall segments correctly identify increase/decrease types."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="finance",
        simulation_type="manual",
        x_star={},
        confidence_level="high",
        data_freshness_signal="medium",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    # Margin: baseline 20%, upside 25% (increase), downside 15% (decrease)
    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"margin_pct": 20.0},
        impact_deltas={},
        confidence_score=90.0,
    )
    upside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="upside",
        input_assumptions={},
        output_metrics={"margin_pct": 25.0},
        impact_deltas={},
        confidence_score=85.0,
    )
    downside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="downside",
        input_assumptions={},
        output_metrics={"margin_pct": 15.0},
        impact_deltas={},
        confidence_score=88.0,
    )
    db_session.add_all([baseline_scenario, upside_scenario, downside_scenario])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    margin_waterfall = data["waterfall"]["margin_pct"]
    assert len(margin_waterfall) == 3

    # Baseline (start)
    assert margin_waterfall[0]["segment_type"] == "start"
    assert margin_waterfall[0]["value"] == 20.0

    # Upside change (+5) should be "increase"
    assert margin_waterfall[1]["segment_type"] == "increase"
    assert margin_waterfall[1]["value"] == 5.0
    assert margin_waterfall[1]["cumulative_value"] == 25.0

    # Downside change (-5) should be "decrease"
    assert margin_waterfall[2]["segment_type"] == "decrease"
    assert margin_waterfall[2]["value"] == -5.0
    assert margin_waterfall[2]["cumulative_value"] == 15.0


def test_get_chart_data_metric_delta_percentages(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Metric deltas include percentage changes."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="retention",
        simulation_type="auto",
        x_star={},
        confidence_level="medium",
        data_freshness_signal="high",
        metric_completeness_signal="medium",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    # Repeat rate: baseline 30%, upside 45% (+50%), downside 20% (-33.33%)
    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"repeat_rate_pct": 30.0},
        impact_deltas={},
        confidence_score=80.0,
    )
    upside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="upside",
        input_assumptions={},
        output_metrics={"repeat_rate_pct": 45.0},
        impact_deltas={},
        confidence_score=75.0,
    )
    downside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="downside",
        input_assumptions={},
        output_metrics={"repeat_rate_pct": 20.0},
        impact_deltas={},
        confidence_score=78.0,
    )
    db_session.add_all([baseline_scenario, upside_scenario, downside_scenario])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    repeat_delta = next(
        m for m in data["metric_deltas"] if m["metric_name"] == "repeat_rate_pct"
    )
    assert repeat_delta["baseline_value"] == 30.0
    assert repeat_delta["upside_value"] == 45.0
    assert repeat_delta["upside_delta"] == 15.0
    assert repeat_delta["upside_delta_pct"] == 50.0  # (15/30) * 100

    assert repeat_delta["downside_value"] == 20.0
    assert repeat_delta["downside_delta"] == -10.0
    assert abs(repeat_delta["downside_delta_pct"] - (-33.333)) < 0.01


def test_get_chart_data_missing_scenarios(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Chart data handles simulations with missing scenario types."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="operations",
        simulation_type="manual",
        x_star={},
        confidence_level="low",
        data_freshness_signal="low",
        metric_completeness_signal="low",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    # Only baseline scenario exists
    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"stockout_risk_pct": 10.0},
        impact_deltas={},
        confidence_score=60.0,
    )
    db_session.add(baseline_scenario)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Should still return valid structure
    assert "time_series" in data
    assert "waterfall" in data
    assert "metric_deltas" in data

    # Metric delta should have None for missing scenarios
    stockout_delta = next(
        m for m in data["metric_deltas"] if m["metric_name"] == "stockout_risk_pct"
    )
    assert stockout_delta["baseline_value"] == 10.0
    assert stockout_delta["upside_value"] is None
    assert stockout_delta["downside_value"] is None


def test_get_chart_data_404_simulation_not_found(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Returns 404 if simulation not found."""
    import uuid

    fake_sim_id = uuid.uuid4()
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{fake_sim_id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_chart_data_404_tenant_not_found(
    client: Any,
    db_session: Any,
    user: Any,
) -> None:
    """E7: Returns 404 if tenant not found."""
    import uuid

    fake_tenant_id = uuid.uuid4()
    fake_sim_id = uuid.uuid4()
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{fake_tenant_id}/simulations/{fake_sim_id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "tenant not found" in response.json()["detail"].lower()


def test_get_chart_data_tenant_isolation(
    client: Any,
    db_session: Any,
    tenant: Any,
    other_tenant: Any,
    user: Any,
    other_user: Any,
) -> None:
    """E7: Tenant isolation enforced - cannot access other tenant's simulations."""
    # Create simulation for tenant
    sim = Simulation(
        tenant_id=tenant.id,
        domain="executive",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"blended_margin": 18.0},
        impact_deltas={},
        confidence_score=85.0,
    )
    db_session.add(baseline_scenario)
    db_session.commit()

    # Try to access with other_tenant's token
    token = _make_token(other_user.email)
    response = client.get(
        f"/tenants/{other_tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should return 403 (RBAC blocks cross-tenant access)
    assert response.status_code == 403


def test_get_chart_data_multiple_metrics(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Chart data includes all metrics from all scenarios."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="growth",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    # Each scenario has different metrics
    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={
            "roas": 2.5,
            "cac": 50.0,
            "revenue": 100000,
            "margin_pct": 20.0,
        },
        impact_deltas={},
        confidence_score=85.0,
    )
    upside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="upside",
        input_assumptions={},
        output_metrics={
            "roas": 3.0,
            "cac": 45.0,
            "revenue": 120000,
            "margin_pct": 22.0,
            "new_customers": 2400,  # Extra metric only in upside
        },
        impact_deltas={},
        confidence_score=80.0,
    )
    downside_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="downside",
        input_assumptions={},
        output_metrics={
            "roas": 2.0,
            "cac": 55.0,
            "revenue": 80000,
            "margin_pct": 18.0,
        },
        impact_deltas={},
        confidence_score=82.0,
    )
    db_session.add_all([baseline_scenario, upside_scenario, downside_scenario])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # All metrics should be present (union of all scenario metrics)
    assert "cac" in data["time_series"]
    assert "margin_pct" in data["time_series"]
    assert "new_customers" in data["time_series"]
    assert "revenue" in data["time_series"]
    assert "roas" in data["time_series"]

    # All metrics should have deltas
    metric_names = {m["metric_name"] for m in data["metric_deltas"]}
    assert metric_names == {"cac", "margin_pct", "new_customers", "revenue", "roas"}


def test_get_chart_data_confidence_and_freshness_signals(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E7: Chart data includes confidence and freshness signals."""
    sim = Simulation(
        tenant_id=tenant.id,
        domain="finance",
        simulation_type="manual",
        x_star={},
        confidence_level="low",
        data_freshness_signal="medium",
        metric_completeness_signal="low",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
    )
    db_session.add(sim)
    db_session.flush()

    baseline_scenario = Scenario(
        simulation_id=sim.id,
        scenario_type="baseline",
        input_assumptions={},
        output_metrics={"cost_per_unit": 15.0},
        impact_deltas={},
        confidence_score=50.0,
    )
    db_session.add(baseline_scenario)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/simulations/{sim.id}/chart-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Signals should be included in response
    assert data["confidence_level"] == "low"
    assert data["data_freshness_signal"] == "medium"
