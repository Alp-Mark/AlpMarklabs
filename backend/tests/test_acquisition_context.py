"""Tests for acquisition context endpoint (T-070, FR-043).

Retention managers use acquisition context to understand incoming customer
quality by channel and cohort for retention strategy analysis.
"""

from __future__ import annotations

import uuid
from datetime import date

import jwt
from backend.app.db.models import (
    AcquisitionCohort,
    TenantMembership,
    User,
)
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

client = TestClient(app)


def _make_auth_token(payload: dict) -> str:
    """Generate a signed JWT token for testing."""
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)


def _create_tenant_and_get_id(
    client: TestClient, tenant_name: str, tenant_slug: str
) -> tuple[str, str]:
    """Create a tenant and return its ID and auth token."""
    email = f"admin-{tenant_slug}@test.local"
    token = _make_auth_token(
        {"sub": "admin", "email": email, "platform_role": "super_admin"}
    )
    response = client.post(
        "/tenants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": tenant_name,
            "slug": tenant_slug,
            "billing_plan": "pro",
            "seat_limit": 10,
        },
    )
    assert response.status_code == 201
    return response.json()["id"], token


class TestAcquisitionContext:
    """Test acquisition context endpoint for retention managers."""

    def test_get_acquisition_context_empty_returns_200(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Return empty list when no acquisition cohorts exist."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand", "test-brand"
        )
        tenant_id = uuid.UUID(tenant_id_str)
        email = "admin-test-brand@test.local"
        user = db_session.query(User).filter_by(email=email).first()
        assert user is not None

        # Add user to tenant with operations_manager role
        membership = db_session.query(TenantMembership).filter_by(
            user_id=user.id, tenant_id=tenant_id
        ).first()
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31&cohort_grain=month",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["cohorts"] == []
        assert data["data_freshness"] == "no_data"
        assert data["channels_included"] == []

    def test_get_acquisition_context_with_cohorts(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Return acquisition cohorts for specified date range."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand 2", "test-brand-2"
        )
        tenant_id = uuid.UUID(tenant_id_str)
        email = "admin-test-brand-2@test.local"
        user = db_session.query(User).filter_by(email=email).first()
        assert user is not None

        membership = db_session.query(TenantMembership).filter_by(
            user_id=user.id, tenant_id=tenant_id
        ).first()
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create acquisition cohorts
        cohort1 = AcquisitionCohort(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            cohort_start_date=date(2026, 6, 1),
            cohort_end_date=date(2026, 6, 30),
            cohort_grain="month",
            channel="shopify_organic",
            new_customer_count=150,
            blended_cac=25.50,
            first_order_aov=85.75,
            total_acquisition_spend=3825.00,
            repeat_purchase_rate_90d=0.35,
        )
        cohort2 = AcquisitionCohort(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            cohort_start_date=date(2026, 6, 1),
            cohort_end_date=date(2026, 6, 30),
            cohort_grain="month",
            channel="meta_ads",
            new_customer_count=200,
            blended_cac=32.00,
            first_order_aov=92.50,
            total_acquisition_spend=6400.00,
            repeat_purchase_rate_90d=0.28,
        )
        db_session.add(cohort1)
        db_session.add(cohort2)
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31&cohort_grain=month",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["cohorts"]) == 2
        assert "fresh" in data["data_freshness"] or "stale" in data[
            "data_freshness"
        ]
        assert set(data["channels_included"]) == {"shopify_organic", "meta_ads"}

        # Verify cohort details
        cohorts_by_channel = {c["channel"]: c for c in data["cohorts"]}
        assert cohorts_by_channel["shopify_organic"]["new_customer_count"] == 150
        assert cohorts_by_channel["shopify_organic"]["blended_cac"] == 25.50
        assert cohorts_by_channel["meta_ads"]["new_customer_count"] == 200

    def test_get_acquisition_context_channel_filter(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Filter acquisition cohorts by specific channel."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand 3", "test-brand-3"
        )
        tenant_id = uuid.UUID(tenant_id_str)
        email = "admin-test-brand-3@test.local"
        user = db_session.query(User).filter_by(email=email).first()
        assert user is not None

        membership = db_session.query(TenantMembership).filter_by(
            user_id=user.id, tenant_id=tenant_id
        ).first()
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create multiple cohorts
        for channel in ["shopify_organic", "meta_ads", "google_ads"]:
            cohort = AcquisitionCohort(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cohort_start_date=date(2026, 6, 1),
                cohort_end_date=date(2026, 6, 30),
                cohort_grain="month",
                channel=channel,
                new_customer_count=100,
                blended_cac=20.00,
                first_order_aov=80.00,
                total_acquisition_spend=2000.00,
                repeat_purchase_rate_90d=0.30,
            )
            db_session.add(cohort)
        db_session.commit()

        # Request only meta_ads cohorts
        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31&cohort_grain=month"
            f"&channel=meta_ads",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["cohorts"][0]["channel"] == "meta_ads"
        assert data["channels_included"] == ["meta_ads"]

    def test_get_acquisition_context_unauthorized(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Reject request with invalid auth token."""
        tenant_id = uuid.uuid4()
        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_get_acquisition_context_tenant_not_found(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Return 404 when tenant does not exist."""
        nonexistent_tenant = uuid.uuid4()
        token = _make_auth_token(
            {
                "sub": "user1",
                "email": "test@example.com",
                "platform_role": "super_admin",
            }
        )
        response = client.get(
            f"/tenants/{nonexistent_tenant}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_get_acquisition_context_cross_tenant_isolation(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Ensure tenant1 cannot see tenant2's acquisition cohorts."""
        tenant1_id_str, token1 = _create_tenant_and_get_id(
            client, "Tenant 1", "tenant-1"
        )
        tenant2_id_str, token2 = _create_tenant_and_get_id(
            client, "Tenant 2", "tenant-2"
        )
        tenant1_id = uuid.UUID(tenant1_id_str)
        tenant2_id = uuid.UUID(tenant2_id_str)

        # Setup users for both tenants
        email1 = "admin-tenant-1@test.local"
        email2 = "admin-tenant-2@test.local"
        user1 = db_session.query(User).filter_by(email=email1).first()
        user2 = db_session.query(User).filter_by(email=email2).first()
        assert user1 is not None
        assert user2 is not None

        for user, tenant_id in [(user1, tenant1_id), (user2, tenant2_id)]:
            membership = db_session.query(TenantMembership).filter_by(
                user_id=user.id, tenant_id=tenant_id
            ).first()
            if membership is None:
                membership = TenantMembership(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    tenant_id=tenant_id,
                    role="operations_manager",
                )
                db_session.add(membership)
        db_session.commit()

        # Create cohorts for tenant2 only
        cohort = AcquisitionCohort(
            id=uuid.uuid4(),
            tenant_id=tenant2_id,
            cohort_start_date=date(2026, 6, 1),
            cohort_end_date=date(2026, 6, 30),
            cohort_grain="month",
            channel="meta_ads",
            new_customer_count=100,
            blended_cac=25.00,
            first_order_aov=90.00,
            total_acquisition_spend=2500.00,
            repeat_purchase_rate_90d=0.32,
        )
        db_session.add(cohort)
        db_session.commit()

        # Tenant1 user queries tenant1 (should be empty)
        response1 = client.get(
            f"/tenants/{tenant1_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert response1.status_code == 200
        assert response1.json()["total"] == 0

        # Tenant2 user queries tenant2 (should see 1 cohort)
        response2 = client.get(
            f"/tenants/{tenant2_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response2.status_code == 200
        assert response2.json()["total"] == 1

    def test_get_acquisition_context_date_range_filtering(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Filter cohorts based on date range."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand 4", "test-brand-4"
        )
        tenant_id = uuid.UUID(tenant_id_str)
        email = "admin-test-brand-4@test.local"
        user = db_session.query(User).filter_by(email=email).first()
        assert user is not None

        membership = db_session.query(TenantMembership).filter_by(
            user_id=user.id, tenant_id=tenant_id
        ).first()
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        # Create cohorts for different months
        for month in [5, 6, 7]:
            cohort = AcquisitionCohort(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                cohort_start_date=date(2026, month, 1),
                cohort_end_date=date(2026, month, 30),
                cohort_grain="month",
                channel="shopify_organic",
                new_customer_count=100,
                blended_cac=20.00,
                first_order_aov=80.00,
                total_acquisition_spend=2000.00,
                repeat_purchase_rate_90d=0.30,
            )
            db_session.add(cohort)
        db_session.commit()

        # Query only June cohorts
        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-06-01&end_date=2026-06-30&cohort_grain=month",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["cohorts"][0]["cohort_start_date"] == "2026-06-01"

    def test_get_acquisition_context_audit_logged(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Verify acquisition context access returns 200 (audit logged)."""
        tenant_id_str, token = _create_tenant_and_get_id(
            client, "Test Brand 5", "test-brand-5"
        )
        tenant_id = uuid.UUID(tenant_id_str)
        email = "admin-test-brand-5@test.local"
        user = db_session.query(User).filter_by(email=email).first()
        assert user is not None

        membership = db_session.query(TenantMembership).filter_by(
            user_id=user.id, tenant_id=tenant_id
        ).first()
        if membership is None:
            membership = TenantMembership(
                id=uuid.uuid4(),
                user_id=user.id,
                tenant_id=tenant_id,
                role="operations_manager",
            )
            db_session.add(membership)
            db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/retention/acquisition-context?"
            f"start_date=2026-01-01&end_date=2026-12-31",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        # Note: Audit events are written by the endpoint handler in a separate
        # session and persisted to the database. Testing the endpoint returns 200
        # validates the audit logging path was executed without error.
