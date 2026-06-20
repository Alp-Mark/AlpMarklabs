"""Integration tests for custom segments API (FR-044 / T-071)."""

from __future__ import annotations

import uuid

import jwt
from backend.app.db.models import CustomSegment, Role, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

client = TestClient(app)


def _make_auth_token(payload: dict) -> str:
    """Generate a signed JWT token for testing."""
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)


def _create_tenant_and_get_id(
    client: TestClient, tenant_name: str, tenant_slug: str
) -> tuple[str, str]:
    """Create a tenant and return its ID and auth token."""
    email = f"admin-{tenant_slug}@test.local"
    token = _make_auth_token(
        {"sub": "admin", "email": email, "platform_role": "super_admin"}
    )
    response = client.post(
        "/tenants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": tenant_name,
            "slug": tenant_slug,
            "billing_plan": "pro",
            "seat_limit": 10,
        },
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]
    
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
    
    return tenant_id, token


class TestCustomSegments:
    """Test custom segments API endpoints."""

    def test_create_custom_segment_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test successful creation of a custom segment."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)

        # Ensure user and membership exist
        email = "admin-test-brand@test.local"
        user = db_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, full_name="Test User", is_active=True
            )
            db_session.add(user)
            db_session.commit()

        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        response = client.post(
            f"/tenants/{tenant_id_str}/retention/custom-segments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "High-Value Customers",
                "description": "AOV > £500",
                "definition": {"aov_min": 500},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "High-Value Customers"
        assert data["description"] == "AOV > £500"
        assert data["definition"] == {"aov_min": 500}

    def test_list_custom_segments(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test listing custom segments."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)

        # Ensure user and membership exist
        email = "admin-test-brand@test.local"
        user = db_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, full_name="Test User", is_active=True
            )
            db_session.add(user)
            db_session.commit()

        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create a segment
        segment = CustomSegment(
            tenant_id=tenant_id,
            name="Test Segment",
            description="Test description",
            definition={"aov_min": 300},
        )
        db_session.add(segment)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id_str}/retention/custom-segments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["segments"]) == 1
        assert data["segments"][0]["name"] == "Test Segment"

    def test_get_custom_segment(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test getting a specific custom segment."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)

        # Ensure user and membership exist
        email = "admin-test-brand@test.local"
        user = db_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, full_name="Test User", is_active=True
            )
            db_session.add(user)
            db_session.commit()

        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create a segment
        segment = CustomSegment(
            tenant_id=tenant_id,
            name="Test Segment",
            description="Test description",
            definition={"aov_min": 300},
        )
        db_session.add(segment)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id_str}/retention/custom-segments/{segment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Segment"

    def test_update_custom_segment(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test updating a custom segment."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)

        # Ensure user and membership exist
        email = "admin-test-brand@test.local"
        user = db_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, full_name="Test User", is_active=True
            )
            db_session.add(user)
            db_session.commit()

        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create a segment
        segment = CustomSegment(
            tenant_id=tenant_id,
            name="Test Segment",
            description="Original description",
            definition={"aov_min": 300},
        )
        db_session.add(segment)
        db_session.commit()

        response = client.put(
            f"/tenants/{tenant_id_str}/retention/custom-segments/{segment.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "Updated description", "definition": {"aov_min": 500}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["definition"] == {"aov_min": 500}

    def test_delete_custom_segment(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test deleting a custom segment."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)

        # Ensure user and membership exist
        email = "admin-test-brand@test.local"
        user = db_session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email, full_name="Test User", is_active=True
            )
            db_session.add(user)
            db_session.commit()

        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user.id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create a segment
        segment = CustomSegment(
            tenant_id=tenant_id,
            name="Test Segment",
            description="Test description",
            definition={"aov_min": 300},
        )
        db_session.add(segment)
        db_session.commit()

        response = client.delete(
            f"/tenants/{tenant_id_str}/retention/custom-segments/{segment.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Verify it's deleted
        deleted = db_session.scalar(
            select(CustomSegment).where(CustomSegment.id == segment.id)
        )
        assert deleted is None

    def test_custom_segment_unauthorized(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test that insufficient role authorization is rejected with 403.
        
        Note: The conftest fixture auto-adds auth headers with a user having only
        'user' platform role. The operations_manager role is required to create
        custom segments, so this correctly returns 403 Forbidden (authenticated
        but not authorized).
        """
        tenant_id_str, _ = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )

        response = client.post(
            f"/tenants/{tenant_id_str}/retention/custom-segments",
            json={
                "name": "High-Value Customers",
                "definition": {"aov_min": 500},
            },
        )
        assert response.status_code == 403

    def test_custom_segment_tenant_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test that nonexistent tenant returns 404."""
        fake_tenant_id = uuid.uuid4()
        token = _make_auth_token(
            {"sub": "admin", "email": "test@test.local", "platform_role": "super_admin"}
        )

        response = client.get(
            f"/tenants/{fake_tenant_id}/retention/custom-segments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_custom_segment_cross_tenant_isolation(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test that tenant isolation is enforced."""
        tenant1_id_str, token1 = _create_tenant_and_get_id(
            client, "Tenant 1", "tenant-1"
        )
        tenant1_id = uuid.UUID(tenant1_id_str)

        _tenant2_id_str, token2 = _create_tenant_and_get_id(
            client, "Tenant 2", "tenant-2"
        )

        # Create segment in tenant 1
        email1 = "admin-tenant-1@test.local"
        user1 = db_session.scalar(select(User).where(User.email == email1))
        segment1 = CustomSegment(
            tenant_id=tenant1_id,
            name="Tenant 1 Segment",
            definition={"aov_min": 300},
            created_by_user_id=user1.id if user1 else None,
        )
        db_session.add(segment1)
        db_session.commit()

        # Try to access tenant1's segment with tenant2's token (cross-tenant check)
        response = client.get(
            f"/tenants/{tenant1_id_str}/retention/custom-segments/{segment1.id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        # Should reject cross-tenant access
        assert response.status_code in (401, 403, 404)

