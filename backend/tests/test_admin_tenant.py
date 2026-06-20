"""Tests for D4 - Super-admin tenant management endpoints."""

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


def test_list_all_tenants_empty(client: Any) -> None:
    """GET /admin/tenants returns list including fixture tenant."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # conftest.py creates 1 fixture tenant
    assert data["total"] >= 1
    assert data["page"] == 1
    assert data["page_size"] == 50


def test_list_all_tenants_shows_multiple(client: Any) -> None:
    """GET /admin/tenants lists all tenants with user counts."""
    token = _make_super_admin_token()

    # Get initial count (includes fixture tenant)
    response = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_count = response.json()["total"]

    # Create 3 tenants
    for i in range(3):
        response = client.post(
            "/tenants",
            json={"name": f"Tenant {i}", "slug": f"tenant-{i}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201

    # List all tenants
    response = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == initial_count + 3
    assert len(data["tenants"]) == initial_count + 3

    # Check first tenant has expected fields
    first = data["tenants"][0]
    assert "id" in first
    assert "name" in first
    assert "slug" in first
    assert "is_active" in first
    assert "billing_plan" in first
    assert "billing_cycle" in first
    assert "billing_status" in first
    assert "seat_limit" in first
    assert "total_users" in first
    assert "active_users" in first


def test_list_tenants_filters_by_is_active(client: Any) -> None:
    """GET /admin/tenants?is_active=false filters correctly."""
    token = _make_super_admin_token()

    # Create 2 tenants
    t1_resp = client.post(
        "/tenants",
        json={"name": "Active Tenant", "slug": "active-tenant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t1_resp.status_code == 201

    t2_resp = client.post(
        "/tenants",
        json={"name": "Suspended Tenant", "slug": "suspended-tenant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t2_resp.status_code == 201
    t2_id = t2_resp.json()["id"]

    # Suspend second tenant
    client.patch(
        f"/admin/tenants/{t2_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter for inactive tenants
    response = client.get(
        "/admin/tenants?is_active=false",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tenants"][0]["id"] == t2_id
    assert data["tenants"][0]["is_active"] is False


def test_list_tenants_pagination(client: Any) -> None:
    """GET /admin/tenants supports pagination."""
    token = _make_super_admin_token()

    # Get initial count
    response = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    initial_count = response.json()["total"]

    # Create 5 tenants
    for i in range(5):
        client.post(
            "/tenants",
            json={"name": f"Tenant {i}", "slug": f"tenant-pg-{i}"},
            headers={"Authorization": f"Bearer {token}"},
        )

    # Page 1 with size 2
    response = client.get(
        "/admin/tenants?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == initial_count + 5
    assert len(data["tenants"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Page 2
    response = client.get(
        "/admin/tenants?page=2&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tenants"]) == 2


def test_list_tenants_requires_super_admin(client: Any) -> None:
    """GET /admin/tenants rejects non-super-admin."""
    token = _make_token("regular@user.com")

    response = client.get(
        "/admin/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_tenant_details(client: Any) -> None:
    """GET /admin/tenants/{id} returns tenant details."""
    token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Detail Test", "slug": "detail-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]

    # Get details
    response = client.get(
        f"/admin/tenants/{tenant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant_id
    assert data["name"] == "Detail Test"
    assert data["slug"] == "detail-test"
    assert data["is_active"] is True
    assert data["total_users"] >= 1  # Creator is a member
    assert "billing_plan" in data


def test_get_tenant_details_not_found(client: Any) -> None:
    """GET /admin/tenants/{id} returns 404 for non-existent tenant."""
    token = _make_super_admin_token()

    response = client.get(
        "/admin/tenants/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_tenant_name_and_plan(client: Any) -> None:
    """PATCH /admin/tenants/{id} updates name and billing_plan."""
    token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Old Name", "slug": "update-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]

    # Update tenant
    response = client.patch(
        f"/admin/tenants/{tenant_id}",
        json={"name": "New Name", "billing_plan": "professional"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["billing_plan"] == "professional"


def test_update_tenant_seat_limit(client: Any) -> None:
    """PATCH /admin/tenants/{id} updates seat_limit."""
    token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Seat Test", "slug": "seat-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]

    # Update seat limit
    response = client.patch(
        f"/admin/tenants/{tenant_id}",
        json={"seat_limit": 25},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["seat_limit"] == 25


def test_update_tenant_partial_update(client: Any) -> None:
    """PATCH /admin/tenants/{id} supports partial updates."""
    token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Partial Test", "slug": "partial-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]

    # Get full details to capture original_plan
    response = client.get(
        f"/admin/tenants/{tenant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    original_plan = response.json()["billing_plan"]

    # Update only name (billing_plan should stay same)
    response = client.patch(
        f"/admin/tenants/{tenant_id}",
        json={"name": "Updated Name Only"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name Only"
    assert data["billing_plan"] == original_plan


def test_update_tenant_not_found(client: Any) -> None:
    """PATCH /admin/tenants/{id} returns 404 for non-existent tenant."""
    token = _make_super_admin_token()

    response = client.patch(
        "/admin/tenants/00000000-0000-0000-0000-000000000000",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_tenant_status_suspend(client: Any) -> None:
    """PATCH /admin/tenants/{id}/status suspends tenant."""
    token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Suspend Test", "slug": "suspend-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]
    assert response.json()["is_active"] is True

    # Suspend tenant
    response = client.patch(
        f"/admin/tenants/{tenant_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


def test_update_tenant_status_reactivate(client: Any) -> None:
    """PATCH /admin/tenants/{id}/status reactivates suspended tenant."""
    token = _make_super_admin_token()

    # Create and suspend tenant
    response = client.post(
        "/tenants",
        json={"name": "Reactivate Test", "slug": "reactivate-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    tenant_id = response.json()["id"]

    client.patch(
        f"/admin/tenants/{tenant_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Reactivate
    response = client.patch(
        f"/admin/tenants/{tenant_id}/status",
        json={"is_active": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True


def test_update_tenant_status_requires_super_admin(client: Any) -> None:
    """PATCH /admin/tenants/{id}/status rejects non-super-admin."""
    super_token = _make_super_admin_token()

    # Create tenant
    response = client.post(
        "/tenants",
        json={"name": "Status Auth Test", "slug": "status-auth-test"},
        headers={"Authorization": f"Bearer {super_token}"},
    )
    tenant_id = response.json()["id"]

    # Try to suspend with regular token
    regular_token = _make_token("regular@user.com")
    response = client.patch(
        f"/admin/tenants/{tenant_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {regular_token}"},
    )

    assert response.status_code == 403


def test_all_admin_tenant_endpoints_require_super_admin(client: Any) -> None:
    """All /admin/tenants/* endpoints require super-admin role."""
    regular_token = _make_token("regular@user.com")
    super_token = _make_super_admin_token()

    # Create a tenant first
    response = client.post(
        "/tenants",
        json={"name": "Auth Test", "slug": "auth-test"},
        headers={"Authorization": f"Bearer {super_token}"},
    )
    tenant_id = response.json()["id"]

    # Try all endpoints with regular token
    endpoints = [
        ("GET", "/admin/tenants", None),
        ("GET", f"/admin/tenants/{tenant_id}", None),
        ("PATCH", f"/admin/tenants/{tenant_id}", {"name": "New"}),
        ("PATCH", f"/admin/tenants/{tenant_id}/status", {"is_active": False}),
    ]

    for method, url, json_data in endpoints:
        if method == "GET":
            response = client.get(
                url,
                headers={"Authorization": f"Bearer {regular_token}"},
            )
        elif method == "PATCH":
            response = client.patch(
                url,
                json=json_data,
                headers={"Authorization": f"Bearer {regular_token}"},
            )

        assert response.status_code == 403, f"{method} {url} should be 403"
