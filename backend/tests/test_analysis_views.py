"""Test saved analysis views and share metadata (FR-032, FR-034 / T-064)."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client() -> Generator[TestClient]:
    """Get a FastAPI test client with the test database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session]:
        db = local_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _token(email: str, role: str = "super_admin") -> str:
    """Generate a JWT token for testing."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _headers(email: str, role: str = "super_admin") -> dict[str, str]:
    """Return authorization headers for a user."""
    return {"Authorization": f"Bearer {_token(email, role)}"}


def _create_tenant(client: TestClient, slug: str, email: str) -> str:
    """Create a test tenant and return tenant_id."""
    resp = client.post(
        "/tenants",
        json={"name": slug, "slug": slug},
        headers=_headers(email),
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Test: Create analysis view
# ---------------------------------------------------------------------------


def test_create_analysis_view(client: TestClient) -> None:
    """POST /analysis-views creates a new saved view."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064a", email)

    resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "ROAS by Channel",
            "description": "Weekly ROAS trends",
            "filters_config": {
                "metrics": ["blended_roas", "cac_payback_period"],
                "date_range": {"from": "2026-05-01", "to": "2026-06-02"},
                "domain": "acquisition",
            },
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201, resp.json()
    data = resp.json()
    assert data["name"] == "ROAS by Channel"
    assert data["description"] == "Weekly ROAS trends"
    assert data["filters_config"]["metrics"] == ["blended_roas", "cac_payback_period"]


# ---------------------------------------------------------------------------
# Test: List analysis views
# ---------------------------------------------------------------------------


def test_list_analysis_views(client: TestClient) -> None:
    """GET /analysis-views lists all views for a tenant."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064b", email)

    # Create two views
    for i in range(2):
        client.post(
            f"/tenants/{tenant_id}/analysis-views",
            json={
                "name": f"View {i + 1}",
                "filters_config": {"metrics": ["blended_roas"]},
            },
            headers=_headers(email),
        )

    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Test: Get analysis view
# ---------------------------------------------------------------------------


def test_get_analysis_view(client: TestClient) -> None:
    """GET /analysis-views/{view_id} retrieves a specific view."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064c", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Test View",
            "filters_config": {"metrics": ["contribution_margin_pct"]},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Get it
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test View"
    assert data["id"] == view_id


# ---------------------------------------------------------------------------
# Test: Delete analysis view
# ---------------------------------------------------------------------------


def test_delete_analysis_view(client: TestClient) -> None:
    """DELETE /analysis-views/{view_id} deletes a view."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064d", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "To Delete",
            "filters_config": {"metrics": []},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Delete it
    resp = client.delete(
        f"/tenants/{tenant_id}/analysis-views/{view_id}",
        headers=_headers(email),
    )
    assert resp.status_code == 204

    # Verify gone
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}",
        headers=_headers(email),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Share analysis view
# ---------------------------------------------------------------------------


def test_share_analysis_view(client: TestClient) -> None:
    """POST /analysis-views/{view_id}/share creates share records."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064e", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "To Share",
            "filters_config": {"metrics": ["blended_roas"]},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Share it
    resp = client.post(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/share",
        json={
            "recipient_emails": ["user1@example.com", "user2@example.com"],
            "scope": "tenant",
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Test: Share with one_time_link scope
# ---------------------------------------------------------------------------


def test_share_analysis_view_one_time_link(client: TestClient) -> None:
    """Share with one_time_link generates token for each recipient."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064f", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Guest Share",
            "filters_config": {},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Share with one_time_link
    resp = client.post(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/share",
        json={
            "recipient_emails": ["guest@external.com"],
            "scope": "one_time_link",
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["items"][0]["scope"] == "one_time_link"
    assert data["items"][0]["one_time_token"] is not None


# ---------------------------------------------------------------------------
# Test: List shares for a view
# ---------------------------------------------------------------------------


def test_list_analysis_view_shares(client: TestClient) -> None:
    """GET /analysis-views/{view_id}/shares lists all shares."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064g", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Share Multiple",
            "filters_config": {},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Share to two recipients
    client.post(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/share",
        json={
            "recipient_emails": ["r1@example.com", "r2@example.com"],
            "scope": "tenant",
        },
        headers=_headers(email),
    )

    # List shares
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/shares",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Test: Get non-existent view
# ---------------------------------------------------------------------------


def test_get_nonexistent_view(client: TestClient) -> None:
    """GET non-existent view returns 404."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064h", email)
    fake_id = uuid.uuid4()

    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{fake_id}",
        headers=_headers(email),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: View with no description
# ---------------------------------------------------------------------------


def test_create_view_optional_description(client: TestClient) -> None:
    """Description is optional when creating view."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064i", email)

    resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "No Description",
            "filters_config": {"metrics": []},
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] is None


# ---------------------------------------------------------------------------
# Test: View filters stored as-is
# ---------------------------------------------------------------------------


