from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy.orm import Session

from backend.app.db.models import AlertEventLog, AuditEvent, SystemHealthEvent


def write_audit_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Mapping[str, object] | None = None,
    actor_user_id: uuid.UUID | None = None,
    severity: str = "info",  # critical, important, info, debug
    category: str = "system",  # user_action, data_sync, alert, recommendation, etc.
    is_system_generated: bool = False,
    visible_to_personas: list[str] | None = None,  # NULL = visible to all
) -> None:
    """Write an audit event with severity and category filtering.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        action: Action code (e.g., "user.invited", "connector.shopify_orders_synced")
        entity_type: Type of entity (e.g., "user", "connector", "recommendation")
        entity_id: Identifier for the entity
        details: Optional context data
        actor_user_id: UUID of user triggering event (None for system actions)
        severity: Event severity (critical, important, info, debug)
        category: Event category for filtering (user_action, data_sync, alert, etc.)
        is_system_generated: True if event is from automated system processes
        visible_to_personas: List of persona names who can see this event (NULL = all)

    Severity Guidelines:
        - critical: Failures, escalations, security events
        - important: Recommendations, alerts, user actions with impact
        - info: Successful operations, routine updates
        - debug: System logs, sync events (hidden by default)

    Category Guidelines:
        - user_action: Invites, role changes, activations
        - data_sync: Shopify/API sync events
        - alert: Alert created, acknowledged, dismissed
        - recommendation: Recommendation created, approved, rejected
        - system_health: Sync failures, API errors
        - billing: Plan changes, payment updates
        - integration: Connector added, credentials updated
        - security: Login attempts, permission changes
    """
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=dict(details or {}),
        severity=severity,
        category=category,
        is_system_generated=is_system_generated,
        visible_to_personas=visible_to_personas,
    )
    db.add(event)


def write_system_health_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    service_name: str,
    event_type: str,
    severity: str,
    error_message: str,
    error_details: Mapping[str, object] | None = None,
) -> SystemHealthEvent:
    """Record a system health event (failure or issue).

    Args:
        db: Database session
        tenant_id: Tenant UUID
        service_name: Service that failed (e.g., "shopify_orders_sync", "meta_ads_api")
        event_type: Type of failure (sync_failure, api_error, data_anomaly, etc.)
        severity: Event severity (critical, important, info, debug)
        error_message: Human-readable error message
        error_details: Optional technical details (stack trace, API response, etc.)

    Returns:
        The created SystemHealthEvent (so caller can update resolved_at later)

    Example:
        # Record failure
        health_event = write_system_health_event(
            db,
            tenant_id=tenant_id,
            service_name="shopify_orders_sync",
            event_type="sync_failure",
            severity="critical",
            error_message="API rate limit exceeded",
            error_details={"status_code": 429, "retry_after": 300},
        )
        
        # Later, mark as resolved
        health_event.resolved_at = datetime.now(UTC)
        db.commit()
    """
    event = SystemHealthEvent(
        tenant_id=tenant_id,
        service_name=service_name,
        event_type=event_type,
        severity=severity,
        error_message=error_message,
        error_details=dict(error_details or {}),
    )
    db.add(event)
    return event


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
