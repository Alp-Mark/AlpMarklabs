from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date
from uuid import UUID

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import Role, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# Test fixtures
@pytest.fixture
def client() -> Generator[TestClient]:
    """In-memory SQLite test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _token(email: str, role: str = "super_admin") -> str:
    """Generate JWT token for testing."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _headers(email: str = "test@example.com", role: str = "super_admin") -> dict:
    """Generate auth headers with JWT token."""
    return {"Authorization": f"Bearer {_token(email, role)}"}


def _create_tenant(client: TestClient, slug: str, email: str) -> str:
    resp = client.post(
        "/tenants",
        json={"name": slug, "slug": slug},
        headers=_headers(email),
    )
    assert resp.status_code == 201
    tenant_id = resp.json()["id"]
    
    # Note: System roles are now seeded automatically by POST /tenants endpoint
    # Note: TenantMembership for creator is created with brand_admin role
    
    # Upgrade to operations_inventory_manager (has all permissions)
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        # Get the operations_inventory_manager role for this tenant
        ops_role = db.scalar(
            select(Role).where(
                Role.tenant_id == uuid.UUID(tenant_id),
                Role.name == "operations_inventory_manager",
                Role.is_system,
            )
        )
        
        # Update the membership to use operations_inventory_manager role
        membership = db.scalar(
            select(TenantMembership)
            .join(User, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == uuid.UUID(tenant_id),
                User.email == email,
            )
        )
        if membership and ops_role:
            membership.role = "operations_inventory_manager"
            membership.role_id = ops_role.id
            db.commit()
    finally:
        db.close()
    
    return tenant_id

def _create_view(
    client: TestClient,
    tenant_id: UUID | str,
    email: str = "test@example.com",
) -> UUID:
    """Create a saved analysis view and return view_id."""
    response = client.post(
        f"/tenants/{tenant_id}/analysis-views",
        json={
            "name": "Test View",
            "description": "Test description",
            "filters_config": {"metrics": ["roas"], "date_range": "last_30_days"},
        },
        headers=_headers(email),
    )
    assert response.status_code == 201, response.json()
    id_val = response.json()["id"]
    if isinstance(id_val, str):
        return UUID(id_val)
    return id_val


