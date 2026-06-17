"""FR-023, FR-075 / T-061: Tests for delegation rules and revocation flow."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_FROM = date(2026, 6, 10)
_VALID_UNTIL = date(2026, 7, 10)


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _seed_member(
    client: TestClient,
    tenant_id: str,
    email: str,
    role: str = "growth_performance_manager",
) -> uuid.UUID:
    """Create a User + TenantMembership directly in the test DB."""
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        user = User(email=email, full_name="Test Member", is_active=True)
        db.add(user)
        db.flush()
        membership = TenantMembership(
            tenant_id=uuid.UUID(tenant_id),
            user_id=user.id,
            role=role,
        )
        db.add(membership)
        db.commit()
        return user.id
    finally:
        db_gen.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_delegation_rule_returns_201(client: TestClient) -> None:
    """Creating a delegation rule returns 201 with the rule data."""
    email = "admin@del001.local"
    tenant_id = _create_tenant(client, "del001", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del001.local")

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["delegatee_user_id"] == str(delegatee_id)
    assert body["domain"] == "inventory"
    assert body["is_active"] is True
    assert body["revoked_at"] is None


def test_create_delegation_rule_non_member_delegatee_returns_400(
    client: TestClient,
) -> None:
    """Delegatee must be a tenant member; non-member → 400."""
    email = "admin@del002.local"
    tenant_id = _create_tenant(client, "del002", email)

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(uuid.uuid4()),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )
    assert resp.status_code == 400


def test_create_delegation_rule_invalid_date_range_returns_422(
    client: TestClient,
) -> None:
    """valid_until before valid_from is rejected by the Pydantic validator."""
    email = "admin@del003.local"
    tenant_id = _create_tenant(client, "del003", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del003.local")

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "retention",
            "valid_from": "2026-07-10",
            "valid_until": "2026-06-10",  # before valid_from
        },
        headers=_headers(email),
    )
    assert resp.status_code == 422


def test_multiple_delegations_same_domain_allowed(client: TestClient) -> None:
    """Multiple active delegations for the same domain are permitted."""
    email = "admin@del004.local"
    tenant_id = _create_tenant(client, "del004", email)
    delegatee_a = _seed_member(client, tenant_id, "ops-a@del004.local")
    delegatee_b = _seed_member(client, tenant_id, "ops-b@del004.local")

    for delegatee_id in [delegatee_a, delegatee_b]:
        resp = client.post(
            f"/tenants/{tenant_id}/delegation-rules",
            json={
                "delegatee_user_id": str(delegatee_id),
                "domain": "inventory",
                "valid_from": str(_VALID_FROM),
                "valid_until": str(_VALID_UNTIL),
            },
            headers=_headers(email),
        )
        assert resp.status_code == 201

    list_resp = client.get(
        f"/tenants/{tenant_id}/delegation-rules",
        headers=_headers(email),
    )
    assert list_resp.json()["total"] == 2


def test_list_delegation_rules_empty(client: TestClient) -> None:
    """GET returns empty list when no rules have been created."""
    email = "admin@del005.local"
    tenant_id = _create_tenant(client, "del005", email)

    resp = client.get(
        f"/tenants/{tenant_id}/delegation-rules",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_delegation_rules_returns_all(client: TestClient) -> None:
    """GET returns all rules including revoked ones by default."""
    email = "admin@del006.local"
    tenant_id = _create_tenant(client, "del006", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del006.local")

    # Create and revoke one rule, create another active rule
    create_resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )
    rule_id = create_resp.json()["id"]
    client.post(
        f"/tenants/{tenant_id}/delegation-rules/{rule_id}/revoke",
        headers=_headers(email),
    )
    client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )

    resp = client.get(
        f"/tenants/{tenant_id}/delegation-rules",
        headers=_headers(email),
    )
    assert resp.json()["total"] == 2


def test_list_delegation_rules_active_only(client: TestClient) -> None:
    """active_only=true filters out revoked rules."""
    email = "admin@del007.local"
    tenant_id = _create_tenant(client, "del007", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del007.local")

    # Create two rules, revoke one
    r1 = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    ).json()["id"]
    client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )
    client.post(
        f"/tenants/{tenant_id}/delegation-rules/{r1}/revoke",
        headers=_headers(email),
    )

    resp = client.get(
        f"/tenants/{tenant_id}/delegation-rules?active_only=true",
        headers=_headers(email),
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["is_active"] is True


def test_revoke_delegation_rule(client: TestClient) -> None:
    """Revoking a rule sets is_active=False and records revoked_at."""
    email = "admin@del008.local"
    tenant_id = _create_tenant(client, "del008", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del008.local")

    rule_id = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    ).json()["id"]

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules/{rule_id}/revoke",
        headers=_headers(email),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["revoked_at"] is not None


def test_revoke_already_revoked_returns_409(client: TestClient) -> None:
    """Revoking an already-revoked rule returns 409."""
    email = "admin@del009.local"
    tenant_id = _create_tenant(client, "del009", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del009.local")

    rule_id = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    ).json()["id"]

    client.post(
        f"/tenants/{tenant_id}/delegation-rules/{rule_id}/revoke",
        headers=_headers(email),
    )
    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules/{rule_id}/revoke",
        headers=_headers(email),
    )
    assert resp.status_code == 409


def test_revoke_wrong_tenant_returns_404(client: TestClient) -> None:
    """Revoking a rule from a different tenant returns 404."""
    email_a = "admin@del010a.local"
    email_b = "admin@del010b.local"
    tenant_a = _create_tenant(client, "del010a", email_a)
    tenant_b = _create_tenant(client, "del010b", email_b)

    delegatee_id = _seed_member(client, tenant_a, "ops@del010a.local")
    rule_id = client.post(
        f"/tenants/{tenant_a}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email_a),
    ).json()["id"]

    # Try to revoke from tenant B
    resp = client.post(
        f"/tenants/{tenant_b}/delegation-rules/{rule_id}/revoke",
        headers=_headers(email_b),
    )
    assert resp.status_code == 404


def test_create_requires_brand_admin(client: TestClient) -> None:
    """Non-member gets 403 when creating a delegation rule."""
    email = "admin@del011.local"
    tenant_id = _create_tenant(client, "del011", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del011.local")

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers("outsider@del011.local"),
    )
    assert resp.status_code == 403


def test_list_requires_brand_admin(client: TestClient) -> None:
    """Non-member gets 403 when listing delegation rules."""
    email = "admin@del012.local"
    tenant_id = _create_tenant(client, "del012", email)

    resp = client.get(
        f"/tenants/{tenant_id}/delegation-rules",
        headers=_headers("outsider@del012.local"),
    )
    assert resp.status_code == 403


def test_revoke_requires_brand_admin(client: TestClient) -> None:
    """Non-member gets 403 when revoking a delegation rule."""
    email = "admin@del013.local"
    tenant_id = _create_tenant(client, "del013", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del013.local")

    rule_id = client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "inventory",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    ).json()["id"]

    resp = client.post(
        f"/tenants/{tenant_id}/delegation-rules/{rule_id}/revoke",
        headers=_headers("outsider@del013.local"),
    )
    assert resp.status_code == 403


def test_audit_event_written_on_create(client: TestClient) -> None:
    """Creating a delegation rule writes a delegation_rule.created audit event."""
    from backend.app.db.models import AuditEvent
    from sqlalchemy import select as sa_select

    email = "admin@del014.local"
    tenant_id = _create_tenant(client, "del014", email)
    delegatee_id = _seed_member(client, tenant_id, "ops@del014.local")

    client.post(
        f"/tenants/{tenant_id}/delegation-rules",
        json={
            "delegatee_user_id": str(delegatee_id),
            "domain": "acquisition",
            "valid_from": str(_VALID_FROM),
            "valid_until": str(_VALID_UNTIL),
        },
        headers=_headers(email),
    )

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        event = db.scalar(
            sa_select(AuditEvent).where(
                AuditEvent.tenant_id == uuid.UUID(tenant_id),
                AuditEvent.action == "delegation_rule.created",
            )
        )
        assert event is not None
        assert event.entity_type == "delegation_rule"
    finally:
        db_gen.close()
