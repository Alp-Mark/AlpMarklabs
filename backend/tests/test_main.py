import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import backend.app.main as main_module
import jwt
import pytest
from backend.app import security
from backend.app.db.base import Base
from backend.app.db.models import (
    AuditEvent,
    ConnectorCredentialVault,
    ConnectorIntegration,
    CostDriverSnapshot,
    CostInput,
    CostInputVersion,
    InventoryRiskThreshold,
    MarginDriftThreshold,
    Role,
    TenantMembership,
    User,
    UserInvitation,
)
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session]:
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        token = jwt.encode(
            {
                "sub": "test-user",
                "email": "tester@alpmark.local",
                "platform_role": "super_admin",
            },
            AUTH_JWT_SECRET,
            algorithm=AUTH_JWT_ALGORITHM,
        )
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _make_auth_token(payload: dict[str, object]) -> str:
    return jwt.encode(
        payload,
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _set_auth_header(client: TestClient, payload: dict[str, object]) -> None:
    client.headers["Authorization"] = f"Bearer {_make_auth_token(payload)}"


def _create_tenant_as_super_admin(
    client: TestClient,
    *,
    tenant_name: str,
    tenant_slug: str,
    email: str,
) -> str:
    _set_auth_header(
        client,
        {
            "sub": f"{tenant_slug}-super-admin",
            "email": email,
            "platform_role": "super_admin",
        },
    )
    response = client.post(
        "/tenants",
        json={"name": tenant_name, "slug": tenant_slug},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]
    
    # Upgrade to operations_inventory_manager (has all permissions)
    db_gen = main_module.app.dependency_overrides[get_db]()
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
    
    return tenant_id


def test_health_route_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_tenant_returns_unique_tenant_id(client: TestClient) -> None:
    response = client.post("/tenants", json={"name": "Acme", "slug": "acme"})

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["name"] == "Acme"
    assert body["slug"] == "acme"
    assert body["is_active"] is True


def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    current_header = client.headers.get("Authorization")
    if current_header is not None:
        del client.headers["Authorization"]

    response = client.post("/tenants", json={"name": "NoAuth", "slug": "noauth"})

    if current_header is not None:
        client.headers["Authorization"] = current_header

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_endpoint_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/tenants",
        json={"name": "BadToken", "slug": "badtoken"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication token."}


def test_create_tenant_requires_super_admin_role(client: TestClient) -> None:
    viewer_token = _make_auth_token(
        {"sub": "viewer-user", "email": "viewer@alpmark.local"}
    )

    response = client.post(
        "/tenants",
        json={"name": "NoPlatformRole", "slug": "noplatformrole"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_protected_endpoint_rejects_token_without_required_claims(
    client: TestClient,
) -> None:
    token = _make_auth_token({"sub": "missing-email"})

    response = client.post(
        "/tenants",
        json={"name": "MissingClaims", "slug": "missingclaims"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Token payload is missing required claims."}


def test_protected_endpoint_accepts_provider_claims_when_optional_checks_unset(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(security, "AUTH_JWT_ISSUER", None)
    monkeypatch.setattr(security, "AUTH_JWT_AUDIENCE", None)
    token = _make_auth_token(
        {
            "sub": "provider-user",
            "email": "provider@alpmark.local",
            "iss": "https://auth.example.com/",
            "aud": "alpmark-api",
            "platform_role": "super_admin",
        }
    )

    response = client.post(
        "/tenants",
        json={"name": "ProviderClaims", "slug": "providerclaims"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201


def test_protected_endpoint_validates_configured_issuer_and_audience(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(security, "AUTH_JWT_ISSUER", "https://auth.example.com/")
    monkeypatch.setattr(security, "AUTH_JWT_AUDIENCE", "alpmark-api")
    token = _make_auth_token(
        {
            "sub": "scoped-user",
            "email": "scoped@alpmark.local",
            "iss": "https://auth.example.com/",
            "aud": "alpmark-api",
            "platform_role": "super_admin",
        }
    )

    response = client.post(
        "/tenants",
        json={"name": "ScopedClaims", "slug": "scopedclaims"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201


def test_create_tenant_rejects_duplicate_slug(client: TestClient) -> None:
    first_response = client.post("/tenants", json={"name": "Acme", "slug": "acme"})
    second_response = client.post("/tenants", json={"name": "Acme 2", "slug": "acme"})

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "A tenant with this slug already exists."
    }


def test_invite_user_creates_activation_token(client: TestClient) -> None:
    tenant_response = client.post("/tenants", json={"name": "Acme", "slug": "acme"})
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    invite_response = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={"email": "new.user@acme.com", "role": "brand_admin"},
    )

    assert invite_response.status_code == 201
    payload = invite_response.json()
    assert uuid.UUID(payload["invitation_id"])
    assert payload["tenant_id"] == tenant_id
    assert payload["email"] == "new.user@acme.com"
    assert payload["role"] == "brand_admin"
    assert payload["token"]
    assert payload["expires_at"]


def test_invite_user_rejects_duplicate_pending_invite(client: TestClient) -> None:
    tenant_response = client.post("/tenants", json={"name": "Nova", "slug": "nova"})
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    first_invite = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "new.user@nova.com",
            "role": "growth_performance_manager",
        },
    )
    second_invite = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "new.user@nova.com",
            "role": "growth_performance_manager",
        },
    )

    assert first_invite.status_code == 201
    assert second_invite.status_code == 409
    assert second_invite.json() == {
        "detail": "A pending invitation already exists for this email."
    }


def test_invite_user_tenant_not_found(client: TestClient) -> None:
    response = client.post(
        f"/tenants/{uuid.uuid4()}/invitations",
        json={
            "email": "missing@tenant.com",
            "role": "growth_performance_manager",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tenant not found."}


def test_tenant_admin_endpoints_reject_non_admin_member(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "MemberRoleCo", "slug": "memberroleco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    viewer_invite = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "viewer@memberroleco.com",
            "role": "growth_performance_manager",
        },
    )
    assert viewer_invite.status_code == 201

    activation = client.post(
        "/accounts/activate",
        json={
            "token": viewer_invite.json()["token"],
            "full_name": "Viewer User",
            "password": "testpass123",
        },
    )
    assert activation.status_code == 200

    _set_auth_header(
        client,
        {"sub": "viewer-member", "email": "viewer@memberroleco.com"},
    )
    response = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "blocked@memberroleco.com",
            "role": "growth_performance_manager",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_tenant_admin_cannot_read_other_tenant_billing(client: TestClient) -> None:
    tenant_a_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Tenant A",
        tenant_slug="tenant-a",
        email="admin-a@alpmark.local",
    )
    tenant_b_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Tenant B",
        tenant_slug="tenant-b",
        email="admin-b@alpmark.local",
    )

    _set_auth_header(
        client,
        {"sub": "tenant-a-admin", "email": "admin-a@alpmark.local"},
    )
    response = client.get(f"/tenants/{tenant_b_id}/billing-seats")

    assert tenant_a_id != tenant_b_id
    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_tenant_admin_cannot_invite_into_other_tenant(client: TestClient) -> None:
    _create_tenant_as_super_admin(
        client,
        tenant_name="Tenant Alpha",
        tenant_slug="tenant-alpha",
        email="admin-alpha@alpmark.local",
    )
    tenant_b_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Tenant Beta",
        tenant_slug="tenant-beta",
        email="admin-beta@alpmark.local",
    )

    _set_auth_header(
        client,
        {"sub": "tenant-alpha-admin", "email": "admin-alpha@alpmark.local"},
    )
    response = client.post(
        f"/tenants/{tenant_b_id}/invitations",
        json={
            "email": "blocked@tenant-beta.com",
            "role": "growth_performance_manager",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_invite_then_activate_flow_works(client: TestClient) -> None:
    tenant_response = client.post("/tenants", json={"name": "Flux", "slug": "flux"})
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    invite_response = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={"email": "invitee@flux.com", "role": "brand_admin"},
    )
    assert invite_response.status_code == 201
    token = invite_response.json()["token"]

    activation_response = client.post(
        "/accounts/activate",
        json={"token": token, "full_name": "Invited User", "password": "testpass123"},
    )

    assert activation_response.status_code == 200
    payload = activation_response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["email"] == "invitee@flux.com"
    assert payload["role"] == "brand_admin"


def _create_active_member(
    client: TestClient,
    *,
    tenant_name: str,
    tenant_slug: str,
    email: str,
    role: str,
    full_name: str,
) -> tuple[str, str]:
    tenant_response = client.post(
        "/tenants", json={"name": tenant_name, "slug": tenant_slug}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    invite_response = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={"email": email, "role": role},
    )
    assert invite_response.status_code == 201
    token = invite_response.json()["token"]

    activation_response = client.post(
        "/accounts/activate",
        json={"token": token, "full_name": full_name, "password": "testpass123"},
    )
    assert activation_response.status_code == 200

    return tenant_id, activation_response.json()["user_id"]


def test_update_member_role_success(client: TestClient) -> None:
    tenant_id, user_id = _create_active_member(
        client,
        tenant_name="RoleCo",
        tenant_slug="roleco",
        email="member@roleco.com",
        role="growth_performance_manager",
        full_name="Role Member",
    )

    update_response = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/role",
        json={"role": "brand_admin"},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["user_id"] == user_id
    assert payload["role"] == "brand_admin"
    assert payload["is_active"] is True


def test_update_member_role_rejects_invalid_role(client: TestClient) -> None:
    tenant_id, user_id = _create_active_member(
        client,
        tenant_name="BadRoleCo",
        tenant_slug="badroleco",
        email="member@badroleco.com",
        role="growth_performance_manager",
        full_name="Bad Role Member",
    )

    response = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/role",
        json={"role": "superadmin"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Role is not supported."}


def test_deactivate_member_success(client: TestClient) -> None:
    tenant_id, user_id = _create_active_member(
        client,
        tenant_name="DeactivateCo",
        tenant_slug="deactivateco",
        email="member@deactivateco.com",
        role="brand_admin",
        full_name="Deactivate Member",
    )

    deactivate_response = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/deactivate"
    )

    assert deactivate_response.status_code == 200
    payload = deactivate_response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["user_id"] == user_id
    assert payload["is_active"] is False


def test_deactivate_member_not_found(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "NoMemberCo", "slug": "nomemberco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.patch(
        f"/tenants/{tenant_id}/members/{uuid.uuid4()}/deactivate"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Membership not found."}


def test_get_billing_and_seats_defaults(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "BillingCo", "slug": "billingco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.get(f"/tenants/{tenant_id}/billing-seats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["billing_plan"] == "starter"
    assert payload["billing_cycle"] == "monthly"
    assert payload["billing_status"] == "active"
    assert payload["seat_limit"] == 5
    assert payload["seats_used"] == 1
    assert payload["seats_available"] == 4
    assert payload["can_invite"] is True


def test_update_billing_and_seats_metadata(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "GrowthCo", "slug": "growthco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    update_response = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={
            "billing_plan": "pro",
            "billing_cycle": "yearly",
            "billing_status": "trialing",
            "seat_limit": 12,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["billing_plan"] == "pro"
    assert payload["billing_cycle"] == "yearly"
    assert payload["billing_status"] == "trialing"
    assert payload["seat_limit"] == 12
    assert payload["seats_available"] == 11


def test_update_billing_and_seats_rejects_invalid_cycle(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "CycleCo", "slug": "cycleco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={"billing_cycle": "weekly"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Billing cycle is not supported."}


def test_update_seat_limit_cannot_go_below_active_members(client: TestClient) -> None:
    tenant_id, _ = _create_active_member(
        client,
        tenant_name="SeatCo",
        tenant_slug="seatco",
        email="member1@seatco.com",
        role="growth_performance_manager",
        full_name="Seat Member 1",
    )

    response = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={"seat_limit": 0},
    )
    assert response.status_code == 422

    response = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={"seat_limit": 2},
    )
    assert response.status_code == 200

    second_member = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "member2@seatco.com",
            "role": "growth_performance_manager",
        },
    )
    assert second_member.status_code == 201
    second_token = second_member.json()["token"]
    activate_second = client.post(
        "/accounts/activate",
        json={
            "token": second_token,
            "full_name": "Seat Member 2",
            "password": "testpass123",
        },
    )
    assert activate_second.status_code == 200

    reject_response = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={"seat_limit": 1},
    )
    assert reject_response.status_code == 409
    assert reject_response.json() == {
        "detail": "Seat limit cannot be lower than current active seats."
    }


def test_get_billing_and_seats_reflects_active_usage(client: TestClient) -> None:
    tenant_id, _ = _create_active_member(
        client,
        tenant_name="UsageCo",
        tenant_slug="usageco",
        email="member@usageco.com",
        role="brand_admin",
        full_name="Usage Member",
    )

    response = client.get(f"/tenants/{tenant_id}/billing-seats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["seats_used"] == 2
    assert payload["seats_available"] == 3
    assert payload["can_invite"] is True


def test_get_notification_routing_defaults_empty(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "NotifyCo", "slug": "notifyco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.get(f"/tenants/{tenant_id}/notification-routing")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["routes"] == []


def test_upsert_notification_routing_settings(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "RouteCo", "slug": "routeco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    update_response = client.put(
        f"/tenants/{tenant_id}/notification-routing",
        json={
            "routes": [
                {
                    "alert_type": "kpi_drop",
                    "channel": "email",
                    "destination": "owner@routeco.com",
                    "is_enabled": True,
                },
                {
                    "alert_type": "sync_failure",
                    "channel": "slack",
                    "destination": "#ops-alerts",
                    "is_enabled": True,
                },
            ]
        },
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["tenant_id"] == tenant_id
    assert len(updated_payload["routes"]) == 2

    fetch_response = client.get(f"/tenants/{tenant_id}/notification-routing")
    assert fetch_response.status_code == 200
    fetched_payload = fetch_response.json()
    assert len(fetched_payload["routes"]) == 2

    routes = {
        (route["alert_type"], route["channel"], route["destination"])
        for route in fetched_payload["routes"]
    }
    assert routes == {
        ("kpi_drop", "email", "owner@routeco.com"),
        ("sync_failure", "slack", "#ops-alerts"),
    }


def test_upsert_notification_routing_rejects_invalid_channel(
    client: TestClient,
) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "BadNotify", "slug": "badnotify"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.put(
        f"/tenants/{tenant_id}/notification-routing",
        json={
            "routes": [
                {
                    "alert_type": "kpi_drop",
                    "channel": "sms",
                    "destination": "+919999999999",
                    "is_enabled": True,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Notification channel is not supported."
    }


def test_notification_routing_tenant_not_found(client: TestClient) -> None:
    response = client.get(f"/tenants/{uuid.uuid4()}/notification-routing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tenant not found."}


def _get_audit_events(tenant_id: str) -> list[AuditEvent]:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        return list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.tenant_id == uuid.UUID(tenant_id))
                .order_by(AuditEvent.created_at.asc())
            )
        )
    finally:
        db_gen.close()


def _get_connector_vault_entries(tenant_id: str) -> list[ConnectorCredentialVault]:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        return list(
            db.scalars(
                select(ConnectorCredentialVault)
                .where(ConnectorCredentialVault.tenant_id == uuid.UUID(tenant_id))
                .order_by(ConnectorCredentialVault.created_at.asc())
            )
        )
    finally:
        db_gen.close()


def test_audit_events_written_for_mutations(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "AuditCo", "slug": "auditco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    invite_response = client.post(
        f"/tenants/{tenant_id}/invitations",
        json={
            "email": "audit@auditco.com",
            "role": "growth_performance_manager",
        },
    )
    assert invite_response.status_code == 201
    token = invite_response.json()["token"]

    activation_response = client.post(
        "/accounts/activate",
        json={"token": token, "full_name": "Audit User", "password": "testpass123"},
    )
    assert activation_response.status_code == 200
    user_id = activation_response.json()["user_id"]

    role_update = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/role",
        json={"role": "brand_admin"},
    )
    assert role_update.status_code == 200

    billing_update = client.patch(
        f"/tenants/{tenant_id}/billing-seats",
        json={"billing_plan": "pro", "seat_limit": 5},
    )
    assert billing_update.status_code == 200

    notification_update = client.put(
        f"/tenants/{tenant_id}/notification-routing",
        json={
            "routes": [
                {
                    "alert_type": "kpi_drop",
                    "channel": "email",
                    "destination": "owner@auditco.com",
                    "is_enabled": True,
                }
            ]
        },
    )
    assert notification_update.status_code == 200

    deactivate = client.patch(f"/tenants/{tenant_id}/members/{user_id}/deactivate")
    assert deactivate.status_code == 200

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]

    assert actions == [
        "tenant.created",
        "user.invited",
        "account.activated",
        "member.role_updated",
        "billing.updated",
        "notification_routing.updated",
        "member.deactivated",
    ]
    assert len({event.id for event in events}) == len(events)


def test_audit_events_are_append_only_across_updates(client: TestClient) -> None:
    tenant_id, user_id = _create_active_member(
        client,
        tenant_name="AppendCo",
        tenant_slug="appendco",
        email="append@appendco.com",
        role="growth_performance_manager",
        full_name="Append User",
    )

    events_before = _get_audit_events(tenant_id)
    ids_before = {event.id for event in events_before}

    first_update = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/role",
        json={"role": "retention_crm_manager"},
    )
    assert first_update.status_code == 200

    second_update = client.patch(
        f"/tenants/{tenant_id}/members/{user_id}/role",
        json={"role": "finance_controller"},
    )
    assert second_update.status_code == 200

    events_after = _get_audit_events(tenant_id)
    ids_after = {event.id for event in events_after}

    assert ids_before.issubset(ids_after)
    assert len(events_after) == len(events_before) + 2


def _create_invitation(
    tenant_id: str,
    token: str,
    *,
    email: str = "founder@acme.com",
    role: str = "brand_admin",
    expires_at: datetime | None = None,
) -> None:
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        invitation = UserInvitation(
            tenant_id=uuid.UUID(tenant_id),
            email=email,
            role=role,
            token=token,
            expires_at=expires_at or (datetime.now(UTC) + timedelta(days=1)),
        )
        db.add(invitation)
        db.commit()
    finally:
        db_gen.close()


def test_account_activation_flow_success(client: TestClient) -> None:
    tenant_response = client.post("/tenants", json={"name": "Acme", "slug": "acme"})
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    _create_invitation(tenant_id, token="activate-token-1")

    activation_response = client.post(
        "/accounts/activate",
        json={
            "token": "activate-token-1",
            "full_name": "Sudeep Pemmaraju",
            "password": "testpass123",
        },
    )

    assert activation_response.status_code == 200
    payload = activation_response.json()
    assert uuid.UUID(payload["user_id"])
    assert payload["tenant_id"] == tenant_id
    assert payload["email"] == "founder@acme.com"
    assert payload["role"] == "brand_admin"
    assert payload["activated_at"]


def test_account_activation_token_not_found(client: TestClient) -> None:
    response = client.post(
        "/accounts/activate",
        json={
            "token": "missing-token",
            "full_name": "Sudeep Pemmaraju",
            "password": "testpass123",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activation token not found."}


def test_account_activation_token_cannot_be_reused(client: TestClient) -> None:
    tenant_response = client.post("/tenants", json={"name": "Beta", "slug": "beta"})
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    _create_invitation(tenant_id, token="activate-token-2")

    first_response = client.post(
        "/accounts/activate",
        json={
            "token": "activate-token-2",
            "full_name": "Sudeep Pemmaraju",
            "password": "testpass123",
        },
    )
    second_response = client.post(
        "/accounts/activate",
        json={
            "token": "activate-token-2",
            "full_name": "Sudeep Pemmaraju",
            "password": "testpass123",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Activation token has already been used."
    }


def test_onboarding_checklist_for_fresh_tenant(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "Gamma", "slug": "gamma"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    checklist_response = client.get(f"/tenants/{tenant_id}/onboarding-checklist")

    assert checklist_response.status_code == 200
    payload = checklist_response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["completed_steps"] == 2
    assert payload["total_steps"] == 4
    assert payload["completion_percent"] == 50

    states = {item["key"]: item["is_complete"] for item in payload["items"]}
    assert states == {
        "tenant_created": True,
        "invite_sent": False,
        "account_activated": True,
        "invite_accepted": False,
    }


def test_onboarding_checklist_updates_after_invite_and_activation(
    client: TestClient,
) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "Delta", "slug": "delta"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    _create_invitation(tenant_id, token="activate-token-3")

    after_invite = client.get(f"/tenants/{tenant_id}/onboarding-checklist")
    assert after_invite.status_code == 200
    invite_payload = after_invite.json()
    invite_states = {
        item["key"]: item["is_complete"] for item in invite_payload["items"]
    }
    assert invite_payload["completed_steps"] == 3
    assert invite_states["invite_sent"] is True
    assert invite_states["account_activated"] is True
    assert invite_states["invite_accepted"] is False

    activation_response = client.post(
        "/accounts/activate",
        json={
            "token": "activate-token-3",
            "full_name": "Delta User",
            "password": "testpass123",
        },
    )
    assert activation_response.status_code == 200

    after_activation = client.get(f"/tenants/{tenant_id}/onboarding-checklist")
    assert after_activation.status_code == 200
    activation_payload = after_activation.json()
    activation_states = {
        item["key"]: item["is_complete"] for item in activation_payload["items"]
    }
    assert activation_payload["completed_steps"] == 4
    assert activation_payload["completion_percent"] == 100
    assert activation_states["invite_sent"] is True
    assert activation_states["account_activated"] is True
    assert activation_states["invite_accepted"] is True


def test_onboarding_checklist_tenant_not_found(client: TestClient) -> None:
    missing_id = uuid.uuid4()
    response = client.get(f"/tenants/{missing_id}/onboarding-checklist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tenant not found."}


def test_create_and_list_privacy_requests(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "PrivacyCo", "slug": "privacyco"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    create_response = client.post(
        f"/tenants/{tenant_id}/privacy-requests",
        json={
            "request_type": "export",
            "subject_email": "customer@privacyco.com",
            "reason": "Customer requested data export",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["request_type"] == "export"
    assert payload["subject_email"] == "customer@privacyco.com"
    assert payload["status"] == "pending"

    list_response = client.get(f"/tenants/{tenant_id}/privacy-requests")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == payload["id"]


def test_update_privacy_request_status_is_audited(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "PrivacyAudit", "slug": "privacyaudit"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    create_response = client.post(
        f"/tenants/{tenant_id}/privacy-requests",
        json={
            "request_type": "delete",
            "subject_email": "erase@privacyaudit.com",
            "reason": "Deletion requested",
        },
    )
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]

    update_response = client.patch(
        f"/tenants/{tenant_id}/privacy-requests/{request_id}",
        json={"status": "completed", "resolution_note": "Deletion workflow executed"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"
    assert update_response.json()["resolution_note"] == "Deletion workflow executed"

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "privacy_request.created" in actions
    assert "privacy_request.status_updated" in actions


def test_privacy_request_rejects_invalid_type(client: TestClient) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "PrivacyInvalid", "slug": "privacyinvalid"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    response = client.post(
        f"/tenants/{tenant_id}/privacy-requests",
        json={
            "request_type": "archive",
            "subject_email": "customer@privacyinvalid.com",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Privacy request type is not supported."}


def test_privacy_request_requires_resolution_note_for_completion(
    client: TestClient,
) -> None:
    tenant_response = client.post(
        "/tenants", json={"name": "PrivacyNote", "slug": "privacynote"}
    )
    assert tenant_response.status_code == 201
    tenant_id = tenant_response.json()["id"]

    create_response = client.post(
        f"/tenants/{tenant_id}/privacy-requests",
        json={
            "request_type": "delete",
            "subject_email": "customer@privacynote.com",
        },
    )
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]

    response = client.patch(
        f"/tenants/{tenant_id}/privacy-requests/{request_id}",
        json={"status": "completed"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "Resolution note is required for completed or rejected privacy "
            "requests."
        )
    }


def test_tenant_admin_cannot_access_other_tenant_privacy_requests(
    client: TestClient,
) -> None:
    tenant_a_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Privacy Tenant A",
        tenant_slug="privacy-tenant-a",
        email="privacy-admin-a@alpmark.local",
    )
    tenant_b_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Privacy Tenant B",
        tenant_slug="privacy-tenant-b",
        email="privacy-admin-b@alpmark.local",
    )

    _set_auth_header(
        client,
        {"sub": "privacy-b-admin", "email": "privacy-admin-b@alpmark.local"},
    )
    create_response = client.post(
        f"/tenants/{tenant_b_id}/privacy-requests",
        json={
            "request_type": "export",
            "subject_email": "tenantb@alpmark.local",
        },
    )
    assert create_response.status_code == 201

    _set_auth_header(
        client,
        {"sub": "privacy-a-admin", "email": "privacy-admin-a@alpmark.local"},
    )
    list_response = client.get(f"/tenants/{tenant_b_id}/privacy-requests")

    assert tenant_a_id != tenant_b_id
    assert list_response.status_code == 403
    assert list_response.json() == {
        "detail": "You do not have permission to perform this action."
    }


def test_shopify_oauth_start_and_callback_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ShopifyCo",
        tenant_slug="shopifyco",
        email="shopify-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "shopify-admin", "email": "shopify-admin@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "test-store.myshopify.com"},
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["tenant_id"] == tenant_id
    assert start_payload["source"] == "shopify"
    assert start_payload["status"] == "pending_oauth"
    assert start_payload["state"]
    parsed = urlparse(start_payload["auth_url"])
    assert parsed.netloc == "test-store.myshopify.com"
    query_params = parse_qs(parsed.query)
    assert query_params["state"][0] == start_payload["state"]

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_payload["state"],
            "code": "authorization-code-1234",
            "shop_domain": "test-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200
    callback_payload = callback_response.json()
    assert callback_payload["tenant_id"] == tenant_id
    assert callback_payload["status"] == "connected"
    assert callback_payload["shop_domain"] == "test-store.myshopify.com"
    assert callback_payload["connected_at"] is not None
    assert callback_payload["last_sync_requested_at"] is not None

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.oauth_started" in actions
    assert "connector.oauth_completed" in actions


def test_shopify_oauth_callback_rejects_invalid_state(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ShopifyInvalidState",
        tenant_slug="shopify-invalid-state",
        email="shopify-invalid@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "shopify-invalid", "email": "shopify-invalid@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "invalid-state.myshopify.com"},
    )
    assert start_response.status_code == 200

    response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": "wrong-state-token",
            "code": "authorization-code-9999",
            "shop_domain": "invalid-state.myshopify.com",
        },
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "OAuth state is invalid."}


def test_shopify_oauth_callback_enforces_tenant_isolation(client: TestClient) -> None:
    tenant_a_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Shopify Tenant A",
        tenant_slug="shopify-tenant-a",
        email="shopify-a@alpmark.local",
    )
    tenant_b_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Shopify Tenant B",
        tenant_slug="shopify-tenant-b",
        email="shopify-b@alpmark.local",
    )

    _set_auth_header(
        client,
        {"sub": "shopify-a", "email": "shopify-a@alpmark.local"},
    )
    start_a = client.post(
        f"/tenants/{tenant_a_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "tenant-a.myshopify.com"},
    )
    assert start_a.status_code == 200

    _set_auth_header(
        client,
        {"sub": "shopify-b", "email": "shopify-b@alpmark.local"},
    )
    start_b = client.post(
        f"/tenants/{tenant_b_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "tenant-b.myshopify.com"},
    )
    assert start_b.status_code == 200

    response = client.post(
        f"/tenants/{tenant_b_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_a.json()["state"],
            "code": "authorization-code-tenant-a",
            "shop_domain": "tenant-b.myshopify.com",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "OAuth state is invalid."}


def test_shopify_oauth_stores_encrypted_secret_in_vault(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="VaultOAuth",
        tenant_slug="vaultoauth",
        email="vault-oauth@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "vault-oauth", "email": "vault-oauth@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "vault-store.myshopify.com"},
    )
    assert start_response.status_code == 200
    oauth_code = "oauth-code-for-vault-1234"
    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_response.json()["state"],
            "code": oauth_code,
            "shop_domain": "vault-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200

    entries = _get_connector_vault_entries(tenant_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.secret_type == "oauth_code"
    assert entry.secret_ciphertext != oauth_code
    assert callback_response.json()["connector_id"]


def test_meta_oauth_start_and_callback_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="MetaCo",
        tenant_slug="metaco",
        email="meta-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "meta-admin", "email": "meta-admin@alpmark.local"},
    )

    start_response = client.post(f"/tenants/{tenant_id}/connectors/meta/oauth/start")
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["tenant_id"] == tenant_id
    assert start_payload["source"] == "meta"
    assert start_payload["status"] == "pending_oauth"
    assert start_payload["state"]
    parsed = urlparse(start_payload["auth_url"])
    assert parsed.netloc == "www.facebook.com"
    query_params = parse_qs(parsed.query)
    assert query_params["state"][0] == start_payload["state"]

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/meta/oauth/callback",
        json={
            "state": start_payload["state"],
            "code": "meta-authorization-code-1234",
        },
    )
    assert callback_response.status_code == 200
    callback_payload = callback_response.json()
    assert callback_payload["tenant_id"] == tenant_id
    assert callback_payload["source"] == "meta"
    assert callback_payload["status"] == "connected"
    assert callback_payload["connected_at"] is not None
    assert callback_payload["last_sync_requested_at"] is not None

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.oauth_started" in actions
    assert "connector.oauth_completed" in actions


def test_meta_oauth_callback_rejects_invalid_state(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="MetaInvalidState",
        tenant_slug="meta-invalid-state",
        email="meta-invalid@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "meta-invalid", "email": "meta-invalid@alpmark.local"},
    )

    start_response = client.post(f"/tenants/{tenant_id}/connectors/meta/oauth/start")
    assert start_response.status_code == 200

    response = client.post(
        f"/tenants/{tenant_id}/connectors/meta/oauth/callback",
        json={
            "state": "wrong-meta-state",
            "code": "meta-authorization-code-9999",
        },
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "OAuth state is invalid."}


def test_google_ads_oauth_start_and_callback_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="GoogleAdsCo",
        tenant_slug="googleadsco",
        email="google-ads-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {
            "sub": "google-ads-admin",
            "email": "google-ads-admin@alpmark.local",
        },
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/google_ads/oauth/start"
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["tenant_id"] == tenant_id
    assert start_payload["source"] == "google_ads"
    assert start_payload["status"] == "pending_oauth"
    assert start_payload["state"]
    parsed = urlparse(start_payload["auth_url"])
    assert parsed.netloc == "accounts.google.com"
    query_params = parse_qs(parsed.query)
    assert query_params["state"][0] == start_payload["state"]

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/google_ads/oauth/callback",
        json={
            "state": start_payload["state"],
            "code": "google-ads-auth-code-1234",
        },
    )
    assert callback_response.status_code == 200
    callback_payload = callback_response.json()
    assert callback_payload["tenant_id"] == tenant_id
    assert callback_payload["source"] == "google_ads"
    assert callback_payload["status"] == "connected"
    assert callback_payload["connected_at"] is not None
    assert callback_payload["last_sync_requested_at"] is not None

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.oauth_started" in actions
    assert "connector.oauth_completed" in actions


def test_google_ads_oauth_callback_rejects_invalid_state(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="GoogleAdsInvalidState",
        tenant_slug="google-ads-invalid-state",
        email="google-ads-invalid@alpmark.local",
    )
    _set_auth_header(
        client,
        {
            "sub": "google-ads-invalid",
            "email": "google-ads-invalid@alpmark.local",
        },
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/google_ads/oauth/start"
    )
    assert start_response.status_code == 200

    response = client.post(
        f"/tenants/{tenant_id}/connectors/google_ads/oauth/callback",
        json={
            "state": "wrong-google-state",
            "code": "google-ads-auth-code-9999",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "OAuth state is invalid."}


def test_api_key_connect_stores_encrypted_secret_in_vault(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="VaultApiKey",
        tenant_slug="vaultapikey",
        email="vault-apikey@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "vault-apikey", "email": "vault-apikey@alpmark.local"},
    )

    api_key = "klv_vault_storage_check_123456"
    response = client.post(
        f"/tenants/{tenant_id}/connectors/klaviyo/api-key",
        json={"api_key": api_key},
    )
    assert response.status_code == 200

    entries = _get_connector_vault_entries(tenant_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.secret_type == "api_key"
    assert entry.secret_ciphertext != api_key


def test_connector_api_key_connect_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ApiKeyCo",
        tenant_slug="apikeyco",
        email="apikey-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "apikey-admin", "email": "apikey-admin@alpmark.local"},
    )

    response = client.post(
        f"/tenants/{tenant_id}/connectors/klaviyo/api-key",
        json={"api_key": "klv_test_key_123456789"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["source"] == "klaviyo"
    assert payload["auth_mode"] == "api_key"
    assert payload["status"] == "connected"
    assert payload["connected_at"] is not None
    assert payload["last_sync_requested_at"] is not None

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.api_key_connected" in actions


def test_connector_api_key_rejects_invalid_key(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ApiKeyInvalid",
        tenant_slug="apikeyinvalid",
        email="apikey-invalid@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "apikey-invalid", "email": "apikey-invalid@alpmark.local"},
    )

    response = client.post(
        f"/tenants/{tenant_id}/connectors/klaviyo/api-key",
        json={"api_key": "bad key 1"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "API key is invalid."}


def test_connector_api_key_rejects_oauth_preferred_source(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ApiKeySourceRule",
        tenant_slug="apikeysourcerule",
        email="apikey-source@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "apikey-source", "email": "apikey-source@alpmark.local"},
    )

    response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/api-key",
        json={"api_key": "shopify_key_123456"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "This source must use OAuth."}


def test_connector_oauth_reauthorize_success_rotates_credential(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ReauthCo",
        tenant_slug="reauthco",
        email="reauth-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "reauth-admin", "email": "reauth-admin@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "reauth-store.myshopify.com"},
    )
    assert start_response.status_code == 200

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_response.json()["state"],
            "code": "initial-oauth-code-1234",
            "shop_domain": "reauth-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200

    entries_before = _get_connector_vault_entries(tenant_id)
    assert len(entries_before) == 1
    fingerprint_before = entries_before[0].fingerprint

    reauth_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/reauthorize",
        json={
            "authorization_code": "rotated-oauth-code-9999",
            "shop_domain": "reauth-store.myshopify.com",
        },
    )

    assert reauth_response.status_code == 200
    payload = reauth_response.json()
    assert payload["status"] == "connected"
    assert payload["last_sync_requested_at"] is not None

    entries_after = _get_connector_vault_entries(tenant_id)
    assert len(entries_after) == 1
    assert entries_after[0].fingerprint != fingerprint_before

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.oauth_reauthorized" in actions


def test_connector_oauth_reauthorize_rejects_unsupported_source(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ReauthUnsupported",
        tenant_slug="reauthunsupported",
        email="reauth-unsupported@alpmark.local",
    )
    _set_auth_header(
        client,
        {
            "sub": "reauth-unsupported",
            "email": "reauth-unsupported@alpmark.local",
        },
    )

    response = client.post(
        f"/tenants/{tenant_id}/connectors/klaviyo/reauthorize",
        json={"authorization_code": "not-applicable-1234"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "This source does not support OAuth reauthorization."
    }


def test_connector_oauth_reauthorize_connector_not_found(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ReauthMissing",
        tenant_slug="reauthmissing",
        email="reauth-missing@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "reauth-missing", "email": "reauth-missing@alpmark.local"},
    )

    response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/reauthorize",
        json={"authorization_code": "missing-connector-code-1234"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Connector not found."}


def test_connector_manual_resync_trigger_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ResyncCo",
        tenant_slug="resyncco",
        email="resync-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "resync-admin", "email": "resync-admin@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "resync-store.myshopify.com"},
    )
    assert start_response.status_code == 200

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_response.json()["state"],
            "code": "resync-oauth-code-1234",
            "shop_domain": "resync-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        main_module,
        "_queue_manual_resync_tasks",
        lambda *, source: [
            "worker.app.tasks.run_shopify_order_sync_schedule",
            "worker.app.tasks.run_shopify_inventory_sync_schedule",
        ],
    )
    try:
        response = client.post(f"/tenants/{tenant_id}/connectors/shopify/resync")
    finally:
        monkeypatch.undo()

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["source"] == "shopify"
    assert payload["status"] == "connected"
    assert payload["last_sync_requested_at"] is not None
    assert payload["queued_tasks"] == [
        "worker.app.tasks.run_shopify_order_sync_schedule",
        "worker.app.tasks.run_shopify_inventory_sync_schedule",
    ]

    events = _get_audit_events(tenant_id)
    actions = [event.action for event in events]
    assert "connector.manual_resync_triggered" in actions


def test_connector_manual_resync_rejects_non_connected_connector(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ResyncPendingCo",
        tenant_slug="resyncpendingco",
        email="resync-pending@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "resync-pending", "email": "resync-pending@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "pending-store.myshopify.com"},
    )
    assert start_response.status_code == 200

    response = client.post(f"/tenants/{tenant_id}/connectors/shopify/resync")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Connector must be connected before resync."
    }


