"""Tests for feature flag enforcement on endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import jwt
from backend.app.db.models import (
    FeatureFlag,
    SubscriptionPlan,
    Tenant,
    TenantFeatureFlag,
)
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from sqlalchemy import select


def get_or_create_flag(
    db_session: Any,
    slug: str,
    name: str,
    description: str,
    category: str,
    is_available: bool,
    default_enabled: bool,
) -> FeatureFlag:
    """Get existing flag or create new one."""
    flag = db_session.scalar(select(FeatureFlag).where(FeatureFlag.slug == slug))
    if not flag:
        flag = FeatureFlag(
            slug=slug,
            name=name,
            description=description,
            category=category,
            is_available=is_available,
            default_enabled=default_enabled,
        )
        db_session.add(flag)
        db_session.commit()
    else:
        # Update properties for this test
        flag.is_available = is_available
        flag.default_enabled = default_enabled
        db_session.commit()
    return flag


def test_simulation_endpoint_requires_feature_flag(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test that simulation endpoints require the 'simulations' feature flag."""
    # Create simulations feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Attempt to access simulation endpoint without feature enabled
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "simulations" in response.json()["detail"].lower()


def test_simulation_endpoint_with_feature_enabled_by_default(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test that simulation endpoints work when feature is enabled by default."""
    # Create simulations feature flag (default enabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=True,
    )

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Access simulation endpoint with feature enabled by default
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should succeed (200 OK, returns list of simulations)
    assert response.status_code == 200


def test_simulation_endpoint_with_feature_enabled_by_plan(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test simulation endpoints work when feature is enabled via plan."""
    # Create simulations feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create subscription plan with simulations feature
    plan = SubscriptionPlan(
        slug="professional",
        name="Professional",
        description="Professional plan",
        price_monthly=149.0,
        price_annual=1490.0,
        features=["dashboards", "simulations", "custom_segments"],
        limits={"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.commit()

    # Update tenant to use professional plan
    tenant.billing_plan = "professional"
    db_session.commit()

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Access simulation endpoint with feature enabled via plan
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should succeed
    assert response.status_code == 200


def test_simulation_endpoint_with_feature_enabled_by_override(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test simulation endpoints work when feature enabled via override."""
    # Create simulations feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create tenant override enabling the feature
    override = TenantFeatureFlag(
        tenant_id=tenant.id,
        feature_flag_slug="simulations",
        is_enabled=True,
        enabled_at=datetime.now(UTC),
    )
    db_session.add(override)
    db_session.commit()

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Access simulation endpoint with feature enabled via override
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should succeed
    assert response.status_code == 200


def test_simulation_endpoint_override_disables_plan_feature(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test that tenant override can disable a feature enabled by plan."""
    # Create simulations feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create subscription plan with simulations feature
    plan = SubscriptionPlan(
        slug="professional",
        name="Professional",
        description="Professional plan",
        price_monthly=149.0,
        price_annual=1490.0,
        features=["dashboards", "simulations"],
        limits={"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.commit()

    # Update tenant to use professional plan
    tenant.billing_plan = "professional"
    db_session.commit()

    # Create tenant override DISABLING the feature (overrides plan)
    override = TenantFeatureFlag(
        tenant_id=tenant.id,
        feature_flag_slug="simulations",
        is_enabled=False,
        disabled_at=datetime.now(UTC),
    )
    db_session.add(override)
    db_session.commit()

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Attempt to access simulation endpoint
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should fail - override disables it
    assert response.status_code == 403
    assert "simulations" in response.json()["detail"].lower()


def test_custom_segments_endpoint_requires_feature_flag(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test custom segments endpoints require 'custom_segments' flag."""
    # Create custom_segments feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="custom_segments",
        name="Custom Segments",
        description="Custom customer segments",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Attempt to access custom segments endpoint without feature enabled
    response = client.get(
        f"/tenants/{tenant.id}/retention/custom-segments",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "custom_segments" in response.json()["detail"].lower()


def test_custom_segments_endpoint_with_feature_enabled(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test that custom segments endpoints work when feature is enabled."""
    # Create custom_segments feature flag (default enabled)
    get_or_create_flag(
        db_session,
        slug="custom_segments",
        name="Custom Segments",
        description="Custom customer segments",
        category="analytics",
        is_available=True,
        default_enabled=True,
    )

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Access custom segments endpoint with feature enabled
    response = client.get(
        f"/tenants/{tenant.id}/retention/custom-segments",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should succeed
    assert response.status_code == 200


def test_unavailable_feature_flag_always_denies_access(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test unavailable feature denies access despite plan/override."""
    # Create simulations feature flag marked as unavailable
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=False,  # Not available
        default_enabled=True,
    )

    # Create subscription plan with simulations feature
    plan = SubscriptionPlan(
        slug="professional",
        name="Professional",
        description="Professional plan",
        price_monthly=149.0,
        price_annual=1490.0,
        features=["dashboards", "simulations"],
        limits={"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    tenant.billing_plan = "professional"
    db_session.commit()

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Attempt to access simulation endpoint
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should fail - feature is not available
    assert response.status_code == 403


def test_feature_enforcement_works_on_create_endpoint(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test that feature enforcement works on POST endpoints (not just GET)."""
    # Create custom_segments feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="custom_segments",
        name="Custom Segments",
        description="Custom customer segments",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create token for user
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Attempt to create custom segment without feature enabled
    response = client.post(
        f"/tenants/{tenant.id}/retention/custom-segments",
        json={
            "name": "High Value Customers",
            "description": "Customers with AOV > $500",
            "filter_expression": {"aov": {"gt": 500}},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should fail
    assert response.status_code == 403
    assert "custom_segments" in response.json()["detail"].lower()


def test_feature_enforcement_resolution_order(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test that feature resolution follows override > plan > default."""
    from backend.app.db.models import Role, TenantMembership
    from backend.tests.conftest import seed_system_roles_for_tenant
    from sqlalchemy import select

    # Create a tenant
    tenant = Tenant(
        name="Test Tenant Resolution",
        slug="test-tenant-resolution",
        billing_plan="starter",
    )
    db_session.add(tenant)
    db_session.commit()

    # Create a role with permissions for this tenant
    seed_system_roles_for_tenant(db_session, tenant.id)

    # Get the operations_inventory_manager role for membership
    role = db_session.scalar(
        select(Role).where(
            Role.tenant_id == tenant.id,
            Role.name == "operations_inventory_manager",
            Role.is_system.is_(True),
        )
    )

    # Create membership for user in this tenant
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_inventory_manager",
        role_id=role.id,
    )
    db_session.add(membership)
    db_session.commit()

    # Create simulations feature flag (default disabled)
    get_or_create_flag(
        db_session,
        slug="simulations",
        name="Simulations",
        description="Simulation engine",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )

    # Create starter plan WITHOUT simulations
    starter_plan = SubscriptionPlan(
        slug="starter",
        name="Starter",
        description="Starter plan",
        price_monthly=49.0,
        price_annual=490.0,
        features=["dashboards"],  # No simulations
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=0,
    )
    db_session.add(starter_plan)
    db_session.commit()

    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Step 1: Default is False, plan doesn't include it -> should fail
    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    # Step 2: Add override enabling it -> should succeed
    override = TenantFeatureFlag(
        tenant_id=tenant.id,
        feature_flag_slug="simulations",
        is_enabled=True,
        enabled_at=datetime.now(UTC),
    )
    db_session.add(override)
    db_session.commit()

    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    # Step 3: Update override to disable -> should fail again
    override.is_enabled = False
    override.disabled_at = datetime.now(UTC)
    db_session.commit()

    response = client.get(
        f"/tenants/{tenant.id}/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
