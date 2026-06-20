"""
T-068: Historical Restatement Engine - Test Suite

Comprehensive tests for historical margin restatement workflow:
- Restate margin under different cost input versions
- Compare prior vs new cost scenarios
- Audit trail logging
"""

import uuid

import jwt
import pytest
from backend.app.db.models import AuditEvent, Role, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
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
    tenant_id = response.json()["id"]
    
    # Upgrade to operations_inventory_manager (has all permissions)
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        # Get the operations_inventory_manager role for this tenant
        ops_role = db.scalar(
            select(Role).where(
                Role.tenant_id == uuid.UUID(tenant_id),
                Role.name == "operations_inventory_manager",
                Role.is_system,
            )
        )
        
        # Update the membership to use operations_inventory_manager role
        membership = db.scalar(
            select(TenantMembership)
            .join(User, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == uuid.UUID(tenant_id),
                User.email == email,
            )
        )
        if membership and ops_role:
            membership.role = "operations_inventory_manager"
            membership.role_id = ops_role.id
            db.commit()
    finally:
        db.close()
    
    return tenant_id, token


class TestHistoricalRestatement:
    """Test historical restatement endpoint."""

    def test_restate_margin_cogs_change(self, client: TestClient) -> None:
        """Restate margin for period under different COGS versions."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand", "testbrand"
        )

        # Create COGS input
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
        assert r1.status_code == 201, (
            f"Create cost input failed: {r1.status_code} {r1.json()}"
        )
        cost_input_id = r1.json()["id"]

        # Update the cost input (creates version 2)
        r2 = client.put(
            f"/tenants/{tenant_id}/finance/cost-inputs/{cost_input_id}",
            json={
                "amount": 60.0,
                "variance_reason": "Updated due to inflation",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200, (
            f"Update cost input failed: {r2.status_code} {r2.json()}"
        )

        # Restate historical margin comparing v1 vs v2
        response = client.post(
            f"/tenants/{tenant_id}/finance/restatements",
            json={
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "cost_input_id": cost_input_id,
                "prior_version_number": 1,
                "new_version_number": 2,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201, (
            f"Restate failed: {response.status_code} {response.json()}"
        )
        body = response.json()
        assert body["cost_input_id"] == cost_input_id
        assert body["prior_version_number"] == 1
        assert body["new_version_number"] == 2
        assert body["prior_amount"] == 50.0
        assert body["new_amount"] == 60.0
        assert body["margin_delta_absolute"] == pytest.approx(1.0)  # 10% of delta

    def test_restate_nonexistent_cost_input_returns_404(
        self, client: TestClient
    ) -> None:
        """Restate on nonexistent cost input returns 404."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand2", "testbrand2"
        )

        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/tenants/{tenant_id}/finance/restatements",
            json={
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "cost_input_id": fake_id,
                "prior_version_number": 1,
                "new_version_number": 2,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_restate_nonexistent_prior_version_returns_404(
        self, client: TestClient
    ) -> None:
        """Restate with nonexistent prior version returns 404."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand3", "testbrand3"
        )

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
        cost_input_id = r1.json()["id"]

        response = client.post(
            f"/tenants/{tenant_id}/finance/restatements",
            json={
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "cost_input_id": cost_input_id,
                "prior_version_number": 99,
                "new_version_number": 100,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_restate_writes_audit_event(
        self, db_session: Session, client: TestClient
    ) -> None:
        """Restate should write audit event with restatement details."""
        tenant_id, token = _create_tenant_and_get_id(
            client, "TestBrand4", "testbrand4"
        )
        tenant_uuid = uuid.UUID(tenant_id)

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
        assert r1.status_code == 201, (
            f"Create cost input failed: {r1.status_code} {r1.json()}"
        )
        cost_input_id = r1.json()["id"]

        # Update to create version 2
        r2 = client.put(
            f"/tenants/{tenant_id}/finance/cost-inputs/{cost_input_id}",
            json={"amount": 60.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200, (
            f"Update cost input failed: {r2.status_code} {r2.json()}"
        )

        # Restate
        r3 = client.post(
            f"/tenants/{tenant_id}/finance/restatements",
            json={
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "cost_input_id": cost_input_id,
                "prior_version_number": 1,
                "new_version_number": 2,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r3.status_code == 201, (
            f"Restate failed: {r3.status_code} {r3.json()}"
        )

        # Check audit
        audit_row = db_session.scalar(
            select(AuditEvent).where(
                AuditEvent.tenant_id == tenant_uuid,
                AuditEvent.action == "finance.historical_restatement_created",
                AuditEvent.entity_id == str(cost_input_id),
            )
        )
        assert audit_row is not None
        assert audit_row.details["prior_version"] == 1
        assert audit_row.details["new_version"] == 2
        assert audit_row.details["margin_delta"] == pytest.approx(1.0)
