"""Tests for retention dashboard endpoint."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, timedelta

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import (
    ConnectorIntegration,
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


def test_get_retention_dashboard_success(
    client: TestClient, db_session: Session
) -> None:
    """Test successful retention dashboard retrieval with customer data."""
    # Create tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    # Seed roles
    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # Create user with retention_crm_manager role
    user = User(
        id=uuid.uuid4(),
        email="retention@test.com",
        full_name="Retention Manager",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    # Create test data
    today = date.today()
    period_start = today - timedelta(days=90)

    connector = ConnectorIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.commit()

    # Add orders for multiple customers with different purchase patterns
    # Customer 1: One-time buyer
    order1 = ShopifyOrder(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_order_id="order-1",
        customer_id="customer-1",
        order_number="#1001",
        currency="USD",
        total_amount=100.0,
        discount_amount=0.0,
        shipping_amount=0.0,
        refund_amount=0.0,
        is_refunded=False,
        order_created_at=period_start + timedelta(days=5),
    )
    db_session.add(order1)

    # Customer 2: Repeat buyer (3 orders)
    for i in range(3):
        order = ShopifyOrder(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id=f"order-2-{i}",
            customer_id="customer-2",
            order_number=f"#2{i:03d}",
            currency="USD",
            total_amount=150.0,
            discount_amount=0.0,
            shipping_amount=0.0,
            refund_amount=0.0,
            is_refunded=False,
            order_created_at=period_start + timedelta(days=10 + (i * 15)),
        )
        db_session.add(order)

    # Customer 3: Loyal customer (5 orders)
    for i in range(5):
        order = ShopifyOrder(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id=f"order-3-{i}",
            customer_id="customer-3",
            order_number=f"#3{i:03d}",
            currency="USD",
            total_amount=200.0,
            discount_amount=0.0,
            shipping_amount=0.0,
            refund_amount=0.0,
            is_refunded=False,
            order_created_at=period_start + timedelta(days=5 + (i * 10)),
        )
        db_session.add(order)

    # Customer 4: Another one-time buyer (old order, churn risk)
    order4 = ShopifyOrder(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_order_id="order-4",
        customer_id="customer-4",
        order_number="#4001",
        currency="USD",
        total_amount=80.0,
        discount_amount=0.0,
        shipping_amount=0.0,
        refund_amount=0.0,
        is_refunded=False,
        order_created_at=period_start + timedelta(days=2),
    )
    db_session.add(order4)

    db_session.commit()

    # Make request
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "total_customers" in data
    assert "repeat_customers" in data
    assert "repeat_purchase_rate" in data
    assert "avg_orders_per_customer" in data
    assert "avg_customer_lifetime_value" in data
    assert "avg_days_between_purchases" in data
    assert "churn_risk_customers" in data
    assert "cohort_retention" in data
    assert "customer_segments" in data
    assert "period_start" in data
    assert "period_end" in data

    # Verify calculations
    assert data["total_customers"] == 4
    assert data["repeat_customers"] == 2  # customer-2 and customer-3
    assert data["repeat_purchase_rate"] == 50.0
    assert data["avg_orders_per_customer"] == 2.5  # 10 orders / 4 customers

    # Verify segments exist
    assert len(data["customer_segments"]) > 0
    segment_names = {s["segment_name"] for s in data["customer_segments"]}
    assert "One-time Buyers" in segment_names


def test_get_retention_dashboard_default_period(
    client: TestClient, db_session: Session
) -> None:
    """Test retention dashboard with default 90-day period."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-default-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="retention2@test.com",
        full_name="Retention Manager 2",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
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

    # Verify defaults
    assert data["period_end"] == date.today().isoformat()
    expected_start = (date.today() - timedelta(days=90)).isoformat()
    assert data["period_start"] == expected_start


