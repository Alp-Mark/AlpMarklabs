"""E8: Navigation menu endpoint tests.

Tests for GET /me/navigation endpoint that returns persona-specific menu
structure based on role, permissions, and feature flags.
"""

from typing import Any

import jwt
import pytest
from backend.app.db.models import (
    AlertEventLog,
    FeatureFlag,
    Recommendation,
    TenantMembership,
)
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from sqlalchemy import select


def _make_token(email: str) -> str:
    """Create a test JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "user"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


@pytest.fixture
def client() -> Any:
    """Test client fixture."""
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_get_navigation_executive_owner_with_simulations(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Executive owner gets admin sections with simulations enabled."""
    # Update membership to executive_owner
    membership = db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership:
        membership.role = "executive_owner"
        db_session.commit()

    # Enable simulations feature
    simulations_flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not simulations_flag:
        simulations_flag = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="What-if scenario simulations",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(simulations_flag)
        db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_role"] == "executive_owner"
    assert data["tenant_id"] == str(tenant.id)
    assert len(data["menu_items"]) > 0

    # Check intelligence section items
    intelligence_items = [
        item for item in data["menu_items"] if item["section"] == "intelligence"
    ]
    # Dashboard, Recommendations, Simulations, Alerts
    assert len(intelligence_items) >= 4

    labels = {item["label"] for item in intelligence_items}
    assert "Dashboard" in labels
    assert "Recommendations" in labels
    # Should appear for executive_owner with feature enabled
    assert "Simulations" in labels
    assert "Alerts" in labels

    # Check admin section items (executive_owner has admin access)
    admin_items = [item for item in data["menu_items"] if item["section"] == "admin"]
    assert len(admin_items) >= 4  # Integrations, Team, Billing, Settings

    admin_labels = {item["label"] for item in admin_items}
    assert "Integrations" in admin_labels
    assert "Team" in admin_labels
    assert "Billing" in admin_labels
    assert "Settings" in admin_labels


