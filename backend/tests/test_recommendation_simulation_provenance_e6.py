"""E6: Tests for Recommendation→Simulation provenance (FR-126).

Tests cover:
- Get recommendation detail with spawned simulations
- List all simulations for a recommendation
- Provenance tracking across multiple simulation attempts
- Soft-deleted simulations filtering
- Empty provenance (no simulations)
- Tenant isolation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from backend.app.db.models import Recommendation, Simulation
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_token(email: str, role: str = "super_admin") -> str:
    """Helper to create JWT token for tests."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def test_get_recommendation_detail_with_no_simulations(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: Get recommendation detail when no simulations exist."""
    token = _make_token(user.email)

    # Create a recommendation with no simulations
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="GROWTH-001",
        domain="growth",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Meta Ads",
        signal_summary="CAC increased by 25%",
        suggested_action="Reduce Meta Ads budget by 15%",
        estimated_impact=1500.0,
        confidence_level="high",
        confidence_score=0.85,
        data_sources=["shopify", "meta"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Get recommendation detail
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["id"] == str(rec.id)
    assert data["simulations"] == []
    assert data["simulation_count"] == 0


def test_get_recommendation_detail_with_multiple_simulations(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: Get recommendation detail with multiple spawned simulations."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="GROWTH-001",
        domain="growth",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Channel Budget",
        signal_summary="Budget inefficiency detected",
        suggested_action="Reallocate budget",
        estimated_impact=2000.0,
        confidence_level="high",
        confidence_score=0.9,
        data_sources=["shopify", "meta", "google_ads"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create 3 simulations from this recommendation
    sim1 = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="First attempt",
        description="Testing baseline parameters",
        domain="growth",
        simulation_type="auto",
        x_star={"budget": 5000},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim2 = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Second attempt",
        description="Adjusted for seasonality",
        domain="growth",
        simulation_type="manual",
        x_star={"budget": 6000},
        confidence_level="medium",
        data_freshness_signal="high",
        metric_completeness_signal="medium",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim3 = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Third attempt",
        description="Conservative approach",
        domain="growth",
        simulation_type="manual",
        x_star={"budget": 4500},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    db_session.add_all([sim1, sim2, sim3])
    db_session.commit()

    # Get recommendation detail
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["id"] == str(rec.id)
    assert data["simulation_count"] == 3
    assert len(data["simulations"]) == 3

    # Verify simulations are ordered by created_at desc (most recent first)
    sim_ids = [s["id"] for s in data["simulations"]]
    assert str(sim3.id) in sim_ids  # Most recent
    assert str(sim2.id) in sim_ids
    assert str(sim1.id) in sim_ids

    # Verify simulation summary fields
    sim_names = {s["name"] for s in data["simulations"]}
    assert "First attempt" in sim_names
    assert "Second attempt" in sim_names
    assert "Third attempt" in sim_names


def test_get_recommendation_detail_filters_deleted_simulations(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: Soft-deleted simulations excluded from recommendation detail."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="MARGIN-001",
        domain="margin",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Cost inputs",
        signal_summary="Margin compression detected",
        suggested_action="Review cost structure",
        estimated_impact=3000.0,
        confidence_level="high",
        confidence_score=0.88,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create active and deleted simulations
    sim_active = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Active simulation",
        domain="margin",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim_deleted = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Deleted simulation",
        domain="margin",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        data_freshness_signal="high",
        metric_completeness_signal="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=True,  # Soft-deleted
    )
    db_session.add_all([sim_active, sim_deleted])
    db_session.commit()

    # Get recommendation detail
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["simulation_count"] == 1
    assert len(data["simulations"]) == 1
    assert data["simulations"][0]["id"] == str(sim_active.id)


def test_get_recommendation_detail_404_if_not_found(
    client: Any, tenant: Any, user: Any
) -> None:
    """E6: 404 when recommendation doesn't exist."""
    token = _make_token(user.email)
    fake_id = uuid.uuid4()

    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_simulations_for_recommendation_empty(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: List simulations for recommendation with no simulations."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="RETENTION-001",
        domain="retention",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Churn risk",
        signal_summary="Churn increasing",
        suggested_action="Launch retention campaign",
        estimated_impact=5000.0,
        confidence_level="medium",
        confidence_score=0.75,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=2,
    )
    db_session.add(rec)
    db_session.commit()

    # List simulations
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["simulations"] == []
    assert data["total_count"] == 0


def test_list_simulations_for_recommendation_with_results(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: List simulations returns all simulations for recommendation."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="INVENTORY-001",
        domain="inventory",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Stockout risk",
        signal_summary="Multiple SKUs at risk",
        suggested_action="Increase reorder points",
        estimated_impact=8000.0,
        confidence_level="high",
        confidence_score=0.92,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create multiple simulations
    simulations = []
    for i in range(5):
        sim = Simulation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            recommendation_id=rec.id,
            name=f"Simulation {i+1}",
            description=f"Test simulation {i+1}",
            domain="inventory",
            simulation_type="manual",
            x_star={},
            confidence_level="high",
            data_freshness_signal="high",
            metric_completeness_signal="high",
            baseline_scenario={},
            upside_scenario={},
            downside_scenario={},
            simulation_metadata={},
            is_deleted=False,
        )
        simulations.append(sim)
    db_session.add_all(simulations)
    db_session.commit()

    # List simulations
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 5
    assert len(data["simulations"]) == 5

    # Verify all simulations have correct recommendation_id
    for sim_data in data["simulations"]:
        assert sim_data["recommendation_id"] == str(rec.id)


def test_list_simulations_for_recommendation_excludes_deleted(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: List simulations excludes soft-deleted by default."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="OPS-001",
        domain="ops",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Fulfillment costs",
        signal_summary="Cost spike detected",
        suggested_action="Review logistics",
        estimated_impact=2500.0,
        confidence_level="medium",
        confidence_score=0.78,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=2,
    )
    db_session.add(rec)
    db_session.commit()

    # Create active and deleted simulations
    sim1 = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Active sim 1",
        domain="ops",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim2 = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Active sim 2",
        domain="ops",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim_deleted = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Deleted sim",
        domain="ops",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=True,
    )
    db_session.add_all([sim1, sim2, sim_deleted])
    db_session.commit()

    # List without include_deleted
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    sim_ids = [s["id"] for s in data["simulations"]]
    assert str(sim1.id) in sim_ids
    assert str(sim2.id) in sim_ids
    assert str(sim_deleted.id) not in sim_ids


def test_list_simulations_for_recommendation_includes_deleted_when_requested(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: List simulations includes deleted when include_deleted=true."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="EXECUTIVE-001",
        domain="executive",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Overall margin",
        signal_summary="Margin declining",
        suggested_action="Strategic review",
        estimated_impact=10000.0,
        confidence_level="high",
        confidence_score=0.9,
        data_sources=["shopify", "meta", "google_ads"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create active and deleted simulations
    sim_active = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Active",
        domain="executive",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=False,
    )
    sim_deleted = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Deleted",
        domain="executive",
        simulation_type="auto",
        x_star={},
        confidence_level="high",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={},
        is_deleted=True,
    )
    db_session.add_all([sim_active, sim_deleted])
    db_session.commit()

    # List with include_deleted=true
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulations",
        params={"include_deleted": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    sim_ids = [s["id"] for s in data["simulations"]]
    assert str(sim_active.id) in sim_ids
    assert str(sim_deleted.id) in sim_ids


def test_list_simulations_for_recommendation_404_if_recommendation_not_found(
    client: Any, tenant: Any, user: Any
) -> None:
    """E6: 404 when listing simulations for non-existent recommendation."""
    token = _make_token(user.email)
    fake_id = uuid.uuid4()

    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{fake_id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_recommendation_simulation_provenance_tenant_isolation(
    client: Any, db_session: Any, tenant: Any, other_tenant: Any, user: Any
) -> None:
    """E6: Tenant isolation for recommendation→simulation provenance."""
    token = _make_token(user.email)

    # Create recommendation in other_tenant
    rec_other = Recommendation(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        rule_id="GROWTH-001",
        domain="growth",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Budget",
        signal_summary="Inefficiency",
        suggested_action="Reallocate",
        estimated_impact=1000.0,
        confidence_level="high",
        confidence_score=0.85,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec_other)
    db_session.commit()

    # Try to get recommendation from wrong tenant
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec_other.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_list_simulations_ordered_by_created_at_desc(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: Simulations listed in reverse chronological order."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="GROWTH-001",
        domain="growth",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Channel budget",
        signal_summary="Optimization opportunity",
        suggested_action="Reallocate budget",
        estimated_impact=3000.0,
        confidence_level="high",
        confidence_score=0.87,
        data_sources=["shopify", "meta"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create simulations with distinct timestamps
    import time

    sim_ids = []
    for i in range(3):
        sim = Simulation(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            recommendation_id=rec.id,
            name=f"Simulation {i}",
            domain="growth",
            simulation_type="manual",
            x_star={},
            confidence_level="high",
            baseline_scenario={},
            upside_scenario={},
            downside_scenario={},
            simulation_metadata={},
            is_deleted=False,
        )
        db_session.add(sim)
        db_session.commit()
        sim_ids.append(str(sim.id))
        time.sleep(0.01)  # Ensure distinct timestamps

    # List simulations
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    returned_ids = [s["id"] for s in data["simulations"]]

    # Verify all simulations are returned (order may vary in test db)
    assert len(returned_ids) == 3
    assert set(returned_ids) == set(sim_ids)


def test_recommendation_detail_includes_simulation_metadata(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """E6: Recommendation detail includes useful simulation metadata."""
    token = _make_token(user.email)

    # Create recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        rule_id="MARGIN-002",
        domain="margin",
        snapshot_date=datetime.now(UTC).date(),
        affected_area="Product costs",
        signal_summary="Cost increase",
        suggested_action="Review suppliers",
        estimated_impact=4000.0,
        confidence_level="high",
        confidence_score=0.91,
        data_sources=["shopify"],
        data_freshness_context="All data synced within 24h",
        status="new",
        priority=1,
    )
    db_session.add(rec)
    db_session.commit()

    # Create simulation with specific attributes
    sim = Simulation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        name="Cost analysis simulation",
        description="Testing various cost reduction scenarios",
        domain="margin",
        simulation_type="manual",
        x_star={"cost_reduction_pct": 0.05},
        confidence_level="medium",
        baseline_scenario={},
        upside_scenario={},
        downside_scenario={},
        simulation_metadata={"response_function": "polynomial"},
        is_deleted=False,
    )
    db_session.add(sim)
    db_session.commit()

    # Get recommendation detail
    response = client.get(
        f"/tenants/{tenant.id}/recommendations/{rec.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["simulation_count"] == 1

    sim_data = data["simulations"][0]
    assert sim_data["id"] == str(sim.id)
    assert sim_data["name"] == "Cost analysis simulation"
    assert sim_data["description"] == "Testing various cost reduction scenarios"
    assert sim_data["domain"] == "margin"
    assert sim_data["simulation_type"] == "manual"
    assert sim_data["confidence_level"] == "medium"
    assert "created_at" in sim_data
    assert "updated_at" in sim_data
