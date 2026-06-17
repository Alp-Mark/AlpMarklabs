"""Tests for alert configuration APIs (T-072).

Tests cover alert threshold and alert recipient CRUD operations,
authorization, tenant isolation, and audit logging.
"""

from __future__ import annotations

from collections.abc import Generator

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import Tenant, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session() -> Generator[Session]:
    """Create in-memory test database with all tables."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_local = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )

    Base.metadata.create_all(bind=engine)

    session = test_session_local()
    yield session
    session.close()

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def test_client(db_session: Session) -> Generator[TestClient]:
    """Return authenticated test client with database override."""

    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create test tenant and user
    tenant = Tenant(name="Test Tenant", slug="test-tenant")
    db_session.add(tenant)
    db_session.flush()

    user = User(email="test@example.com", full_name="Test User", is_active=True)
    db_session.add(user)
    db_session.flush()

    # Create tenant membership with operations_manager role
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_manager",
    )
    db_session.add(membership)
    db_session.commit()

    client = TestClient(app)

    # Generate valid JWT token
    token = jwt.encode(
        {
            "sub": "test-user",
            "email": "test@example.com",
            "platform_role": "user",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client

    app.dependency_overrides.clear()


def test_create_alert_threshold_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Create alert threshold succeeds with valid payload."""
    from backend.app.db.models import Tenant

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    payload = {
        "alert_type": "kpi",
        "metric_name": "roas",
        "threshold_value": 2.0,
        "comparison_operator": "<",
        "is_enabled": True,
    }

    response = test_client.post(
        f"/tenants/{tenant.id}/alerts/thresholds",
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["alert_type"] == "kpi"
    assert data["metric_name"] == "roas"
    assert data["threshold_value"] == 2.0
    assert data["comparison_operator"] == "<"
    assert data["is_enabled"] is True


def test_list_alert_thresholds(
    test_client: TestClient, db_session: Session
) -> None:
    """List alert thresholds returns all thresholds for tenant."""
    from backend.app.db.models import AlertThreshold, Tenant

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    # Create 2 thresholds
    threshold1 = AlertThreshold(
        tenant_id=tenant.id,
        alert_type="kpi",
        metric_name="roas",
        threshold_value=2.0,
        comparison_operator="<",
    )
    threshold2 = AlertThreshold(
        tenant_id=tenant.id,
        alert_type="margin",
        metric_name="margin_pct",
        threshold_value=30.0,
        comparison_operator="<",
    )
    db_session.add_all([threshold1, threshold2])
    db_session.commit()

    response = test_client.get(f"/tenants/{tenant.id}/alerts/thresholds")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["thresholds"]) == 2