def test_get_navigation_growth_manager_no_simulations(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Growth manager without simulations feature sees reduced menu."""
    # Update membership to growth_performance_manager
    membership = db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership:
        membership.role = "growth_performance_manager"
        db_session.commit()

    # Disable simulations feature by setting default_enabled=False
    simulations_flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if simulations_flag:
        simulations_flag.default_enabled = False
        db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_role"] == "growth_performance_manager"

    # Intelligence items only (no admin section for growth manager)
    intelligence_items = [
        item for item in data["menu_items"] if item["section"] == "intelligence"
    ]
    labels = {item["label"] for item in intelligence_items}

    assert "Dashboard" in labels
    assert "Recommendations" in labels
    assert "Alerts" in labels
    assert "Simulations" not in labels  # Should NOT appear when feature disabled

    # No admin section for growth manager
    admin_items = [item for item in data["menu_items"] if item["section"] == "admin"]
    assert len(admin_items) == 0


def test_get_navigation_brand_admin_no_dashboards(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Brand admin sees only admin section, no intelligence dashboards."""
    # Update membership to brand_admin
    membership = db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership:
        membership.role = "brand_admin"
        db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["user_role"] == "brand_admin"

    # No intelligence section for brand_admin
    intelligence_items = [
        item for item in data["menu_items"] if item["section"] == "intelligence"
    ]
    assert len(intelligence_items) == 0

    # Admin section only
    admin_items = [item for item in data["menu_items"] if item["section"] == "admin"]
    assert len(admin_items) >= 4

    admin_labels = {item["label"] for item in admin_items}
    assert "Integrations" in admin_labels
    assert "Team" in admin_labels
    assert "Billing" in admin_labels
    assert "Settings" in admin_labels


def test_get_navigation_badge_counts(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Badge counts reflect unread alerts and pending recommendations."""
    # Update membership to executive_owner
    membership = db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership:
        membership.role = "executive_owner"
        db_session.commit()

    # Create unread alerts
    alert1 = AlertEventLog(
        tenant_id=tenant.id,
        alert_id="alert-001",
        alert_type="early_warning",
        event_type="created",
        event_data={},
    )
    alert2 = AlertEventLog(
        tenant_id=tenant.id,
        alert_id="alert-002",
        alert_type="threshold_breach",
        event_type="created",
        event_data={},
    )
    db_session.add_all([alert1, alert2])

    # Create pending recommendations
    from datetime import date

    rec1 = Recommendation(
        tenant_id=tenant.id,
        rule_id="test_rule_1",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="Meta Ads",
        signal_summary="CAC increased 20%",
        suggested_action="Reduce Meta spend 15%",
        confidence_level="high",
        confidence_score=0.75,
        data_freshness_context="Last synced 2 hours ago",
        status="new",
    )
    rec2 = Recommendation(
        tenant_id=tenant.id,
        rule_id="test_rule_2",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="Email campaigns",
        signal_summary="Repeat rate declining",
        suggested_action="Launch winback sequence",
        confidence_level="medium",
        confidence_score=0.65,
        data_freshness_context="Last synced 1 day ago",
        status="new",
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Find Alerts menu item and check badge
    alerts_item = next(
        (item for item in data["menu_items"] if item["label"] == "Alerts"),
        None,
    )
    assert alerts_item is not None
    assert alerts_item["badge_count"] == 2  # 2 unread alerts

    # Find Recommendations menu item and check badge
    recs_item = next(
        (item for item in data["menu_items"] if item["label"] == "Recommendations"),
        None,
    )
    assert recs_item is not None
    assert recs_item["badge_count"] == 2  # 2 pending recommendations


def test_get_navigation_404_tenant_not_found(
    client: Any,
    db_session: Any,
    user: Any,
) -> None:
    """E8: Returns 404 if tenant not found."""
    import uuid

    fake_tenant_id = uuid.uuid4()
    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={fake_tenant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert "tenant not found" in response.json()["detail"].lower()


def test_get_navigation_403_user_not_member(
    client: Any,
    db_session: Any,
    other_tenant: Any,
    user: Any,
) -> None:
    """E8: Returns 403 if user is not a member of the tenant."""
    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={other_tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_get_navigation_all_roles_have_items(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: All role types receive at least one menu item."""
    roles = [
        "brand_admin",
        "executive_owner",
        "growth_performance_manager",
        "retention_crm_manager",
        "finance_controller",
        "operations_inventory_manager",
    ]

    for role in roles:
        # Update membership role
        membership = db_session.scalar(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant.id,
                TenantMembership.user_id == user.id,
            )
        )
        if membership:
            membership.role = role
            db_session.commit()

        token = _make_token(user.email)
        response = client.get(
            f"/me/navigation?tenant_id={tenant.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200, f"Failed for role: {role}"
        data = response.json()

        assert data["user_role"] == role
        assert len(data["menu_items"]) > 0, f"No menu items for role: {role}"
        assert all(
            "section" in item for item in data["menu_items"]
        ), f"Missing section for role: {role}"
        assert all(
            "path" in item for item in data["menu_items"]
        ), f"Missing path for role: {role}"


def test_get_navigation_menu_item_structure(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Menu items have correct structure with all required fields."""
    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Each menu item must have all required fields
    required_fields = ["section", "label", "path", "icon", "enabled", "order"]

    for item in data["menu_items"]:
        for field in required_fields:
            assert field in item, f"Missing field '{field}' in menu item"

        # Validate types
        assert isinstance(item["section"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["path"], str)
        assert isinstance(item["icon"], str)
        assert isinstance(item["enabled"], bool)
        assert isinstance(item["order"], int)
        # badge_count can be None or int
        assert item.get("badge_count") is None or isinstance(
            item.get("badge_count"), int
        )


def test_get_navigation_retention_manager_has_segments(
    client: Any,
    db_session: Any,
    tenant: Any,
    user: Any,
) -> None:
    """E8: Retention manager sees Segments menu when custom_segments feature enabled."""
    # Update membership to retention_crm_manager
    membership = db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership:
        membership.role = "retention_crm_manager"
        db_session.commit()

    # Enable custom_segments feature
    segments_flag = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "custom_segments")
    )
    if not segments_flag:
        segments_flag = FeatureFlag(
            slug="custom_segments",
            name="Custom Segments",
            description="Create and manage custom customer segments",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(segments_flag)
        db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/me/navigation?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Check for Segments menu item
    labels = {item["label"] for item in data["menu_items"]}
    assert "Segments" in labels