def test_connector_manual_resync_rejects_unsupported_source(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="ResyncUnsupportedCo",
        tenant_slug="resyncunsupportedco",
        email="resync-unsupported@alpmark.local",
    )
    _set_auth_header(
        client,
        {
            "sub": "resync-unsupported",
            "email": "resync-unsupported@alpmark.local",
        },
    )

    connect_response = client.post(
        f"/tenants/{tenant_id}/connectors/klaviyo/api-key",
        json={"api_key": "klv_resync_unsupported_123456"},
    )
    assert connect_response.status_code == 200

    response = client.post(f"/tenants/{tenant_id}/connectors/klaviyo/resync")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Manual resync is not supported for this source."
    }


def test_connector_integration_status_api_exposes_sync_progress(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="StatusCo",
        tenant_slug="statusco",
        email="status-admin@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "status-admin", "email": "status-admin@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "status-store.myshopify.com"},
    )
    assert start_response.status_code == 200

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_response.json()["state"],
            "code": "status-oauth-code-1234",
            "shop_domain": "status-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200

    queued_status_response = client.get(
        f"/tenants/{tenant_id}/connectors/shopify/status"
    )
    assert queued_status_response.status_code == 200
    queued_payload = queued_status_response.json()
    assert queued_payload["status"] == "connected"
    assert queued_payload["last_sync_requested_at"] is not None
    assert queued_payload["last_synced_at"] is None
    assert queued_payload["sync_progress"] == "sync_queued"
    assert queued_payload["freshness_label"] == "low"
    assert queued_payload["stale_data_gate"] == "hold"
    assert queued_payload["stale_data_reason"] == "No successful sync found yet."

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        connector = db.scalar(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == uuid.UUID(tenant_id),
                ConnectorIntegration.source == "shopify",
            )
        )
        assert connector is not None
        connector.last_synced_at = datetime.now(UTC) + timedelta(minutes=1)
        db.commit()
    finally:
        db_gen.close()

    healthy_status_response = client.get(
        f"/tenants/{tenant_id}/connectors/shopify/status"
    )
    assert healthy_status_response.status_code == 200
    healthy_payload = healthy_status_response.json()
    assert healthy_payload["last_synced_at"] is not None
    assert healthy_payload["sync_progress"] == "healthy"
    assert healthy_payload["freshness_label"] == "high"
    assert healthy_payload["stale_data_gate"] == "none"
    assert healthy_payload["stale_data_reason"] is None

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        connector = db.scalar(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == uuid.UUID(tenant_id),
                ConnectorIntegration.source == "shopify",
            )
        )
        assert connector is not None
        connector.last_synced_at = datetime.now(UTC) - timedelta(hours=3)
        db.commit()
    finally:
        db_gen.close()

    medium_status_response = client.get(
        f"/tenants/{tenant_id}/connectors/shopify/status"
    )
    assert medium_status_response.status_code == 200
    medium_payload = medium_status_response.json()
    assert medium_payload["freshness_label"] == "medium"
    assert medium_payload["stale_data_gate"] == "none"

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        connector = db.scalar(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == uuid.UUID(tenant_id),
                ConnectorIntegration.source == "shopify",
            )
        )
        assert connector is not None
        connector.last_synced_at = datetime.now(UTC) - timedelta(hours=10)
        db.commit()
    finally:
        db_gen.close()

    stale_warning_response = client.get(
        f"/tenants/{tenant_id}/connectors/shopify/status"
    )
    assert stale_warning_response.status_code == 200
    stale_warning_payload = stale_warning_response.json()
    assert stale_warning_payload["freshness_label"] == "low"
    assert stale_warning_payload["stale_data_gate"] == "warning"

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        connector = db.scalar(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == uuid.UUID(tenant_id),
                ConnectorIntegration.source == "shopify",
            )
        )
        assert connector is not None
        connector.error_message = "Provider error"
        db.commit()
    finally:
        db_gen.close()

    error_hold_response = client.get(
        f"/tenants/{tenant_id}/connectors/shopify/status"
    )
    assert error_hold_response.status_code == 200
    error_hold_payload = error_hold_response.json()
    assert error_hold_payload["stale_data_gate"] == "hold"
    assert (
        error_hold_payload["stale_data_reason"]
        == "Connector has an active sync error."
    )