class TestAnnotationsCRUD:
    """Test CRUD operations on annotations."""

    def test_create_annotation(self, client: TestClient) -> None:
        """FR-033 / T-065: Create annotation on analysis view."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        response = client.post(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            json={
                "text": "Creative fatigue — pausing Campaign A",
                "event_date": None,
                "annotation_type": "context",
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "Creative fatigue — pausing Campaign A"
        assert data["annotation_type"] == "context"
        assert "id" in data
        assert "created_at" in data

    def test_list_annotations(self, client: TestClient) -> None:
        """FR-033 / T-065: List annotations for a view."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        # Create 3 annotations
        for i in range(3):
            client.post(
                f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
                json={
                    "text": f"Annotation {i+1}",
                    "event_date": None,
                    "annotation_type": "context",
                },
                headers=_headers("test@example.com"),
            )

        response = client.get(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # All annotations present (ordering is created_at DESC; sub-second ties
        # are undefined, so assert membership rather than exact order).
        texts = {item["text"] for item in data["items"]}
        assert texts == {"Annotation 1", "Annotation 2", "Annotation 3"}

    def test_delete_annotation(self, client: TestClient) -> None:
        """FR-033 / T-065: Delete annotation."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        # Create annotation
        create_response = client.post(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            json={
                "text": "Test annotation",
                "event_date": None,
                "annotation_type": "context",
            },
            headers=_headers("test@example.com"),
        )
        annotation_id = create_response.json()["id"]

        # Delete annotation
        delete_response = client.delete(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations/{annotation_id}",
            headers=_headers("test@example.com"),
        )
        assert delete_response.status_code == 204

        # Verify annotation is gone
        list_response = client.get(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            headers=_headers("test@example.com"),
        )
        assert list_response.json()["total"] == 0


class TestAnnotationsWithEventDate:
    """Test annotations with date-linked events (FR-045, FR-068)."""

    def test_create_annotation_with_event_date(self, client: TestClient) -> None:
        """FR-045 / T-065: Create lifecycle event annotation with date."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        event_date = date(2026, 6, 10)
        response = client.post(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            json={
                "text": "Flash sale Nov 15",
                "event_date": event_date.isoformat(),
                "annotation_type": "lifecycle",
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_date"] == event_date.isoformat()
        assert data["annotation_type"] == "lifecycle"

    def test_list_annotations_filter_by_event_date(
        self, client: TestClient
    ) -> None:
        """FR-045, FR-068 / T-065: Filter annotations by event date range."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        # Create annotations with different dates
        dates = [
            date(2026, 6, 1),
            date(2026, 6, 10),
            date(2026, 6, 20),
        ]
        for i, d in enumerate(dates):
            client.post(
                f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
                json={
                    "text": f"Event {i+1}",
                    "event_date": d.isoformat(),
                    "annotation_type": "lifecycle",
                },
                headers=_headers("test@example.com"),
            )

        # Filter by date range
        response = client.get(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations"
            f"?event_date_min=2026-06-05&event_date_max=2026-06-15",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only the 2026-06-10 annotation
        assert data["items"][0]["text"] == "Event 2"


class TestAnnotationsIsolation:
    """Test cross-tenant isolation and access control."""

    def test_cross_tenant_isolation(self, client: TestClient) -> None:
        """T-065: Cannot create annotation on another tenant's view."""
        # Create two tenants
        tenant1_id = _create_tenant(client, "tenant-1", "user1@example.com")
        tenant2_id = _create_tenant(client, "tenant-2", "user2@example.com")

        # Create view in tenant 1
        view_id = _create_view(client, tenant1_id, "user1@example.com")

        # Try to create annotation in tenant 2 on tenant 1's view (should fail)
        response = client.post(
            f"/tenants/{tenant2_id}/analysis-views/{view_id}/annotations",
            json={
                "text": "Malicious annotation",
                "event_date": None,
                "annotation_type": "context",
            },
            headers=_headers("user2@example.com"),
        )

        assert response.status_code == 404

    def test_annotation_nonexistent_view(self, client: TestClient) -> None:
        """T-065: Cannot create annotation on non-existent view."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        fake_view_id = UUID(int=999)

        response = client.post(
            f"/tenants/{tenant_id}/analysis-views/{fake_view_id}/annotations",
            json={
                "text": "Test annotation",
                "event_date": None,
                "annotation_type": "context",
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAnnotationsEmptyList:
    """Test edge cases for annotation list."""

    def test_list_annotations_empty_view(self, client: TestClient) -> None:
        """T-065: List annotations on view with no annotations."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)

        response = client.get(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_annotations_nonexistent_view(self, client: TestClient) -> None:
        """T-065: List annotations on non-existent view."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        fake_view_id = UUID(int=999)

        response = client.get(
            f"/tenants/{tenant_id}/analysis-views/{fake_view_id}/annotations",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 404


class TestAnnotationsDelete:
    """Test deletion and error cases."""

    def test_delete_nonexistent_annotation(self, client: TestClient) -> None:
        """T-065: Delete non-existent annotation."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view_id = _create_view(client, tenant_id)
        fake_annotation_id = UUID(int=999)

        response = client.delete(
            f"/tenants/{tenant_id}/analysis-views/{view_id}/annotations/{fake_annotation_id}",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 404

    def test_delete_annotation_wrong_view(self, client: TestClient) -> None:
        """T-065: Cannot delete annotation from wrong view."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")
        view1_id = _create_view(client, tenant_id)
        view2_id = _create_view(client, tenant_id)

        # Create annotation on view 1
        create_response = client.post(
            f"/tenants/{tenant_id}/analysis-views/{view1_id}/annotations",
            json={
                "text": "Test annotation",
                "event_date": None,
                "annotation_type": "context",
            },
            headers=_headers("test@example.com"),
        )
        annotation_id = create_response.json()["id"]

        # Try to delete from view 2 (should fail)
        response = client.delete(
            f"/tenants/{tenant_id}/analysis-views/{view2_id}/annotations/{annotation_id}",
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 404
