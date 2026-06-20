"""Tests for E3 - Connector health + workspace-health panel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from backend.app.db.models import ConnectorIntegration
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_token(email: str) -> str:
    """Create JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def test_connector_has_health_status_field(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """ConnectorIntegration model includes health_status field."""
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        health_status="healthy",
    )
    db_session.add(connector)
    db_session.commit()

    fetched = db_session.get(ConnectorIntegration, connector.id)
    assert fetched is not None
    assert fetched.health_status == "healthy"


def test_connector_health_status_defaults_to_unknown(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """ConnectorIntegration health_status defaults to unknown."""
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="disconnected",
    )
    db_session.add(connector)
    db_session.commit()

    fetched = db_session.get(ConnectorIntegration, connector.id)
    assert fetched is not None
    assert fetched.health_status == "unknown"


def test_workspace_health_with_no_connectors(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health returns healthy when no connectors exist."""
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["overall_health_status"] == "healthy"
    assert data["total_connectors"] == 0
    assert data["healthy_count"] == 0
    assert data["degraded_count"] == 0
    assert data["critical_count"] == 0
    assert data["unknown_count"] == 0
    assert len(data["connectors"]) == 0


def test_workspace_health_with_all_healthy_connectors(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health returns healthy when all connectors healthy."""
    now = datetime.now(UTC)

    # Create 3 healthy connectors (synced within 1 hour = high freshness)
    shopify = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=30),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    meta = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=20),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    google_ads = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=10),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    db_session.add_all([shopify, meta, google_ads])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["overall_health_status"] == "healthy"
    assert data["total_connectors"] == 3
    assert data["healthy_count"] == 3
    assert data["degraded_count"] == 0
    assert data["critical_count"] == 0
    assert len(data["connectors"]) == 3

    # Verify all connectors marked healthy
    sources = {c["source"] for c in data["connectors"]}
    assert sources == {"shopify", "meta", "google_ads"}
    for connector_data in data["connectors"]:
        assert connector_data["health_status"] == "healthy"


def test_workspace_health_with_degraded_connector(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health shows degraded when sync queued."""
    now = datetime.now(UTC)

    healthy = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=30),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    # Degraded: sync requested but not completed (medium freshness 3 hours)
    degraded = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(hours=3),
        last_sync_requested_at=now - timedelta(minutes=5),
    )
    db_session.add_all([healthy, degraded])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["overall_health_status"] == "degraded"
    assert data["total_connectors"] == 2
    assert data["healthy_count"] == 1
    assert data["degraded_count"] == 1
    assert data["critical_count"] == 0

    # Find degraded connector in response
    degraded_data = [c for c in data["connectors"] if c["source"] == "meta"][0]
    assert degraded_data["health_status"] == "degraded"
    assert degraded_data["sync_progress"] == "sync_queued"


def test_workspace_health_with_critical_connector(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health shows critical when connector has errors."""
    now = datetime.now(UTC)

    healthy = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=30),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    # Critical: has error message
    critical = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(hours=2),
        error_message="OAuth token expired",
    )
    db_session.add_all([healthy, critical])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["overall_health_status"] == "critical"
    assert data["total_connectors"] == 2
    assert data["healthy_count"] == 1
    assert data["degraded_count"] == 0
    assert data["critical_count"] == 1

    # Find critical connector
    critical_data = [c for c in data["connectors"] if c["source"] == "meta"][0]
    assert critical_data["health_status"] == "critical"
    assert critical_data["error_message"] == "OAuth token expired"


def test_workspace_health_with_disconnected_connector(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health shows critical for disconnected connectors."""
    disconnected = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="disconnected",
    )
    db_session.add(disconnected)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["overall_health_status"] == "critical"
    assert data["total_connectors"] == 1
    assert data["critical_count"] == 1

    assert data["connectors"][0]["health_status"] == "critical"
    assert data["connectors"][0]["status"] == "disconnected"


def test_workspace_health_with_stale_data(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health shows critical for very stale data (>7d)."""
    now = datetime.now(UTC)

    # Stale: last synced over 7 days ago
    stale = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(days=10),
        last_sync_requested_at=now - timedelta(days=11),
    )
    db_session.add(stale)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["overall_health_status"] == "critical"
    assert data["critical_count"] == 1
    assert data["connectors"][0]["health_status"] == "critical"
    assert data["connectors"][0]["freshness_label"] == "low"


def test_workspace_health_includes_connector_summaries(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health includes all required fields in summaries."""
    now = datetime.now(UTC)

    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=30),
        last_sync_requested_at=now - timedelta(hours=1),
    )
    db_session.add(connector)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    summary = data["connectors"][0]
    assert "connector_id" in summary
    assert "source" in summary
    assert "health_status" in summary
    assert "status" in summary
    assert "last_synced_at" in summary
    assert "error_message" in summary
    assert "sync_progress" in summary
    assert "freshness_label" in summary

    assert summary["source"] == "shopify"
    assert summary["health_status"] == "healthy"
    assert summary["status"] == "connected"
    assert summary["sync_progress"] == "healthy"
    assert summary["freshness_label"] == "high"


def test_workspace_health_updates_connector_health_status_in_db(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /workspace-health updates health_status field in database."""
    now = datetime.now(UTC)

    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
        last_synced_at=now - timedelta(minutes=30),
        last_sync_requested_at=now - timedelta(hours=1),
        health_status="unknown",  # Start as unknown
    )
    db_session.add(connector)
    db_session.commit()
    connector_id = connector.id

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    # Verify health_status updated in DB
    db_session.expire_all()
    updated_connector = db_session.get(ConnectorIntegration, connector_id)
    assert updated_connector is not None
    assert updated_connector.health_status == "healthy"


def test_workspace_health_404_if_tenant_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """GET /workspace-health returns 404 for nonexistent tenant."""
    token = _make_token(user.email)
    fake_tenant_id = "00000000-0000-0000-0000-000000000999"
    response = client.get(
        f"/tenants/{fake_tenant_id}/workspace-health",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
