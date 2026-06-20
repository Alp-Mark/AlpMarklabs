"""Tests for E5 - User notification preferences and inbox."""

from __future__ import annotations

from typing import Any

import jwt
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_token(email: str, role: str = "super_admin") -> str:
    """Create JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


# User Notification Preferences Tests


def test_create_user_notification_preference(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """POST /user-notification-preferences creates preference."""
    token = _make_token(user.email, "user")
    response = client.post(
        "/user-notification-preferences",
        json={
            "tenant_id": str(tenant.id),
            "alert_category": "kpi_drift",
            "channel": "email",
            "is_enabled": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["tenant_id"] == str(tenant.id)
    assert data["alert_category"] == "kpi_drift"
    assert data["channel"] == "email"
    assert data["is_enabled"] is True


def test_create_preference_defaults_to_both_channel(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Preference defaults to 'both' channel."""
    token = _make_token(user.email, "user")
    response = client.post(
        "/user-notification-preferences",
        json={
            "tenant_id": str(tenant.id),
            "alert_category": "stockout_risk",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "both"


def test_create_preference_409_if_duplicate(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """POST /user-notification-preferences returns 409 for duplicate."""
    token = _make_token(user.email, "user")

    # Create first preference
    client.post(
        "/user-notification-preferences",
        json={
            "tenant_id": str(tenant.id),
            "alert_category": "sync_failure",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to create duplicate
    response = client.post(
        "/user-notification-preferences",
        json={
            "tenant_id": str(tenant.id),
            "alert_category": "sync_failure",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_list_user_notification_preferences(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /user-notification-preferences lists user preferences."""
    token = _make_token(user.email, "user")

    # Create 2 preferences
    client.post(
        "/user-notification-preferences",
        json={"tenant_id": str(tenant.id), "alert_category": "kpi_drift"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/user-notification-preferences",
        json={"tenant_id": str(tenant.id), "alert_category": "churn_risk"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/user-notification-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["preferences"]) == 2


def test_list_preferences_filters_by_tenant(
    client: Any, db_session: Any, tenant: Any, other_tenant: Any, user: Any
) -> None:
    """GET /user-notification-preferences filters by tenant_id."""
    token = _make_token(user.email, "user")

    # Create preferences for both tenants
    client.post(
        "/user-notification-preferences",
        json={"tenant_id": str(tenant.id), "alert_category": "kpi_drift"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/user-notification-preferences",
        json={"tenant_id": str(other_tenant.id), "alert_category": "churn_risk"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by tenant
    response = client.get(
        f"/user-notification-preferences?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["preferences"][0]["tenant_id"] == str(tenant.id)


def test_update_user_notification_preference(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /user-notification-preferences/{id} updates preference."""
    token = _make_token(user.email, "user")

    # Create preference
    create_resp = client.post(
        "/user-notification-preferences",
        json={
            "tenant_id": str(tenant.id),
            "alert_category": "kpi_drift",
            "channel": "email",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    preference_id = create_resp.json()["id"]

    # Update preference
    response = client.patch(
        f"/user-notification-preferences/{preference_id}",
        json={"channel": "in_app", "is_enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "in_app"
    assert data["is_enabled"] is False


def test_update_preference_404_if_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """PATCH /user-notification-preferences/{id} returns 404."""
    token = _make_token(user.email, "user")
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = client.patch(
        f"/user-notification-preferences/{fake_id}",
        json={"channel": "email"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_user_notification_preference(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """DELETE /user-notification-preferences/{id} removes preference."""
    token = _make_token(user.email, "user")

    # Create preference
    create_resp = client.post(
        "/user-notification-preferences",
        json={"tenant_id": str(tenant.id), "alert_category": "kpi_drift"},
        headers={"Authorization": f"Bearer {token}"},
    )
    preference_id = create_resp.json()["id"]

    # Delete preference
    response = client.delete(
        f"/user-notification-preferences/{preference_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    # Verify deleted
    get_resp = client.get(
        "/user-notification-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.json()["total"] == 0


def test_delete_preference_404_if_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """DELETE /user-notification-preferences/{id} returns 404."""
    token = _make_token(user.email, "user")
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = client.delete(
        f"/user-notification-preferences/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


# Notification Inbox Tests


def test_create_notification(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """POST /notifications creates notification."""
    token = _make_token(user.email, "super_admin")
    response = client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "kpi_drift",
            "title": "CAC increased by 25%",
            "message": "Your CAC has increased significantly over the past week.",
            "severity": "warning",
            "deep_link": "/dashboard/acquisition",
            "context_data": {"metric": "cac", "change_pct": 25},
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["user_id"] == str(user.id)
    assert data["notification_type"] == "kpi_drift"
    assert data["title"] == "CAC increased by 25%"
    assert data["severity"] == "warning"
    assert data["status"] == "unread"
    assert data["deep_link"] == "/dashboard/acquisition"
    assert data["context_data"]["metric"] == "cac"


def test_list_notifications_returns_all_for_user(
    client: Any, db_session: Any, tenant: Any, user: Any, other_user: Any
) -> None:
    """GET /notifications returns all notifications for user."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create 2 notifications for user
    for i in range(2):
        client.post(
            "/notifications",
            json={
                "tenant_id": str(tenant.id),
                "user_id": str(user.id),
                "notification_type": "kpi_drift",
                "title": f"Alert {i+1}",
                "message": f"Message {i+1}",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Create 1 for other_user (should not appear)
    client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(other_user.id),
            "notification_type": "churn_risk",
            "title": "Other user alert",
            "message": "Other message",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["notifications"]) == 2
    assert data["unread_count"] == 2


def test_list_notifications_filters_by_status(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /notifications filters by status."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create 2 notifications
    notif1 = client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "kpi_drift",
            "title": "Alert 1",
            "message": "Message 1",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()

    client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "churn_risk",
            "title": "Alert 2",
            "message": "Message 2",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Mark first as read
    client.patch(
        f"/notifications/{notif1['id']}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by unread
    response = client.get(
        "/notifications?status_filter=unread",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["status"] == "unread"


def test_list_notifications_filters_by_type_and_severity(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /notifications filters by notification_type and severity."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create notifications with different types/severities
    client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "kpi_drift",
            "title": "KPI alert",
            "message": "KPI message",
            "severity": "critical",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "sync_failure",
            "title": "Sync alert",
            "message": "Sync message",
            "severity": "warning",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Filter by type
    response = client.get(
        "/notifications?notification_type=kpi_drift",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1

    # Filter by severity
    response2 = client.get(
        "/notifications?severity=critical",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 200
    assert response2.json()["total"] == 1


def test_mark_notification_read(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /notifications/{id}/read marks notification as read."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create notification
    create_resp = client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "kpi_drift",
            "title": "Alert",
            "message": "Message",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    notification_id = create_resp.json()["id"]

    # Mark as read
    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "read"
    assert data["read_at"] is not None


def test_mark_notification_dismissed(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /notifications/{id}/dismiss marks notification as dismissed."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create notification
    create_resp = client.post(
        "/notifications",
        json={
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "notification_type": "kpi_drift",
            "title": "Alert",
            "message": "Message",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    notification_id = create_resp.json()["id"]

    # Mark as dismissed
    response = client.patch(
        f"/notifications/{notification_id}/dismiss",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dismissed"
    assert data["dismissed_at"] is not None


def test_mark_notification_read_404_if_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """PATCH /notifications/{id}/read returns 404."""
    token = _make_token(user.email, "user")
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = client.patch(
        f"/notifications/{fake_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_list_notifications_pagination(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /notifications respects limit and offset."""
    token = _make_token(user.email, "user")
    admin_token = _make_token(user.email, "super_admin")

    # Create 5 notifications
    for i in range(5):
        client.post(
            "/notifications",
            json={
                "tenant_id": str(tenant.id),
                "user_id": str(user.id),
                "notification_type": "kpi_drift",
                "title": f"Alert {i+1}",
                "message": f"Message {i+1}",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Get first page (limit 2)
    response = client.get(
        "/notifications?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["notifications"]) == 2

    # Get second page
    response2 = client.get(
        "/notifications?limit=2&offset=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["notifications"]) == 2