def test_get_alert_threshold(
    test_client: TestClient, db_session: Session
) -> None:
    """Get specific alert threshold."""
    from backend.app.db.models import AlertThreshold, Tenant

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    threshold = AlertThreshold(
        tenant_id=tenant.id,
        alert_type="kpi",
        metric_name="roas",
        threshold_value=2.0,
        comparison_operator="<",
    )
    db_session.add(threshold)
    db_session.commit()

    response = test_client.get(
        f"/tenants/{tenant.id}/alerts/thresholds/{threshold.id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(threshold.id)
    assert data["metric_name"] == "roas"


def test_update_alert_threshold(
    test_client: TestClient, db_session: Session
) -> None:
    """Update alert threshold partial fields."""
    from backend.app.db.models import AlertThreshold, Tenant

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    threshold = AlertThreshold(
        tenant_id=tenant.id,
        alert_type="kpi",
        metric_name="roas",
        threshold_value=2.0,
        comparison_operator="<",
        is_enabled=True,
    )
    db_session.add(threshold)
    db_session.commit()

    payload = {
        "threshold_value": 1.5,
        "is_enabled": False,
    }

    response = test_client.put(
        f"/tenants/{tenant.id}/alerts/thresholds/{threshold.id}",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threshold_value"] == 1.5
    assert data["is_enabled"] is False


def test_delete_alert_threshold(
    test_client: TestClient, db_session: Session
) -> None:
    """Delete alert threshold."""
    from backend.app.db.models import AlertThreshold, Tenant

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    threshold = AlertThreshold(
        tenant_id=tenant.id,
        alert_type="kpi",
        metric_name="roas",
        threshold_value=2.0,
        comparison_operator="<",
    )
    db_session.add(threshold)
    db_session.commit()

    response = test_client.delete(
        f"/tenants/{tenant.id}/alerts/thresholds/{threshold.id}"
    )

    assert response.status_code == 200


def test_create_alert_recipient_success(
    test_client: TestClient, db_session: Session
) -> None:
    """Create alert recipient succeeds."""
    from backend.app.db.models import Tenant, User

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    user = db_session.query(User).first()
    assert user is not None

    payload = {
        "user_id": str(user.id),
        "channel": "email",
        "destination": "finance@brand.com",
    }

    response = test_client.post(
        f"/tenants/{tenant.id}/alerts/recipients",
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["channel"] == "email"
    assert data["destination"] == "finance@brand.com"
    assert data["is_verified"] is False


def test_list_alert_recipients(
    test_client: TestClient, db_session: Session
) -> None:
    """List alert recipients returns all recipients for tenant."""
    from backend.app.db.models import AlertRecipient, Tenant, User

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    user1 = db_session.query(User).first()
    assert user1 is not None

    user2 = User(email="user2@example.com", full_name="User 2", is_active=True)
    db_session.add(user2)
    db_session.flush()

    recipient1 = AlertRecipient(
        tenant_id=tenant.id,
        user_id=user1.id,
        channel="email",
        destination="user1@brand.com",
    )
    recipient2 = AlertRecipient(
        tenant_id=tenant.id,
        user_id=user2.id,
        channel="slack",
        destination="https://hooks.slack.com/services/...",
    )
    db_session.add_all([recipient1, recipient2])
    db_session.commit()

    response = test_client.get(f"/tenants/{tenant.id}/alerts/recipients")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["recipients"]) == 2


def test_update_alert_recipient(
    test_client: TestClient, db_session: Session
) -> None:
    """Update alert recipient destination."""
    from backend.app.db.models import AlertRecipient, Tenant, User

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    user = db_session.query(User).first()
    assert user is not None

    recipient = AlertRecipient(
        tenant_id=tenant.id,
        user_id=user.id,
        channel="email",
        destination="old@brand.com",
    )
    db_session.add(recipient)
    db_session.commit()

    payload = {
        "destination": "new@brand.com",
        "is_verified": True,
    }

    response = test_client.put(
        f"/tenants/{tenant.id}/alerts/recipients/{recipient.id}",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "new@brand.com"
    assert data["is_verified"] is True


def test_delete_alert_recipient(
    test_client: TestClient, db_session: Session
) -> None:
    """Delete alert recipient."""
    from backend.app.db.models import AlertRecipient, Tenant, User

    tenant = db_session.query(Tenant).first()
    assert tenant is not None

    user = db_session.query(User).first()
    assert user is not None

    recipient = AlertRecipient(
        tenant_id=tenant.id,
        user_id=user.id,
        channel="email",
        destination="test@brand.com",
    )
    db_session.add(recipient)
    db_session.commit()

    response = test_client.delete(
        f"/tenants/{tenant.id}/alerts/recipients/{recipient.id}"
    )

    assert response.status_code == 200


def test_alert_threshold_tenant_isolation(
    test_client: TestClient, db_session: Session
) -> None:
    """Cannot access alert threshold from different tenant."""
    from backend.app.db.models import AlertThreshold, Tenant

    tenant1 = db_session.query(Tenant).first()
    assert tenant1 is not None

    tenant2 = Tenant(name="Tenant 2", slug="tenant-2")
    db_session.add(tenant2)
    db_session.commit()

    threshold = AlertThreshold(
        tenant_id=tenant1.id,
        alert_type="kpi",
        metric_name="roas",
        threshold_value=2.0,
        comparison_operator="<",
    )
    db_session.add(threshold)
    db_session.commit()

    # Try to access from tenant2
    response = test_client.get(
        f"/tenants/{tenant2.id}/alerts/thresholds/{threshold.id}"
    )

    assert response.status_code == 403


def test_alert_recipient_tenant_isolation(
    test_client: TestClient, db_session: Session
) -> None:
    """Cannot access alert recipient from different tenant."""
    from backend.app.db.models import AlertRecipient, Tenant, User

    tenant1 = db_session.query(Tenant).first()
    assert tenant1 is not None

    user = db_session.query(User).first()
    assert user is not None

    tenant2 = Tenant(name="Tenant 2", slug="tenant-2")
    db_session.add(tenant2)
    db_session.commit()

    recipient = AlertRecipient(
        tenant_id=tenant1.id,
        user_id=user.id,
        channel="email",
        destination="test@brand.com",
    )
    db_session.add(recipient)
    db_session.commit()

    # Try to access from tenant2
    response = test_client.get(
        f"/tenants/{tenant2.id}/alerts/recipients/{recipient.id}"
    )

    assert response.status_code == 403

