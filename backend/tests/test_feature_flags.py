"""Tests for feature flags endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import jwt
from backend.app.db.models import FeatureFlag, SubscriptionPlan, TenantFeatureFlag
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def test_get_tenant_features_default(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test tenant features with defaults only."""
    from sqlalchemy import select

    # Get or create dashboards flag
    flag1 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "dashboards")
    )
    if not flag1:
        flag1 = FeatureFlag(
            slug="dashboards",
            name="Dashboards",
            description="Dashboard access",
            category="analytics",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(flag1)

    # Get or create simulations flag
    flag2 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag2:
        flag2 = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag2)
    else:
        # Update for this test
        flag2.default_enabled = False

    db_session.commit()

    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    response = client.get(
        f"/tenants/{tenant.id}/features",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # At least these 2, may have more

    # Find each feature
    dashboards = next(f for f in data if f["slug"] == "dashboards")
    simulations = next(f for f in data if f["slug"] == "simulations")

    assert dashboards["is_enabled"] is True
    assert dashboards["source"] == "default"
    assert simulations["is_enabled"] is False
    assert simulations["source"] == "default"


def test_get_tenant_features_from_plan(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test tenant features inherited from subscription plan."""
    from sqlalchemy import select

    # Create plan with features
    plan = SubscriptionPlan(
        slug="professional",
        name="Professional",
        description="Pro plan",
        price_monthly=149.0,
        price_annual=1490.0,
        features=["dashboards", "simulations", "api_access"],
        limits={"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.commit()

    # Update tenant to use this plan
    tenant.billing_plan = "professional"
    db_session.commit()

    # Get or create feature flags
    flag1 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "dashboards")
    )
    if not flag1:
        flag1 = FeatureFlag(
            slug="dashboards",
            name="Dashboards",
            description="Dashboard access",
            category="analytics",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag1)
    else:
        flag1.default_enabled = False

    flag2 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag2:
        flag2 = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag2)
    else:
        flag2.default_enabled = False

    flag3 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "api_access")
    )
    if not flag3:
        flag3 = FeatureFlag(
            slug="api_access",
            name="API Access",
            description="API access",
            category="integrations",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag3)
    else:
        flag3.default_enabled = False

    db_session.commit()

    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    response = client.get(
        f"/tenants/{tenant.id}/features",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # Should have at least our 3 features
    assert len(data) >= 3

    # All our features should be enabled from plan
    for slug in ["dashboards", "simulations", "api_access"]:
        feature = next(f for f in data if f["slug"] == slug)
        assert feature["is_enabled"] is True
        assert feature["source"] == "plan"


def test_get_tenant_features_with_override(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test tenant features with overrides."""
    from sqlalchemy import select

    # Get existing feature flag from tenant fixture (or create if not exists)
    flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag:
        flag = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag)
        db_session.commit()
    else:
        # Update to have default_enabled=False for this test
        flag.default_enabled = False
        db_session.commit()

    # Create override enabling it
    override = TenantFeatureFlag(
        tenant_id=tenant.id,
        feature_flag_slug="simulations",
        is_enabled=True,
        enabled_at=datetime.now(UTC),
    )
    db_session.add(override)
    db_session.commit()

    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    response = client.get(
        f"/tenants/{tenant.id}/features",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1  # At least simulations, may have more from fixture
    # Find simulations in results
    sim = [f for f in data if f["slug"] == "simulations"][0]
    assert sim["is_enabled"] is True
    assert sim["source"] == "override"


def test_list_feature_flags_super_admin(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test super-admin can list all feature flags."""
    from sqlalchemy import select

    user.is_platform_admin = True
    db_session.commit()

    # Get or create dashboards flag
    flag1 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "dashboards")
    )
    if not flag1:
        flag1 = FeatureFlag(
            slug="dashboards",
            name="Dashboards",
            description="Dashboard access",
            category="analytics",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(flag1)

    # Get or create simulations flag
    flag2 = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag2:
        flag2 = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=False,
            default_enabled=False,
        )
        db_session.add(flag2)
    else:
        # Update properties for this test
        flag2.is_available = False
        flag2.default_enabled = False

    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    response = client.get(
        "/admin/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # At least these 2, may have more from migration
    # Find our flags
    dashboards = [f for f in data if f["slug"] == "dashboards"][0]
    simulations = [f for f in data if f["slug"] == "simulations"][0]
    assert dashboards["is_available"] is True
    assert simulations["is_available"] is False


def test_list_feature_flags_requires_super_admin(client: Any, user: Any) -> None:
    """Test regular user cannot list feature flags."""
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    response = client.get(
        "/admin/feature-flags",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_create_feature_flag_success(client: Any, db_session: Any, user: Any) -> None:
    """Test super-admin can create feature flag."""
    user.is_platform_admin = True
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {
        "slug": "new-feature",
        "name": "New Feature",
        "description": "A brand new feature for testing",
        "category": "platform",
        "is_available": True,
        "default_enabled": False,
    }

    response = client.post(
        "/admin/feature-flags",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "new-feature"
    assert data["name"] == "New Feature"
    assert data["is_available"] is True
    assert data["default_enabled"] is False


def test_create_feature_flag_duplicate_slug(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test cannot create feature flag with duplicate slug."""
    user.is_platform_admin = True
    db_session.commit()

    # Create existing flag
    flag = FeatureFlag(
        slug="existing",
        name="Existing",
        description="Already exists",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )
    db_session.add(flag)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {
        "slug": "existing",
        "name": "Duplicate",
        "description": "Trying to duplicate",
        "category": "analytics",
    }

    response = client.post(
        "/admin/feature-flags",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_update_feature_flag_success(client: Any, db_session: Any, user: Any) -> None:
    """Test super-admin can update feature flag."""
    user.is_platform_admin = True
    db_session.commit()

    flag = FeatureFlag(
        slug="test-flag",
        name="Test Flag",
        description="Original description",
        category="analytics",
        is_available=True,
        default_enabled=False,
    )
    db_session.add(flag)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {
        "name": "Updated Flag",
        "description": "Updated description",
        "is_available": False,
    }

    response = client.patch(
        f"/admin/feature-flags/{flag.id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Flag"
    assert data["description"] == "Updated description"
    assert data["is_available"] is False
    assert data["slug"] == "test-flag"  # Unchanged


def test_toggle_tenant_feature_enable(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test super-admin can enable feature for tenant."""
    from sqlalchemy import select

    user.is_platform_admin = True
    db_session.commit()

    # Get existing feature flag from tenant fixture (or create if not exists)
    flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag:
        flag = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=False,
        )
        db_session.add(flag)
        db_session.commit()
    else:
        # Update to have default_enabled=False for this test
        flag.default_enabled = False
        db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {"feature_slug": "simulations", "is_enabled": True}

    response = client.post(
        f"/admin/tenants/{tenant.id}/features/toggle",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "enabled" in response.json()["message"]

    # Verify override was created
    override = db_session.scalar(
        db_session.query(TenantFeatureFlag)
        .filter_by(tenant_id=tenant.id, feature_flag_slug="simulations")
        .statement
    )
    assert override is not None
    assert override.is_enabled is True
    assert override.enabled_at is not None


def test_toggle_tenant_feature_disable(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test super-admin can disable feature for tenant."""
    from sqlalchemy import select

    user.is_platform_admin = True
    db_session.commit()

    # Get existing feature flag from tenant fixture (or create if not exists)
    flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not flag:
        flag = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(flag)
        db_session.commit()

    # Create existing override (enabled)
    override = TenantFeatureFlag(
        tenant_id=tenant.id,
        feature_flag_slug="simulations",
        is_enabled=True,
        enabled_at=datetime.now(UTC),
    )
    db_session.add(override)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {"feature_slug": "simulations", "is_enabled": False}

    response = client.post(
        f"/admin/tenants/{tenant.id}/features/toggle",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "disabled" in response.json()["message"]

    # Verify override was updated
    db_session.refresh(override)
    assert override.is_enabled is False
    assert override.disabled_at is not None


def test_toggle_tenant_feature_not_found(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Test cannot toggle non-existent feature."""
    user.is_platform_admin = True
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {"feature_slug": "nonexistent", "is_enabled": True}

    response = client.post(
        f"/admin/tenants/{tenant.id}/features/toggle",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