def test_connector_integration_status_api_not_found(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="StatusMissingCo",
        tenant_slug="statusmissingco",
        email="status-missing@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "status-missing", "email": "status-missing@alpmark.local"},
    )

    response = client.get(f"/tenants/{tenant_id}/connectors/shopify/status")

    assert response.status_code == 404
    assert response.json() == {"detail": "Connector not found."}


def test_connector_integration_status_api_exposes_sync_uptime_metrics(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="StatusMetricsCo",
        tenant_slug="statusmetricsco",
        email="status-metrics@alpmark.local",
    )
    _set_auth_header(
        client,
        {"sub": "status-metrics", "email": "status-metrics@alpmark.local"},
    )

    start_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/start",
        json={"shop_domain": "status-metrics-store.myshopify.com"},
    )
    assert start_response.status_code == 200

    callback_response = client.post(
        f"/tenants/{tenant_id}/connectors/shopify/oauth/callback",
        json={
            "state": start_response.json()["state"],
            "code": "status-metrics-oauth-code-1234",
            "shop_domain": "status-metrics-store.myshopify.com",
        },
    )
    assert callback_response.status_code == 200

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        connector = db.scalar(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == uuid.UUID(tenant_id),
                ConnectorIntegration.source == "shopify",
            )
        )
        assert connector is not None

        now = datetime.now(UTC)
        db.add_all(
            [
                AuditEvent(
                    tenant_id=connector.tenant_id,
                    actor_user_id=None,
                    action="connector.shopify_orders_synced",
                    entity_type="connector",
                    entity_id=str(connector.id),
                    details={"source": "shopify"},
                    created_at=now - timedelta(hours=2),
                ),
                AuditEvent(
                    tenant_id=connector.tenant_id,
                    actor_user_id=None,
                    action="connector.shopify_inventory_synced",
                    entity_type="connector",
                    entity_id=str(connector.id),
                    details={"source": "shopify"},
                    created_at=now - timedelta(hours=1),
                ),
                AuditEvent(
                    tenant_id=connector.tenant_id,
                    actor_user_id=None,
                    action="connector.shopify_orders_synced",
                    entity_type="connector",
                    entity_id=str(connector.id),
                    details={"source": "shopify"},
                    created_at=now - timedelta(minutes=30),
                ),
                AuditEvent(
                    tenant_id=connector.tenant_id,
                    actor_user_id=None,
                    action="alert.connector_sync_failure_created",
                    entity_type="connector",
                    entity_id=str(connector.id),
                    details={"source": "shopify", "reason": "timeout"},
                    created_at=now - timedelta(minutes=10),
                ),
                AuditEvent(
                    tenant_id=connector.tenant_id,
                    actor_user_id=None,
                    action="alert.connector_sync_failure_created",
                    entity_type="connector",
                    entity_id=str(connector.id),
                    details={"source": "shopify", "reason": "old failure"},
                    created_at=now - timedelta(days=10),
                ),
            ]
        )
        db.commit()
    finally:
        db_gen.close()

    response = client.get(f"/tenants/{tenant_id}/connectors/shopify/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_jobs_total_7d"] == 4
    assert payload["sync_jobs_success_7d"] == 3
    assert payload["sync_jobs_failed_7d"] == 1
    assert payload["sync_uptime_percentage_7d"] == 75.0
    assert payload["sync_failure_rate_percentage_7d"] == 25.0