def test_get_retention_dashboard_requires_permission(
    client: TestClient, db_session: Session
) -> None:
    """Test that retention.view permission is required."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-perm-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # User with growth role (no retention.view)
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
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_retention_dashboard_tenant_not_found(
    client: TestClient, db_session: Session
) -> None:
    """Test 404 when tenant doesn't exist."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-404-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="retention3@test.com",
        full_name="Retention Manager 3",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    fake_tenant_id = uuid.uuid4()
    response = client.get(
        f"/tenants/{fake_tenant_id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_get_retention_dashboard_invalid_period(
    client: TestClient, db_session: Session
) -> None:
    """Test validation when period_start > period_end."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-invalid-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="retention4@test.com",
        full_name="Retention Manager 4",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)
    today = date.today()
    response = client.get(
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": today.isoformat(),
            "period_end": (today - timedelta(days=10)).isoformat(),
        },
    )

    assert response.status_code == 400
    assert "period_start must be before" in response.json()["detail"]


def test_get_retention_dashboard_cross_tenant_isolation(
    client: TestClient, db_session: Session
) -> None:
    """Test tenant isolation."""
    # Create two tenants
    tenant1 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 1",
        slug=f"test-retention-iso1-{uuid.uuid4().hex[:8]}",
    )
    tenant2 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 2",
        slug=f"test-retention-iso2-{uuid.uuid4().hex[:8]}",
    )
    db_session.add_all([tenant1, tenant2])
    db_session.commit()

    roles1 = seed_system_roles_for_tenant(db_session, tenant1.id)
    seed_system_roles_for_tenant(db_session, tenant2.id)

    # User for tenant1
    user = User(
        id=uuid.uuid4(),
        email="retention-iso@test.com",
        full_name="Retention Isolation User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant1.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles1["retention_crm_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)

    # Try to access tenant2
    response = client.get(
        f"/tenants/{tenant2.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_retention_dashboard_with_no_data(
    client: TestClient, db_session: Session
) -> None:
    """Test retention dashboard when tenant has no orders."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-nodata-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="retention-nodata@test.com",
        full_name="Retention No Data User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
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

    # Zero/null values for no data
    assert data["total_customers"] == 0
    assert data["repeat_customers"] == 0
    assert data["repeat_purchase_rate"] is None
    assert data["avg_orders_per_customer"] is None
    assert len(data["cohort_retention"]) == 0
    assert len(data["customer_segments"]) == 0


def test_get_retention_dashboard_cohort_analysis(
    client: TestClient, db_session: Session
) -> None:
    """Test cohort retention analysis with multi-month data."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Retention Test Corp",
        slug=f"test-retention-cohort-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="retention-cohort@test.com",
        full_name="Retention Cohort User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="retention_crm_manager",
        role_id=roles["retention_crm_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    # Create test data spanning multiple months
    today = date.today()
    period_start = today - timedelta(days=120)

    connector = ConnectorIntegration(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db_session.add(connector)
    db_session.commit()

    # Add orders for cohort analysis
    # Customer from 4 months ago with repeat purchase
    order1a = ShopifyOrder(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_order_id="cohort-1a",
        customer_id="cohort-customer-1",
        order_number="#C1001",
        currency="USD",
        total_amount=100.0,
        discount_amount=0.0,
        shipping_amount=0.0,
        refund_amount=0.0,
        is_refunded=False,
        order_created_at=period_start + timedelta(days=5),
    )
    db_session.add(order1a)

    order1b = ShopifyOrder(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_order_id="cohort-1b",
        customer_id="cohort-customer-1",
        order_number="#C1002",
        currency="USD",
        total_amount=120.0,
        discount_amount=0.0,
        shipping_amount=0.0,
        refund_amount=0.0,
        is_refunded=False,
        order_created_at=period_start + timedelta(days=35),
    )
    db_session.add(order1b)

    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/retention/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify cohort data exists
    assert len(data["cohort_retention"]) > 0
    cohort = data["cohort_retention"][0]
    assert "cohort_month" in cohort
    assert "cohort_size" in cohort
    assert "retention_rate_month_1" in cohort
