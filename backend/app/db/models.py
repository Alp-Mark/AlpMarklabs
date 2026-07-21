from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from backend.app.db.base import Base


def _default_invitation_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=7)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    billing_plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="starter"
    )
    billing_cycle: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    billing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    seat_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # NFR-022 / T-052: tenant base currency (ISO 4217) and locale (IETF BCP-47)
    base_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USD"
    )
    locale: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en-US"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    # Admin audit trail fields
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, suspended, deleted
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    memberships: Mapped[list[TenantMembership]] = relationship(back_populates="tenant")
    invitations: Mapped[list[UserInvitation]] = relationship(back_populates="tenant")
    notification_routes: Mapped[list[NotificationRoutingSetting]] = relationship(
        back_populates="tenant"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="tenant")
    system_health_events: Mapped[list[SystemHealthEvent]] = relationship(
        back_populates="tenant"
    )
    privacy_requests: Mapped[list[PrivacyRequest]] = relationship(
        back_populates="tenant"
    )
    connectors: Mapped[list[ConnectorIntegration]] = relationship(
        back_populates="tenant"
    )
    connector_credentials: Mapped[list[ConnectorCredentialVault]] = relationship(
        back_populates="tenant"
    )
    shopify_orders: Mapped[list[ShopifyOrder]] = relationship(
        back_populates="tenant"
    )
    shopify_inventory_items: Mapped[list[ShopifyInventoryItem]] = relationship(
        back_populates="tenant"
    )
    locations: Mapped[list[Location]] = relationship(
        back_populates="tenant"
    )
    acquisition_cohorts: Mapped[list[AcquisitionCohort]] = relationship(
        back_populates="tenant"
    )
    custom_segments: Mapped[list[CustomSegment]] = relationship(
        back_populates="tenant"
    )
    meta_ad_spends: Mapped[list[MetaAdSpend]] = relationship(back_populates="tenant")
    google_ad_spends: Mapped[list[GoogleAdSpend]] = relationship(
        back_populates="tenant"
    )
    marketing_channel_spends: Mapped[list[MarketingChannelSpend]] = relationship(
        back_populates="tenant"
    )
    executive_kpi_snapshots: Mapped[list[ExecutiveKpiSnapshot]] = relationship(
        back_populates="tenant"
    )
    acquisition_metrics_snapshots: Mapped[list[AcquisitionMetricsSnapshot]] = (
        relationship(back_populates="tenant")
    )
    retention_daily_snapshots: Mapped[list[RetentionDailySnapshot]] = relationship(
        back_populates="tenant"
    )
    cohort_retention_snapshots: Mapped[list[CohortRetentionSnapshot]] = relationship(
        back_populates="tenant"
    )
    segment_margin_snapshots: Mapped[list[SegmentMarginSnapshot]] = relationship(
        back_populates="tenant"
    )
    cohort_return_signals: Mapped[list[CohortReturnSignal]] = relationship(
        back_populates="tenant"
    )
    cost_driver_snapshots: Mapped[list[CostDriverSnapshot]] = relationship(
        back_populates="tenant"
    )
    margin_drift_thresholds: Mapped[list[MarginDriftThreshold]] = relationship(
        back_populates="tenant"
    )
    margin_drift_snapshots: Mapped[list[MarginDriftSnapshot]] = relationship(
        back_populates="tenant"
    )
    cost_inputs: Mapped[list[CostInput]] = relationship(back_populates="tenant")
    cost_input_versions: Mapped[list[CostInputVersion]] = relationship(
        back_populates="tenant"
    )
    inventory_risk_thresholds: Mapped[list[InventoryRiskThreshold]] = relationship(
        back_populates="tenant"
    )
    inventory_risk_snapshots: Mapped[list[InventoryRiskSnapshot]] = relationship(
        back_populates="tenant"
    )
    shopify_order_line_items: Mapped[list[ShopifyOrderLineItem]] = relationship(
        back_populates="tenant"
    )
    operational_impact_snapshots: Mapped[
        list[OperationalImpactSnapshot]
    ] = relationship(
        back_populates="tenant"
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="tenant"
    )
    rule_thresholds: Mapped[list[TenantRuleThreshold]] = relationship(
        back_populates="tenant"
    )
    recommendation_suppression_states: Mapped[
        list[RecommendationSuppressionState]
    ] = relationship(back_populates="tenant")
    delegation_rules: Mapped[list[DelegationRule]] = relationship(
        back_populates="tenant"
    )
    saved_analysis_views: Mapped[list[SavedAnalysisView]] = relationship(
        back_populates="tenant"
    )
    annotations: Mapped[list[AnalysisAnnotation]] = relationship(
        back_populates="tenant"
    )
    alert_thresholds: Mapped[list[AlertThreshold]] = relationship(
        back_populates="tenant"
    )
    alert_recipients: Mapped[list[AlertRecipient]] = relationship(
        back_populates="tenant"
    )
    alert_acknowledgements: Mapped[list[AlertAcknowledgement]] = relationship(
        back_populates="tenant"
    )
    alert_dismissals: Mapped[list[AlertDismissal]] = relationship(
        back_populates="tenant"
    )
    escalation_rules: Mapped[list[EscalationRule]] = relationship(
        back_populates="tenant"
    )
    alert_event_logs: Mapped[list[AlertEventLog]] = relationship(
        back_populates="tenant"
    )
    email_delivery_logs: Mapped[list[EmailDeliveryLog]] = relationship(
        back_populates="tenant"
    )
    simulations: Mapped[list[Simulation]] = relationship(
        back_populates="tenant"
    )
    # Phase 1: Optimization engine relationships
    optimization_strategies: Mapped[list[OptimizationStrategy]] = relationship()
    optimization_runs: Mapped[list[OptimizationRun]] = relationship()
    fitted_models: Mapped[list[FittedModel]] = relationship()
    optimization_experiments: Mapped[list[OptimizationExperiment]] = relationship()
    roles: Mapped[list[Role]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    memberships: Mapped[list[TenantMembership]] = relationship(back_populates="user")
    alert_recipients: Mapped[list[AlertRecipient]] = relationship(
        back_populates="user"
    )
    alert_acknowledgements: Mapped[list[AlertAcknowledgement]] = relationship(
        back_populates="user"
    )
    alert_dismissals: Mapped[list[AlertDismissal]] = relationship(
        back_populates="user"
    )
    created_escalation_rules: Mapped[list[EscalationRule]] = relationship(
        back_populates="created_by_user",
        foreign_keys="EscalationRule.created_by_user_id",
    )
    triggered_alert_events: Mapped[list[AlertEventLog]] = relationship(
        back_populates="actor_user",
        foreign_keys="AlertEventLog.actor_user_id",
    )
    email_deliveries: Mapped[list[EmailDeliveryLog]] = relationship(
        back_populates="user"
    )
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="roles")
    memberships: Mapped[list[TenantMembership]] = relationship(
        back_populates="role_obj"
    )


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", name="uq_tenant_membership_tenant_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="growth_performance_manager"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
    role_obj: Mapped[Role | None] = relationship(back_populates="memberships")


