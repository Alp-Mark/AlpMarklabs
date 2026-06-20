"""Tests for alert escalation and acknowledgement (T-078)."""

from __future__ import annotations

from uuid import UUID

from backend.app.db.models import (
    AlertAcknowledgement,
    AlertDismissal,
    EscalationRule,
    Tenant,
    User,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


class TestAlertAcknowledgement:
    """Test alert acknowledgement functionality."""

    def test_acknowledge_alert_success(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test successful alert acknowledgement."""
        response = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "alert-001"
        assert data["alert_type"] == "early_warning"
        assert data["user_id"] == str(user.id)
        assert data["tenant_id"] == str(tenant.id)

        # Verify in database
        ack = db_session.scalar(
            select(AlertAcknowledgement).where(
                AlertAcknowledgement.alert_id == "alert-001"
            )
        )
        assert ack is not None
        assert ack.user_id == user.id

    def test_acknowledge_alert_duplicate_forbidden(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that user cannot acknowledge same alert twice."""
        # First acknowledgement
        client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        # Second acknowledgement should fail
        response = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        assert response.status_code == 409
        assert "already acknowledged" in response.json()["detail"].lower()

    def test_acknowledge_alert_tenant_not_found(
        self,
        user: User,
        client: TestClient,
        nonexistent_uuid: UUID,
    ) -> None:
        """Test acknowledgement with invalid tenant."""
        response = client.post(
            f"/tenants/{nonexistent_uuid}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        assert response.status_code == 404
        assert "tenant" in response.json()["detail"].lower()

    def test_acknowledge_alert_different_users(
        self,
        tenant: Tenant,
        user: User,
        other_user: User,
        db_session: Session,
        client: TestClient,
        other_client: TestClient,
    ) -> None:
        """Test that different users can acknowledge same alert independently."""
        # User 1 acknowledges
        response1 = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response1.status_code == 200

        # User 2 acknowledges same alert
        response2 = other_client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response2.status_code == 200

        # Verify both are recorded
        acks = db_session.scalars(
            select(AlertAcknowledgement).where(
                AlertAcknowledgement.alert_id == "alert-001"
            )
        ).all()
        assert len(acks) == 2
        user_ids = {ack.user_id for ack in acks}
        assert user.id in user_ids
        assert other_user.id in user_ids


class TestAlertDismissal:
    """Test alert dismissal functionality."""

    def test_dismiss_alert_success(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test successful alert dismissal."""
        response = client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
                "dismiss_reason": "False positive, sales were seasonal.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_id"] == "alert-001"
        assert data["alert_type"] == "early_warning"
        assert data["dismiss_reason"] == "False positive, sales were seasonal."

    def test_dismiss_alert_without_reason(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test dismissal without optional reason."""
        response = client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert-001",
                "alert_type": "operational_anomaly",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dismiss_reason"] is None

    def test_dismiss_alert_duplicate_forbidden(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that user cannot dismiss same alert twice."""
        # First dismissal
        client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        # Second dismissal should fail
        response = client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )

        assert response.status_code == 409
        assert "already dismissed" in response.json()["detail"].lower()

    def test_ack_and_dismiss_same_alert(
        self,
        tenant: Tenant,
        user: User,
        other_user: User,
        db_session: Session,
        client: TestClient,
        other_client: TestClient,
    ) -> None:
        """Test that one user can acknowledge while another dismisses same alert."""
        # User 1 acknowledges
        response1 = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response1.status_code == 200

        # User 2 dismisses
        response2 = other_client.post(
            f"/tenants/{tenant.id}/alerts/dismiss",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response2.status_code == 200

        # Verify both actions recorded
        acks = db_session.scalars(
            select(AlertAcknowledgement).where(
                AlertAcknowledgement.alert_id == "alert-001"
            )
        ).all()
        dismissals = db_session.scalars(
            select(AlertDismissal).where(
                AlertDismissal.alert_id == "alert-001"
            )
        ).all()
        assert len(acks) == 1
        assert len(dismissals) == 1


class TestEscalationRuleCreation:
    """Test escalation rule creation."""

    def test_create_escalation_rule_success(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test successful escalation rule creation."""
        response = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner", "growth_manager"],
                "is_enabled": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alert_type"] == "early_warning"
        assert data["domain"] == "growth"
        assert data["unacknowledged_hours"] == 6.0
        assert data["escalation_to_roles"] == [
            "executive_owner",
            "growth_manager",
        ]
        assert data["is_enabled"] is True

        # Verify in database
        rule = db_session.scalar(
            select(EscalationRule).where(
                EscalationRule.alert_type == "early_warning",
                EscalationRule.domain == "growth",
            )
        )
        assert rule is not None

    def test_create_escalation_rule_duplicate_forbidden(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that duplicate escalation rule is not allowed."""
        # Create first rule
        client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )

        # Try to create duplicate
        response = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 12.0,
                "escalation_to_roles": ["growth_manager"],
                "is_enabled": True,
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_escalation_rule_different_domains(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test creating rules for same alert type but different domains."""
        domains = ["growth", "retention", "operations"]
        for domain in domains:
            response = client.post(
                f"/tenants/{tenant.id}/alerts/escalation-rules",
                json={
                    "alert_type": "early_warning",
                    "domain": domain,
                    "unacknowledged_hours": 6.0,
                    "escalation_to_roles": ["executive_owner"],
                    "is_enabled": True,
                },
            )
            assert response.status_code == 200

        # Verify all three created
        rules = db_session.scalars(
            select(EscalationRule).where(
                EscalationRule.alert_type == "early_warning",
                EscalationRule.tenant_id == tenant.id,
            )
        ).all()
        assert len(rules) == 3


class TestEscalationRuleRetrieval:
    """Test escalation rule retrieval."""

    def test_list_escalation_rules(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test listing all escalation rules."""
        # Create three rules
        for i in range(3):
            client.post(
                f"/tenants/{tenant.id}/alerts/escalation-rules",
                json={
                    "alert_type": f"alert_type_{i}",
                    "domain": "growth",
                    "unacknowledged_hours": 6.0 + i,
                    "escalation_to_roles": ["executive_owner"],
                    "is_enabled": True,
                },
            )

        response = client.get(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) == 3
        assert data["total_count"] == 3

    def test_list_escalation_rules_empty(
        self,
        tenant: Tenant,
        user: User,
        client: TestClient,
    ) -> None:
        """Test listing when no rules exist."""
        response = client.get(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) == 0
        assert data["total_count"] == 0

    def test_get_escalation_rule(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test getting a specific escalation rule."""
        # Create rule
        response_create = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )

        rule_id = UUID(response_create.json()["id"])

        # Get rule
        response = client.get(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{rule_id}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(rule_id)
        assert data["alert_type"] == "early_warning"

    def test_get_escalation_rule_not_found(
        self,
        tenant: Tenant,
        user: User,
        nonexistent_uuid: UUID,
        client: TestClient,
    ) -> None:
        """Test getting nonexistent rule."""
        response = client.get(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{nonexistent_uuid}",
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestEscalationRuleUpdate:
    """Test escalation rule updates."""

    def test_update_escalation_rule_success(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test successful rule update."""
        # Create rule
        response_create = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )

        rule_id = UUID(response_create.json()["id"])

        # Update rule
        response = client.put(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{rule_id}",
            json={
                "unacknowledged_hours": 12.0,
                "escalation_to_roles": ["executive_owner", "growth_manager"],
                "is_enabled": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unacknowledged_hours"] == 12.0
        assert data["escalation_to_roles"] == [
            "executive_owner",
            "growth_manager",
        ]
        assert data["is_enabled"] is False

    def test_update_escalation_rule_partial(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test partial rule update (only some fields)."""
        # Create rule
        response_create = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )

        rule_id = UUID(response_create.json()["id"])

        # Update only hours
        response = client.put(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{rule_id}",
            json={"unacknowledged_hours": 24.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["unacknowledged_hours"] == 24.0
        # Other fields should remain unchanged
        assert data["escalation_to_roles"] == ["executive_owner"]
        assert data["is_enabled"] is True

    def test_update_escalation_rule_not_found(
        self,
        tenant: Tenant,
        user: User,
        nonexistent_uuid: UUID,
        client: TestClient,
    ) -> None:
        """Test updating nonexistent rule."""
        response = client.put(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{nonexistent_uuid}",
            json={"unacknowledged_hours": 12.0},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestEscalationRuleDeletion:
    """Test escalation rule deletion."""

    def test_delete_escalation_rule_success(
        self,
        tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test successful rule deletion."""
        # Create rule
        response_create = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )

        rule_id = UUID(response_create.json()["id"])

        # Delete rule
        response = client.delete(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{rule_id}",
        )

        assert response.status_code == 200

        # Verify deleted
        rule = db_session.scalar(
            select(EscalationRule).where(EscalationRule.id == rule_id)
        )
        assert rule is None

    def test_delete_escalation_rule_not_found(
        self,
        tenant: Tenant,
        user: User,
        nonexistent_uuid: UUID,
        client: TestClient,
    ) -> None:
        """Test deleting nonexistent rule."""
        response = client.delete(
            f"/tenants/{tenant.id}/alerts/escalation-rules/{nonexistent_uuid}",
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTenantIsolation:
    """Test tenant isolation for alerts and escalation rules."""

    def test_acknowledge_alert_tenant_isolation(
        self,
        tenant: Tenant,
        other_tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that acknowledgements are tenant-isolated."""
        # Add user to other_tenant
        from uuid import uuid4

        from backend.app.db.models import Role, TenantMembership
        from sqlalchemy import select
        
        # Get the operations_inventory_manager system role
        role = db_session.scalar(
            select(Role).where(
                Role.tenant_id == other_tenant.id,
                Role.name == "operations_inventory_manager",
                Role.is_system == True,  # noqa: E712
            )
        )
        assert role is not None, "operations_inventory_manager role must exist"
        
        membership = TenantMembership(
            id=uuid4(),
            tenant_id=other_tenant.id,
            user_id=user.id,
            role="operations_inventory_manager",
            role_id=role.id,
        )
        db_session.add(membership)
        db_session.commit()
        
        # User acknowledges alert in tenant 1
        response1 = client.post(
            f"/tenants/{tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response1.status_code == 200

        # User acknowledges same alert in tenant 2 (should succeed - different tenant)
        response2 = client.post(
            f"/tenants/{other_tenant.id}/alerts/acknowledge",
            json={
                "alert_id": "alert-001",
                "alert_type": "early_warning",
            },
        )
        assert response2.status_code == 200

        # Verify both acknowledgements exist
        acks = db_session.scalars(
            select(AlertAcknowledgement).where(
                AlertAcknowledgement.alert_id == "alert-001"
            )
        ).all()
        assert len(acks) == 2
        tenant_ids = {ack.tenant_id for ack in acks}
        assert tenant.id in tenant_ids
        assert other_tenant.id in tenant_ids

    def test_escalation_rule_tenant_isolation(
        self,
        tenant: Tenant,
        other_tenant: Tenant,
        user: User,
        db_session: Session,
        client: TestClient,
    ) -> None:
        """Test that escalation rules are tenant-isolated."""
        # Add user to other_tenant
        from uuid import uuid4

        from backend.app.db.models import Role, TenantMembership
        from sqlalchemy import select
        
        # Get the operations_inventory_manager system role
        role = db_session.scalar(
            select(Role).where(
                Role.tenant_id == other_tenant.id,
                Role.name == "operations_inventory_manager",
                Role.is_system == True,  # noqa: E712
            )
        )
        assert role is not None, "operations_inventory_manager role must exist"
        
        membership = TenantMembership(
            id=uuid4(),
            tenant_id=other_tenant.id,
            user_id=user.id,
            role="operations_inventory_manager",
            role_id=role.id,
        )
        db_session.add(membership)
        db_session.commit()
        
        # Create rule in tenant 1
        response1 = client.post(
            f"/tenants/{tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )
        assert response1.status_code == 200

        # Create same rule in tenant 2 (should succeed - different tenant)
        response2 = client.post(
            f"/tenants/{other_tenant.id}/alerts/escalation-rules",
            json={
                "alert_type": "early_warning",
                "domain": "growth",
                "unacknowledged_hours": 6.0,
                "escalation_to_roles": ["executive_owner"],
                "is_enabled": True,
            },
        )
        assert response2.status_code == 200

        # Verify both rules exist
        rules = db_session.scalars(
            select(EscalationRule).where(
                EscalationRule.alert_type == "early_warning",
                EscalationRule.domain == "growth",
            )
        ).all()
        assert len(rules) == 2
        tenant_ids = {rule.tenant_id for rule in rules}
        assert tenant.id in tenant_ids
        assert other_tenant.id in tenant_ids
