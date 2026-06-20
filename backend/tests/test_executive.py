"""Tests for executive overview endpoint."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, timedelta

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import (
    ConnectorIntegration,
    GoogleAdSpend,
    MetaAdSpend,
    Role,
    ShopifyOrder,
    Tenant,
    TenantMembership,
    User,
)
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


def test_get_executive_overview_success(
    client: TestClient, db_session: Session
) -> None:
    """Test successful executive overview retrieval with real data."""
    # Create tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    # Seed roles
    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # Create user
    user = User(
        id=uuid.uuid4(),
        email="exec@test.com",
        full_name="Executive User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles["executive_owner"].id,
    )
    db_session.add(membership)
    db_session.commit()

    # Create test data
    today = date.today()
    period_start = today - timedelta(days=30)

    connector = ConnectorIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.commit()

    # Add orders
    for i in range(10):
        order = ShopifyOrder(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id=f"order-{i}",
            customer_id=f"cust-{i % 5}",
            order_number=f"#{1000 + i}",
            currency="USD",
            total_amount=100.0 + (i * 10),
            discount_amount=5.0,
            shipping_amount=10.0,
            refund_amount=0.0 if i % 5 != 0 else 20.0,
            is_refunded=i % 5 == 0,
            order_created_at=period_start + timedelta(days=i * 3),
        )
        db_session.add(order)

    # Add Meta ad spend
    for i in range(15):
        meta_spend = MetaAdSpend(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_campaign_id=f"meta-{i % 3}",
            campaign_name=f"Meta Campaign {i % 3}",
            spend_date=period_start + timedelta(days=i * 2),
            currency="USD",
            spend_amount=50.0 + (i * 5),
        )
        db_session.add(meta_spend)

    # Add Google ad spend
    for i in range(10):
        google_spend = GoogleAdSpend(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_campaign_id=f"google-{i % 2}",
            campaign_name=f"Google Campaign {i % 2}",
            spend_date=period_start + timedelta(days=i * 3),
            currency="USD",
            spend_amount=40.0 + (i * 4),
        )
        db_session.add(google_spend)

    db_session.commit()

    # Make request
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "total_revenue" in data
    assert "gross_profit" in data
    assert "contribution_margin" in data
    assert "blended_roas" in data
    assert "overall_health_status" in data
    assert "health_indicators" in data
    assert "team_performance" in data

    # Verify calculations
    expected_revenue = sum(100 + (i * 10) for i in range(10)) - 40
    assert data["total_revenue"] == expected_revenue
    assert data["blended_roas"] is not None
    assert data["blended_roas"] > 0


def test_get_executive_overview_default_period(
    client: TestClient, db_session: Session
) -> None:
    """Test executive overview with default 30-day period."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-default-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="exec2@test.com",
        full_name="Executive User 2",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles["executive_owner"].id,
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

    # Verify defaults
    assert data["period_end"] == date.today().isoformat()
    expected_start = (date.today() - timedelta(days=30)).isoformat()
    assert data["period_start"] == expected_start


def test_get_executive_overview_requires_permission(
    client: TestClient, db_session: Session
) -> None:
    """Test that executive.view permission is required."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-perm-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # User with growth role (no executive.view)
    user = User(
        id=uuid.uuid4(),
        email="growth@test.com",
        full_name="Growth User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="growth_performance_manager",
        role_id=roles["growth_performance_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_executive_overview_tenant_not_found(
    client: TestClient, db_session: Session
) -> None:
    """Test 404 when tenant doesn't exist."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-404-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="exec3@test.com",
        full_name="Executive User 3",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles["executive_owner"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    fake_tenant_id = uuid.uuid4()
    response = client.get(
        f"/tenants/{fake_tenant_id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_get_executive_overview_invalid_period(
    client: TestClient, db_session: Session
) -> None:
    """Test validation when period_start > period_end."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-invalid-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="exec4@test.com",
        full_name="Executive User 4",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles["executive_owner"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    today = date.today()
    response = client.get(
        f"/tenants/{tenant.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": today.isoformat(),
            "period_end": (today - timedelta(days=10)).isoformat(),
        },
    )

    assert response.status_code == 400
    assert "period_start must be before" in response.json()["detail"]


def test_get_executive_overview_cross_tenant_isolation(
    client: TestClient, db_session: Session
) -> None:
    """Test tenant isolation."""
    # Create two tenants
    tenant1 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 1",
        slug=f"test-exec-iso1-{uuid.uuid4().hex[:8]}",
    )
    tenant2 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 2",
        slug=f"test-exec-iso2-{uuid.uuid4().hex[:8]}",
    )
    db_session.add_all([tenant1, tenant2])
    db_session.commit()

    roles1 = seed_system_roles_for_tenant(db_session, tenant1.id)
    seed_system_roles_for_tenant(db_session, tenant2.id)

    # User for tenant1
    user = User(
        id=uuid.uuid4(),
        email="exec-iso@test.com",
        full_name="Executive Isolation User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant1.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles1["executive_owner"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)

    # Try to access tenant2
    response = client.get(
        f"/tenants/{tenant2.id}/executive/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_executive_overview_with_no_data(
    client: TestClient, db_session: Session
) -> None:
    """Test executive overview when tenant has no data."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Corp",
        slug=f"test-exec-nodata-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="exec-nodata@test.com",
        full_name="Executive No Data User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="executive_owner",
        role_id=roles["executive_owner"].id,
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

    # Zero/null values for no data
    assert data["total_revenue"] == 0.0
    assert data["blended_roas"] is None
    assert data["revenue_growth_rate"] is None