@pytest.mark.parametrize(
    ("age", "expected_label"),
    [
        (timedelta(0), "high"),
        (timedelta(hours=1), "high"),
        (timedelta(hours=1, seconds=1), "medium"),
        (timedelta(hours=6), "medium"),
        (timedelta(hours=6, seconds=1), "low"),
    ],
)
def test_freshness_label_computation_is_deterministic_at_thresholds(
    age: timedelta,
    expected_label: str,
) -> None:
    fixed_now = datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC)
    connector = ConnectorIntegration(
        tenant_id=uuid.uuid4(),
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=fixed_now - age,
    )

    first = main_module._derive_freshness_label(connector, now=fixed_now)
    second = main_module._derive_freshness_label(connector, now=fixed_now)

    assert first == expected_label
    assert second == expected_label


def test_freshness_label_computation_is_consistent_for_future_synced_at() -> None:
    fixed_now = datetime(2026, 5, 23, 12, 0, 0, tzinfo=UTC)
    connector = ConnectorIntegration(
        tenant_id=uuid.uuid4(),
        source="shopify",
        auth_mode="oauth",
        status="connected",
        last_synced_at=fixed_now + timedelta(minutes=5),
    )

    labels = [
        main_module._derive_freshness_label(connector, now=fixed_now)
        for _ in range(3)
    ]

    assert labels == ["high", "high", "high"]


