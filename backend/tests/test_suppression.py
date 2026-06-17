"""FR-074 / T-060: Tests for recommendation suppression logic and endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, timedelta

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import Recommendation
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.recommendations.suppression import (
    is_suppressed,
    lift_suppression,
    record_rejection,
)
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TODAY = date(2026, 6, 2)


@pytest.fixture()
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session]:
        db = local_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db(client: TestClient) -> Session:
    db_gen = app.dependency_overrides[get_db]()
    return next(db_gen)


def _token(email: str, role: str = "super_admin") -> str:
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": role},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _headers(email: str, role: str = "super_admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(email, role)}"}


def _create_tenant(client: TestClient, slug: str, email: str) -> str:
    resp = client.post(
        "/tenants",
        json={"name": slug, "slug": slug},
        headers=_headers(email),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _seed_recommendation(
    client: TestClient,
    tenant_id: str,
    rule_id: str = "ACQ-001",
    status: str = "reviewed",
    snapshot_date: date | None = None,
) -> str:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        rec = Recommendation(
            tenant_id=uuid.UUID(tenant_id),
            rule_id=rule_id,
            domain="acquisition",
            snapshot_date=snapshot_date or date.today(),
            affected_area="Meta",
            signal_summary="ROAS below threshold",
            suggested_action="Reduce Meta budget",
            confidence_level="high",
            data_freshness_context="1 day old",
            priority=10,
            status=status,
        )
        db.add(rec)
        db.commit()
        return str(rec.id)
    finally:
        db_gen.close()


# ---------------------------------------------------------------------------
# Service unit tests (no HTTP, direct SQLAlchemy)
# ---------------------------------------------------------------------------


def test_is_suppressed_returns_false_when_no_row(db: Session) -> None:
    """No suppression row → not suppressed."""
    tid = uuid.uuid4()
    assert is_suppressed(db, tid, "ACQ-001", today=_TODAY) is False


def test_record_rejection_creates_row_on_first_call(db: Session) -> None:
    """First rejection creates a state row with count=1."""
    tid = uuid.uuid4()
    row = record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert row.rejection_count == 1
    assert row.suppressed_until is None


def test_record_rejection_increments_count(db: Session) -> None:
    """Two rejections → count=2, still no suppression (threshold=3)."""
    tid = uuid.uuid4()
    record_rejection(db, tid, "ACQ-001", today=_TODAY)
    row = record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert row.rejection_count == 2
    assert row.suppressed_until is None


def test_record_rejection_triggers_suppression_at_threshold(db: Session) -> None:
    """Third rejection opens a suppression window and resets count to 0."""
    tid = uuid.uuid4()
    record_rejection(db, tid, "ACQ-001", today=_TODAY)
    record_rejection(db, tid, "ACQ-001", today=_TODAY)
    row = record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    expected_until = _TODAY + timedelta(days=30)
    assert row.suppressed_until == expected_until
    assert row.rejection_count == 0


def test_is_suppressed_returns_true_after_threshold(db: Session) -> None:
    """is_suppressed returns True once suppression window is open."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert is_suppressed(db, tid, "ACQ-001", today=_TODAY) is True


def test_is_suppressed_returns_false_after_window_expires(db: Session) -> None:
    """is_suppressed returns False once suppressed_until is in the past."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    day_after_expiry = _TODAY + timedelta(days=31)
    assert is_suppressed(db, tid, "ACQ-001", today=day_after_expiry) is False


def test_record_rejection_while_suppressed_does_not_increment(db: Session) -> None:
    """Rejections during active suppression are ignored."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    row = record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert row.rejection_count == 0  # still at 0, unchanged


def test_record_rejection_resets_after_natural_expiry(db: Session) -> None:
    """After natural expiry, the next rejection starts a fresh count of 1."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    day_after_expiry = _TODAY + timedelta(days=31)
    row = record_rejection(db, tid, "ACQ-001", today=day_after_expiry)
    db.commit()

    assert row.rejection_count == 1
    assert row.suppressed_until is None


def test_lift_suppression_marks_overridden(db: Session) -> None:
    """lift_suppression sets is_overridden=True and resets count."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    row = lift_suppression(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert row is not None
    assert row.is_overridden is True
    assert row.rejection_count == 0


def test_lift_suppression_returns_none_when_nothing_active(db: Session) -> None:
    """lift_suppression returns None when there is no active window."""
    tid = uuid.uuid4()
    result = lift_suppression(db, tid, "ACQ-001", today=_TODAY)
    assert result is None