class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_invitation_expiry
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="invitations")


def _default_password_reset_expiry() -> datetime:
    """Default password reset token expiry: 24 hours from now."""
    return datetime.now(UTC) + timedelta(hours=24)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_password_reset_expiry
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


def _default_session_expiry() -> datetime:
    """Default session expiry: 30 days from now."""
    return datetime.now(UTC) + timedelta(days=30)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_session_expiry
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class NotificationRoutingSetting(Base):
    __tablename__ = "notification_routing_settings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "alert_type",
            "channel",
            "destination",
            name="uq_notification_route_per_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="notification_routes")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Activity log filtering fields (Phase 1)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info"
    )  # critical, important, info, debug
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="system"
    )  # user_action, data_sync, alert, recommendation, system_health, etc.
    is_system_generated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    visible_to_personas: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )  # NULL = visible to all
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="audit_events")


class SystemHealthEvent(Base):
    """
    System health and failure tracking.
    Records when services fail (syncs, APIs, connections) and when they recover.
    Used to surface "What's broken right now?" prominently in activity logs.
    """

    __tablename__ = "system_health_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    service_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "shopify_orders_sync", "meta_ads_api", "google_ads_api"
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # sync_failure, api_error, data_anomaly, connection_lost, rate_limit_exceeded
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # critical, important, info, debug
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_details: Mapped[dict[str, object] | None] = mapped_column(
        JSON, nullable=True
    )  # Stack trace, API response, etc.
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # NULL = unresolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="system_health_events")


class AdminAuditLog(Base):
    """
    Platform-level audit log for Super Admin actions.
    Tracks tenant lifecycle events, user management, and admin operations.
    """

    __tablename__ = "admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., tenant_created, tenant_suspended, tenant_deleted
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., tenant, user, subscription
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changes: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )  # Before/after state
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships (optional - can query without them)
    # tenant: Mapped[Tenant | None] = relationship()
    # admin_user: Mapped[User] = relationship()


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="privacy_requests")


class ConnectorIntegration(Base):
    """FR-014 to FR-017 / T-014 to T-017: External data source integrations.

    Represents connections to Shopify, Meta, Google Ads, and other third-party
    platforms. Each tenant can have one connector per source.

    E3: Added health_status field (healthy/degraded/critical/unknown) to track
    overall connector health based on sync progress, data freshness, and errors.
    """

    __tablename__ = "connector_integrations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", name="uq_connector_per_tenant_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="oauth")
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="disconnected",
    )
    # E3: Health status derived from sync/freshness/errors
    health_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown"
    )
    shop_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oauth_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    oauth_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    oauth_expiry_warning_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    oauth_expired_alert_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_sync_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="connectors")
    credential: Mapped[ConnectorCredentialVault | None] = relationship(
        back_populates="connector",
        uselist=False,
    )
    shopify_orders: Mapped[list[ShopifyOrder]] = relationship(
        back_populates="connector"
    )
    shopify_inventory_items: Mapped[list[ShopifyInventoryItem]] = relationship(
        back_populates="connector"
    )
    locations: Mapped[list[Location]] = relationship(
        back_populates="connector"
    )
    meta_ad_spends: Mapped[list[MetaAdSpend]] = relationship(
        back_populates="connector"
    )
    google_ad_spends: Mapped[list[GoogleAdSpend]] = relationship(
        back_populates="connector"
    )


class ConnectorCredentialVault(Base):
    __tablename__ = "connector_credential_vault"
    __table_args__ = (
        UniqueConstraint("connector_id", name="uq_connector_credential_connector"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    secret_type: Mapped[str] = mapped_column(String(30), nullable=False)
    secret_ciphertext: Mapped[str] = mapped_column(String(2000), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="connector_credentials")
    connector: Mapped[ConnectorIntegration] = relationship(back_populates="credential")


class MetaAdSpend(Base):
    __tablename__ = "meta_ad_spends"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_campaign_id",
            "spend_date",
            name="uq_meta_ad_spend_per_campaign_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    external_campaign_id: Mapped[str] = mapped_column(String(100), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    spend_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    spend_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="meta_ad_spends")
    connector: Mapped[ConnectorIntegration] = relationship(
        back_populates="meta_ad_spends"
    )


class GoogleAdSpend(Base):
    __tablename__ = "google_ad_spends"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_campaign_id",
            "spend_date",
            name="uq_google_ad_spend_per_campaign_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    external_campaign_id: Mapped[str] = mapped_column(String(100), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    spend_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    spend_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="google_ad_spends")
    connector: Mapped[ConnectorIntegration] = relationship(
        back_populates="google_ad_spends"
    )


class MarketingChannelSpend(Base):
    """Daily spend, conversions, and revenue for non-Meta/Google channels.

    Covers: influencer, email, tv_streaming, affiliate, and any future channels.
    Used by MultiChannelAllocator to train Hill saturation curves per channel.
    """

    __tablename__ = "marketing_channel_spends"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel_name",
            "spend_date",
            name="uq_marketing_channel_spend_per_channel_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    channel_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # influencer, email, tv_streaming, affiliate
    spend_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    spend_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conversions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="marketing_channel_spends")


class ShopifyOrder(Base):
    __tablename__ = "shopify_orders"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_order_id",
            name="uq_shopify_order_per_connector",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    external_order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_number: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    total_amount: Mapped[float] = mapped_column(nullable=False, default=0.0)
    discount_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    shipping_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    refund_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="shopify_orders")
    connector: Mapped[ConnectorIntegration] = relationship(
        back_populates="shopify_orders"
    )
    line_items: Mapped[list[ShopifyOrderLineItem]] = relationship(
        back_populates="order"
    )