# ---------------------------------------------------------------------------
# T-047: Finance cost drivers and margin drift API
# ---------------------------------------------------------------------------


def test_get_cost_drivers_returns_404_when_no_snapshots(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Finance Co",
        tenant_slug="finance-co",
        email="admin@finance-co.local",
    )
    _set_auth_header(
        client,
        {"sub": "admin-finance", "email": "admin@finance-co.local"},
    )
    response = client.get(f"/tenants/{tenant_id}/finance/cost-drivers")
    assert response.status_code == 404


def test_get_cost_drivers_returns_latest_snapshots(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Cost Driver Co",
        tenant_slug="cost-driver-co",
        email="admin@cost-driver-co.local",
    )

    # Seed two CostDriverSnapshots for today
    snapshot_date = date(2026, 5, 25)
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        tid = uuid.UUID(tenant_id)
        db.add(
            CostDriverSnapshot(
                tenant_id=tid,
                driver_type="shipping",
                snapshot_date=snapshot_date,
                period_start_date=date(2026, 4, 25),
                period_end_date=snapshot_date,
                absolute_amount=50.0,
                revenue=1000.0,
                pct_of_revenue=5.0,
                margin_impact_amount=-50.0,
                source="synced",
                source_platform="shopify",
                last_updated_at=datetime(2026, 5, 25, 9, 0, tzinfo=UTC),
                confidence_score=0.96,
                confidence_label="high",
            )
        )
        db.add(
            CostDriverSnapshot(
                tenant_id=tid,
                driver_type="ad_spend",
                snapshot_date=snapshot_date,
                period_start_date=date(2026, 4, 25),
                period_end_date=snapshot_date,
                absolute_amount=120.0,
                revenue=1000.0,
                pct_of_revenue=12.0,
                margin_impact_amount=-120.0,
                source="synced",
                source_platform="meta_google",
                last_updated_at=datetime(2026, 5, 25, 8, 0, tzinfo=UTC),
                confidence_score=0.923,
                confidence_label="high",
            )
        )
        db.commit()
    finally:
        db_gen.close()

    _set_auth_header(
        client,
        {"sub": "admin-cdc", "email": "admin@cost-driver-co.local"},
    )
    response = client.get(f"/tenants/{tenant_id}/finance/cost-drivers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_date"] == "2026-05-25"
    assert len(payload["drivers"]) == 2
    types = {d["driver_type"] for d in payload["drivers"]}
    assert types == {"shipping", "ad_spend"}