def test_is_suppressed_returns_false_after_override(db: Session) -> None:
    """is_suppressed returns False once the window is overridden."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()
    lift_suppression(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert is_suppressed(db, tid, "ACQ-001", today=_TODAY) is False


def test_record_rejection_resets_after_override(db: Session) -> None:
    """After an admin override, the next rejection starts a fresh count of 1."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()
    lift_suppression(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    row = record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert row.rejection_count == 1
    assert row.suppressed_until is None
    assert row.is_overridden is False


def test_suppression_does_not_bleed_across_rule_ids(db: Session) -> None:
    """Suppression for one rule_id does not affect another."""
    tid = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid, "ACQ-001", today=_TODAY)
    db.commit()

    assert is_suppressed(db, tid, "ACQ-001", today=_TODAY) is True
    assert is_suppressed(db, tid, "INV-001", today=_TODAY) is False


def test_suppression_does_not_bleed_across_tenants(db: Session) -> None:
    """Suppression for one tenant does not affect another tenant."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    for _ in range(3):
        record_rejection(db, tid_a, "ACQ-001", today=_TODAY)
    db.commit()

    assert is_suppressed(db, tid_a, "ACQ-001", today=_TODAY) is True
    assert is_suppressed(db, tid_b, "ACQ-001", today=_TODAY) is False


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------


def test_list_suppressions_empty(client: TestClient) -> None:
    """GET suppressions returns empty list when no rejections recorded."""
    email = "admin@sup001.local"
    tenant_id = _create_tenant(client, "sup001", email)

    resp = client.get(
        f"/tenants/{tenant_id}/recommendation-suppressions",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_patch_reject_creates_suppression_state(client: TestClient) -> None:
    """Rejecting a recommendation via PATCH creates a suppression state row."""
    email = "admin@sup002.local"
    tenant_id = _create_tenant(client, "sup002", email)
    rec_id = _seed_recommendation(client, tenant_id)

    client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "rejected"},
        headers=_headers(email),
    )

    resp = client.get(
        f"/tenants/{tenant_id}/recommendation-suppressions",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["rule_id"] == "ACQ-001"
    assert body["items"][0]["rejection_count"] == 1
    assert body["items"][0]["suppressed_until"] is None


def test_three_rejects_creates_active_suppression(client: TestClient) -> None:
    """Three rejections via PATCH triggers a suppression window."""
    email = "admin@sup003.local"
    tenant_id = _create_tenant(client, "sup003", email)

    for i in range(3):
        rec_id = _seed_recommendation(
            client,
            tenant_id,
            snapshot_date=date(2026, 6, i + 1),
        )
        client.patch(
            f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
            json={"to_status": "rejected"},
            headers=_headers(email),
        )

    resp = client.get(
        f"/tenants/{tenant_id}/recommendation-suppressions",
        headers=_headers(email),
    )
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["suppressed_until"] is not None
    assert items[0]["rejection_count"] == 0


def test_override_endpoint_lifts_suppression(client: TestClient) -> None:
    """POST override clears an active suppression window."""
    email = "admin@sup004.local"
    tenant_id = _create_tenant(client, "sup004", email)

    for i in range(3):
        rec_id = _seed_recommendation(
            client,
            tenant_id,
            snapshot_date=date(2026, 6, i + 1),
        )
        client.patch(
            f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
            json={"to_status": "rejected"},
            headers=_headers(email),
        )

    resp = client.post(
        f"/tenants/{tenant_id}/recommendation-suppressions/ACQ-001/override",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_overridden"] is True
    assert body["rejection_count"] == 0


def test_override_endpoint_404_when_nothing_active(client: TestClient) -> None:
    """POST override returns 404 when no active suppression exists."""
    email = "admin@sup005.local"
    tenant_id = _create_tenant(client, "sup005", email)

    resp = client.post(
        f"/tenants/{tenant_id}/recommendation-suppressions/ACQ-001/override",
        headers=_headers(email),
    )
    assert resp.status_code == 404


def test_list_suppressions_requires_tenant_membership(client: TestClient) -> None:
    """Non-member gets 403 on the suppression list endpoint."""
    email = "admin@sup006.local"
    tenant_id = _create_tenant(client, "sup006", email)

    resp = client.get(
        f"/tenants/{tenant_id}/recommendation-suppressions",
        headers=_headers("outsider@sup006.local"),
    )
    assert resp.status_code == 403