class ShopifyInventoryItem(Base):
    __tablename__ = "shopify_inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_inventory_item_id",
            name="uq_shopify_inventory_item_per_connector",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    external_inventory_item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_point: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="shopify_inventory_items")
    connector: Mapped[ConnectorIntegration] = relationship(
        back_populates="shopify_inventory_items"
    )


class Location(Base):
    """Warehouse or fulfillment location metadata.
    
    Stores mapping between external location IDs (e.g. Shopify location_id)
    and human-readable location names/metadata.
    Used for multi-warehouse inventory views.
    """
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_location_id",
            name="uq_location_per_tenant_connector_external_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connector_integrations.id"), nullable=False
    )
    external_location_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="locations")
    connector: Mapped[ConnectorIntegration] = relationship(
        back_populates="locations"
    )


class ExecutiveKpiSnapshot(Base):
    __tablename__ = "executive_kpi_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "snapshot_date",
            name="uq_executive_kpi_snapshot_per_tenant_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    revenue_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ad_spend_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blended_roas: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contribution_margin_pct: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    drift: Mapped[dict[str, float | None]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="executive_kpi_snapshots")


class AcquisitionMetricsSnapshot(Base):
    __tablename__ = "acquisition_metrics_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel",
            "snapshot_date",
            name="uq_acquisition_metrics_per_tenant_channel_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    ad_spend_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue_attributed: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    roas: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cac: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contribution_margin_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    payback_period_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    payback_upside_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    payback_downside_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(
        back_populates="acquisition_metrics_snapshots"
    )


class RetentionDailySnapshot(Base):
    __tablename__ = "retention_daily_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "snapshot_date",
            name="uq_retention_daily_per_tenant_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeat_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeat_purchase_rate_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    trend_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_60d: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_90d: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_repurchase_cadence_days: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    lifecycle_funnel: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    churn_risk_summary: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="retention_daily_snapshots")


class CohortRetentionSnapshot(Base):
    __tablename__ = "cohort_retention_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cohort_month",
            "snapshot_date",
            name="uq_cohort_retention_per_tenant_cohort_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    cohort_month: Mapped[str] = mapped_column(String(7), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repeat_customer_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    repeat_purchase_rate_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    days_since_cohort_start: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    avg_days_to_second_order: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="cohort_retention_snapshots")


class SegmentMarginSnapshot(Base):
    """FR-041: Contribution margin per customer segment, computed daily.

    One row per tenant × segment_type × snapshot_date.
    COGS is stored as 0.0 until cost inputs are wired in (T-047/T-048).
    data_completeness records which cost components were available at
    computation time so consumers can surface the right confidence signal.
    """

    __tablename__ = "segment_margin_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "segment_type",
            "snapshot_date",
            name="uq_segment_margin_per_tenant_segment_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    segment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cogs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    shipping_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    returns_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    acquisition_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contribution_margin_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    contribution_margin_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    data_completeness: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="segment_margin_snapshots")


class CohortReturnSignal(Base):
    """FR-042: Return/refund data as a retention signal per cohort.

    Completely separate from the operational returns view — no unit cost
    or logistics data is stored here.  One row per tenant × cohort_month
    × snapshot_date.  The repeat_purchase_rate_pct is copied from the
    most recent CohortRetentionSnapshot so callers can compare the two
    metrics side-by-side without a join.
    """

    __tablename__ = "cohort_return_signals"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cohort_month",
            "snapshot_date",
            name="uq_cohort_return_signal_per_tenant_cohort_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    cohort_month: Mapped[str] = mapped_column(String(7), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunded_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    repeat_purchase_rate_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="cohort_return_signals")


class CostDriverSnapshot(Base):
    """FR-048/FR-049: Daily cost-driver impact per driver type.

    One row per tenant × driver_type × snapshot_date.  Captures the
    absolute cost, % of revenue, margin impact, data source, and a
    confidence label derived purely from how recently the underlying
    data was synced or updated (FR-049: recency, not source type).

    Phase 1 driver types: cogs, shipping, returns, discounts, ad_spend.
    COGS is 0.0 until cost inputs are provided (T-048).
    """

    __tablename__ = "cost_driver_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "driver_type",
            "snapshot_date",
            name="uq_cost_driver_per_tenant_driver_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    driver_type: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    absolute_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pct_of_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    margin_impact_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    confidence_label: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="cost_driver_snapshots")


class MarginDriftThreshold(Base):
    """FR-053: Finance Controller's per-channel/category alert threshold profiles.

    One profile per tenant × channel × category.  Takes effect on the
    next daily drift computation run after it is created or updated.
    """

    __tablename__ = "margin_drift_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel",
            "category",
            name="uq_margin_drift_threshold_per_tenant_channel_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="margin_drift_thresholds")


class MarginDriftSnapshot(Base):
    """FR-054: Daily margin drift computation per channel/category.

    One row per tenant × channel × category × snapshot_date.
    expected_margin_pct and drift_pct are None on the first snapshot
    (no prior baseline to compare against).  threshold_exceeded triggers
    an alert AuditEvent when True.
    """

    __tablename__ = "margin_drift_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel",
            "category",
            "snapshot_date",
            name="uq_margin_drift_per_tenant_channel_category_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    actual_margin_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_margin_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    drift_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_exceeded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    variance_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    data_completeness: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="margin_drift_snapshots")


