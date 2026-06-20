"""Tests for subscription plans endpoints."""

from __future__ import annotations

from typing import Any

import jwt
from backend.app.db.models import SubscriptionPlan
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def test_list_subscription_plans_public(client: Any, db_session: Any) -> None:
    """Test public endpoint lists only active plans."""
    # Create 2 active plans and 1 inactive
    plan1 = SubscriptionPlan(
        slug="starter",
        name="Starter",
        description="For small teams",
        price_monthly=49.0,
        price_annual=490.0,
        features=["dashboards", "basic_recommendations"],
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=1,
    )
    plan2 = SubscriptionPlan(
        slug="professional",
        name="Professional",
        description="For growing teams",
        price_monthly=149.0,
        price_annual=1490.0,
        features=["dashboards", "simulations"],
        limits={"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200},
        is_active=True,
        sort_order=2,
    )
    plan3 = SubscriptionPlan(
        slug="legacy",
        name="Legacy Plan",
        description="No longer available",
        price_monthly=99.0,
        price_annual=990.0,
        features=["dashboards"],
        limits={"seat_limit": 10, "connector_limit": 5, "recommendation_limit": 100},
        is_active=False,
        sort_order=99,
    )
    db_session.add_all([plan1, plan2, plan3])
    db_session.commit()

    # Make request without authentication
    response = client.get("/subscription-plans")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Only active plans
    assert data[0]["slug"] == "starter"  # Sorted by sort_order
    assert data[1]["slug"] == "professional"
    assert "legacy" not in [p["slug"] for p in data]


def test_get_subscription_plan_by_slug(client: Any, db_session: Any) -> None:
    """Test get plan by slug."""
    plan = SubscriptionPlan(
        slug="starter",
        name="Starter",
        description="For small teams",
        price_monthly=49.0,
        price_annual=490.0,
        features=["dashboards", "basic_recommendations", "email_alerts"],
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.commit()

    response = client.get("/subscription-plans/starter")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "starter"
    assert data["name"] == "Starter"
    assert data["price_monthly"] == 49.0
    assert data["price_annual"] == 490.0
    assert "dashboards" in data["features"]
    assert data["limits"]["seat_limit"] == 5


def test_get_subscription_plan_not_found(client: Any) -> None:
    """Test 404 when plan doesn't exist."""
    response = client.get("/subscription-plans/nonexistent")
    assert response.status_code == 404


def test_get_subscription_plan_inactive_not_found(
    client: Any, db_session: Any
) -> None:
    """Test inactive plans are not returned by public endpoint."""
    plan = SubscriptionPlan(
        slug="legacy",
        name="Legacy",
        description="Old plan",
        price_monthly=99.0,
        price_annual=990.0,
        features=["dashboards"],
        limits={"seat_limit": 10, "connector_limit": 5, "recommendation_limit": 100},
        is_active=False,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.commit()

    response = client.get("/subscription-plans/legacy")
    assert response.status_code == 404


def test_create_subscription_plan_super_admin(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test super-admin can create new plan."""
    # Mark user as platform admin
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
        "slug": "enterprise",
        "name": "Enterprise",
        "description": "For large organizations with custom needs",
        "price_monthly": 499.0,
        "price_annual": 4990.0,
        "features": ["dashboards", "simulations", "api_access", "sso"],
        "limits": {
            "seat_limit": 50,
            "connector_limit": 999,
            "recommendation_limit": 999,
        },
        "is_active": True,
        "sort_order": 3,
    }

    response = client.post(
        "/admin/subscription-plans",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "enterprise"
    assert data["name"] == "Enterprise"
    assert data["price_monthly"] == 499.0
    assert len(data["features"]) == 4
    assert data["limits"]["seat_limit"] == 50


def test_create_subscription_plan_duplicate_slug(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test cannot create plan with duplicate slug."""
    user.is_platform_admin = True
    db_session.commit()

    # Create existing plan
    plan = SubscriptionPlan(
        slug="starter",
        name="Starter",
        description="Existing",
        price_monthly=49.0,
        price_annual=490.0,
        features=[],
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
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
        "slug": "starter",  # Duplicate
        "name": "New Starter",
        "description": "Another starter plan",
        "price_monthly": 59.0,
        "price_annual": 590.0,
        "features": [],
        "limits": {
            "seat_limit": 5,
            "connector_limit": 3,
            "recommendation_limit": 50,
        },
    }

    response = client.post(
        "/admin/subscription-plans",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_subscription_plan_requires_super_admin(
    client: Any, user: Any
) -> None:
    """Test regular user cannot create plan."""
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    payload = {
        "slug": "test",
        "name": "Test",
        "description": "Test plan",
        "price_monthly": 10.0,
        "price_annual": 100.0,
        "features": [],
        "limits": {
            "seat_limit": 5,
            "connector_limit": 3,
            "recommendation_limit": 50,
        },
    }

    response = client.post(
        "/admin/subscription-plans",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_update_subscription_plan(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test super-admin can update plan."""
    user.is_platform_admin = True
    db_session.commit()

    plan = SubscriptionPlan(
        slug="starter",
        name="Starter",
        description="Original description",
        price_monthly=49.0,
        price_annual=490.0,
        features=["dashboards"],
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
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
        "name": "Starter Plus",
        "price_monthly": 59.0,
        "features": ["dashboards", "basic_recommendations"],
        "limits": {
            "seat_limit": 10,
            "connector_limit": 5,
            "recommendation_limit": 100,
        },
    }

    response = client.patch(
        f"/admin/subscription-plans/{plan.id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Starter Plus"
    assert data["price_monthly"] == 59.0
    assert data["price_annual"] == 490.0  # Unchanged
    assert len(data["features"]) == 2
    assert data["limits"]["seat_limit"] == 10


def test_deactivate_subscription_plan(
    client: Any, db_session: Any, user: Any
) -> None:
    """Test super-admin can deactivate plan."""
    user.is_platform_admin = True
    db_session.commit()

    plan = SubscriptionPlan(
        slug="old-plan",
        name="Old Plan",
        description="To be deactivated",
        price_monthly=99.0,
        price_annual=990.0,
        features=[],
        limits={"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50},
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
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

    response = client.delete(
        f"/admin/subscription-plans/{plan.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify plan is deactivated
    db_session.refresh(plan)
    assert plan.is_active is False

    # Verify public endpoint no longer returns it
    list_response = client.get("/subscription-plans")
    assert len(list_response.json()) == 0
