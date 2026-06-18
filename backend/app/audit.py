from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy.orm import Session

from backend.app.db.models import AlertEventLog, AuditEvent


def write_audit_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Mapping[str, object] | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> None:
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=dict(details or {}),
    )
    db.add(event)


def write_alert_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    alert_id: str,
    alert_type: str,
    event_type: str,
    actor_user_id: uuid.UUID | None = None,
    event_data: Mapping[str, object] | None = None,
) -> None:
    """Log an immutable alert event to the audit trail.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        alert_id: Alert identifier (e.g., domain:key)
        alert_type: Type of alert (e.g., "margin_drift", "inventory_risk")
        event_type: Type of event (e.g., "created", "acknowledged",
            "dismissed", "escalation_rule_created")
        actor_user_id: UUID of user triggering event (None for system)
        event_data: Optional context data for the event

    Example:
        write_alert_event(
            db,
            tenant_id=tenant_id,
            alert_id="margin_drift:product_123",
            alert_type="margin_drift",
            event_type="acknowledged",
            actor_user_id=user_id,
            event_data={"acknowledged_at_confidence": 0.95},
        )
    """
    event = AlertEventLog(
        tenant_id=tenant_id,
        alert_id=alert_id,
        alert_type=alert_type,
        event_type=event_type,
        actor_user_id=actor_user_id,
        event_data=dict(event_data or {}),
    )
    db.add(event)