def test_create_and_list_margin_drift_threshold(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Drift Threshold Co",
        tenant_slug="drift-threshold-co",
        email="admin@drift-threshold-co.local",
    )
    _set_auth_header(
        client,
        {"sub": "admin-dtc", "email": "admin@drift-threshold-co.local"},
    )

    create_response = client.post(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds",
        json={
            "channel": "blended",
            "category": "all",
            "threshold_pct": 10.0,
            "effective_date": "2026-01-01",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["channel"] == "blended"
    assert created["category"] == "all"
    assert created["threshold_pct"] == 10.0
    assert created["is_active"] is True

    list_response = client.get(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds"
    )
    assert list_response.status_code == 200
    thresholds = list_response.json()["thresholds"]
    assert len(thresholds) == 1
    assert thresholds[0]["id"] == created["id"]


def test_create_margin_drift_threshold_duplicate_returns_409(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Dup Threshold Co",
        tenant_slug="dup-threshold-co",
        email="admin@dup-threshold-co.local",
    )
    _set_auth_header(
        client,
        {"sub": "admin-dtco", "email": "admin@dup-threshold-co.local"},
    )

    body = {
        "channel": "blended",
        "category": "all",
        "threshold_pct": 5.0,
        "effective_date": "2026-01-01",
    }
    first = client.post(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds", json=body
    )
    assert first.status_code == 201

    second = client.post(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds", json=body
    )
    assert second.status_code == 409


def test_update_margin_drift_threshold(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Update Threshold Co",
        tenant_slug="update-threshold-co",
        email="admin@update-threshold-co.local",
    )
    _set_auth_header(
        client,
        {"sub": "admin-utc", "email": "admin@update-threshold-co.local"},
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds",
        json={
            "channel": "blended",
            "category": "all",
            "threshold_pct": 5.0,
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    threshold_id = created.json()["id"]

    updated = client.put(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}",
        json={"threshold_pct": 15.0},
    )
    assert updated.status_code == 200
    assert updated.json()["threshold_pct"] == 15.0
    assert updated.json()["is_active"] is True


def test_delete_margin_drift_threshold_soft_deletes(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Delete Threshold Co",
        tenant_slug="delete-threshold-co",
        email="admin@delete-threshold-co.local",
    )
    _set_auth_header(
        client,
        {"sub": "admin-del-tc", "email": "admin@delete-threshold-co.local"},
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds",
        json={
            "channel": "blended",
            "category": "all",
            "threshold_pct": 8.0,
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    threshold_id = created.json()["id"]

    delete_response = client.delete(
        f"/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}"
    )
    assert delete_response.status_code == 204

    # Verify soft-delete: record still exists but is_active=False
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        from sqlalchemy import select as sa_select
        threshold = db.scalar(
            sa_select(MarginDriftThreshold).where(
                MarginDriftThreshold.id == uuid.UUID(threshold_id)
            )
        )
        assert threshold is not None
        assert threshold.is_active is False
    finally:
        db_gen.close()


# ---------------------------------------------------------------------------
# T-048: Tiered cost inputs (FR-050 / FR-051)
# ---------------------------------------------------------------------------


def test_list_cost_inputs_empty(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Empty Co",
        tenant_slug="ci-empty-co",
        email="admin@ci-empty-co.local",
    )
    _set_auth_header(client, {"sub": "admin-cie", "email": "admin@ci-empty-co.local"})

    response = client.get(f"/tenants/{tenant_id}/finance/cost-inputs")
    assert response.status_code == 200
    assert response.json()["cost_inputs"] == []


def test_create_cost_input_shipping_success(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Shipping Co",
        tenant_slug="ci-shipping-co",
        email="admin@ci-shipping-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-cis", "email": "admin@ci-shipping-co.local"}
    )

    response = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "shipping",
            "tier_label": "0–0.5 kg domestic",
            "weight_min_kg": 0.0,
            "weight_max_kg": 0.5,
            "destination_zone": "domestic",
            "amount": 3.50,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["input_type"] == "shipping"
    assert data["tier_label"] == "0–0.5 kg domestic"
    assert data["destination_zone"] == "domestic"
    assert data["amount"] == 3.50
    assert data["confirmation_required"] is False
    assert data["confirmed_at"] is None

    # Appears in list
    list_resp = client.get(f"/tenants/{tenant_id}/finance/cost-inputs")
    assert len(list_resp.json()["cost_inputs"]) == 1


def test_create_cost_input_cogs_requires_confirmation(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI COGS Co",
        tenant_slug="ci-cogs-co",
        email="admin@ci-cogs-co.local",
    )
    _set_auth_header(client, {"sub": "admin-cic", "email": "admin@ci-cogs-co.local"})

    create_resp = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "cogs",
            "tier_label": "Standard COGS",
            "amount": 12.00,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["confirmation_required"] is True
    assert data["confirmed_at"] is None

    input_id = data["id"]

    # Confirm the high-impact change
    confirm_resp = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm"
    )
    assert confirm_resp.status_code == 204

    # Verify confirmed_at is now set via DB
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        row = db.scalar(select(CostInput).where(CostInput.id == uuid.UUID(input_id)))
        assert row is not None
        assert row.confirmation_required is False
        assert row.confirmed_at is not None
    finally:
        db_gen.close()


def test_confirm_already_confirmed_returns_409(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Confirm409 Co",
        tenant_slug="ci-confirm409-co",
        email="admin@ci-confirm409-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-cc409", "email": "admin@ci-confirm409-co.local"}
    )

    create_resp = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "shipping",
            "tier_label": "0.5–1 kg EU",
            "weight_min_kg": 0.5,
            "weight_max_kg": 1.0,
            "destination_zone": "eu",
            "amount": 6.00,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    assert create_resp.status_code == 201
    input_id = create_resp.json()["id"]

    # shipping is not high-impact → confirmation_required=False → 409 on confirm
    confirm_resp = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm"
    )
    assert confirm_resp.status_code == 409


def test_update_cost_input(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Update Co",
        tenant_slug="ci-update-co",
        email="admin@ci-update-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-ciu", "email": "admin@ci-update-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "return_processing",
            "tier_label": "Standard Return",
            "amount": 2.50,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    input_id = created.json()["id"]

    updated = client.put(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
        json={"amount": 3.75, "tier_label": "Updated Return Cost"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 3.75
    assert updated.json()["tier_label"] == "Updated Return Cost"


def test_delete_cost_input_soft_deletes(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Delete Co",
        tenant_slug="ci-delete-co",
        email="admin@ci-delete-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-cid", "email": "admin@ci-delete-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "ad_spend_vat",
            "tier_label": "Meta VAT 20%",
            "amount": 20.0,
            "unit": "pct",
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    input_id = created.json()["id"]

    delete_resp = client.delete(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}"
    )
    assert delete_resp.status_code == 204

    # Deleted entry is excluded from the active list
    list_resp = client.get(f"/tenants/{tenant_id}/finance/cost-inputs")
    assert all(ci["id"] != input_id for ci in list_resp.json()["cost_inputs"])

    # Record still exists in DB with is_active=False
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        row = db.scalar(
            select(CostInput).where(CostInput.id == uuid.UUID(input_id))
        )
        assert row is not None
        assert row.is_active is False
    finally:
        db_gen.close()


def test_list_cost_inputs_filtered_by_type(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Filter Co",
        tenant_slug="ci-filter-co",
        email="admin@ci-filter-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-cif", "email": "admin@ci-filter-co.local"}
    )

    for i in range(2):
        client.post(
            f"/tenants/{tenant_id}/finance/cost-inputs",
            json={
                "input_type": "shipping",
                "tier_label": f"Shipping Tier {i}",
                "amount": float(3 + i),
                "unit": "per_order",
                "effective_date": "2026-01-01",
            },
        )
    client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "return_processing",
            "tier_label": "Return Cost",
            "amount": 2.0,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )

    resp = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        params={"input_type": "shipping"},
    )
    assert resp.status_code == 200
    rows = resp.json()["cost_inputs"]
    assert len(rows) == 2
    assert all(r["input_type"] == "shipping" for r in rows)


def test_cost_input_role_enforcement(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="CI Role Co",
        tenant_slug="ci-role-co",
        email="admin@ci-role-co.local",
    )
    _set_auth_header(
        client, {"sub": "nobody", "email": "nobody@example.com"}
    )
    resp = client.get(f"/tenants/{tenant_id}/finance/cost-inputs")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# T-049: Cost input version history (FR-052 / NFR-013)
# ---------------------------------------------------------------------------


def test_create_cost_input_writes_version_1(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver Create Co",
        tenant_slug="ver-create-co",
        email="admin@ver-create-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-vcc", "email": "admin@ver-create-co.local"}
    )

    resp = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "shipping",
            "tier_label": "0–0.5 kg domestic",
            "amount": 3.50,
            "unit": "per_order",
            "effective_date": "2026-01-01",
            "variance_reason": "initial onboarding baseline",
        },
    )
    assert resp.status_code == 201
    input_id = resp.json()["id"]

    history = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history"
    )
    assert history.status_code == 200
    versions = history.json()["versions"]
    assert len(versions) == 1
    v = versions[0]
    assert v["version_number"] == 1
    assert v["action"] == "created"
    assert v["prior_amount"] is None
    assert v["prior_unit"] is None
    assert v["new_amount"] == 3.50
    assert v["new_unit"] == "per_order"
    assert v["variance_reason"] == "initial onboarding baseline"


def test_update_cost_input_appends_version(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver Update Co",
        tenant_slug="ver-update-co",
        email="admin@ver-update-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-vuc", "email": "admin@ver-update-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "return_processing",
            "tier_label": "Standard Return",
            "amount": 2.50,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    input_id = created.json()["id"]

    client.put(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
        json={
            "amount": 3.00,
            "variance_reason": "3PL rate increase Q2 2026",
        },
    )

    history = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history"
    )
    versions = history.json()["versions"]
    assert len(versions) == 2

    v2 = versions[1]
    assert v2["version_number"] == 2
    assert v2["action"] == "updated"
    assert v2["prior_amount"] == 2.50
    assert v2["new_amount"] == 3.00
    assert v2["variance_reason"] == "3PL rate increase Q2 2026"


