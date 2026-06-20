"""Tests for role and permission endpoints."""

import uuid

from backend.app.db.models import Role, Tenant, User
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_get_permissions_catalog_returns_all_permissions(
    client: TestClient,
) -> None:
    """Test GET /permissions returns all available permissions."""
    response = client.get("/permissions")

    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert len(data["permissions"]) > 0
    
    # Check structure of permission info
    first_perm = data["permissions"][0]
    assert "permission" in first_perm
    assert "description" in first_perm
    
    # Check for expected permissions
    permission_names = [p["permission"] for p in data["permissions"]]
    assert "admin.members" in permission_names
    assert "executive.view" in permission_names
    assert "growth.view" in permission_names
    assert "intel.recommendations.view" in permission_names


def test_get_roles_returns_system_roles_for_tenant(
    db_session: Session, client: TestClient
) -> None:
    """Test GET /roles returns system roles for a tenant."""
    # Create tenant
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    # Create system roles for tenant (normally done by migration)
    role1 = Role(
        tenant_id=tenant.id,
        name="brand_admin",
        permissions=["admin.members", "admin.roles"],
        is_system=True,
    )
    role2 = Role(
        tenant_id=tenant.id,
        name="executive_owner",
        permissions=["executive.view", "executive.approve"],
        is_system=True,
    )
    db_session.add_all([role1, role2])
    db_session.commit()

    response = client.get(f"/roles?tenant_id={tenant.id}")

    assert response.status_code == 200
    data = response.json()
    assert "roles" in data
    assert len(data["roles"]) == 2
    
    # Verify role structure
    first_role = data["roles"][0]
    assert "id" in first_role
    assert "tenant_id" in first_role
    assert "name" in first_role
    assert "permissions" in first_role
    assert "is_system" in first_role
    assert first_role["is_system"] is True


def test_create_role_creates_custom_role(
    db_session: Session, client: TestClient
) -> None:
    """Test POST /roles creates a custom role."""
    # Create tenant
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()

    response = client.post(
        f"/roles?tenant_id={tenant.id}",
        json={
            "name": "custom_role",
            "permissions": ["growth.view", "intel.recommendations.view"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "custom_role"
    assert data["is_system"] is False
    assert len(data["permissions"]) == 2
    assert "growth.view" in data["permissions"]
    
    # Verify in database
    role = db_session.query(Role).filter_by(id=uuid.UUID(data["id"])).first()
    assert role is not None
    assert role.name == "custom_role"
    assert role.is_system is False


def test_create_role_rejects_duplicate_name(
    db_session: Session, client: TestClient
) -> None:
    """Test POST /roles rejects duplicate role name."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    # Create existing role
    existing_role = Role(
        tenant_id=tenant.id,
        name="existing_role",
        permissions=["growth.view"],
        is_system=False,
    )
    db_session.add(existing_role)
    db_session.commit()

    # Try to create role with same name
    response = client.post(
        f"/roles?tenant_id={tenant.id}",
        json={
            "name": "existing_role",
            "permissions": ["finance.view"],
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_role_rejects_invalid_permissions(
    db_session: Session, client: TestClient
) -> None:
    """Test POST /roles rejects invalid permissions."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()

    response = client.post(
        f"/roles?tenant_id={tenant.id}",
        json={
            "name": "bad_role",
            "permissions": ["invalid.permission", "another.bad.one"],
        },
    )

    assert response.status_code == 400
    assert "Invalid permissions" in response.json()["detail"]


def test_get_role_returns_role_details(
    db_session: Session, client: TestClient
) -> None:
    """Test GET /roles/{role_id} returns role details."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    role = Role(
        tenant_id=tenant.id,
        name="test_role",
        permissions=["growth.view", "growth.analyze"],
        is_system=False,
    )
    db_session.add(role)
    db_session.commit()

    response = client.get(f"/roles/{role.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(role.id)
    assert data["name"] == "test_role"
    assert len(data["permissions"]) == 2


def test_get_role_returns_404_for_nonexistent_role(
    client: TestClient,
) -> None:
    """Test GET /roles/{role_id} returns 404 for nonexistent role."""
    fake_id = uuid.uuid4()
    response = client.get(f"/roles/{fake_id}")

    assert response.status_code == 404


def test_update_role_updates_custom_role(
    db_session: Session, client: TestClient
) -> None:
    """Test PUT /roles/{role_id} updates custom role."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    role = Role(
        tenant_id=tenant.id,
        name="old_name",
        permissions=["growth.view"],
        is_system=False,
    )
    db_session.add(role)
    db_session.commit()

    response = client.put(
        f"/roles/{role.id}",
        json={
            "name": "new_name",
            "permissions": ["growth.view", "growth.analyze", "growth.simulate"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "new_name"
    assert len(data["permissions"]) == 3
    
    # Verify in database
    db_session.refresh(role)
    assert role.name == "new_name"
    assert len(role.permissions) == 3


def test_update_role_rejects_system_role_modification(
    db_session: Session, client: TestClient
) -> None:
    """Test PUT /roles/{role_id} rejects system role modification."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    system_role = Role(
        tenant_id=tenant.id,
        name="brand_admin",
        permissions=["admin.members"],
        is_system=True,
    )
    db_session.add(system_role)
    db_session.commit()

    response = client.put(
        f"/roles/{system_role.id}",
        json={"name": "hacked_admin"},
    )

    assert response.status_code == 403
    assert "System roles cannot be modified" in response.json()["detail"]


def test_delete_role_deletes_custom_role(
    db_session: Session, client: TestClient
) -> None:
    """Test DELETE /roles/{role_id} deletes custom role."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    role = Role(
        tenant_id=tenant.id,
        name="deletable_role",
        permissions=["growth.view"],
        is_system=False,
    )
    db_session.add(role)
    db_session.commit()
    role_id = role.id

    response = client.delete(f"/roles/{role_id}")

    assert response.status_code == 204
    
    # Verify deleted from database
    deleted_role = db_session.query(Role).filter_by(id=role_id).first()
    assert deleted_role is None


def test_delete_role_rejects_system_role_deletion(
    db_session: Session, client: TestClient
) -> None:
    """Test DELETE /roles/{role_id} rejects system role deletion."""
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    system_role = Role(
        tenant_id=tenant.id,
        name="brand_admin",
        permissions=["admin.members"],
        is_system=True,
    )
    db_session.add(system_role)
    db_session.commit()

    response = client.delete(f"/roles/{system_role.id}")

    assert response.status_code == 403
    assert "System roles cannot be deleted" in response.json()["detail"]


def test_delete_role_rejects_if_role_in_use(
    db_session: Session, client: TestClient
) -> None:
    """Test DELETE /roles/{role_id} rejects if role is assigned to members."""
    from backend.app.db.models import TenantMembership
    
    tenant = Tenant(name="Test Tenant", slug=f"test-tenant-{uuid.uuid4().hex[:8]}")
    db_session.add(tenant)
    db_session.commit()
    
    role = Role(
        tenant_id=tenant.id,
        name="in_use_role",
        permissions=["growth.view"],
        is_system=False,
    )
    user = User(
        email="user@test.com",
        full_name="Test User",
        is_active=True,
    )
    db_session.add_all([role, user])
    db_session.commit()
    
    # Assign role to user
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role_id=role.id,
        role="in_use_role",  # Legacy field
    )
    db_session.add(membership)
    db_session.commit()

    response = client.delete(f"/roles/{role.id}")

    assert response.status_code == 409
    assert "Cannot delete role" in response.json()["detail"]
    assert "assigned to" in response.json()["detail"]