class CostInput(Base):
    """FR-050: Tiered/banded cost inputs managed by the Finance Controller.

    Each row represents one tier or band of a cost input type for a tenant.
    Shipping cost inputs are banded by weight range and destination zone.
    COGS inputs include landed cost (import duties).  Ad-spend VAT and
    return-processing inputs are stored as flat amounts or percentages.

    FR-051: When input_type == "cogs" the change is high-impact and
    confirmation_required is set True on create/update.  The change only
    propagates to live computations after the Finance Controller calls the
    confirm endpoint.
    """

    __tablename__ = "cost_inputs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    # "shipping" | "cogs" | "ad_spend_vat" | "return_processing"
    input_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Human-readable label, e.g. "0–0.5 kg domestic"
    tier_label: Mapped[str] = mapped_column(String(150), nullable=False)
    # Shipping-tier bounds (kg).  NULL for non-shipping types.
    weight_min_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_max_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "domestic" | "eu" | "international" | NULL for non-shipping types
    destination_zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Cost value
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # "per_order" | "per_kg" | "flat" | "pct"
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    # FR-051: high-impact (cogs) changes require explicit confirmation
    confirmation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="cost_inputs")
    versions: Mapped[list[CostInputVersion]] = relationship(
        back_populates="cost_input",
        order_by="CostInputVersion.version_number",
    )


class CostInputVersion(Base):
    """FR-052 / NFR-013: Full version history for every cost input.

    One row per change event (created, updated, deactivated).  version_number
    is 1-based and monotonically increasing per cost_input_id.  The first row
    (version_number == 1) represents the initial value captured in AlpMark
    (including any onboarding-imported baseline).  prior_amount and prior_unit
    are NULL on version 1.
    """

    __tablename__ = "cost_input_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    cost_input_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cost_inputs.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # "created" | "updated" | "deactivated"
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    prior_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_amount: Mapped[float] = mapped_column(Float, nullable=False)
    prior_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    variance_reason: Mapped[str | None] = mapped_column(String(150), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="cost_input_versions")
    cost_input: Mapped[CostInput] = relationship(back_populates="versions")


class InventoryRiskThreshold(Base):
    """FR-060 / FR-061 / FR-062: Configurable alert thresholds per tenant × category.

    Thresholds control when each status is triggered during the daily
    inventory risk computation.  Use category="all" for a tenant-wide
    fallback.  Category-specific rows override "all" when the SKU's
    category matches.
    """

    __tablename__ = "inventory_risk_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "category",
            name="uq_inventory_risk_threshold_per_tenant_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # FR-060: days-to-stockout alert threshold
    stockout_alert_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=7.0
    )
    # FR-061: weeks-of-cover threshold to flag overstock
    overstock_weeks_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=12.0
    )
    # FR-062: slow-moving requires all four conditions
    slow_moving_min_qty: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    slow_moving_min_weeks_cover: Mapped[float] = mapped_column(
        Float, nullable=False, default=4.0
    )
    slow_moving_min_capital: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="inventory_risk_thresholds")


class InventoryRiskSnapshot(Base):
    """FR-058 to FR-062: Daily inventory risk snapshot per SKU.

    One row per tenant × sku × snapshot_date.  Velocity figures are
    estimated from tenant-level order counts distributed across active
    SKUs (Phase 1 — no line-item data).  data_completeness records this
    limitation.  Seasonal adjustment is reserved for Phase 2.
    """

    __tablename__ = "inventory_risk_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sku",
            "snapshot_date",
            name="uq_inventory_risk_per_tenant_sku_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_point: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "in_stock" | "low_stock" | "stockout_risk" | "overstock" | "slow_moving"
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    daily_velocity_30d: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    days_to_stockout: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_velocity_90d: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    weeks_of_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_since_last_sale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capital_at_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    seasonal_adjustment_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # "high" | "medium" | "low"
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    data_completeness: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="inventory_risk_snapshots")


class ShopifyOrderLineItem(Base):
    """One row per line item within a Shopify order.

    Stores per-SKU units sold, enabling real velocity computation
    in the inventory risk job (FR-058 to FR-062).
    """

    __tablename__ = "shopify_order_line_items"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "order_id",
            "line_item_index",
            name="uq_shopify_order_line_item_per_order_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shopify_orders.id"), nullable=False
    )
    # Position within the order (0-based) used as dedup key
    line_item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    order_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="shopify_order_line_items")
    order: Mapped[ShopifyOrder] = relationship(back_populates="line_items")


class OperationalImpactSnapshot(Base):
    """FR-064 to FR-066: Daily operational impact per SKU.

    FR-064: Stockout lost-revenue estimate and repeat-purchase risk.
    FR-065: Logistics cost burden per SKU (shipping + return processing).
    FR-066: Operational return rate analytics — completely separate from
            the retention cohort return signal view.

    One row per tenant × sku × snapshot_date.
    """

    __tablename__ = "operational_impact_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sku",
            "snapshot_date",
            name="uq_operational_impact_per_tenant_sku_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # FR-064: Stockout impact
    # "high" | "medium" | "low" | "none"
    inventory_status: Mapped[str] = mapped_column(String(20), nullable=False)
    daily_velocity_30d: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    avg_unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    days_to_restock_estimate: Mapped[float] = mapped_column(
        Float, nullable=False, default=7.0
    )
    stockout_lost_revenue_estimate: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    # "high" | "medium" | "low" | "none"
    repeat_purchase_risk: Mapped[str] = mapped_column(
        String(10), nullable=False, default="none"
    )

    # FR-065: Logistics cost burden
    logistics_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    logistics_cost_total_30d: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    logistics_margin_impact_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # FR-066: Operational return analytics (separate from retention cohort)
    units_sold_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_quantity_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_rate_30d_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    return_cost_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_cost_total_30d: Mapped[float | None] = mapped_column(Float, nullable=True)

    # "high" | "medium" | "low"
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    data_completeness: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(
        back_populates="operational_impact_snapshots"
    )