def test_delete_cost_input_appends_deactivated_version(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver Delete Co",
        tenant_slug="ver-delete-co",
        email="admin@ver-delete-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-vdc", "email": "admin@ver-delete-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "ad_spend_vat",
            "tier_label": "Meta VAT 20%",
            "amount": 20.0,
            "unit": "pct",
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    input_id = created.json()["id"]

    client.delete(f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}")

    history = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history"
    )
    versions = history.json()["versions"]
    assert len(versions) == 2
    assert versions[-1]["action"] == "deactivated"


def test_history_ordering_is_version_number(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver Order Co",
        tenant_slug="ver-order-co",
        email="admin@ver-order-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-voc", "email": "admin@ver-order-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "shipping",
            "tier_label": "Domestic",
            "amount": 1.0,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    input_id = created.json()["id"]
    for i in range(3):
        client.put(
            f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
            json={"amount": float(2 + i)},
        )

    history = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history"
    )
    versions = history.json()["versions"]
    assert len(versions) == 4
    assert [v["version_number"] for v in versions] == [1, 2, 3, 4]


def test_history_returns_404_for_unknown_input(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver 404 Co",
        tenant_slug="ver-404-co",
        email="admin@ver-404-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-v404", "email": "admin@ver-404-co.local"}
    )
    resp = client.get(
        f"/tenants/{tenant_id}/finance/cost-inputs/{uuid.uuid4()}/history"
    )
    assert resp.status_code == 404


def test_version_history_in_db_matches_api(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Ver DB Co",
        tenant_slug="ver-db-co",
        email="admin@ver-db-co.local",
    )
    _set_auth_header(
        client, {"sub": "admin-vdb", "email": "admin@ver-db-co.local"}
    )

    created = client.post(
        f"/tenants/{tenant_id}/finance/cost-inputs",
        json={
            "input_type": "cogs",
            "tier_label": "Standard COGS",
            "amount": 10.0,
            "unit": "per_order",
            "effective_date": "2026-01-01",
        },
    )
    input_id = created.json()["id"]

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        versions = list(
            db.scalars(
                select(CostInputVersion).where(
                    CostInputVersion.cost_input_id == uuid.UUID(input_id)
                )
            )
        )
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].action == "created"
        assert versions[0].new_amount == 10.0
    finally:
        db_gen.close()


# ---------------------------------------------------------------------------
# T-050: Inventory risk endpoints (FR-058 to FR-062)
# ---------------------------------------------------------------------------


def test_get_inventory_risk_returns_404_when_no_snapshots(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvTest404Co",
        tenant_slug="invtest404co",
        email="admin@invtest404.local",
    )
    _set_auth_header(client, {"sub": "admin-inv404", "email": "admin@invtest404.local"})
    resp = client.get(f"/tenants/{tenant_id}/inventory/risk")
    assert resp.status_code == 404


def test_create_and_list_inventory_risk_threshold(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvThreshListCo",
        tenant_slug="invthreshlistco",
        email="admin@invthreshlist.local",
    )
    _set_auth_header(
        client, {"sub": "admin-invlist", "email": "admin@invthreshlist.local"}
    )
    created = client.post(
        f"/tenants/{tenant_id}/inventory/risk-thresholds",
        json={
            "category": "all",
            "stockout_alert_days": 5.0,
            "effective_date": "2026-01-01",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["category"] == "all"
    assert body["stockout_alert_days"] == 5.0

    listed = client.get(f"/tenants/{tenant_id}/inventory/risk-thresholds")
    assert listed.status_code == 200
    assert len(listed.json()["thresholds"]) == 1


def test_create_inventory_risk_threshold_duplicate_returns_409(
    client: TestClient,
) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvThresh409Co",
        tenant_slug="invthresh409co",
        email="admin@invthresh409.local",
    )
    _set_auth_header(
        client, {"sub": "admin-inv409", "email": "admin@invthresh409.local"}
    )
    payload = {"category": "electronics", "effective_date": "2026-01-01"}
    first = client.post(f"/tenants/{tenant_id}/inventory/risk-thresholds", json=payload)
    assert first.status_code == 201
    second = client.post(
        f"/tenants/{tenant_id}/inventory/risk-thresholds", json=payload
    )
    assert second.status_code == 409


def test_update_inventory_risk_threshold(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvThreshUpdCo",
        tenant_slug="invthreshupdco",
        email="admin@invthreshupd.local",
    )
    _set_auth_header(
        client, {"sub": "admin-invupd", "email": "admin@invthreshupd.local"}
    )
    created = client.post(
        f"/tenants/{tenant_id}/inventory/risk-thresholds",
        json={"category": "apparel", "effective_date": "2026-01-01"},
    )
    threshold_id = created.json()["id"]

    updated = client.put(
        f"/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}",
        json={"stockout_alert_days": 3.0},
    )
    assert updated.status_code == 200
    assert updated.json()["stockout_alert_days"] == 3.0


def test_delete_inventory_risk_threshold_soft_deletes(client: TestClient) -> None:
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvThreshDelCo",
        tenant_slug="invthreshdelco",
        email="admin@invthreshdel.local",
    )
    _set_auth_header(
        client, {"sub": "admin-invdel", "email": "admin@invthreshdel.local"}
    )
    created = client.post(
        f"/tenants/{tenant_id}/inventory/risk-thresholds",
        json={"category": "footwear", "effective_date": "2026-01-01"},
    )
    threshold_id = created.json()["id"]

    deleted = client.delete(
        f"/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}"
    )
    assert deleted.status_code == 204

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        row = db.scalar(
            select(InventoryRiskThreshold).where(
                InventoryRiskThreshold.id == uuid.UUID(threshold_id)
            )
        )
        assert row is not None
        assert row.is_active is False
    finally:
        db_gen.close()


def test_inventory_risk_role_enforcement(client: TestClient) -> None:
    """User with no tenant membership must receive 403."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="InvRoleEnfCo",
        tenant_slug="invroleenfco",
        email="admin@invroleenf.local",
    )
    _set_auth_header(client, {"sub": "nobody", "email": "nobody@invroleenf.local"})
    resp = client.get(f"/tenants/{tenant_id}/inventory/risk")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# T-051 Operational Impact API Tests
# ---------------------------------------------------------------------------


def test_get_operational_impact_empty_returns_200(client: TestClient) -> None:
    """GET /tenants/{id}/operational/impact returns 200 with empty snapshots."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="OpImpactEmpty Co",
        tenant_slug="opimpactempty",
        email="admin@opimpactempty.local",
    )
    _set_auth_header(
        client, {"sub": "admin-oi-empty", "email": "admin@opimpactempty.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/operational/impact")
    assert resp.status_code == 200
    body = resp.json()
    assert body["snapshots"] == []


def test_get_operational_impact_sku_filter_empty(client: TestClient) -> None:
    """GET /tenants/{id}/operational/impact?sku=X returns 200 with empty snapshots."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="OpImpactSku Co",
        tenant_slug="opimpactsku",
        email="admin@opimpactsku.local",
    )
    _set_auth_header(
        client, {"sub": "admin-oi-sku", "email": "admin@opimpactsku.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/operational/impact?sku=MISSING-SKU")
    assert resp.status_code == 200
    assert resp.json()["snapshots"] == []


def test_get_operational_impact_requires_auth(client: TestClient) -> None:
    """Non-member user must receive 403."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="OpImpact403 Co",
        tenant_slug="opimpact403",
        email="admin@opimpact403.local",
    )
    _set_auth_header(client, {"sub": "nobody", "email": "nobody@opimpact403.local"})
    resp = client.get(f"/tenants/{tenant_id}/operational/impact")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# T-052 Tenant Locale / Currency API Tests
# ---------------------------------------------------------------------------