def test_filters_config_stored_as_json(client: TestClient) -> None:
    """filters_config stored and retrieved as-is (JSON flexibility)."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064j", email)

    filter_config = {
        "metrics": ["blended_roas", "contribution_margin_pct"],
        "date_range": {
            "from": "2026-05-01",
            "to": "2026-06-02",
        },
        "domain": "acquisition",
        "rec_status": ["reviewed", "approved"],
        "custom_field": "flexible",
    }

    resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Complex Filters",
            "filters_config": filter_config,
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201
    view_id = resp.json()["id"]

    # Retrieve and verify exact match
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}",
        headers=_headers(email),
    )
    assert resp.json()["filters_config"] == filter_config


# ---------------------------------------------------------------------------
# Test: Cross-tenant isolation on views
# ---------------------------------------------------------------------------


def test_cross_tenant_isolation_views(client: TestClient) -> None:
    """Views from tenant A are not visible to tenant B."""
    email1 = "admin@t1.local"
    email2 = "admin@t2.local"
    tenant1_id = _create_tenant(client, "tenant1", email1)
    tenant2_id = _create_tenant(client, "tenant2", email2)

    # Tenant1 creates a view
    create_resp = client.post(
        f"/tenants/{tenant1_id}/analysis-views",
        json={
            "name": "Tenant1 View",
            "filters_config": {},
        },
        headers=_headers(email1),
    )
    view_id = create_resp.json()["id"]

    # Tenant2 cannot access it
    resp = client.get(
        f"/tenants/{tenant2_id}/analysis-views/{view_id}",
        headers=_headers(email2),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Empty analysis views list
# ---------------------------------------------------------------------------


def test_list_empty_analysis_views(client: TestClient) -> None:
    """List returns empty items if no views exist."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064k", email)

    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Test: Export analysis view
# ---------------------------------------------------------------------------


def test_export_view_as_csv(client: TestClient) -> None:
    """GET /analysis-views/{view_id}/export?format=csv downloads CSV."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064l", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Export Test",
            "filters_config": {"metrics": ["blended_roas"]},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Export as CSV
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/export?format=csv",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert b"Export Test" in resp.content
    assert b"AlpMark Analysis View Export" in resp.content


def test_export_view_as_json(client: TestClient) -> None:
    """GET /analysis-views/{view_id}/export?format=json downloads JSON."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064m", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "JSON Export",
            "filters_config": {"metrics": []},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Export as JSON
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/export?format=json",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    import json

    data = json.loads(resp.content)
    assert data["view"]["name"] == "JSON Export"
    assert "recommendations" in data


def test_export_invalid_format(client: TestClient) -> None:
    """Export with invalid format returns 400."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064n", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Bad Format",
            "filters_config": {},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Export with bad format
    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/export?format=pdf",
        headers=_headers(email),
    )
    assert resp.status_code == 400


def test_export_nonexistent_view(client: TestClient) -> None:
    """Export non-existent view returns 404."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064o", email)
    fake_id = uuid.uuid4()

    resp = client.get(
        f"/tenants/{tenant_id}/analysis-views/{fake_id}/export?format=csv",
        headers=_headers(email),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Guest access via one-time token
# ---------------------------------------------------------------------------


def test_guest_access_with_one_time_token(client: TestClient) -> None:
    """GET /saved-views/{one_time_token} returns view without auth."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064p", email)

    # Create a view
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Guest View",
            "filters_config": {"metrics": ["contribution_margin_pct"]},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    # Share with one-time link
    share_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/share",
        json={
            "recipient_emails": ["guest@external.com"],
            "scope": "one_time_link",
        },
        headers=_headers(email),
    )
    token = share_resp.json()["items"][0]["one_time_token"]

    # Access via token WITHOUT auth
    resp = client.get(f"/saved-views/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Guest View"
    assert data["filters_config"]["metrics"] == ["contribution_margin_pct"]


def test_guest_access_invalid_token(client: TestClient) -> None:
    """GET /saved-views/{invalid_token} returns 404."""
    resp = client.get("/saved-views/invalid-token-xyz")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_guest_access_tenant_scope_no_token(client: TestClient) -> None:
    """Share with tenant scope has no token (not guest accessible)."""
    email = "admin@t064.local"
    tenant_id = _create_tenant(client, "t064q", email)

    # Create and share with tenant scope
    create_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Tenant Only",
            "filters_config": {},
        },
        headers=_headers(email),
    )
    view_id = create_resp.json()["id"]

    share_resp = client.post(
        f"/tenants/{tenant_id}/analysis-views/{view_id}/share",
        json={
            "recipient_emails": ["internal@company.com"],
            "scope": "tenant",
        },
        headers=_headers(email),
    )
    # Verify no token was generated
    assert share_resp.json()["items"][0]["one_time_token"] is None