class Recommendation(Base):
    """FR-071 / T-053: Persisted output of the deterministic rule engine.

    One row per tenant × rule_id × snapshot_date.  The unique constraint
    prevents duplicate recommendations if the job runs more than once in
    a day.

    Status lifecycle (cross-cutting rule 2 + E1 extensions):
        new → reviewed → approved → rejected
            → implemented_externally → outcome_observed
        Additional E1 states:
            - expired: recommendation no longer relevant
            - archived: removed from active view but preserved
    
    Confidence level (E1): Structured 5-level enum mapped from confidence_score:
        - very_low (0.0-0.3): Low signal quality or stale data
        - low (0.3-0.5): Moderate signal with gaps
        - medium (0.5-0.7): Solid signal, some uncertainty
        - high (0.7-0.9): Strong signal, high data quality
        - very_high (0.9-1.0): Very strong signal, fresh comprehensive data
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "rule_id",
            "snapshot_date",
            name="uq_recommendation_per_tenant_rule_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    domain: Mapped[str] = mapped_column(String(30), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    affected_area: Mapped[str] = mapped_column(String(255), nullable=False)
    signal_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    suggested_action: Mapped[str] = mapped_column(String(500), nullable=False)
    estimated_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    data_freshness_context: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="new"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # E1: Numeric confidence score (0-1 scale) and data source tracking
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    data_sources: Mapped[list] = mapped_column(
        JSON, nullable=False, server_default="[]"
    )
    # Phase 1: Source of recommendation (threshold-based vs optimization-based)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="threshold"
    )
    # Phase 2: Optimization metadata for ML-generated recommendations
    optimization_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Optimization details: conversions, lift, accuracy",
    )
    fitted_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fitted_models.id"), nullable=True,
        comment="FK to the fitted model that generated this recommendation"
    )
    review_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # FR-076 / T-062: Stamps when recommendation transitions to "approved" status.
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # FR-076 / T-062: Implementation gap flag. Values: null (no gap),
    # "warning" (14-30 days since approved), "escalated" (>30 days since approved).
    # Scanned daily by task.
    implementation_gap_flag: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    # FR-069, FR-077 / T-063: Outcome observation and cross-metric impact tracking.
    # Stamped when recommendation transitions to "implemented_externally" status.
    implemented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Stamped when recommendation transitions to "outcome_observed" status.
    outcome_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Before-window snapshot of all 7 KPIs at implementation time.
    # Keys: contribution_margin_pct, cac_payback_period, blended_roas,
    # return_rate_pct, repeat_purchase_rate_pct, cac_by_channel, time_to_insight.
    outcome_metrics_before: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    # After-window snapshot of all 7 KPIs after observation window (default 30 days).
    outcome_metrics_after: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    # Comparison summary: per metric shows before/after/change/direction; flags
    # any guardrail violations (e.g., ROAS improved but repeat rate dropped).
    outcome_impact_summary: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="recommendations")
    fitted_model: Mapped[FittedModel | None] = relationship(
        "FittedModel", foreign_keys=[fitted_model_id]
    )


class TenantRuleThreshold(Base):
    """FR-071 / T-054: Tenant-configurable threshold for each recommendation rule.

    One row per tenant × rule_id.  Seeded with sensible defaults at tenant
    creation time.  Brand Admins can update threshold_value via the API,
    which sets is_customised=True.  suggested_value is populated in T-054b
    by the suggested-threshold engine.
    """

    __tablename__ = "tenant_rule_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "rule_id",
            name="uq_tenant_rule_threshold_per_tenant_rule",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    # Populated by T-054b suggested-threshold engine; null until then.
    suggested_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Set to True when a Brand Admin explicitly changes the value.
    is_customised: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="rule_thresholds")


class RecommendationSuppressionState(Base):
    """FR-074 / T-060: Tracks rejection counts and active suppression windows.

    One row per tenant × rule_id.  Created on the first rejection of a
    recommendation type.  When rejection_count reaches rejection_threshold,
    suppressed_until is set and further recommendations for that rule are
    blocked until the window expires or a Brand Admin overrides it.
    """

    __tablename__ = "recommendation_suppression_states"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "rule_id",
            name="uq_suppression_per_tenant_rule",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rejection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Configurable per tenant × rule; set at row creation, support-ticket to change.
    rejection_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    suppression_window_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(
        back_populates="recommendation_suppression_states"
    )


class DelegationRule(Base):
    """FR-023, FR-075 / T-061: Recommendation approval authority delegation.

    Brand Admin or Executive Owner can delegate approval authority for a
    specific recommendation domain to another tenant member for a bounded
    date range.  Multiple active delegations for the same domain are allowed.
    Any Brand Admin can revoke a delegation at any time.
    """

    __tablename__ = "delegation_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    # Nullable so tests that bypass the full user-creation flow still work,
    # matching the same pattern used for actor_user_id on AuditEvent.
    delegator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    delegatee_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="delegation_rules")


class SavedAnalysisView(Base):
    """FR-032 / T-064: Saved custom analysis views for quick recall and sharing.

    Stores filters (metrics, date_range, domain, status filters), name,
    description, and metadata for later reuse and team sharing.
    """

    __tablename__ = "saved_analysis_views"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # JSON object: {metrics: [...], date_range: {from, to}, domain: string,
    # rec_status: [...]}, etc. Flexible schema for future extensibility.
    filters_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="saved_analysis_views")
    created_by: Mapped[User] = relationship()
    shares: Mapped[list[AnalysisViewShare]] = relationship(
        back_populates="saved_view"
    )
    annotations: Mapped[list[AnalysisAnnotation]] = relationship(
        back_populates="saved_view"
    )


class AnalysisAnnotation(Base):
    """FR-033, FR-045, FR-068 / T-065: Timestamped annotations on analysis views.

    Annotations are immutable (created once, never updated). Attach context to
    analyses and date-linked events (lifecycle, operational).
    Growth/Retention/Operations personas add these for team context.
    """

    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    saved_view_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_analysis_views.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    # Optional: Date-linked for lifecycle (FR-045) and operational (FR-068) annotations.
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Optional: Type tag for future filtering ("lifecycle", "operational", "context").
    annotation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    saved_view: Mapped[SavedAnalysisView] = relationship(
        back_populates="annotations"
    )
    tenant: Mapped[Tenant] = relationship(back_populates="annotations")
    created_by: Mapped[User] = relationship()


class AnalysisViewShare(Base):
    """FR-034 / T-064: Track sharing of analysis views with recipients.

    One row per view × recipient share action. Stores recipient email,
    shared_by user, shared_at timestamp, and optional one-time token for
    guest access.
    """

    __tablename__ = "analysis_view_shares"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    saved_view_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_analysis_views.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    shared_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    # Scope: "tenant" (recipient must be tenant member) or "one_time_link"
    # (guest access via one_time_token).
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="tenant")
    one_time_token: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    saved_view: Mapped[SavedAnalysisView] = relationship(
        back_populates="shares"
    )
    tenant: Mapped[Tenant] = relationship()
    shared_by: Mapped[User] = relationship()


class CohortSnapshot(Base):
    """FR-037 / T-066: Pre-computed cohort metrics for side-by-side comparison.

    Captures retention, churn, AOV, and revenue metrics for a cohort over a
    fixed observation window. Growth/Finance/Executive use these snapshots to
    compare acquisition quality across time periods.
    """

    __tablename__ = "cohort_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    # Cohort bucketing: which time period customers were acquired.
    cohort_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Grain: 'month', 'week', 'quarter'
    cohort_grain: Mapped[str] = mapped_column(String(50), nullable=False)
    # Observation window: how many days after cohort start we measured metrics.
    observation_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # Metrics
    customer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_rate: Mapped[float] = mapped_column(Float, nullable=False)
    churn_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_order_value: Mapped[float] = mapped_column(Float, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    repeat_purchase_frequency: Mapped[float] = mapped_column(Float, nullable=False)
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()


class AcquisitionCohort(Base):
    """FR-043 / T-070: Read-only acquisition context for retention managers.

    Captures acquisition metrics (channel, CAC, first-order AOV, customer
    quality) by cohort time period. Retention managers use this to understand
    incoming customer quality and segment quality differences for retention
    strategy analysis.
    """

    __tablename__ = "acquisition_cohorts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cohort_start_date",
            "cohort_end_date",
            "channel",
            name="uq_acquisition_cohort_per_tenant_period_channel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    # Cohort bucketing: time period when customers were acquired
    cohort_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_grain: Mapped[str] = mapped_column(String(50), nullable=False)
    # Channel from which customers were acquired
    # (e.g., 'shopify_organic', 'meta_ads', 'google_ads')
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    # Acquisition metrics
    new_customer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blended_cac: Mapped[float] = mapped_column(Float, nullable=False)
    first_order_aov: Mapped[float] = mapped_column(Float, nullable=False)
    total_acquisition_spend: Mapped[float] = mapped_column(Float, nullable=False)
    # Customer quality signal: early indicator of repeat purchase potential
    repeat_purchase_rate_90d: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    # Audit
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="acquisition_cohorts")


class CustomSegment(Base):
    """FR-044 / T-071: Custom customer segments defined by Retention Manager.

    Retention managers can create and save reusable customer segments
    (e.g., "High-Value: AOV > £500") for use in dashboards, cohort
    analysis, and alert configuration. Definition is stored as JSON
    with flexible filter structure.
    """

    __tablename__ = "custom_segments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_custom_segment_per_tenant_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Flexible JSON definition: { filters: [...], rules: [...] }
    # Phase 1 examples:
    #   { "aov_min": 500 }
    #   { "aov_min": 500, "aov_max": 2000 }
    #   { "segment_type": ["new", "returning"] }
    definition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="custom_segments")


class AlertThreshold(Base):
    """FR-107 / T-072: User-configured alert thresholds per metric per domain.

    One row per tenant × metric × alert_type.
    Stores the threshold value, comparison operator, and whether it is enabled.
    """

    __tablename__ = "alert_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "alert_type",
            "metric_name",
            name="uq_alert_threshold_per_tenant_type_metric",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    comparison_operator: Mapped[str] = mapped_column(
        String(10), nullable=False, default="<"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="alert_thresholds")


class AlertRecipient(Base):
    """FR-108 / T-072: Recipients for alerts (users or delivery channels).

    Stores alert delivery preferences per user per channel.
    One row per tenant × user × channel combination.
    """

    __tablename__ = "alert_recipients"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "channel",
            name="uq_alert_recipient_per_user_channel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="alert_recipients")
    user: Mapped[User] = relationship(back_populates="alert_recipients")


class AlertAcknowledgement(Base):
    """FR-122 / T-078: Track alert acknowledgement events.

    Records when a user acknowledges an alert. Each alert can be
    acknowledged by multiple users, and each user acknowledges once per alert.
    One row per tenant × user × alert_id combination.
    """

    __tablename__ = "alert_acknowledgements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "alert_id",
            name="uq_alert_ack_per_tenant_user_alert",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="alert_acknowledgements")
    user: Mapped[User] = relationship(back_populates="alert_acknowledgements")


class AlertDismissal(Base):
    """FR-122 / T-078: Track alert dismissal events.

    Records when a user dismisses an alert. Each alert can be
    dismissed by multiple users, and each user dismisses once per alert.
    One row per tenant × user × alert_id combination.
    """

    __tablename__ = "alert_dismissals"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "alert_id",
            name="uq_alert_dismiss_per_tenant_user_alert",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dismiss_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="alert_dismissals")
    user: Mapped[User] = relationship(back_populates="alert_dismissals")


class EscalationRule(Base):
    """FR-122 / T-078: Configure escalation rules for unacknowledged alerts.

    Allows Brand Admin and Executive Owner to set up rules that automatically
    escalate (re-notify) unacknowledged alerts after a configurable time window.
    Example: "If early_warning alert sits unacknowledged for 6 hours,
    re-notify Executive Owner and Growth Manager."
    One row per tenant × alert_type × domain combination.
    """

    __tablename__ = "escalation_rules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "alert_type",
            "domain",
            name="uq_escalation_rule_per_tenant_type_domain",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    unacknowledged_hours: Mapped[float] = mapped_column(Float, nullable=False)
    escalation_to_roles: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="escalation_rules")
    created_by_user: Mapped[User | None] = relationship(
        back_populates="created_escalation_rules",
        foreign_keys=[created_by_user_id],
    )


class AlertEventLog(Base):
    """FR-125 / T-079: Immutable audit log for all alert-related events.

    Tracks creation, acknowledgement, dismissal, and escalation rule changes.
    Every event is append-only (immutable) with actor identity and timestamp.
    Supports querying alert history by alert_id or bulk event querying by tenant.
    """

    __tablename__ = "alert_event_log"
    __table_args__ = (
        # Index for fast alert_id + event type lookups (history for specific alert)
        # Index for tenant-level audits (all events in tenant for compliance)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "created", "acknowledged", "dismissed", "escalation_rule_created", etc.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    event_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Flexible schema for event-specific details
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    tenant: Mapped[Tenant] = relationship(back_populates="alert_event_logs")
    actor_user: Mapped[User | None] = relationship(
        back_populates="triggered_alert_events", foreign_keys=[actor_user_id]
    )


class EmailDeliveryLog(Base):
    """FR-116 / T-079: Immutable log for all email delivery attempts.

    Tracks each email send for alerts with status, retry attempts, and errors.
    Supports email delivery auditing, retry logic, and bounce handling.
    Append-only log with recipient, alert reference, and delivery status.
    """

    __tablename__ = "email_delivery_log"
    __table_args__ = (
        # Index for querying delivery status by tenant
        # Index for user-level delivery history
        # Index for alert-specific delivery tracking
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    email_address: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Snapshot of email at send time
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # "pending", "sent", "failed", "bounced"
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Error details if status is "failed"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    tenant: Mapped[Tenant] = relationship(back_populates="email_delivery_logs")
    user: Mapped[User] = relationship(back_populates="email_deliveries")


class Simulation(Base):
    """FR-081, FR-087 / T-081: Three-scenario simulation (baseline/upside/downside).

    Stores the output of the simulation engine: baseline (no change),
    upside (best case), and downside (risk case) with all projected impacts.

    Simulations are created automatically when a recommendation fires (rule engine
    triggers). The simulator uses response functions and scipy.optimize to find x*
    (the mathematical optimum) and generates three scenarios around that optimum.

    One row per simulation run, persisted for audit trail and comparison.
    
    E2 additions:
    - name: User-provided label for simulation identification
    - description: User notes about simulation purpose/context
    - is_deleted: Soft delete flag (preserves audit trail)
    - updated_at: Timestamp for rename/edit tracking
    """

    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recommendations.id"), nullable=True, index=True
    )
    # E2: User-provided name and description
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Simulation domain: 'acquisition', 'retention', 'margin', 'inventory', 'ops',
    # 'executive'
    domain: Mapped[str] = mapped_column(String(30), nullable=False)
    # Simulation type: 'auto' (fires after rule engine), 'manual' (user-triggered)
    simulation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="auto"
    )
    # Mathematical optimum found by optimizer (e.g., optimal spend level,
    # optimal price point)
    x_star: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Confidence in the simulation output (reflects data freshness and signal
    # strength)
    confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    # Data freshness signal: high/medium/low (impacts confidence score)
    data_freshness_signal: Mapped[str] = mapped_column(
        String(20), nullable=False, default="high"
    )
    # Metric completeness signal: high/medium/low (reflects data coverage)
    metric_completeness_signal: Mapped[str] = mapped_column(
        String(20), nullable=False, default="high"
    )
    # Baseline scenario (no change)
    baseline_scenario: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Upside scenario (best case)
    upside_scenario: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Downside scenario (risk case)
    downside_scenario: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Metadata: which response function was used, optimizer details
    simulation_metadata: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # E2: Soft delete flag (preserves audit trail)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # E2: Updated timestamp for rename/edit tracking
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()
    recommendation: Mapped[Recommendation | None] = relationship()


class SupportTicket(Base):
    """E4: Support ticket lifecycle management (FR-092, FR-093, FR-099-101).

    Tracks support tickets for tenant issues with assignment, resolution,
    and closure workflow.
    """

    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="open"
    )  # open, in_progress, resolved, closed, escalated
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # low, medium, high, urgent
    issue_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # integration_failure, sync_error, onboarding_help, etc.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # FR-099: Internal support notes
    resolution_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # FR-100: Resolution summary
    resolution_category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # FR-100: Root cause category
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserNotificationPreference(Base):
    """E5: User-level notification preferences (FR-007, FR-108).

    Controls which alert categories a user receives and via which channels.
    """

    __tablename__ = "user_notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "tenant_id",
            "alert_category",
            name="uq_user_notification_preference_per_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    alert_category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # kpi_drift, stockout_risk, churn_risk, sync_failure, etc.
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="both"
    )  # in_app, email, both
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Notification(Base):
    """E5: In-app notification inbox (FR-123, FR-124, FR-125).

    Tracks individual notifications sent to users with read/dismiss workflow.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Alert type
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info"
    )  # info, warning, critical
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unread"
    )  # unread, read, dismissed
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    context_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Scenario(Base):
    """FR-081, FR-087 / T-081: Individual scenario data within a simulation.

    Each simulation generates three scenarios. Scenario stores normalized data
    about inputs, outputs, impact projections, and confidence level per scenario.

    Useful for queries like "show me all upside scenarios across simulations" or
    "compare downside scenarios for this recommendation".
    """

    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint(
            "simulation_id",
            "scenario_type",
            name="uq_scenario_per_simulation_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulations.id"), nullable=False, index=True
    )
    # Scenario type: 'baseline', 'upside', 'downside'
    scenario_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Input assumptions for this scenario (e.g., response rate, execution quality)
    input_assumptions: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    # Computed output values (e.g., projected_roas, projected_cac, projected_margin)
    output_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Impact deltas: how this scenario changes from baseline (percentage or absolute)
    impact_deltas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Confidence score for this specific scenario (0.0-1.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    # Rationale for this scenario (why these assumptions were chosen)
    rationale: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    simulation: Mapped[Simulation] = relationship()


class ExportShare(Base):
    """T-086: Scoped export sharing with permission checks.

    Tracks which user shared a simulation export with which recipient.
    Enforces permission checks at share creation time.
    Shares are immutable once created; revocation creates audit trail.
    """

    __tablename__ = "export_shares"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "simulation_id",
            "shared_by_user_id",
            "shared_with_user_id",
            name="uq_export_share_per_sim_sharer_recipient",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulations.id"), nullable=False, index=True
    )
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    # Status: 'active' or 'revoked'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped[Tenant] = relationship()
    simulation: Mapped[Simulation] = relationship()
    shared_by_user: Mapped[User] = relationship(
        foreign_keys=[shared_by_user_id]
    )
    shared_with_user: Mapped[User] = relationship(
        foreign_keys=[shared_with_user_id]
    )