def test_get_tenant_locale_defaults(client: TestClient) -> None:
    """Freshly provisioned tenant returns default USD / en-US locale."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale Default Co",
        tenant_slug="localedefaultco",
        email="admin@localedefault.local",
    )
    _set_auth_header(
        client, {"sub": "admin-loc-def", "email": "admin@localedefault.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/locale")
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_currency"] == "USD"
    assert body["locale"] == "en-US"


def test_patch_tenant_locale_currency(client: TestClient) -> None:
    """PATCH updates base_currency and locale; GET reflects the change."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale GBP Co",
        tenant_slug="localegbpco",
        email="admin@localegbp.local",
    )
    _set_auth_header(
        client, {"sub": "admin-loc-gbp", "email": "admin@localegbp.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/locale",
        json={"base_currency": "GBP", "locale": "en-GB"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_currency"] == "GBP"
    assert body["locale"] == "en-GB"

    # Confirm persistence via GET
    get_resp = client.get(f"/tenants/{tenant_id}/locale")
    assert get_resp.status_code == 200
    assert get_resp.json()["base_currency"] == "GBP"
    assert get_resp.json()["locale"] == "en-GB"


def test_patch_tenant_locale_invalid_currency(client: TestClient) -> None:
    """PATCH with unsupported currency code returns 422."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale BadCur Co",
        tenant_slug="localebadcurco",
        email="admin@localebadcur.local",
    )
    _set_auth_header(
        client, {"sub": "admin-loc-bad", "email": "admin@localebadcur.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/locale",
        json={"base_currency": "XYZ"},
    )
    assert resp.status_code == 422


def test_patch_tenant_locale_invalid_locale(client: TestClient) -> None:
    """PATCH with malformed locale tag returns 422."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale BadLoc Co",
        tenant_slug="localebadlocco",
        email="admin@localebadloc.local",
    )
    _set_auth_header(
        client, {"sub": "admin-loc-badloc", "email": "admin@localebadloc.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/locale",
        json={"locale": "INVALID_TAG!!!"},
    )
    assert resp.status_code == 422


def test_patch_tenant_locale_partial_update(client: TestClient) -> None:
    """PATCH with only base_currency leaves locale unchanged."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale INR Co",
        tenant_slug="localeinrco",
        email="admin@localeinr.local",
    )
    _set_auth_header(
        client, {"sub": "admin-loc-inr", "email": "admin@localeinr.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/locale",
        json={"base_currency": "INR"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_currency"] == "INR"
    assert body["locale"] == "en-US"  # unchanged default


def test_get_tenant_locale_requires_auth(client: TestClient) -> None:
    """Non-member must receive 403."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Locale Auth Co",
        tenant_slug="localeauthco",
        email="admin@localeauth.local",
    )
    _set_auth_header(
        client, {"sub": "nobody", "email": "nobody@localeauth.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/locale")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# T-053 Recommendations API tests
# ---------------------------------------------------------------------------


def test_get_recommendations_returns_empty_list(client: TestClient) -> None:
    """Fresh tenant has no recommendations."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Rec Empty Co",
        tenant_slug="recemptyco",
        email="admin@recempty.local",
    )
    _set_auth_header(
        client, {"sub": "admin-rec-empty", "email": "admin@recempty.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_recommendations_returns_seeded_data(client: TestClient) -> None:
    """Seeded recommendation is returned by the endpoint."""
    from datetime import date

    from backend.app.db.models import Recommendation

    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Rec Seeded Co",
        tenant_slug="recseededco",
        email="admin@recseeded.local",
    )
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        rec = Recommendation(
            tenant_id=uuid.UUID(tenant_id),
            rule_id="TEST-001",
            domain="inventory",
            snapshot_date=date.today(),
            affected_area="SKU: BOOT-001",
            signal_summary="3 days to stockout",
            suggested_action="Replenish stock",
            estimated_impact=500.0,
            confidence_level="high",
            data_freshness_context="1 day old",
            priority=10,
            status="new",
            source="optimization",
        )
        db.add(rec)
        db.commit()
    finally:
        db_gen.close()

    _set_auth_header(
        client, {"sub": "admin-rec-seed", "email": "admin@recseeded.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["rule_id"] == "TEST-001"
    assert body["items"][0]["domain"] == "inventory"
    assert body["items"][0]["status"] == "new"


def test_get_recommendations_domain_filter(client: TestClient) -> None:
    """domain= query param returns only matching recommendations."""
    from datetime import date

    from backend.app.db.models import Recommendation

    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Rec Filter Co",
        tenant_slug="recfilterco",
        email="admin@recfilter.local",
    )
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        for domain, rule_id in [
            ("inventory", "INV-001"),
            ("acquisition", "ACQ-001"),
        ]:
            db.add(
                Recommendation(
                    tenant_id=uuid.UUID(tenant_id),
                    rule_id=rule_id,
                    domain=domain,
                    snapshot_date=date.today(),
                    affected_area="area",
                    signal_summary="signal",
                    suggested_action="action",
                    estimated_impact=None,
                    confidence_level="low",
                    data_freshness_context="fresh",
                    priority=50,
                    status="new",
                    source="optimization",
                )
            )
        db.commit()
    finally:
        db_gen.close()

    _set_auth_header(
        client, {"sub": "admin-rec-filter", "email": "admin@recfilter.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/recommendations?domain=inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["rule_id"] == "INV-001"


def test_get_recommendations_requires_auth(client: TestClient) -> None:
    """Non-member receives 403."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Rec Auth Co",
        tenant_slug="recauthco",
        email="admin@recauth.local",
    )
    _set_auth_header(
        client, {"sub": "nobody", "email": "nobody@recauth.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/recommendations")
    assert resp.status_code == 403


# ===========================================================================
# T-054: Rule threshold API tests
# ===========================================================================


def test_get_rule_thresholds_returns_seeded_defaults(client: TestClient) -> None:
    """Tenant creation seeds 6 default thresholds; GET returns all of them."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Threshold Co",
        tenant_slug="thresholdco",
        email="admin@threshold.local",
    )
    _set_auth_header(
        client, {"sub": "admin-threshold", "email": "admin@threshold.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/rule-thresholds")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    rule_ids = {item["rule_id"] for item in body["items"]}
    expected_ids = {"ACQ-001", "EXC-001", "INV-001", "MRG-001", "OPS-001", "RET-001"}
    assert rule_ids == expected_ids
    # Defaults must not be marked as customised
    assert all(not item["is_customised"] for item in body["items"])


def test_patch_rule_threshold_updates_value(client: TestClient) -> None:
    """PATCH updates threshold_value and sets is_customised=True."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Patch Threshold Co",
        tenant_slug="patchthresholdco",
        email="admin@patchthreshold.local",
    )
    _set_auth_header(
        client, {"sub": "admin-patch-threshold", "email": "admin@patchthreshold.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/rule-thresholds/ACQ-001",
        json={"threshold_value": 2.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["threshold_value"] == 2.0
    assert body["is_customised"] is True
    assert body["rule_id"] == "ACQ-001"


def test_patch_rule_threshold_404_for_unknown_rule(client: TestClient) -> None:
    """PATCH returns 404 for a rule_id that was never seeded."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Unknown Rule Co",
        tenant_slug="unknownruleco",
        email="admin@unknownrule.local",
    )
    _set_auth_header(
        client, {"sub": "admin-unknown-rule", "email": "admin@unknownrule.local"}
    )
    resp = client.patch(
        f"/tenants/{tenant_id}/rule-thresholds/NONEXISTENT-999",
        json={"threshold_value": 5.0},
    )
    assert resp.status_code == 404


def test_get_rule_thresholds_requires_auth(client: TestClient) -> None:
    """Non-member receives 403."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Threshold Auth Co",
        tenant_slug="thresholdauthco",
        email="admin@thresholdauth.local",
    )
    _set_auth_header(
        client, {"sub": "nobody", "email": "nobody@thresholdauth.local"}
    )
    resp = client.get(f"/tenants/{tenant_id}/rule-thresholds")
    assert resp.status_code == 403


def test_ops001_seed_scales_for_inr_currency(client: TestClient) -> None:
    """Tenant created with INR currency should get OPS-001 scaled to ~₹42,000."""
    _set_auth_header(
        client,
        {
            "sub": "inr-super-admin",
            "email": "super@inrco.local",
            "platform_role": "super_admin",
        },
    )
    resp = client.post(
        "/tenants",
        json={"name": "INR Co", "slug": "inrco", "base_currency": "INR"},
    )
    assert resp.status_code == 201
    tenant_id = resp.json()["id"]
    assert resp.json()["base_currency"] == "INR"

    _set_auth_header(
        client, {"sub": "admin-inrco", "email": "super@inrco.local"}
    )
    thresholds = client.get(f"/tenants/{tenant_id}/rule-thresholds")
    assert thresholds.status_code == 200
    ops = next(
        i for i in thresholds.json()["items"] if i["rule_id"] == "OPS-001"
    )
    # 500.0 USD × 84.0 (INR scale) = 42,000.0 INR
    assert ops["threshold_value"] == 42000.0
    assert ops["threshold_unit"] == "INR"


def test_ops001_recalibrates_on_locale_patch(client: TestClient) -> None:
    """PATCH /locale with a new currency recalibrates non-customised OPS-001."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Recal Co",
        tenant_slug="recalco",
        email="admin@recalco.local",
    )
    _set_auth_header(
        client, {"sub": "admin-recalco", "email": "admin@recalco.local"}
    )

    # Confirm OPS-001 starts at USD default (500.0 USD)
    before = client.get(f"/tenants/{tenant_id}/rule-thresholds").json()
    ops_before = next(i for i in before["items"] if i["rule_id"] == "OPS-001")
    assert ops_before["threshold_value"] == 500.0
    assert ops_before["threshold_unit"] == "USD"

    # Change currency to JPY
    patch_resp = client.patch(
        f"/tenants/{tenant_id}/locale",
        json={"base_currency": "JPY"},
    )
    assert patch_resp.status_code == 200

    # OPS-001 must recalibrate: 500.0 × 156.0 = 78,000.0 JPY
    after = client.get(f"/tenants/{tenant_id}/rule-thresholds").json()
    ops_after = next(i for i in after["items"] if i["rule_id"] == "OPS-001")
    assert ops_after["threshold_value"] == 78000.0
    assert ops_after["threshold_unit"] == "JPY"
    assert not ops_after["is_customised"]  # flag must stay False


def test_ops001_locale_patch_skips_customised_threshold(
    client: TestClient,
) -> None:
    """PATCH /locale must NOT recalibrate OPS-001 if it has been customised."""
    tenant_id = _create_tenant_as_super_admin(
        client,
        tenant_name="Custom Recal Co",
        tenant_slug="customrecalco",
        email="admin@customrecalco.local",
    )
    _set_auth_header(
        client, {"sub": "admin-customrecalco", "email": "admin@customrecalco.local"}
    )

    # Manually customise OPS-001
    patch_ops = client.patch(
        f"/tenants/{tenant_id}/rule-thresholds/OPS-001",
        json={"threshold_value": 999.0},
    )
    assert patch_ops.status_code == 200

    # Change currency to GBP
    client.patch(f"/tenants/{tenant_id}/locale", json={"base_currency": "GBP"})

    # OPS-001 must NOT change — is_customised=True protects the manual value
    after = client.get(f"/tenants/{tenant_id}/rule-thresholds").json()
    ops_after = next(i for i in after["items"] if i["rule_id"] == "OPS-001")
    assert ops_after["threshold_value"] == 999.0
    assert ops_after["is_customised"] is True
