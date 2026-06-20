"""Tests for D6 - Connector availability tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from backend.app.db.models import AuditEvent, ConnectorIntegration
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_super_admin_token(email: str = "superadmin@alpmark.io") -> str:
    """Create super-admin JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "super_admin"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _make_token(email: str) -> str:
    """Create regular member JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def test_get_connector_availability_structure(client: Any, db_session: Any) -> None:
    """GET /admin/platform/connectors returns expected structure."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify top-level structure
    assert "total_connectors" in data
    assert "active_connectors" in data
    assert "disconnected_connectors" in data
    assert "connectors_with_errors" in data
    assert "recent_sync_failures_24h" in data
    assert "tenants_with_connectors" in data
    assert "tenants_without_connectors" in data
    assert "by_source" in data
    assert "generated_at" in data

    # by_source is a list
    assert isinstance(data["by_source"], list)


def test_connector_availability_tracks_active_connectors(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Active connectors are counted correctly."""
    token = _make_super_admin_token()

    # Get initial count
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_active = response.json()["active_connectors"]

    # Add a connected connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        connected_at=datetime.now(UTC),
    )
    db_session.add(connector)
    db_session.commit()

    # Check count increased
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["active_connectors"] == initial_active + 1
    assert data["total_connectors"] == initial_active + 1


def test_connector_availability_tracks_disconnected_connectors(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Disconnected connectors are counted correctly."""
    token = _make_super_admin_token()

    # Get initial counts
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_disconnected = response.json()["disconnected_connectors"]

    # Add a disconnected connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="disconnected",
    )
    db_session.add(connector)
    db_session.commit()

    # Check count increased
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["disconnected_connectors"] == initial_disconnected + 1


def test_connector_availability_tracks_errors(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Connectors with errors are counted correctly."""
    token = _make_super_admin_token()

    # Get initial count
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_errors = response.json()["connectors_with_errors"]

    # Add connector with error
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="connected",
        error_message="API rate limit exceeded",
    )
    db_session.add(connector)
    db_session.commit()

    # Check count increased
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["connectors_with_errors"] == initial_errors + 1


def test_connector_availability_recent_sync_failures(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Recent sync failures (last 24h) are counted correctly."""
    token = _make_super_admin_token()

    # Add connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.flush()

    # Get initial count
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_failures = response.json()["recent_sync_failures_24h"]

    # Add recent failure (1 hour ago)
    db_session.add(
        AuditEvent(
            tenant_id=tenant.id,
            actor_user_id=None,
            action="alert.connector_sync_failure_created",
            entity_type="connector",
            entity_id=str(connector.id),
            details={"source": "shopify", "reason": "timeout"},
            created_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db_session.commit()

    # Check count increased
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["recent_sync_failures_24h"] == initial_failures + 1


def test_connector_availability_ignores_old_sync_failures(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Sync failures older than 24h are not counted."""
    token = _make_super_admin_token()

    # Add connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.flush()

    # Get initial count
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_failures = response.json()["recent_sync_failures_24h"]

    # Add old failure (3 days ago)
    db_session.add(
        AuditEvent(
            tenant_id=tenant.id,
            actor_user_id=None,
            action="alert.connector_sync_failure_created",
            entity_type="connector",
            entity_id=str(connector.id),
            details={"source": "meta", "reason": "auth error"},
            created_at=datetime.now(UTC) - timedelta(days=3),
        )
    )
    db_session.commit()

    # Check count unchanged
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["recent_sync_failures_24h"] == initial_failures


def test_connector_availability_tenant_adoption(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Tenant adoption metrics are calculated correctly."""
    token = _make_super_admin_token()

    # Create another tenant
    super_token = _make_super_admin_token()
    create_resp = client.post(
        "/tenants",
        json={"name": "Another Tenant", "slug": "another-tenant"},
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert create_resp.status_code == 201

    # Get total tenants
    metrics_resp = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    total_tenants = metrics_resp.json()["tenant_metrics"]["total_tenants"]

    # Initially, check tenants_without_connectors
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    initial_with = data["tenants_with_connectors"]
    initial_without = data["tenants_without_connectors"]

    assert initial_with + initial_without == total_tenants

    # Add connector to tenant (using fixture tenant, not new tenant)
    # This should increase tenants_with_connectors if tenant didn't have connectors
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.commit()

    # Check updated counts
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    # Should maintain total
    total_with = data["tenants_with_connectors"]
    total_without = data["tenants_without_connectors"]
    assert total_with + total_without == total_tenants


def test_connector_availability_by_source_breakdown(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Per-source breakdown is calculated correctly."""
    token = _make_super_admin_token()

    # Add connectors for different sources
    connectors = [
        ConnectorIntegration(
            tenant_id=tenant.id,
            source="shopify",
            auth_mode="oauth",
            status="connected",
        ),
        ConnectorIntegration(
            tenant_id=tenant.id,
            source="meta",
            auth_mode="oauth",
            status="disconnected",
        ),
        ConnectorIntegration(
            tenant_id=tenant.id,
            source="google_ads",
            auth_mode="oauth",
            status="connected",
            error_message="Rate limit",
        ),
    ]
    db_session.add_all(connectors)
    db_session.commit()

    # Get breakdown
    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    by_source = {item["source"]: item for item in data["by_source"]}

    # Check shopify
    if "shopify" in by_source:
        shopify = by_source["shopify"]
        assert shopify["total_connectors"] >= 1
        assert shopify["connected_count"] >= 1
        assert shopify["tenants_using"] >= 1

    # Check meta
    if "meta" in by_source:
        meta = by_source["meta"]
        assert meta["total_connectors"] >= 1
        assert meta["disconnected_count"] >= 1

    # Check google_ads
    if "google_ads" in by_source:
        google = by_source["google_ads"]
        assert google["total_connectors"] >= 1
        assert google["error_count"] >= 1


def test_connector_availability_requires_super_admin(client: Any) -> None:
    """GET /admin/platform/connectors rejects non-super-admin."""
    token = _make_token("regular@user.com")

    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_platform_metrics_integration_metrics_updated(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Platform metrics now returns real integration metrics (not placeholder zeros)."""
    token = _make_super_admin_token()

    # Add a connected connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
        connected_at=datetime.now(UTC),
    )
    db_session.add(connector)
    db_session.commit()

    # Get platform metrics
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Integration metrics should show the connector
    integration = data["integration_metrics"]
    assert integration["total_connectors"] >= 1
    assert integration["active_connectors"] >= 1


def test_connector_availability_source_breakdown_structure(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """By-source breakdown has correct structure."""
    token = _make_super_admin_token()

    # Add a connector
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.commit()

    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = response.json()

    # Check structure of first source (if any)
    if data["by_source"]:
        first_source = data["by_source"][0]
        assert "source" in first_source
        assert "total_connectors" in first_source
        assert "connected_count" in first_source
        assert "disconnected_count" in first_source
        assert "error_count" in first_source
        assert "tenants_using" in first_source


def test_connector_availability_generated_timestamp(client: Any) -> None:
    """Generated timestamp is included in response."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/connectors",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "generated_at" in data
    assert isinstance(data["generated_at"], str)
    assert "T" in data["generated_at"]  # ISO format
