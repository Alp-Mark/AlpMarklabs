"""Tests for E4 - Support tickets lifecycle."""

from __future__ import annotations

from datetime import date, timedelta
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


def test_create_support_ticket(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """POST /support-tickets creates a new ticket."""
    token = _make_token(user.email)
    response = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "priority": "high",
            "issue_type": "integration_failure",
            "title": "Shopify sync failing",
            "description": "OAuth token expired",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["tenant_id"] == str(tenant.id)
    assert data["status"] == "open"
    assert data["priority"] == "high"
    assert data["issue_type"] == "integration_failure"
    assert data["title"] == "Shopify sync failing"
    assert data["description"] == "OAuth token expired"
    assert data["created_by_user_id"] == str(user.id)
    assert data["assigned_to_user_id"] is None
    assert data["resolution_summary"] is None
    assert data["closed_at"] is None


def test_create_ticket_defaults_to_medium_priority(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """Ticket defaults to medium priority if not specified."""
    token = _make_token(user.email)
    response = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "onboarding_help",
            "title": "Need help with setup",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "medium"


def test_create_ticket_404_if_tenant_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """POST /support-tickets returns 404 for nonexistent tenant."""
    token = _make_token(user.email)
    fake_tenant_id = "00000000-0000-0000-0000-000000000999"
    response = client.post(
        "/support-tickets",
        json={
            "tenant_id": fake_tenant_id,
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_list_support_tickets_returns_all_tickets(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /support-tickets returns all tickets."""
    token = _make_token(user.email)

    # Create 3 tickets
    for i in range(3):
        client.post(
            "/support-tickets",
            json={
                "tenant_id": str(tenant.id),
                "issue_type": "sync_error",
                "title": f"Ticket {i+1}",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    response = client.get(
        "/support-tickets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["tickets"]) == 3


def test_list_tickets_filter_by_status(
    client: Any, db_session: Any, tenant: Any, user: Any, other_user: Any
) -> None:
    """GET /support-tickets filters by status."""
    token = _make_token(user.email)

    # Create open ticket
    client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Open ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    # Create in_progress ticket
    in_progress_ticket = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "integration_failure",
            "title": "In progress ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    # Update to in_progress
    client.patch(
        f"/support-tickets/{in_progress_ticket['id']}",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by status=open
    response = client.get(
        "/support-tickets?status_filter=open",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tickets"][0]["status"] == "open"


def test_list_tickets_filter_by_priority(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /support-tickets filters by priority."""
    token = _make_token(user.email)

    # Create high priority ticket
    client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "priority": "high",
            "issue_type": "sync_error",
            "title": "High priority",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Create low priority ticket
    client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "priority": "low",
            "issue_type": "onboarding_help",
            "title": "Low priority",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by priority=high
    response = client.get(
        "/support-tickets?priority=high",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tickets"][0]["priority"] == "high"


def test_list_tickets_filter_by_tenant(
    client: Any, db_session: Any, tenant: Any, user: Any, other_tenant: Any
) -> None:
    """GET /support-tickets filters by tenant_id."""
    token = _make_token(user.email)

    # Create ticket for tenant1
    client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Tenant 1 ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Create ticket for tenant2
    client.post(
        "/support-tickets",
        json={
            "tenant_id": str(other_tenant.id),
            "issue_type": "integration_failure",
            "title": "Tenant 2 ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Filter by tenant1
    response = client.get(
        f"/support-tickets?tenant_id={tenant.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tickets"][0]["tenant_id"] == str(tenant.id)


def test_get_support_ticket_by_id(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /support-tickets/{id} returns single ticket."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "priority": "urgent",
            "issue_type": "integration_failure",
            "title": "Critical issue",
            "description": "System down",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Get by ID
    response = client.get(
        f"/support-tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["title"] == "Critical issue"
    assert data["priority"] == "urgent"


def test_get_ticket_404_if_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """GET /support-tickets/{id} returns 404 for nonexistent ticket."""
    token = _make_token(user.email)
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = client.get(
        f"/support-tickets/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_ticket_status(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id} updates status."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Update status
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


def test_update_ticket_assign_to_user(
    client: Any, db_session: Any, tenant: Any, user: Any, other_user: Any
) -> None:
    """PATCH /support-tickets/{id} assigns ticket to user (FR-093)."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Assign to other_user
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"assigned_to_user_id": str(other_user.id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["assigned_to_user_id"] == str(other_user.id)


def test_update_ticket_set_due_date(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id} sets due date (FR-093)."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Set due date
    due = (date.today() + timedelta(days=3)).isoformat()
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"due_date": due},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["due_date"] == due


def test_update_ticket_add_internal_notes(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id} adds internal notes (FR-099)."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Add internal note
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"internal_notes": "Contacted customer via email"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "Contacted customer via email" in data["internal_notes"]
    assert "[" in data["internal_notes"]  # Timestamp present

    # Add another note (appends)
    response2 = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"internal_notes": "Issue resolved"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert "Contacted customer via email" in data2["internal_notes"]
    assert "Issue resolved" in data2["internal_notes"]


def test_update_ticket_409_if_closed(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id} returns 409 for closed tickets."""
    token = _make_token(user.email)

    # Create and close ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    client.patch(
        f"/support-tickets/{ticket_id}/close",
        json={
            "resolution_summary": "Fixed OAuth token",
            "resolution_category": "integration_auth",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to update closed ticket
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_update_ticket_400_if_trying_to_close_via_patch(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id} returns 400 if trying to set status=closed."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Try to close via PATCH (should use /close endpoint)
    response = client.patch(
        f"/support-tickets/{ticket_id}",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_close_ticket_with_resolution(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id}/close closes ticket with resolution."""
    token = _make_token(user.email)

    # Create ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "integration_failure",
            "title": "OAuth expired",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    # Close with resolution
    response = client.patch(
        f"/support-tickets/{ticket_id}/close",
        json={
            "resolution_summary": (
                "Customer re-authenticated OAuth token. Sync resumed."
            ),
            "resolution_category": "integration_auth",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert (
        data["resolution_summary"]
        == "Customer re-authenticated OAuth token. Sync resumed."
    )
    assert data["resolution_category"] == "integration_auth"
    assert data["closed_at"] is not None


def test_close_ticket_409_if_already_closed(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id}/close returns 409 if already closed."""
    token = _make_token(user.email)

    # Create and close ticket
    create_resp = client.post(
        "/support-tickets",
        json={
            "tenant_id": str(tenant.id),
            "issue_type": "sync_error",
            "title": "Test ticket",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    ticket_id = create_resp.json()["id"]

    client.patch(
        f"/support-tickets/{ticket_id}/close",
        json={
            "resolution_summary": "Fixed",
            "resolution_category": "sync_config",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to close again
    response = client.patch(
        f"/support-tickets/{ticket_id}/close",
        json={
            "resolution_summary": "Another fix",
            "resolution_category": "sync_config",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_close_ticket_404_if_not_found(
    client: Any, db_session: Any, user: Any
) -> None:
    """PATCH /support-tickets/{id}/close returns 404 for nonexistent ticket."""
    token = _make_token(user.email)
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = client.patch(
        f"/support-tickets/{fake_id}/close",
        json={
            "resolution_summary": "Fixed",
            "resolution_category": "sync_config",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