class ExportLink(Base):
    """T-087: Signed file links and expiry management.

    Stores secure, temporary download links for shared exports.
    Each link has a signed token (proven to belong to recipient) and expiry time.
    Links are created on-demand when a recipient needs to download the file.
    """

    __tablename__ = "export_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    share_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("export_shares.id"), nullable=False, index=True
    )
    # Signed token (URL-safe, contains share_id and timestamp info)
    token: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    # When this link stops working
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Last time this link was used to download the file
    accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    share: Mapped[ExportShare] = relationship()


class SubscriptionPlan(Base):
    """Phase D / D1: Subscription plan definitions.

    Defines available subscription tiers with pricing, features, and limits.
    Tenants reference these via Tenant.billing_plan (slug match).
    Super-admins can create/update plans via platform admin endpoints.
    """

    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # URL-safe identifier (e.g., "starter", "professional", "enterprise")
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Display name shown to users
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Marketing description
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    # Pricing (USD, can extend to multi-currency later)
    price_monthly: Mapped[float] = mapped_column(Float, nullable=False)
    price_annual: Mapped[float] = mapped_column(Float, nullable=False)
    # Feature flags enabled for this plan (JSON array of feature slugs)
    # Example: ["simulations", "advanced_analytics", "api_access"]
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    # Plan limits (JSON object)
    # Example: {"seat_limit": 5, "connector_limit": 3, "api_rate_limit": 1000}
    limits: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Whether plan is available for new signups
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Display order (lower = shown first)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FeatureFlag(Base):
    """Phase D / D2: Global feature flag definitions.

    Defines available feature flags that can be enabled/disabled per tenant.
    Used for plan-based features, beta features, and gradual rollouts.
    """

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # URL-safe identifier (e.g., "simulations", "advanced_analytics")
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Display name
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Description of what this feature enables
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    # Category for grouping (e.g., "analytics", "integrations", "platform")
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # Whether this flag is available for use (admin can disable flags globally)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Default state for new tenants
    default_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant_overrides: Mapped[list[TenantFeatureFlag]] = relationship(
        back_populates="feature_flag"
    )


