"""Tests for D5 - Platform metrics dashboard endpoint."""

from __future__ import annotations

from typing import Any

import jwt
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


def test_get_platform_metrics_structure(client: Any) -> None:
    """GET /admin/platform/metrics returns expected structure."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify top-level structure
    assert "tenant_metrics" in data
    assert "user_metrics" in data
    assert "subscription_metrics" in data
    assert "feature_flag_metrics" in data
    assert "integration_metrics" in data
    assert "generated_at" in data
    assert "platform_version" in data

    # Verify tenant_metrics structure
    assert "total_tenants" in data["tenant_metrics"]
    assert "active_tenants" in data["tenant_metrics"]
    assert "suspended_tenants" in data["tenant_metrics"]
    assert "new_tenants_last_30_days" in data["tenant_metrics"]
    assert "new_tenants_last_7_days" in data["tenant_metrics"]

    # Verify user_metrics structure
    assert "total_users" in data["user_metrics"]
    assert "active_users" in data["user_metrics"]
    assert "users_per_tenant_avg" in data["user_metrics"]
    assert "new_users_last_30_days" in data["user_metrics"]
    assert "new_users_last_7_days" in data["user_metrics"]

    # Verify subscription_metrics structure
    assert "starter_count" in data["subscription_metrics"]
    assert "professional_count" in data["subscription_metrics"]
    assert "enterprise_count" in data["subscription_metrics"]
    assert "total_seats_allocated" in data["subscription_metrics"]
    assert "total_seats_used" in data["subscription_metrics"]

    # Verify feature_flag_metrics structure
    assert "total_flags" in data["feature_flag_metrics"]
    assert "total_overrides" in data["feature_flag_metrics"]
    assert "most_enabled_features" in data["feature_flag_metrics"]
    assert "most_disabled_features" in data["feature_flag_metrics"]

    # Verify integration_metrics structure
    assert "total_connectors" in data["integration_metrics"]
    assert "active_connectors" in data["integration_metrics"]
    assert "connectors_with_errors" in data["integration_metrics"]
    assert "total_sync_jobs_last_24h" in data["integration_metrics"]
    assert "failed_sync_jobs_last_24h" in data["integration_metrics"]


def test_platform_metrics_includes_fixture_tenant(client: Any) -> None:
    """Platform metrics include fixture tenant from conftest.py."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # conftest.py creates at least 1 tenant
    assert data["tenant_metrics"]["total_tenants"] >= 1
    assert data["tenant_metrics"]["active_tenants"] >= 1

    # conftest.py creates at least 1 user
    assert data["user_metrics"]["total_users"] >= 1


def test_platform_metrics_tenant_count_increases(client: Any) -> None:
    """Creating tenants increases total_tenants count."""
    token = _make_super_admin_token()

    # Get initial count
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_count = response.json()["tenant_metrics"]["total_tenants"]

    # Create 2 new tenants
    for i in range(2):
        client.post(
            "/tenants",
            json={"name": f"Metrics Test {i}", "slug": f"metrics-test-{i}"},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Check count increased by 2
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    new_count = response.json()["tenant_metrics"]["total_tenants"]

    assert new_count == initial_count + 2


def test_platform_metrics_subscription_distribution(client: Any) -> None:
    """Subscription metrics show plan distribution."""
    token = _make_super_admin_token()

    # Get initial counts
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_starter = response.json()["subscription_metrics"]["starter_count"]

    # Create a tenant (defaults to starter plan)
    client.post(
        "/tenants",
        json={"name": "Plan Test", "slug": "plan-test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check starter count increased
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    new_starter = response.json()["subscription_metrics"]["starter_count"]

    assert new_starter == initial_starter + 1


def test_platform_metrics_suspended_tenant_count(client: Any) -> None:
    """Suspended tenants are counted correctly."""
    token = _make_super_admin_token()

    # Get initial counts
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_active = response.json()["tenant_metrics"]["active_tenants"]
    initial_suspended = response.json()["tenant_metrics"]["suspended_tenants"]

    # Create and suspend a tenant
    create_resp = client.post(
        "/tenants",
        json={"name": "Suspend Test", "slug": "suspend-test-metrics"},
        headers={"Authorization": f"Bearer {token}"},
    )
    tenant_id = create_resp.json()["id"]

    client.patch(
        f"/admin/tenants/{tenant_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check counts updated
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    # Total active should be same (new tenant is suspended)
    assert data["tenant_metrics"]["active_tenants"] == initial_active
    # Suspended increased by 1
    assert data["tenant_metrics"]["suspended_tenants"] == initial_suspended + 1


def test_platform_metrics_users_per_tenant_avg(client: Any) -> None:
    """Users per tenant average is calculated correctly."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = response.json()
    total_tenants = data["tenant_metrics"]["total_tenants"]
    total_users = data["user_metrics"]["total_users"]
    avg = data["user_metrics"]["users_per_tenant_avg"]

    # Calculate expected average
    expected_avg = round(float(total_users) / float(total_tenants), 2)

    assert avg == expected_avg


def test_platform_metrics_feature_flags(client: Any) -> None:
    """Feature flag metrics show total flags and overrides."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = response.json()

    # conftest.py creates simulations and custom_segments flags
    assert data["feature_flag_metrics"]["total_flags"] >= 2

    # Most enabled/disabled features are lists
    assert isinstance(data["feature_flag_metrics"]["most_enabled_features"], list)
    assert isinstance(data["feature_flag_metrics"]["most_disabled_features"], list)


def test_platform_metrics_requires_super_admin(client: Any) -> None:
    """GET /admin/platform/metrics rejects non-super-admin."""
    token = _make_token("regular@user.com")

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_platform_metrics_version_present(client: Any) -> None:
    """Platform version is included in response."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "platform_version" in data
    assert isinstance(data["platform_version"], str)
    assert len(data["platform_version"]) > 0


def test_platform_metrics_generated_at_timestamp(client: Any) -> None:
    """Generated timestamp is included in response."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "generated_at" in data
    # Should be ISO format datetime string
    assert isinstance(data["generated_at"], str)
    assert "T" in data["generated_at"]  # ISO format contains 'T'


def test_platform_metrics_new_tenant_tracking(client: Any) -> None:
    """New tenant counts track last 7 and 30 days."""
    token = _make_super_admin_token()

    # Get initial counts
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_7d = response.json()["tenant_metrics"]["new_tenants_last_7_days"]
    initial_30d = response.json()["tenant_metrics"]["new_tenants_last_30_days"]

    # Create a new tenant
    client.post(
        "/tenants",
        json={"name": "New Tenant", "slug": "new-tenant-tracking"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Check counts increased
    response = client.get(
        "/admin/platform/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()

    assert data["tenant_metrics"]["new_tenants_last_7_days"] == initial_7d + 1
    assert data["tenant_metrics"]["new_tenants_last_30_days"] == initial_30d + 1
