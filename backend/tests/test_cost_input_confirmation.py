"""
T-067: Cost Input Confirmation Gate - Test Suite

Comprehensive tests for cost input confirmation workflow:
- High-impact (COGS) inputs require confirmation
- Approval and rejection workflows (confirm/reject)
- Pending confirmation filtering
- Audit trail logging
"""

import uuid

import jwt
from backend.app.db.models import AuditEvent
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def _make_auth_token(payload: dict) -> str:
    return jwt.encode(
        payload,
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _create_tenant_and_get_id(
    client: TestClient, tenant_name: str, tenant_slug: str
) -> tuple[str, str]:
    """Create a test tenant and return its ID and token for accessing it."""
    email = f"admin-{tenant_slug}@test.local"
    token = _make_auth_token(
        {"sub": "admin", "email": email, "platform_role": "super_admin"}
    )
    response = client.post(
        "/tenants",
        json={"name": tenant_name, "slug": tenant_slug},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id"], token


class TestCostInputConfirmationRequired:
    """Test confirmation requirement for high-impact inputs."""

    def test_create_cogs_input_requires_confirmation(self, client: TestClient) -> None:
        """COGS inputs should have confirmation_required=True."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand", "testbrand")
        
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["confirmation_required"] is True
        assert body["confirmed_at"] is None

    def test_create_non_cogs_input_no_confirmation(self, client: TestClient) -> None:
        """Non-COGS inputs should have confirmation_required=False."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand2", "testbrand2")
        
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "shipping",
                "tier_label": "Zone1",
                "amount": 10.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["confirmation_required"] is False


class TestCostInputGetSingle:
    """Test GET single cost input endpoint."""

    def test_get_single_cost_input_shows_confirmation_status(
        self, client: TestClient
    ) -> None:
        """GET /cost-inputs/{id} should return confirmation status."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand3", "testbrand3"
        )
        
        # Create input
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Get single
        response = client.get(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == input_id
        assert body["confirmation_required"] is True

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        """GET nonexistent should return 404."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand4", "testbrand4")
        
        fake_id = uuid.uuid4()
        response = client.get(
            f"/tenants/{tenant_id}/finance/cost-inputs/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


class TestCostInputListPendingFilter:
    """Test pending_confirmation query filter."""

    def test_list_pending_confirmation_filter(self, client: TestClient) -> None:
        """Filter pending_confirmation should work correctly."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand5", "testbrand5")
        
        # Create COGS (pending)
        r1 = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        pending_id = r1.json()["id"]

        # Create shipping (not pending)
        client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "shipping",
                "tier_label": "Zone1",
                "amount": 10.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # List with pending_confirmation=true
        response = client.get(
            f"/tenants/{tenant_id}/finance/cost-inputs?pending_confirmation=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["cost_inputs"]) == 1
        assert body["cost_inputs"][0]["id"] == pending_id


class TestCostInputConfirm:
    """Test confirm endpoint."""

    def test_confirm_pending_cost_input(self, client: TestClient) -> None:
        """Confirm should approve pending confirmation."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand6", "testbrand6")
        
        # Create COGS input
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Confirm
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Verify state
        get_response = client.get(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = get_response.json()
        assert body["confirmation_required"] is False
        assert body["confirmed_at"] is not None

    def test_confirm_non_pending_returns_409(self, client: TestClient) -> None:
        """Confirm on non-pending should return 409."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand7", "testbrand7")
        
        # Create shipping input (not pending)
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "shipping",
                "tier_label": "Zone1",
                "amount": 10.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Try to confirm
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409


class TestCostInputReject:
    """Test reject endpoint."""

    def test_reject_pending_cost_input(self, client: TestClient) -> None:
        """Reject should deny pending confirmation."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand8", "testbrand8")
        
        # Create COGS input
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Reject
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/reject",
            json={"reason": "Pricing not aligned with strategy"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Verify state
        get_response = client.get(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = get_response.json()
        assert body["confirmation_required"] is False
        assert body["confirmed_at"] is None

    def test_reject_non_pending_returns_409(self, client: TestClient) -> None:
        """Reject on non-pending should return 409."""
        tenant_id, token = _create_tenant_and_get_id(client, "TestBrand9", "testbrand9")
        
        # Create shipping input (not pending)
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "shipping",
                "tier_label": "Zone1",
                "amount": 10.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Try to reject
        response = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/reject",
            json={"reason": "Just because"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409


class TestAuditTrail:
    """Test audit logging for confirmation workflow."""

    def test_confirm_writes_audit_event(
        self, db_session: Session, client: TestClient
    ) -> None:
        """Confirm should write audit event."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand10", "testbrand10"
        )
        tenant_uuid = uuid.UUID(tenant_id)
        
        # Create input
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Confirm
        client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check audit
        audit_row = db_session.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant_uuid,
                AuditEvent.action == "finance.cost_input_confirmed",
                AuditEvent.entity_id == str(input_id),
            )
        )
        assert audit_row is not None
        assert audit_row.details["input_type"] == "cogs"

    def test_reject_writes_audit_event(
        self, db_session: Session, client: TestClient
    ) -> None:
        """Reject should write audit event with reason."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand11", "testbrand11"
        )
        tenant_uuid = uuid.UUID(tenant_id)
        
        # Create input
        r = client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "cogs",
                "tier_label": "Standard",
                "amount": 50.0,
                "unit": "USD",
                "effective_date": "2026-06-01",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        input_id = r.json()["id"]

        # Reject
        reason = "Pricing not aligned with strategy"
        client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/reject",
            json={"reason": reason},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check audit
        audit_row = db_session.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == tenant_uuid,
                AuditEvent.action == "finance.cost_input_rejected",
                AuditEvent.entity_id == str(input_id),
            )
        )
        assert audit_row is not None
        assert audit_row.details["input_type"] == "cogs"
        assert audit_row.details["rejection_reason"] == reason
