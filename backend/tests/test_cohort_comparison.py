"""Test cohort snapshot creation and comparison (FR-037 / T-066)."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client() -> Generator[TestClient]:
    """In-memory SQLite test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _token(email: str, role: str = "super_admin") -> str:
    """Generate JWT token for testing."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _headers(email: str = "test@example.com", role: str = "super_admin") -> dict:
    """Generate auth headers with JWT token."""
    return {"Authorization": f"Bearer {_token(email, role)}"}


def _create_tenant(client: TestClient, slug: str, email: str) -> UUID:
    """Create a tenant and return tenant_id."""
    response = client.post(
        "/tenants",
        json={"name": "Test Tenant", "slug": slug},
        headers=_headers(email),
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


class TestCohortSnapshotCRUD:
    """Test create and list cohort snapshots."""

    def test_create_cohort_snapshot(self, client: TestClient) -> None:
        """FR-037 / T-066: Create cohort snapshot."""
        tenant_id = _create_tenant(client, "test-tenant", "test@example.com")

        response = client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 150,
                "repeat_rate": 0.42,
                "churn_rate": 0.58,
                "avg_order_value": 85.50,
                "total_revenue": 12825.00,
                "repeat_purchase_frequency": 2.3,
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cohort_grain"] == "month"
        assert data["customer_count"] == 150
        assert data["repeat_rate"] == 0.42

    def test_create_multiple_cohorts(self, client: TestClient) -> None:
        """Create multiple cohort snapshots for comparison."""
        tenant_id = _create_tenant(client, "multi-tenant", "test@example.com")

        # May cohort
        r1 = client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 100,
                "repeat_rate": 0.40,
                "churn_rate": 0.60,
                "avg_order_value": 80.00,
                "total_revenue": 8000.00,
                "repeat_purchase_frequency": 2.0,
            },
            headers=_headers("test@example.com"),
        )
        assert r1.status_code == 201

        # June cohort
        r2 = client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-06-01",
                "cohort_end_date": "2026-06-30",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 120,
                "repeat_rate": 0.45,
                "churn_rate": 0.55,
                "avg_order_value": 90.00,
                "total_revenue": 10800.00,
                "repeat_purchase_frequency": 2.5,
            },
            headers=_headers("test@example.com"),
        )
        assert r2.status_code == 201

    def test_cohort_snapshot_not_found(self, client: TestClient) -> None:
        """Verify 404 on nonexistent tenant for compare endpoint."""
        fake_tenant_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/tenants/{fake_tenant_id}/cohorts/compare",
            json={
                "cohort_grain": "month",
                "start_date": "2026-05-01",
                "end_date": "2026-06-30",
                "observation_window_days": 90,
            },
            headers=_headers("test@example.com"),
        )
        # Nonexistent tenant should return 404
        assert response.status_code == 404


class TestCohortComparison:
    """Test side-by-side cohort comparison."""

    def test_compare_cohorts_by_grain_and_window(self, client: TestClient) -> None:
        """FR-037 / T-066: Compare cohorts filtered by grain and window."""
        tenant_id = _create_tenant(client, "compare-tenant", "test@example.com")

        # Create 3 May cohorts with 90-day window
        for i in range(3):
            client.post(
                f"/tenants/{tenant_id}/cohorts",
                json={
                    "cohort_start_date": "2026-05-01",
                    "cohort_end_date": "2026-05-31",
                    "cohort_grain": "month",
                    "observation_window_days": 90,
                    "customer_count": 100 + (i * 10),
                    "repeat_rate": 0.40 + (i * 0.05),
                    "churn_rate": 0.60 - (i * 0.05),
                    "avg_order_value": 80.00,
                    "total_revenue": 8000.00,
                    "repeat_purchase_frequency": 2.0,
                },
                headers=_headers("test@example.com"),
            )

        # Compare May cohorts with 90-day window
        response = client.post(
            f"/tenants/{tenant_id}/cohorts/compare",
            json={
                "cohort_grain": "month",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "observation_window_days": 90,
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["cohorts"]) == 3

    def test_compare_excludes_different_window(self, client: TestClient) -> None:
        """Comparison should exclude cohorts with different observation windows."""
        tenant_id = _create_tenant(client, "window-tenant", "test@example.com")

        # 90-day window
        client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 100,
                "repeat_rate": 0.40,
                "churn_rate": 0.60,
                "avg_order_value": 80.00,
                "total_revenue": 8000.00,
                "repeat_purchase_frequency": 2.0,
            },
            headers=_headers("test@example.com"),
        )

        # 180-day window (different)
        client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 180,
                "customer_count": 100,
                "repeat_rate": 0.50,
                "churn_rate": 0.50,
                "avg_order_value": 90.00,
                "total_revenue": 9000.00,
                "repeat_purchase_frequency": 2.5,
            },
            headers=_headers("test@example.com"),
        )

        # Request only 90-day cohorts
        response = client.post(
            f"/tenants/{tenant_id}/cohorts/compare",
            json={
                "cohort_grain": "month",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "observation_window_days": 90,
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["cohorts"][0]["observation_window_days"] == 90

    def test_compare_cohorts_ordered_by_date(self, client: TestClient) -> None:
        """Cohorts should be ordered by cohort_start_date ascending."""
        tenant_id = _create_tenant(client, "order-tenant", "test@example.com")

        # Create cohorts out of order: June, May
        client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-06-01",
                "cohort_end_date": "2026-06-30",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 120,
                "repeat_rate": 0.45,
                "churn_rate": 0.55,
                "avg_order_value": 90.00,
                "total_revenue": 10800.00,
                "repeat_purchase_frequency": 2.5,
            },
            headers=_headers("test@example.com"),
        )

        client.post(
            f"/tenants/{tenant_id}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 100,
                "repeat_rate": 0.40,
                "churn_rate": 0.60,
                "avg_order_value": 80.00,
                "total_revenue": 8000.00,
                "repeat_purchase_frequency": 2.0,
            },
            headers=_headers("test@example.com"),
        )

        response = client.post(
            f"/tenants/{tenant_id}/cohorts/compare",
            json={
                "cohort_grain": "month",
                "start_date": "2026-05-01",
                "end_date": "2026-06-30",
                "observation_window_days": 90,
            },
            headers=_headers("test@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        # May should come before June
        assert data["cohorts"][0]["cohort_start_date"] == "2026-05-01"
        assert data["cohorts"][1]["cohort_start_date"] == "2026-06-01"


class TestCohortIsolation:
    """Test cross-tenant isolation."""

    def test_cross_tenant_isolation(self, client: TestClient) -> None:
        """Cohorts from one tenant should not leak to another."""
        tenant_a = _create_tenant(client, "tenant-a", "admin-a@example.com")
        tenant_b = _create_tenant(client, "tenant-b", "admin-b@example.com")

        # Create cohort in tenant A
        client.post(
            f"/tenants/{tenant_a}/cohorts",
            json={
                "cohort_start_date": "2026-05-01",
                "cohort_end_date": "2026-05-31",
                "cohort_grain": "month",
                "observation_window_days": 90,
                "customer_count": 100,
                "repeat_rate": 0.40,
                "churn_rate": 0.60,
                "avg_order_value": 80.00,
                "total_revenue": 8000.00,
                "repeat_purchase_frequency": 2.0,
            },
            headers=_headers("admin-a@example.com"),
        )

        # Query from tenant B should be empty
        response = client.post(
            f"/tenants/{tenant_b}/cohorts/compare",
            json={
                "cohort_grain": "month",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "observation_window_days": 90,
            },
            headers=_headers("admin-b@example.com"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
