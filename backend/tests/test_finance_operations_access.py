"""Tests for finance and operations role access to dashboard endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import Role, Tenant, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session() -> Generator[Session]:
    """Create test database session with clean slate."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator:
        session = local_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    session = local_session()
    yield session
    session.close()

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """Get test client."""
    return TestClient(app)


def seed_system_roles_for_tenant(db: Session, tenant_id: uuid.UUID) -> dict[str, Role]:
    """Seed system roles for a tenant."""
    from backend.app.permissions import get_system_role_permissions

    role_names = [
        "brand_admin",
        "executive_owner",
        "growth_performance_manager",
        "retention_crm_manager",
        "finance_controller",
        "operations_inventory_manager",
    ]

    roles = {}
    for role_name in role_names:
        permissions = get_system_role_permissions(role_name)
        role = Role(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=role_name,
            permissions=permissions,
            is_system=True,
        )
        db.add(role)
        roles[role_name] = role

    db.commit()
    return roles


def _make_token(email: str) -> str:
    """Create JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": None},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def test_finance_controller_can_access_executive_dashboard(
    client: TestClient, db_session: Session
) -> None:
    """Test that finance_controller can access executive overview dashboard."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Finance Access Test",
        slug=f"test-finance-exec-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="finance@test.com",
        full_name="Finance Controller",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="finance_controller",
        role_id=roles["finance_controller"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "contribution_margin" in data


def test_finance_controller_can_access_growth_dashboard(
    client: TestClient, db_session: Session
) -> None:
    """Test that finance_controller can access growth dashboard."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Finance Access Test",
        slug=f"test-finance-growth-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="finance2@test.com",
        full_name="Finance Controller 2",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="finance_controller",
        role_id=roles["finance_controller"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_spend" in data
    assert "blended_roas" in data


def test_finance_controller_can_access_retention_dashboard(
    client: TestClient, db_session: Session
) -> None:
    """Test that finance_controller can access retention dashboard."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Finance Access Test",
        slug=f"test-finance-retention-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="finance3@test.com",
        full_name="Finance Controller 3",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="finance_controller",
        role_id=roles["finance_controller"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "repeat_purchase_rate" in data
    assert "total_customers" in data


def test_operations_manager_can_access_all_dashboards(
    client: TestClient, db_session: Session
) -> None:
    """Test that operations_inventory_manager can access all dashboards."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Operations Access Test",
        slug=f"test-ops-all-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="ops@test.com",
        full_name="Operations Manager",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_inventory_manager",
        role_id=roles["operations_inventory_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    
    # Should have access to all dashboards
    exec_response = client.get(
        f"/tenants/{tenant.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert exec_response.status_code == 200

    growth_response = client.get(
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert growth_response.status_code == 200

    retention_response = client.get(
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retention_response.status_code == 200
