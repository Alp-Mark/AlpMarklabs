"""FR-073 / T-059: Tests for recommendation status PATCH endpoint."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import AuditEvent, Recommendation
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    *,
    status: str = "new",
    rule_id: str = "TEST-001",
) -> str:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        rec = Recommendation(
            tenant_id=uuid.UUID(tenant_id),
            rule_id=rule_id,
            domain="acquisition",
            snapshot_date=date.today(),
            affected_area="Channel: Meta",
            signal_summary="ROAS below threshold",
            suggested_action="Reduce Meta budget",
            estimated_impact=1000.0,
            confidence_level="high",
            data_freshness_context="1 day old",
            priority=10,
            status=status,
        )
        db.add(rec)
        db.commit()
        rec_id = str(rec.id)
    finally:
        db_gen.close()
    return rec_id


def _get_db(client: TestClient) -> Session:
    db_gen = app.dependency_overrides[get_db]()
    return next(db_gen)


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_transition_new_to_reviewed(client: TestClient) -> None:
    """new → reviewed succeeds and returns updated status."""
    email = "admin@t059a.local"
    tenant_id = _create_tenant(client, "t059a", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed"},
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "reviewed"
    assert body["review_note"] is None


def test_transition_with_note_persisted(client: TestClient) -> None:
    """Note is stored when provided."""
    email = "admin@t059b.local"
    tenant_id = _create_tenant(client, "t059b", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed", "note": "Looks good, escalating."},
        headers=_headers(email),
    )
    assert resp.status_code == 200
    assert resp.json()["review_note"] == "Looks good, escalating."


def test_transition_approved_then_rejected(client: TestClient) -> None:
    """reviewed → approved → rejected full chain works."""
    email = "admin@t059c.local"
    tenant_id = _create_tenant(client, "t059c", email)
    rec_id = _seed_recommendation(client, tenant_id, status="reviewed")

    client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "approved"},
        headers=_headers(email),
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "rejected", "note": "Changed strategy."},
        headers=_headers(email),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["review_note"] == "Changed strategy."


def test_transition_full_chain_to_outcome_observed(client: TestClient) -> None:
    """Full chain new→reviewed→approved→implemented_externally→outcome_observed."""
    email = "admin@t059d.local"
    tenant_id = _create_tenant(client, "t059d", email)
    rec_id = _seed_recommendation(client, tenant_id)

    for to_status in (
        "reviewed",
        "approved",
        "implemented_externally",
        "outcome_observed",
    ):
        resp = client.patch(
            f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
            json={"to_status": to_status},
            headers=_headers(email),
        )
        assert resp.status_code == 200, f"Failed at {to_status}: {resp.json()}"
        assert resp.json()["status"] == to_status


def test_note_is_optional(client: TestClient) -> None:
    """Omitting note entirely is accepted."""
    email = "admin@t059e.local"
    tenant_id = _create_tenant(client, "t059e", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed"},
        headers=_headers(email),
    )
    assert resp.status_code == 200
    assert resp.json()["review_note"] is None


def test_audit_event_written_on_transition(client: TestClient) -> None:
    """An audit event is created with from/to status on each transition."""
    email = "admin@t059f.local"
    tenant_id = _create_tenant(client, "t059f", email)
    rec_id = _seed_recommendation(client, tenant_id)

    client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed", "note": "audit check"},
        headers=_headers(email),
    )

    db = _get_db(client)
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == rec_id,
            AuditEvent.action == "recommendation.status_changed",
        )
    )
    assert event is not None
    assert event.details["from_status"] == "new"
    assert event.details["to_status"] == "reviewed"
    assert event.details["note"] == "audit check"


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_illegal_transition_returns_422(client: TestClient) -> None:
    """Skipping reviewed (new → approved) returns 422."""
    email = "admin@t059g.local"
    tenant_id = _create_tenant(client, "t059g", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "approved"},
        headers=_headers(email),
    )
    assert resp.status_code == 422
    assert "approved" in resp.json()["detail"]


def test_unknown_to_status_returns_422(client: TestClient) -> None:
    """Unknown status string is rejected with 422."""
    email = "admin@t059h.local"
    tenant_id = _create_tenant(client, "t059h", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "flying"},
        headers=_headers(email),
    )
    assert resp.status_code == 422


def test_transition_from_terminal_rejected_returns_422(client: TestClient) -> None:
    """Cannot transition out of rejected (terminal state)."""
    email = "admin@t059i.local"
    tenant_id = _create_tenant(client, "t059i", email)
    rec_id = _seed_recommendation(client, tenant_id, status="rejected")

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "new"},
        headers=_headers(email),
    )
    assert resp.status_code == 422


def test_transition_from_terminal_outcome_observed_returns_422(
    client: TestClient,
) -> None:
    """Cannot transition out of outcome_observed (terminal state)."""
    email = "admin@t059j.local"
    tenant_id = _create_tenant(client, "t059j", email)
    rec_id = _seed_recommendation(client, tenant_id, status="outcome_observed")

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "approved"},
        headers=_headers(email),
    )
    assert resp.status_code == 422


def test_recommendation_not_found_returns_404(client: TestClient) -> None:
    """Unknown recommendation_id returns 404."""
    email = "admin@t059k.local"
    tenant_id = _create_tenant(client, "t059k", email)
    fake_id = str(uuid.uuid4())

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{fake_id}/status",
        json={"to_status": "reviewed"},
        headers=_headers(email),
    )
    assert resp.status_code == 404


def test_recommendation_from_other_tenant_returns_404(client: TestClient) -> None:
    """rec belonging to tenant A is not visible when patching via tenant B's URL."""
    email_a = "admin@t059la.local"
    email_b = "admin@t059lb.local"
    tenant_a = _create_tenant(client, "t059la", email_a)
    tenant_b = _create_tenant(client, "t059lb", email_b)
    rec_id = _seed_recommendation(client, tenant_a)

    resp = client.patch(
        f"/tenants/{tenant_b}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed"},
        headers=_headers(email_b),
    )
    assert resp.status_code == 404


def test_non_member_cannot_transition_status(client: TestClient) -> None:
    """A user who is not a member of the tenant gets 403."""
    email = "admin@t059m.local"
    tenant_id = _create_tenant(client, "t059m", email)
    rec_id = _seed_recommendation(client, tenant_id)

    resp = client.patch(
        f"/tenants/{tenant_id}/recommendations/{rec_id}/status",
        json={"to_status": "reviewed"},
        headers=_headers("outsider@t059m.local"),
    )
    assert resp.status_code == 403
