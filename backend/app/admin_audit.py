"""Admin audit logging utilities for platform-level operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AdminAuditLog, TenantMembership, UserSession


def write_admin_audit_log(
    db: Session,
    admin_user_id: uuid.UUID,
    action_type: str,
    resource_type: str,
    resource_id: str | None = None,
    tenant_id: uuid.UUID | None = None,
    changes: dict[str, object] | None = None,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AdminAuditLog:
    """
    Write an admin audit log entry for platform-level operations.

    Args:
        db: Database session
        admin_user_id: ID of the admin user performing the action
        action_type: Type of action
            (e.g., tenant_created, tenant_suspended, tenant_deleted)
        resource_type: Type of resource (e.g., tenant, user, subscription)
        resource_id: Optional ID of the affected resource
        tenant_id: Optional tenant ID if action affects a specific tenant
        changes: Optional dict of before/after state or relevant details
        reason: Optional reason or notes for the action
        ip_address: Optional IP address of the admin user
        user_agent: Optional user agent of the admin user

    Returns:
        The created AdminAuditLog entry
    """
    log_entry = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=admin_user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        changes=changes or {},
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(UTC),
    )
    db.add(log_entry)
    # Note: Caller is responsible for committing the transaction
    return log_entry


def get_tenant_usage_metrics(
    db: Session, tenant_id: uuid.UUID
) -> tuple[int, datetime | None, int]:
    """
    Compute usage metrics for a tenant.

    Returns:
        Tuple of (total_logins, last_activity_at, active_users_30d)
    """
    total_logins = (
        db.scalar(
            select(func.count())
            .select_from(UserSession)
            .join(TenantMembership, UserSession.user_id == TenantMembership.user_id)
            .where(TenantMembership.tenant_id == tenant_id)
        )
        or 0
    )

    last_activity_at = db.scalar(
        select(func.max(UserSession.last_seen_at))
        .select_from(UserSession)
        .join(TenantMembership, UserSession.user_id == TenantMembership.user_id)
        .where(TenantMembership.tenant_id == tenant_id)
    )

    cutoff_30d = datetime.now(UTC) - timedelta(days=30)
    active_users_30d = (
        db.scalar(
            select(func.count(func.distinct(UserSession.user_id)))
            .select_from(UserSession)
            .join(TenantMembership, UserSession.user_id == TenantMembership.user_id)
            .where(
                TenantMembership.tenant_id == tenant_id,
                UserSession.last_seen_at >= cutoff_30d,
            )
        )
        or 0
    )

    return (total_logins, last_activity_at, active_users_30d)