class TenantFeatureFlag(Base):
    """Phase D / D2: Per-tenant feature flag overrides.

    Allows enabling/disabling specific features for individual tenants,
    overriding subscription plan defaults.
    """

    __tablename__ = "tenant_feature_flags"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "feature_flag_slug",
            name="uq_tenant_feature_flag",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    feature_flag_slug: Mapped[str] = mapped_column(
        ForeignKey("feature_flags.slug"), nullable=False, index=True
    )
    # Whether this feature is enabled for this tenant
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # When it was enabled/disabled
    enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Who made the change (for audit trail)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()
    feature_flag: Mapped[FeatureFlag] = relationship(back_populates="tenant_overrides")
    changed_by_user: Mapped[User | None] = relationship()


class OptimizationStrategy(Base):
    """Phase 1: Optimization strategy configuration per tenant and domain.

    Stores which optimization algorithm each tenant uses for a specific domain.
    Examples:
    - domain='acquisition', strategy_name='Hill Curve Budget Allocation'
    - domain='margin', strategy_name='Dynamic Pricing Optimizer'
    - domain='retention', strategy_name='Email Campaign Timing'
    """

    __tablename__ = "optimization_strategies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "domain",
            "strategy_name",
            name="uq_strategy_per_tenant_domain",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(30), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()
    optimization_runs: Mapped[list[OptimizationRun]] = relationship(
        back_populates="strategy"
    )
    fitted_models: Mapped[list[FittedModel]] = relationship(back_populates="strategy")


