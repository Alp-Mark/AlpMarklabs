"""Tests for growth dashboard endpoint."""

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


def test_get_growth_dashboard_success(
    client: TestClient, db_session: Session
) -> None:
    """Test successful growth dashboard retrieval with multi-channel data."""
    # Create tenant
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    # Seed roles
    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # Create user with growth_performance_manager role
    user = User(
        id=uuid.uuid4(),
        email="growth@test.com",
        full_name="Growth Manager",
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
    for i in range(20):
        order = ShopifyOrder(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id=f"order-{i}",
            customer_id=f"cust-{i % 10}",  # 10 unique customers
            order_number=f"#{2000 + i}",
            currency="USD",
            total_amount=150.0 + (i * 5),
            discount_amount=10.0,
            shipping_amount=8.0,
            refund_amount=0.0,
            is_refunded=False,
            order_created_at=period_start + timedelta(days=i),
        )
        db_session.add(order)

    # Add Meta ad spend across 3 campaigns
    for i in range(20):
        meta_spend = MetaAdSpend(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_campaign_id=f"meta-{i % 3}",  # 3 campaigns
            campaign_name=f"Meta Campaign {i % 3}",
            spend_date=period_start + timedelta(days=i),
            currency="USD",
            spend_amount=100.0 + (i * 3),
        )
        db_session.add(meta_spend)

    # Add Google ad spend across 2 campaigns
    for i in range(15):
        google_spend = GoogleAdSpend(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_campaign_id=f"google-{i % 2}",  # 2 campaigns
            campaign_name=f"Google Campaign {i % 2}",
            spend_date=period_start + timedelta(days=i * 2),
            currency="USD",
            spend_amount=80.0 + (i * 4),
        )
        db_session.add(google_spend)

    db_session.commit()

    # Make request
    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "total_spend" in data
    assert "total_revenue" in data
    assert "blended_roas" in data
    assert "total_orders" in data
    assert "total_new_customers" in data
    assert "blended_cac" in data
    assert "channel_performance" in data
    assert "top_campaigns" in data
    assert "underperforming_campaigns" in data
    assert "period_start" in data
    assert "period_end" in data

    # Verify calculations
    assert data["total_spend"] > 0
    assert data["total_revenue"] > 0
    assert data["blended_roas"] is not None
    assert data["total_orders"] == 20

    # Verify channel breakdown
    assert len(data["channel_performance"]) == 2  # Meta and Google
    channels = {c["channel"] for c in data["channel_performance"]}
    assert channels == {"meta", "google_ads"}

    # Verify campaigns exist
    assert len(data["top_campaigns"]) > 0
    assert all("campaign_id" in c for c in data["top_campaigns"])
    assert all("roas" in c for c in data["top_campaigns"])


def test_get_growth_dashboard_default_period(
    client: TestClient, db_session: Session
) -> None:
    """Test growth dashboard with default 30-day period."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-default-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="growth2@test.com",
        full_name="Growth Manager 2",
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
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify defaults
    assert data["period_end"] == date.today().isoformat()
    expected_start = (date.today() - timedelta(days=30)).isoformat()
    assert data["period_start"] == expected_start


def test_get_growth_dashboard_requires_permission(
    client: TestClient, db_session: Session
) -> None:
    """Test that growth.view permission is required."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-perm-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    # User with retention role (no growth.view)
    user = User(
        id=uuid.uuid4(),
        email="retention@test.com",
        full_name="Retention User",
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
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_growth_dashboard_tenant_not_found(
    client: TestClient, db_session: Session
) -> None:
    """Test 404 when tenant doesn't exist."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-404-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="growth3@test.com",
        full_name="Growth Manager 3",
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
    fake_tenant_id = uuid.uuid4()
    response = client.get(
        f"/tenants/{fake_tenant_id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_get_growth_dashboard_invalid_period(
    client: TestClient, db_session: Session
) -> None:
    """Test validation when period_start > period_end."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-invalid-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="growth4@test.com",
        full_name="Growth Manager 4",
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
    today = date.today()
    response = client.get(
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": today.isoformat(),
            "period_end": (today - timedelta(days=10)).isoformat(),
        },
    )

    assert response.status_code == 400
    assert "period_start must be before" in response.json()["detail"]


def test_get_growth_dashboard_cross_tenant_isolation(
    client: TestClient, db_session: Session
) -> None:
    """Test tenant isolation."""
    # Create two tenants
    tenant1 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 1",
        slug=f"test-growth-iso1-{uuid.uuid4().hex[:8]}",
    )
    tenant2 = Tenant(
        id=uuid.uuid4(),
        name="Tenant 2",
        slug=f"test-growth-iso2-{uuid.uuid4().hex[:8]}",
    )
    db_session.add_all([tenant1, tenant2])
    db_session.commit()

    roles1 = seed_system_roles_for_tenant(db_session, tenant1.id)
    seed_system_roles_for_tenant(db_session, tenant2.id)

    # User for tenant1
    user = User(
        id=uuid.uuid4(),
        email="growth-iso@test.com",
        full_name="Growth Isolation User",
        password_hash="hash",
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    membership = TenantMembership(
        id=uuid.uuid4(),
        tenant_id=tenant1.id,
        user_id=user.id,
        role="growth_performance_manager",
        role_id=roles1["growth_performance_manager"].id,
    )
    db_session.add(membership)
    db_session.commit()

    token = _make_token(user.email)

    # Try to access tenant2
    response = client.get(
        f"/tenants/{tenant2.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_get_growth_dashboard_with_no_data(
    client: TestClient, db_session: Session
) -> None:
    """Test growth dashboard when tenant has no ad spend or orders."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-nodata-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="growth-nodata@test.com",
        full_name="Growth No Data User",
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
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Zero/null values for no data
    assert data["total_spend"] == 0.0
    assert data["total_revenue"] == 0.0
    assert data["blended_roas"] is None
    assert data["total_orders"] == 0
    assert len(data["channel_performance"]) == 0
    assert len(data["top_campaigns"]) == 0


def test_get_growth_dashboard_campaign_details(
    client: TestClient, db_session: Session
) -> None:
    """Test campaign-level details and underperforming detection."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Growth Test Corp",
        slug=f"test-growth-campaigns-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()

    roles = seed_system_roles_for_tenant(db_session, tenant.id)

    user = User(
        id=uuid.uuid4(),
        email="growth-campaigns@test.com",
        full_name="Growth Campaign User",
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

    # Create test data
    today = date.today()
    period_start = today - timedelta(days=15)

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
            customer_id=f"cust-{i}",
            order_number=f"#{3000 + i}",
            currency="USD",
            total_amount=200.0,
            discount_amount=0.0,
            shipping_amount=0.0,
            refund_amount=0.0,
            is_refunded=False,
            order_created_at=period_start + timedelta(days=i),
        )
        db_session.add(order)

    # Add low-spend Meta campaign (will likely have low ROAS due to attribution)
    spend = MetaAdSpend(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_campaign_id="meta-low-perf",
        campaign_name="Low Performance Campaign",
        spend_date=period_start,
        currency="USD",
        spend_amount=500.0,  # High spend
    )
    db_session.add(spend)

    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/growth/dashboard",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify campaign data
    assert len(data["top_campaigns"]) >= 1
    campaign = data["top_campaigns"][0]
    assert "campaign_id" in campaign
    assert "campaign_name" in campaign
    assert "channel" in campaign
    assert "spend" in campaign
    assert "is_underperforming" in campaign
