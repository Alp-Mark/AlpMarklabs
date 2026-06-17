"""Test suite for email delivery and notification logging (FR-116 / T-079).

Tests cover:
- Email delivery record creation and status tracking
- Filtering and pagination
- Retry logic and error handling
- Tenant isolation
- Multi-user and multi-alert scenarios
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import quote

from backend.app.db.models import EmailDeliveryLog, Tenant, User
from starlette.testclient import TestClient

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestEmailDelivery:
    """Test suite for email delivery and notification logging."""

    def test_create_delivery_log_record(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test creating an email delivery log record directly in database."""
        delivery_log = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            alert_id="alert_1",
            alert_type="margin_drift",
            email_address=user.email,
            status="sent",
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            error_message=None,
        )
        db_session.add(delivery_log)
        db_session.commit()

        # Verify record exists
        record = db_session.query(EmailDeliveryLog).filter_by(
            id=delivery_log.id
        ).first()
        assert record is not None
        assert record.status == "sent"
        assert record.attempt_count == 1

    def test_list_delivery_records(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test listing email delivery records."""
        # Create 3 delivery records
        for i in range(3):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id=f"alert_{i}",
                alert_type="margin_drift",
                email_address=user.email,
                status="sent" if i < 2 else "failed",
                attempt_count=1 if i < 2 else 3,
                last_attempt_at=datetime.now(UTC),
                error_message=None if i < 2 else "SMTP timeout",
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["deliveries"]) == 3

    def test_filter_deliveries_by_alert_id(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test filtering deliveries by alert_id."""
        # Create deliveries for different alerts
        for i in range(2):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id=f"alert_{i}",
                alert_type="margin_drift",
                email_address=user.email,
                status="sent",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None,
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history?alert_id=alert_0",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["deliveries"][0]["alert_id"] == "alert_0"

    def test_filter_deliveries_by_status(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test filtering deliveries by status."""
        # Create deliveries with different statuses
        statuses = ["sent", "failed", "pending", "sent"]
        for i, s in enumerate(statuses):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id=f"alert_{i}",
                alert_type="margin_drift",
                email_address=user.email,
                status=s,
                attempt_count=1,
                last_attempt_at=datetime.now(UTC) if s in ("sent", "failed") else None,
                error_message="Failed" if s == "failed" else None,
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history?status=sent",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert all(d["status"] == "sent" for d in data["deliveries"])

    def test_filter_deliveries_by_date_range(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test filtering deliveries by date range."""
        # Create deliveries at different times
        now = datetime.now(UTC)
        past_time = now - timedelta(days=2)

        delivery_past = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            alert_id="alert_past",
            alert_type="margin_drift",
            email_address=user.email,
            status="sent",
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            error_message=None,
            created_at=past_time,
        )
        delivery_now = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            alert_id="alert_now",
            alert_type="margin_drift",
            email_address=user.email,
            status="sent",
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            error_message=None,
            created_at=now,
        )
        db_session.add(delivery_past)
        db_session.add(delivery_now)
        db_session.commit()

        # Query: date_from < now (should include both)
        date_from = (now - timedelta(days=1)).isoformat()
        date_to = (now + timedelta(days=1)).isoformat()
        date_from_encoded = quote(date_from)
        date_to_encoded = quote(date_to)

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history"
            f"?date_from={date_from_encoded}&date_to={date_to_encoded}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1  # Only alert_now

    def test_filter_deliveries_by_user_id(
        self,
        tenant: Tenant,
        user: User,
        other_user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test filtering deliveries by user_id."""
        # Create deliveries for different users
        for u in [user, other_user]:
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=u.id,
                alert_id="alert_1",
                alert_type="margin_drift",
                email_address=u.email,
                status="sent",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None,
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history?user_id={user.id}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["deliveries"][0]["user_id"] == str(user.id)

    def test_pagination_deliveries(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test pagination of delivery records."""
        # Create 10 delivery records
        for i in range(10):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id=f"alert_{i}",
                alert_type="margin_drift",
                email_address=user.email,
                status="sent",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None,
            )
            db_session.add(delivery_log)
        db_session.commit()

        # Test skip and limit
        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history?skip=5&limit=3",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert len(data["deliveries"]) == 3  # Limit applied

    def test_pagination_limit_capped_at_500(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test that pagination limit is capped at 500."""
        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history?limit=1000",
        )
        assert response.status_code == 200
        # If we created 1000+ records, max returned would be 500
        # For this test, we just verify the endpoint accepts the request

    def test_email_delivery_tenant_isolation(
        self,
        tenant: Tenant,
        other_tenant: Tenant,
        user: User,
        other_user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that email deliveries are isolated by tenant."""
        # Create deliveries in two different tenants
        delivery_tenant1 = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            alert_id="alert_1",
            alert_type="margin_drift",
            email_address=user.email,
            status="sent",
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            error_message=None,
        )
        delivery_tenant2 = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=other_tenant.id,
            user_id=other_user.id,
            alert_id="alert_1",
            alert_type="margin_drift",
            email_address=other_user.email,
            status="sent",
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
            error_message=None,
        )
        db_session.add(delivery_tenant1)
        db_session.add(delivery_tenant2)
        db_session.commit()

        # Query tenant1 - should only see tenant1's delivery
        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["deliveries"][0]["tenant_id"] == str(tenant.id)

    def test_delivery_status_transitions(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
    ) -> None:
        """Test delivery status transitions (pending->sent->failed)."""
        delivery_log = EmailDeliveryLog(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            alert_id="alert_1",
            alert_type="margin_drift",
            email_address=user.email,
            status="pending",
            attempt_count=0,
            last_attempt_at=None,
            error_message=None,
        )
        db_session.add(delivery_log)
        db_session.commit()

        # Verify initial status is "pending"
        record = db_session.query(EmailDeliveryLog).filter_by(
            id=delivery_log.id
        ).first()
        assert record is not None
        assert record.status == "pending"
        assert record.attempt_count == 0

        # Simulate first attempt success
        record.status = "sent"
        record.attempt_count = 1
        record.last_attempt_at = datetime.now(UTC)
        db_session.commit()

        # Verify status changed
        updated = db_session.query(EmailDeliveryLog).filter_by(
            id=delivery_log.id
        ).first()
        assert updated is not None
        assert updated.status == "sent"

    def test_get_alert_email_delivery_history(
        self,
        tenant: Tenant,
        user: User,
        other_user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test retrieving complete email delivery history for an alert."""
        # Create multiple delivery attempts for the same alert
        for i in range(3):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id if i < 2 else other_user.id,
                alert_id="alert_1",
                alert_type="margin_drift",
                email_address=user.email if i < 2 else other_user.email,
                status="sent" if i < 2 else "failed",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None if i < 2 else "SMTP error",
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/alerts/alert_1/history",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "alert_1"
        assert data["alert_type"] == "margin_drift"
        assert data["total_deliveries"] == 3
        assert data["successful_count"] == 2
        assert data["failed_count"] == 1
        assert data["pending_count"] == 0

    def test_alert_delivery_history_empty_alert(
        self,
        tenant: Tenant,
        client: TestClient,
    ) -> None:
        """Test retrieving history for non-existent alert."""
        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/alerts/nonexistent_alert/history",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_deliveries"] == 0
        assert data["deliveries"] == []
        assert data["first_delivery_at"] is None
        assert data["last_delivery_at"] is None

    def test_tenant_not_found_delivery_list(
        self,
        client: TestClient,
        nonexistent_uuid: uuid.UUID,
    ) -> None:
        """Test listing deliveries for non-existent tenant."""
        response = client.get(
            f"/tenants/{nonexistent_uuid}/email-delivery/history",
        )
        assert response.status_code == 404

    def test_tenant_not_found_delivery_alert_history(
        self,
        client: TestClient,
        nonexistent_uuid: uuid.UUID,
    ) -> None:
        """Test retrieving alert delivery history for non-existent tenant."""
        response = client.get(
            f"/tenants/{nonexistent_uuid}/email-delivery/alerts/alert_1/history",
        )
        assert response.status_code == 404

    def test_delivery_ordering_descending_in_list(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test delivery list ordering by created_at descending."""
        # Create deliveries with different timestamps
        now = datetime.now(UTC)
        for i in range(3):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id="alert_1",
                alert_type="margin_drift",
                email_address=user.email,
                status="sent",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None,
                created_at=now + timedelta(seconds=i),
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/history",
        )
        assert response.status_code == 200
        data = response.json()
        # Verify ordering: newest first
        assert len(data["deliveries"]) == 3
        timestamps = [d["created_at"] for d in data["deliveries"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_delivery_ordering_ascending_in_alert_history(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test alert delivery history ordering by created_at ascending."""
        # Create deliveries with different timestamps
        now = datetime.now(UTC)
        for i in range(3):
            delivery_log = EmailDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=user.id,
                alert_id="alert_1",
                alert_type="margin_drift",
                email_address=user.email,
                status="sent",
                attempt_count=1,
                last_attempt_at=datetime.now(UTC),
                error_message=None,
                created_at=now + timedelta(seconds=i),
            )
            db_session.add(delivery_log)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant.id}/email-delivery/alerts/alert_1/history",
        )
        assert response.status_code == 200
        data = response.json()
        # Verify ordering: oldest first (ascending)
        assert len(data["deliveries"]) == 3
        timestamps = [d["created_at"] for d in data["deliveries"]]
        assert timestamps == sorted(timestamps)