class OptimizationRun(Base):
    """Phase 1: Log of each optimization engine execution.

    Tracks when optimization runs, what inputs it used, results,
    errors, and performance. Each run may generate recommendations
    and fitted models.
    """

    __tablename__ = "optimization_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_strategies.id"), nullable=False, index=True
    )
    run_status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # pending, running, success, failed
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    input_snapshot_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, server_default="[]"
    )
    optimization_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship()
    strategy: Mapped[OptimizationStrategy] = relationship(
        back_populates="optimization_runs"
    )
    fitted_models: Mapped[list[FittedModel]] = relationship(
        back_populates="optimization_run"
    )
    optimization_recommendations: Mapped[list[OptimizationRecommendation]] = (
        relationship(back_populates="optimization_run")
    )


class FittedModel(Base):
    """Phase 1: ML model metadata and S3 storage keys.

    Stores references to pickled ML models in AWS S3.
    Models are too large for database storage (can be 10-100MB),
    so we store metadata here and actual model files in S3.
    """

    __tablename__ = "fitted_models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_strategies.id"), nullable=False, index=True
    )
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_runs.id"), nullable=False
    )
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # hill_curve, linear_regression, random_forest, etc.
    s3_key: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True, index=True
    )
    model_metadata: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    accuracy_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship()
    strategy: Mapped[OptimizationStrategy] = relationship(
        back_populates="fitted_models"
    )
    optimization_run: Mapped[OptimizationRun] = relationship(
        back_populates="fitted_models"
    )
    optimization_recommendations: Mapped[list[OptimizationRecommendation]] = (
        relationship(back_populates="fitted_model")
    )


class OptimizationRecommendation(Base):
    """Phase 1: Link between optimization runs and generated recommendations.

    When the optimization engine generates a recommendation, this table
    stores the optimization-specific insights (e.g., optimal spend level,
    expected improvement, alternative scenarios).
    """

    __tablename__ = "optimization_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            name="uq_one_optimization_per_recommendation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id"), nullable=False, index=True
    )
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_runs.id"), nullable=False, index=True
    )
    fitted_model_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fitted_models.id"), nullable=True
    )
    optimization_insight: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    alternative_scenarios: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recommendation: Mapped[Recommendation] = relationship()
    optimization_run: Mapped[OptimizationRun] = relationship(
        back_populates="optimization_recommendations"
    )
    fitted_model: Mapped[FittedModel | None] = relationship(
        back_populates="optimization_recommendations"
    )


class OptimizationExperiment(Base):
    """Phase 1: A/B testing framework for threshold vs optimization.

    Allows running controlled experiments to compare threshold-based
    recommendations against optimization-based recommendations.
    Tracks metrics for both control and treatment groups.
    """

    __tablename__ = "optimization_experiments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    experiment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # acquisition, retention, margin, etc.
    experiment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # threshold_vs_optimization, strategy_comparison, etc.
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    control_group_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    treatment_group_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, server_default="{}"
    )
    control_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    treatment_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    winner: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # control, treatment, no_difference
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()
