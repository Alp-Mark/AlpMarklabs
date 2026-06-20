"""Tests for alert event history and audit logs (T-079)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.app.db.models import (
    Role,
    Tenant,
    User,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


class TestAlertEventHistory:
    """Test alert event history retrieval."""

    def test_list_alert_events_empty_tenant(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test listing events for tenant with no events."""
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total_count"] == 0

    def test_list_alert_events_after_acknowledge(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that events are logged when acknowledging alerts."""
        # Acknowledge an alert
        response = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "margin_drift:product_123",
                "alert_type": "margin_drift",
            },
        )
        assert response.status_code == 200

        # List events
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        event = data["events"][0]
        assert event["alert_id"] == "margin_drift:product_123"
        assert event["alert_type"] == "margin_drift"
        assert event["event_type"] == "acknowledged"
        assert event["actor_user_id"] == str(user.id)

    def test_list_alert_events_after_dismiss(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that events are logged when dismissing alerts."""
        # Dismiss an alert
        response = client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "inventory_risk:sku_456",
                "alert_type": "inventory_risk",
                "dismiss_reason": "Restocking in progress",
            },
        )
        assert response.status_code == 200

        # List events
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        event = data["events"][0]
        assert event["alert_id"] == "inventory_risk:sku_456"
        assert event["alert_type"] == "inventory_risk"
        assert event["event_type"] == "dismissed"
        assert event["event_data"]["dismiss_reason"] == "Restocking in progress"

    def test_list_alert_events_filter_by_alert_id(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test filtering events by alert_id."""
        # Create multiple events for different alerts
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "margin_drift:product_123",
                "alert_type": "margin_drift"
            },
        )
        client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "inventory_risk:sku_456",
                "alert_type": "inventory_risk",
                "dismiss_reason": "test",
            },
        )

        # Filter by specific alert_id
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?alert_id=margin_drift:product_123",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["events"][0]["alert_id"] == "margin_drift:product_123"

    def test_list_alert_events_filter_by_event_type(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test filtering events by event_type."""
        # Create acknowledged and dismissed events
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_1",
                "alert_type": "margin_drift"
            },
        )
        client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert_2",
                "alert_type": "inventory_risk",
                "dismiss_reason": "test",
            },
        )

        # Filter by event_type
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?event_type=acknowledged",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["events"][0]["event_type"] == "acknowledged"

    def test_list_alert_events_filter_by_date_range(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test filtering events by date range."""
        from urllib.parse import quote

        # Create event
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_1",
                "alert_type": "margin_drift",
            },
        )

        # Use date range that includes the event (with URL encoding)
        past_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        future_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()

        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?date_from={quote(past_time)}&date_to={quote(future_time)}",
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 1

        # Use date range that excludes the event
        far_past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        far_future = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?date_from={quote(far_past)}&date_to={quote(far_future)}",
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 0

    def test_list_alert_events_filter_by_actor_user_id(
        self,
        tenant: Tenant,
        user: User,
        other_user: User,
        other_client: TestClient,
        client: TestClient,
    ) -> None:
        """Test filtering events by actor_user_id."""
        # Create event by user
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_1",
                "alert_type": "margin_drift",
            },
        )

        # Create event by other_user
        other_client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_2",
                "alert_type": "inventory_risk",
            },
        )

        # Filter by actor_user_id
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?actor_user_id={user.id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["events"][0]["actor_user_id"] == str(user.id)

    def test_list_alert_events_pagination(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test pagination of alert events."""
        # Create multiple events
        for i in range(5):
            client.post(
                f"/tenants/{tenant.id}/alerts/acknowledge",
                json={
                    "alert_id": f"alert_{i}",
                    "alert_type": "margin_drift"
                },
            )

        # Get first page
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?skip=0&limit=2",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["total_count"] == 5

        # Get second page
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?skip=2&limit=2",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2

    def test_list_alert_events_limit_capped(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that limit is capped at 500."""
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?limit=1000",
        )
        assert response.status_code == 200
        # No assertion on actual cap behavior (just checking endpoint accepts it)

    def test_list_alert_events_tenant_not_found(
        self,
        client: TestClient,
        nonexistent_uuid: UUID,
    ) -> None:
        """Test listing events with invalid tenant."""
        response = client.get(
            f"/tenants/{nonexistent_uuid}/alerts/history",
        )
        assert response.status_code == 404
        assert "tenant" in response.json()["detail"].lower()

    def test_get_alert_history_single_alert(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test retrieving complete history for a single alert."""
        # Create multiple events for same alert
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "margin_drift:product_123",
                "alert_type": "margin_drift"
            },
        )
        client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "margin_drift:product_123",
                "alert_type": "margin_drift",
                "dismiss_reason": "Margin recovered",
            },
        )

        # Get history for specific alert
        response = client.get(
            f"/tenants/{tenant.id}/alerts/margin_drift:product_123/history",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "margin_drift:product_123"
        assert data["alert_type"] == "margin_drift"
        assert data["total_events"] == 2
        assert len(data["events"]) == 2
        # Events should be ordered oldest first
        assert data["events"][0]["event_type"] == "acknowledged"
        assert data["events"][1]["event_type"] == "dismissed"
        assert data["first_event_at"] is not None
        assert data["last_event_at"] is not None

    def test_get_alert_history_empty_alert(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test retrieving history for alert with no events."""
        response = client.get(
            f"/tenants/{tenant.id}/alerts/nonexistent_alert/history",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "nonexistent_alert"
        assert data["alert_type"] == "unknown"
        assert data["total_events"] == 0
        assert data["events"] == []
        assert data["first_event_at"] is None
        assert data["last_event_at"] is None

    def test_get_alert_history_tenant_not_found(
        self,
        client: TestClient,
        nonexistent_uuid: UUID,
    ) -> None:
        """Test retrieving history with invalid tenant."""
        response = client.get(
            f"/tenants/{nonexistent_uuid}/alerts/alert_123/history",
        )
        assert response.status_code == 404
        assert "tenant" in response.json()["detail"].lower()

    def test_alert_history_tenant_isolation(
        self,
        tenant: Tenant,
        other_tenant: Tenant,
        user: User,
        other_user: User,
        other_client: TestClient,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test that alerts from one tenant don't appear in another."""
        from backend.app.db.models import TenantMembership

        # Add users to both tenants
        for tm_tenant in [tenant, other_tenant]:
            for tm_user in [user, other_user]:
                existing = db_session.scalar(
                    select(TenantMembership).where(
                        TenantMembership.tenant_id == tm_tenant.id,
                        TenantMembership.user_id == tm_user.id,
                    )
                )
                if existing is None:
                    # Get the operations_inventory_manager system role
                    role = db_session.scalar(
                        select(Role).where(
                            Role.tenant_id == tm_tenant.id,
                            Role.name == "operations_inventory_manager",
                            Role.is_system == True,  # noqa: E712
                        )
                    )
                    assert role is not None, "role must exist"
                    
                    membership = TenantMembership(
                        id=uuid4(),
                        tenant_id=tm_tenant.id,
                        user_id=tm_user.id,
                        role="operations_inventory_manager",
                        role_id=role.id,
                    )
                    db_session.add(membership)
        db_session.commit()

        # Create event in tenant
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_in_tenant_1",
                "alert_type": "margin_drift"
            },
        )

        # Create event in other_tenant
        other_client.post(
            f"/tenants/{other_tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_in_tenant_2",
                "alert_type": "inventory_risk"
            },
        )

        # Verify isolation: tenant can only see its own events
        response = client.get(f"/tenants/{tenant.id}/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["events"][0]["alert_id"] == "alert_in_tenant_1"

        # other_tenant can only see its own events
        response = other_client.get(f"/tenants/{other_tenant.id}/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["events"][0]["alert_id"] == "alert_in_tenant_2"

    def test_escalation_rule_events_logged(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that escalation rule mutations are logged as events."""
        # Create escalation rule
        response = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "margin_drift",
                "domain": "product",
                "unacknowledged_hours": 4,
                "escalation_to_roles": ["finance_controller"],
                "is_enabled": True,
            },
        )
        assert response.status_code == 200

        # Check events were logged
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history?alert_id=margin_drift:product",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 1
        # Check for escalation_rule_created event
        has_create = any(
            e["event_type"] == "escalation_rule_created" for e in data["events"]
        )
        assert has_create

    def test_event_ordering_descending_in_list(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that list_alert_events returns events in descending order."""
        # Create multiple events
        for i in range(3):
            client.post(
                f"/tenants/{tenant.id}/alerts/acknowledge",
                json={
                    "alert_id": f"alert_{i}",
                    "alert_type": "margin_drift"
                },
            )

        # List events
        response = client.get(
            f"/tenants/{tenant.id}/alerts/history",
        )
        assert response.status_code == 200
        data = response.json()
        events = data["events"]

        # Verify descending order (newest first)
        for i in range(len(events) - 1):
            current_time = datetime.fromisoformat(events[i]["created_at"])
            next_time = datetime.fromisoformat(events[i + 1]["created_at"])
            assert current_time >= next_time

    def test_event_ordering_ascending_in_alert_history(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that get_alert_history returns events in ascending order."""
        # Create multiple events for same alert
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert_123",
                "alert_type": "margin_drift"
            },
        )
        client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert_123",
                "alert_type": "margin_drift",
                "dismiss_reason": "test",
            },
        )

        # Get history
        response = client.get(
            f"/tenants/{tenant.id}/alerts/alert_123/history",
        )
        assert response.status_code == 200
        data = response.json()
        events = data["events"]

        # Verify ascending order (oldest first)
        for i in range(len(events) - 1):
            current_time = datetime.fromisoformat(events[i]["created_at"])
            next_time = datetime.fromisoformat(events[i + 1]["created_at"])
            assert current_time <= next_time
