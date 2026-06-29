import os
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta
from importlib import import_module
from typing import Annotated, Any, TypedDict
from urllib.parse import urlencode
from uuid import UUID

import jwt
import sqlalchemy as sa
from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app import (
    date_utils,
    executive_service,
    growth_service,
    kpis,
    retention_service,
)
from backend.app import permissions as perm
from backend.app.audit import write_alert_event, write_audit_event
from backend.app.db.models import (
    AcquisitionCohort,
    AcquisitionMetricsSnapshot,
    AlertAcknowledgement,
    AlertDismissal,
    AlertEventLog,
    AlertRecipient,
    AlertThreshold,
    AnalysisAnnotation,
    AnalysisViewShare,
    AuditEvent,
    CohortSnapshot,
    ConnectorCredentialVault,
    ConnectorIntegration,
    CostDriverSnapshot,
    CostInput,
    CostInputVersion,
    CustomSegment,
    DelegationRule,
    EmailDeliveryLog,
    EscalationRule,
    ExecutiveKpiSnapshot,
    ExportShare,
    FeatureFlag,
    InventoryRiskSnapshot,
    InventoryRiskThreshold,
    MarginDriftSnapshot,
    MarginDriftThreshold,
    Notification,
    NotificationRoutingSetting,
    OperationalImpactSnapshot,
    OptimizationStrategy,
    PasswordResetToken,
    PrivacyRequest,
    Recommendation,
    RecommendationSuppressionState,
    RetentionDailySnapshot,
    Role,
    SavedAnalysisView,
    Scenario,
    Simulation,
    SubscriptionPlan,
    SupportTicket,
    Tenant,
    TenantFeatureFlag,
    TenantMembership,
    TenantRuleThreshold,
    User,
    UserInvitation,
    UserNotificationPreference,
    UserSession,
)
from backend.app.db.session import get_db
from backend.app.feature_enforcement import (
    RequireCustomSegments,
    RequireSimulations,
)
from backend.app.password import hash_password, verify_password
from backend.app.permissions import get_system_role_permissions
from backend.app.recommendations.export import export_analysis_view
from backend.app.recommendations.lifecycle import (
    InvalidTransitionError,
    RecommendationStatus,
    transition,
)
from backend.app.recommendations.suppression import (
    lift_suppression,
    record_rejection,
)
from backend.app.schemas.account import (
    AccountActivationRequest,
    AccountActivationResponse,
    BootstrapSuperAdminRequest,
    BootstrapSuperAdminResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SessionListResponse,
    UserResponse,
    UserSessionResponse,
)
from backend.app.schemas.admin_audit import (
    AdminAuditLogListResponse,
    AdminAuditLogResponse,
)
from backend.app.schemas.admin_tenant import (
    AdminTenantDeleteResponse,
    AdminTenantListResponse,
    AdminTenantResponse,
    AdminTenantStatusUpdateRequest,
    AdminTenantUpdateRequest,
)
from backend.app.schemas.alert_config import (
    AlertRecipientCreate,
    AlertRecipientListResponse,
    AlertRecipientResponse,
    AlertRecipientUpdate,
    AlertThresholdCreate,
    AlertThresholdListResponse,
    AlertThresholdResponse,
    AlertThresholdUpdate,
)
from backend.app.schemas.alert_escalation import (
    AlertAcknowledgementCreate,
    AlertAcknowledgementResponse,
    AlertDismissalCreate,
    AlertDismissalResponse,
    EscalationRuleCreate,
    EscalationRuleListResponse,
    EscalationRuleResponse,
    EscalationRuleUpdate,
)
from backend.app.schemas.alert_history import (
    AlertEventListResponse,
    AlertEventResponse,
    AlertHistoryResponse,
)
from backend.app.schemas.analysis_view import (
    AnalysisViewShareListResponse,
    AnalysisViewShareRequest,
    AnalysisViewShareResponse,
    SavedAnalysisViewCreateRequest,
    SavedAnalysisViewListResponse,
    SavedAnalysisViewResponse,
)
from backend.app.schemas.annotation import (
    AnnotationCreateRequest,
    AnnotationListResponse,
    AnnotationResponse,
)
from backend.app.schemas.billing import BillingSeatResponse, BillingSeatUpdateRequest
from backend.app.schemas.cohort import (
    AcquisitionCohortResponse,
    AcquisitionContextResponse,
    CohortComparisonRequest,
    CohortComparisonResponse,
    CohortSnapshotCreateRequest,
    CohortSnapshotResponse,
)
from backend.app.schemas.connector import (
    ConnectorApiKeyConnectRequest,
    ConnectorHealthSummary,
    ConnectorIntegrationStatusResponse,
    ConnectorManualResyncResponse,
    ConnectorOAuthReauthorizeRequest,
    ConnectorResponse,
    GoogleAdsOAuthCallbackRequest,
    GoogleAdsOAuthStartResponse,
    MetaOAuthCallbackRequest,
    MetaOAuthStartResponse,
    ShopifyOAuthCallbackRequest,
    ShopifyOAuthStartRequest,
    ShopifyOAuthStartResponse,
    WorkspaceHealthResponse,
)
from backend.app.schemas.connector_availability import (
    ConnectorAvailabilityResponse,
    ConnectorSourceBreakdown,
)
from backend.app.schemas.custom_segment import (
    CustomSegmentCreate,
    CustomSegmentListResponse,
    CustomSegmentResponse,
    CustomSegmentUpdate,
)
from backend.app.schemas.delegation import (
    DelegationRuleCreateRequest,
    DelegationRuleListResponse,
    DelegationRuleResponse,
)
from backend.app.schemas.email_delivery import (
    EmailDeliveryHistoryResponse,
    EmailDeliveryListResponse,
    EmailDeliveryResponse,
)
from backend.app.schemas.executive import ExecutiveOverviewResponse
from backend.app.schemas.feature_flags import (
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    TenantFeatureResponse,
    TenantFeatureToggleRequest,
)
from backend.app.schemas.finance import (
    CostDriverListResponse,
    CostDriverSnapshotResponse,
    CostInputCreateRequest,
    CostInputHistoryResponse,
    CostInputListResponse,
    CostInputRejectRequest,
    CostInputResponse,
    CostInputUpdateRequest,
    CostInputVersionResponse,
    HistoricalRestatementRequest,
    HistoricalRestatementResponse,
    MarginDriftListResponse,
    MarginDriftSnapshotResponse,
    MarginDriftThresholdCreateRequest,
    MarginDriftThresholdListResponse,
    MarginDriftThresholdResponse,
    MarginDriftThresholdUpdateRequest,
)
from backend.app.schemas.growth import GrowthDashboardResponse
from backend.app.schemas.inventory import (
    InventoryRiskListResponse,
    InventoryRiskThresholdCreateRequest,
    InventoryRiskThresholdListResponse,
    InventoryRiskThresholdResponse,
    InventoryRiskThresholdUpdateRequest,
    LocationResponse,
    LogisticsCostBreakdownResponse,
    MultiWarehouseInventoryResponse,
    StockoutImpactResponse,
    WarehouseInventoryHealthResponse,
)
from backend.app.schemas.invitation import UserInviteRequest, UserInviteResponse
from backend.app.schemas.kpis import KPICatalogResponse, KPIMetadataResponse
from backend.app.schemas.locale import (
    OPS_CURRENCY_SCALE_VS_USD,
    OPS_USD_DEFAULT,
    TenantLocaleResponse,
    TenantLocaleUpdateRequest,
)
from backend.app.schemas.membership import (
    MembershipResponse,
    MembershipRoleUpdateRequest,
)
from backend.app.schemas.navigation import (
    NavigationMenuItem,
    NavigationMenuResponse,
)
from backend.app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationRouteItem,
    NotificationRoutingResponse,
    NotificationRoutingUpdateRequest,
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceListResponse,
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
)
from backend.app.schemas.onboarding import (
    OnboardingChecklistItem,
    OnboardingChecklistResponse,
)
from backend.app.schemas.operations import (
    OperationalImpactListResponse,
    OperationalImpactSnapshotResponse,
)
from backend.app.schemas.platform_metrics import (
    FeatureFlagMetrics,
    IntegrationMetrics,
    PlatformMetricsResponse,
    SubscriptionMetrics,
    TenantMetrics,
    UserMetrics,
)
from backend.app.schemas.privacy import (
    PrivacyRequestCreateRequest,
    PrivacyRequestResponse,
    PrivacyRequestStatusUpdateRequest,
)
from backend.app.schemas.recommendation import (
    RecommendationDetailResponse,
    RecommendationListResponse,
    RecommendationResponse,
    RecommendationStatusUpdateRequest,
)
from backend.app.schemas.retention import RetentionDashboardResponse
from backend.app.schemas.roles import (
    PermissionCatalogResponse,
    PermissionInfo,
    RoleCreateRequest,
    RoleListResponse,
    RoleResponse,
    RoleUpdateRequest,
)
from backend.app.schemas.rule_threshold import (
    RuleThresholdListResponse,
    RuleThresholdResponse,
    RuleThresholdUpdateRequest,
)
from backend.app.schemas.simulation import (
    ExportLinkResponse,
    ExportShareListResponse,
    ExportShareRequest,
    ExportShareResponse,
    GeneratedExportLinkResponse,
    NarrationRequest,
    NarrationResponse,
    RecommendationSimulationLaunchRequest,
    RecommendationSimulationLaunchResponse,
    ScenarioResponse,
    SimulationChartDataResponse,
    SimulationComparisonRequest,
    SimulationDetailResponse,
    SimulationDuplicateRequest,
    SimulationDuplicateResponse,
    SimulationExportRequest,
    SimulationListResponse,
    SimulationResponse,
    SimulationUpdateRequest,
)
from backend.app.schemas.simulation_inputs import (
    ExecutiveSimulationInput,
    FinanceSimulationInput,
    GrowthSimulationInput,
    OperationsSimulationInput,
    RetentionSimulationInput,
)
from backend.app.schemas.subscription_plans import (
    SubscriptionPlanCreateRequest,
    SubscriptionPlanLimits,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdateRequest,
)
from backend.app.schemas.support_ticket import (
    SupportTicketClose,
    SupportTicketCreate,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from backend.app.schemas.suppression import (
    SuppressionStateListResponse,
    SuppressionStateResponse,
)
from backend.app.schemas.tenant import TenantCreateRequest, TenantCreateResponse
from backend.app.schemas.trends import (
    CostDriverTrendResponse,
    ExecutiveTrendResponse,
    GrowthTrendResponse,
    InventoryRiskTrendResponse,
    MarginDriftTrendResponse,
    OperationalImpactTrendResponse,
    RetentionTrendResponse,
)
from backend.app.security import (
    AUTH_JWT_ALGORITHM,
    AUTH_JWT_SECRET,
    AuthContext,
    get_current_auth,
    require_permissions,
    require_platform_roles,
)
from backend.app.vault import (
    VAULT_KEY_VERSION,
    encrypt_connector_secret,
    get_secret_fingerprint,
)

app = FastAPI(title="AlpMark Backend", version="0.1.0")

# Add CORS middleware to allow frontend requests.
# Origins are configurable via CORS_ALLOW_ORIGINS (comma-separated) so new
# frontend deployments can be allow-listed without a code change.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,"
    "http://localhost:3001,"
    "https://alpmark-labs-dev.replit.app"
)
_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MEMBER_ROLES = {
    "brand_admin",
    "executive_owner",
    "growth_performance_manager",
    "retention_crm_manager",
    "finance_controller",
    "operations_inventory_manager",
}
ALLOWED_BILLING_CYCLES = {"monthly", "yearly"}
ALLOWED_BILLING_STATUSES = {"active", "past_due", "trialing", "canceled"}
ALLOWED_NOTIFICATION_CHANNELS = {"email", "in_app", "slack"}
ALLOWED_PRIVACY_REQUEST_TYPES = {"export", "delete"}
ALLOWED_PRIVACY_REQUEST_STATUSES = {"pending", "approved", "completed", "rejected"}
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "alpmark-shopify-client-id")
SHOPIFY_OAUTH_SCOPES = "read_orders,read_products"
SHOPIFY_REDIRECT_URI = os.getenv(
    "SHOPIFY_REDIRECT_URI",
    "https://app.alpmark.ai/integrations/shopify/callback",
)
META_CLIENT_ID = os.getenv("META_CLIENT_ID", "alpmark-meta-client-id")
META_OAUTH_SCOPES = "ads_read,business_management"
META_REDIRECT_URI = os.getenv(
    "META_REDIRECT_URI",
    "https://app.alpmark.ai/integrations/meta/callback",
)
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "alpmark-google-ads-client-id")
GOOGLE_ADS_OAUTH_SCOPES = "https://www.googleapis.com/auth/adwords"
GOOGLE_ADS_REDIRECT_URI = os.getenv(
    "GOOGLE_ADS_REDIRECT_URI",
    "https://app.alpmark.ai/integrations/google-ads/callback",
)
OAUTH_TOKEN_LIFETIME_DAYS = 30
OAUTH_PREFERRED_SOURCES = {"shopify", "meta", "google_ads"}
API_KEY_SUPPORTED_SOURCES = {"klaviyo", "amazon_ads", "tiktok_ads", "custom"}
FRESHNESS_HIGH_THRESHOLD = timedelta(hours=1)
FRESHNESS_MEDIUM_THRESHOLD = timedelta(hours=6)
MANUAL_RESYNC_TASKS = {
    "shopify": [
        "worker.app.tasks.run_shopify_order_sync_schedule",
        "worker.app.tasks.run_shopify_inventory_sync_schedule",
    ]
}
SYNC_METRICS_LOOKBACK = timedelta(days=7)
SYNC_SUCCESS_ACTIONS_BY_SOURCE = {
    "shopify": (
        "connector.shopify_orders_synced",
        "connector.shopify_inventory_synced",
    ),
    "meta": ("connector.meta_spend_synced",),
    "google_ads": ("connector.google_ads_spend_synced",),
}
AuthDep = Annotated[AuthContext, Depends(get_current_auth)]
SuperAdminDep = Annotated[AuthContext, Depends(require_platform_roles("super_admin"))]

# Permission-based dependencies for tenant access
AdminMembersDep = Annotated[
    AuthContext, Depends(require_permissions("admin.members"))
]
AdminRolesDep = Annotated[
    AuthContext, Depends(require_permissions("admin.roles"))
]
AdminBillingDep = Annotated[
    AuthContext, Depends(require_permissions("admin.billing"))
]
AdminIntegrationsDep = Annotated[
    AuthContext, Depends(require_permissions("admin.integrations"))
]
AdminSettingsDep = Annotated[
    AuthContext, Depends(require_permissions("admin.settings"))
]
AdminAuditDep = Annotated[
    AuthContext, Depends(require_permissions("admin.audit"))
]

ExecutiveViewDep = Annotated[
    AuthContext, Depends(require_permissions("executive.view"))
]
ExecutiveTargetsDep = Annotated[
    AuthContext, Depends(require_permissions("executive.targets"))
]
ExecutiveApproveDep = Annotated[
    AuthContext, Depends(require_permissions("executive.approve"))
]
ExecutiveSimulateDep = Annotated[
    AuthContext, Depends(require_permissions("executive.simulate"))
]

FinanceViewDep = Annotated[
    AuthContext, Depends(require_permissions("finance.view"))
]
FinanceEditCostsDep = Annotated[
    AuthContext, Depends(require_permissions("finance.edit_costs"))
]
FinanceAnalyzeDep = Annotated[
    AuthContext, Depends(require_permissions("finance.analyze"))
]

OperationsViewDep = Annotated[
    AuthContext, Depends(require_permissions("operations.view"))
]
OperationsInventoryDep = Annotated[
    AuthContext, Depends(require_permissions("operations.inventory"))
]
OperationsAnalyzeDep = Annotated[
    AuthContext, Depends(require_permissions("operations.analyze"))
]

GrowthViewDep = Annotated[
    AuthContext, Depends(require_permissions("growth.view"))
]
GrowthAnalyzeDep = Annotated[
    AuthContext, Depends(require_permissions("growth.analyze"))
]
GrowthSimulateDep = Annotated[
    AuthContext, Depends(require_permissions("growth.simulate"))
]

RetentionViewDep = Annotated[
    AuthContext, Depends(require_permissions("retention.view"))
]
RetentionAnalyzeDep = Annotated[
    AuthContext, Depends(require_permissions("retention.analyze"))
]
RetentionSimulateDep = Annotated[
    AuthContext, Depends(require_permissions("retention.simulate"))
]

IntelRecommendationsViewDep = Annotated[
    AuthContext, Depends(require_permissions("intel.recommendations.view"))
]
IntelRecommendationsReviewDep = Annotated[
    AuthContext, Depends(require_permissions("intel.recommendations.review"))
]
IntelSimulationsRunDep = Annotated[
    AuthContext, Depends(require_permissions("intel.simulations.run"))
]
IntelSimulationsViewDep = Annotated[
    AuthContext, Depends(require_permissions("intel.simulations.view"))
]
IntelInsightsViewDep = Annotated[
    AuthContext, Depends(require_permissions("intel.insights.view"))
]
IntelAlertsManageDep = Annotated[
    AuthContext, Depends(require_permissions("intel.alerts.manage"))
]

# Legacy aliases removed - all endpoints now use granular permission-based deps


def _generate_unique_invitation_token(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(24)
        existing_token = db.scalar(
            select(UserInvitation).where(UserInvitation.token == token)
        )
        if existing_token is None:
            return token


def _get_tenant_or_404(db: Session, tenant_id: uuid.UUID) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )
    return tenant


def _get_tenant_membership_with_user_or_404(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[TenantMembership, User]:
    result = db.execute(
        select(TenantMembership, User)
        .join(User, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    ).first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found.",
        )
    membership, user = result
    return membership, user


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def _get_privacy_request_or_404(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
) -> PrivacyRequest:
    privacy_request = db.scalar(
        select(PrivacyRequest).where(
            PrivacyRequest.tenant_id == tenant_id,
            PrivacyRequest.id == request_id,
        )
    )
    if privacy_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Privacy request not found.",
        )
    return privacy_request


def _get_connector_for_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source: str,
) -> ConnectorIntegration | None:
    return db.scalar(
        select(ConnectorIntegration).where(
            ConnectorIntegration.tenant_id == tenant_id,
            ConnectorIntegration.source == source,
        )
    )


def _build_shopify_auth_url(*, shop_domain: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": SHOPIFY_CLIENT_ID,
            "scope": SHOPIFY_OAUTH_SCOPES,
            "redirect_uri": SHOPIFY_REDIRECT_URI,
            "state": state,
        }
    )
    return f"https://{shop_domain}/admin/oauth/authorize?{query}"


def _build_meta_auth_url(*, state: str) -> str:
    query = urlencode(
        {
            "client_id": META_CLIENT_ID,
            "redirect_uri": META_REDIRECT_URI,
            "scope": META_OAUTH_SCOPES,
            "response_type": "code",
            "state": state,
        }
    )
    return f"https://www.facebook.com/v18.0/dialog/oauth?{query}"


def _build_google_ads_auth_url(*, state: str) -> str:
    query = urlencode(
        {
            "client_id": GOOGLE_ADS_CLIENT_ID,
            "redirect_uri": GOOGLE_ADS_REDIRECT_URI,
            "scope": GOOGLE_ADS_OAUTH_SCOPES,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def _validate_api_key_or_422(raw_api_key: str) -> str:
    normalized_key = raw_api_key.strip()
    if len(normalized_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key is invalid.",
        )
    if any(character.isspace() for character in normalized_key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key is invalid.",
        )
    return normalized_key


def _upsert_connector_vault_secret(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connector: ConnectorIntegration,
    secret_value: str,
    secret_type: str,
) -> ConnectorCredentialVault:
    vault_entry = db.scalar(
        select(ConnectorCredentialVault).where(
            ConnectorCredentialVault.connector_id == connector.id
        )
    )
    encrypted_secret = encrypt_connector_secret(secret_value)
    secret_fingerprint = get_secret_fingerprint(secret_value)
    if vault_entry is None:
        vault_entry = ConnectorCredentialVault(
            tenant_id=tenant_id,
            connector_id=connector.id,
            secret_type=secret_type,
            secret_ciphertext=encrypted_secret,
            fingerprint=secret_fingerprint,
            key_version=VAULT_KEY_VERSION,
        )
        db.add(vault_entry)
        db.flush()
        return vault_entry

    vault_entry.secret_type = secret_type
    vault_entry.secret_ciphertext = encrypted_secret
    vault_entry.fingerprint = secret_fingerprint
    vault_entry.key_version = VAULT_KEY_VERSION
    db.flush()
    return vault_entry


def _queue_manual_resync_tasks(*, source: str) -> list[str]:
    tasks = MANUAL_RESYNC_TASKS.get(source)
    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manual resync is not supported for this source.",
        )

    celery_module = import_module("worker.app.celery_app")
    celery_app = celery_module.celery_app
    for task_name in tasks:
        celery_app.send_task(task_name)
    return tasks


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _derive_sync_progress(connector: ConnectorIntegration) -> str:
    if connector.status != "connected":
        return "not_connected"
    if connector.error_message is not None:
        return "error"

    requested_at = connector.last_sync_requested_at
    if requested_at is None:
        return "idle"

    synced_at = connector.last_synced_at
    if synced_at is None:
        return "sync_queued"

    return "healthy" if _to_utc(synced_at) >= _to_utc(requested_at) else "sync_queued"


def _derive_freshness_label(
    connector: ConnectorIntegration,
    *,
    now: datetime | None = None,
) -> str:
    synced_at = connector.last_synced_at
    if synced_at is None:
        return "low"

    current_time = _to_utc(now or datetime.now(UTC))
    synced_time = _to_utc(synced_at)
    age = max(current_time - synced_time, timedelta(0))

    if age <= FRESHNESS_HIGH_THRESHOLD:
        return "high"
    if age <= FRESHNESS_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _derive_stale_data_gate(
    connector: ConnectorIntegration,
    *,
    now: datetime | None = None,
) -> tuple[str, str | None]:
    if connector.status != "connected":
        return "hold", "Connector is not connected."

    if connector.error_message is not None:
        return "hold", "Connector has an active sync error."

    freshness_label = _derive_freshness_label(connector, now=now)
    if freshness_label != "low":
        return "none", None

    if connector.last_synced_at is None:
        return "hold", "No successful sync found yet."

    return "warning", "Data is stale and should be reviewed before decisions."


def _compute_connector_health_status(
    connector: ConnectorIntegration,
    *,
    now: datetime | None = None,
) -> str:
    """Compute overall connector health status (E3).

    Returns:
        "healthy": Connected, syncing well, data fresh, no errors
        "degraded": Connected but queued/stale data/minor issues
        "critical": Disconnected, errors, or very stale data
        "unknown": Cannot determine status
    """
    sync_progress = _derive_sync_progress(connector)
    freshness_label = _derive_freshness_label(connector, now=now)

    # Critical: disconnected, errors, or very stale data
    if connector.status != "connected":
        return "critical"
    if sync_progress == "error":
        return "critical"
    if connector.error_message is not None:
        return "critical"
    if freshness_label == "low":
        return "critical"

    # Degraded: sync queued or medium freshness
    if sync_progress == "sync_queued":
        return "degraded"
    if freshness_label == "medium":
        return "degraded"

    # Healthy: connected, healthy sync, high freshness
    if sync_progress in ("healthy", "idle") and freshness_label == "high":
        return "healthy"

    return "unknown"


def _derive_sync_metrics(
    db: Session,
    *,
    connector: ConnectorIntegration,
    now: datetime | None = None,
) -> tuple[int, int, int, float, float]:
    current_time = _to_utc(now or datetime.now(UTC))
    window_start = current_time - SYNC_METRICS_LOOKBACK
    connector_id = str(connector.id)
    success_actions = SYNC_SUCCESS_ACTIONS_BY_SOURCE.get(connector.source, ())

    success_count = 0
    if success_actions:
        success_count_raw = db.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.tenant_id == connector.tenant_id,
                AuditEvent.entity_type == "connector",
                AuditEvent.entity_id == connector_id,
                AuditEvent.created_at >= window_start,
                AuditEvent.action.in_(success_actions),
            )
        )
        success_count = int(success_count_raw or 0)

    failure_count_raw = db.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.tenant_id == connector.tenant_id,
            AuditEvent.entity_type == "connector",
            AuditEvent.entity_id == connector_id,
            AuditEvent.created_at >= window_start,
            AuditEvent.action == "alert.connector_sync_failure_created",
        )
    )
    failure_count = int(failure_count_raw or 0)

    total_count = success_count + failure_count
    if total_count == 0:
        return 0, 0, 0, 0.0, 0.0

    uptime = round((success_count / total_count) * 100, 2)
    failure_rate = round((failure_count / total_count) * 100, 2)
    return total_count, success_count, failure_count, uptime, failure_rate


def _build_billing_seat_response(db: Session, tenant: Tenant) -> BillingSeatResponse:
    seats_used = db.scalar(
        select(func.count(TenantMembership.id))
        .join(User, TenantMembership.user_id == User.id)
        .where(TenantMembership.tenant_id == tenant.id, User.is_active.is_(True))
    )
    used = seats_used or 0
    available = max(tenant.seat_limit - used, 0)

    return BillingSeatResponse(
        tenant_id=tenant.id,
        billing_plan=tenant.billing_plan,
        billing_cycle=tenant.billing_cycle,
        billing_status=tenant.billing_status,
        seat_limit=tenant.seat_limit,
        seats_used=used,
        seats_available=available,
        can_invite=used < tenant.seat_limit,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/subscription-plans", response_model=list[SubscriptionPlanResponse])
def list_subscription_plans(
    db: Session = Depends(get_db),  # noqa: B008
) -> list[SubscriptionPlanResponse]:
    """List all active subscription plans (public endpoint)."""
    plans = db.scalars(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order)
    ).all()

    return [
        SubscriptionPlanResponse(
            id=plan.id,
            slug=plan.slug,
            name=plan.name,
            description=plan.description,
            price_monthly=plan.price_monthly,
            price_annual=plan.price_annual,
            features=plan.features if isinstance(plan.features, list) else [],
            limits=SubscriptionPlanLimits(**plan.limits),
            is_active=plan.is_active,
            sort_order=plan.sort_order,
        )
        for plan in plans
    ]


@app.get("/subscription-plans/{slug}", response_model=SubscriptionPlanResponse)
def get_subscription_plan(
    slug: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> SubscriptionPlanResponse:
    """Get subscription plan by slug (public endpoint)."""
    plan = db.scalar(
        select(SubscriptionPlan)
        .where(
            SubscriptionPlan.slug == slug,
            SubscriptionPlan.is_active.is_(True),
        )
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    return SubscriptionPlanResponse(
        id=plan.id,
        slug=plan.slug,
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_annual=plan.price_annual,
        features=plan.features if isinstance(plan.features, list) else [],
        limits=SubscriptionPlanLimits(**plan.limits),
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


@app.post(
    "/auth/bootstrap/super-admin",
    response_model=BootstrapSuperAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_super_admin(
    request_body: BootstrapSuperAdminRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> BootstrapSuperAdminResponse:
    """
    Bootstrap the first Super Admin user.
    
    This endpoint should ONLY be used for initial platform setup when the database
    is empty. It creates the first Super Admin user who can then create tenants
    and other users through the platform UI.
    
    Security:
    - Only works when there are ZERO users in the database
    - Returns 403 Forbidden if any user already exists
    - Creates user with is_platform_admin=true and tenant_id=null
    
    Use case:
    1. Fresh database (after migrations)
    2. Call this endpoint once to create Super Admin
    3. Super Admin logs in and creates tenants through UI
    4. Endpoint becomes permanently disabled
    """
    # Check if any user exists
    existing_user_count = db.scalar(select(func.count()).select_from(User))
    
    if existing_user_count and existing_user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Super Admin already exists. Bootstrap endpoint is disabled. "
                "Please use the login page to access your account."
            ),
        )
    
    # Create the first Super Admin user
    super_admin = User(
        id=uuid.uuid4(),
        email=request_body.email,
        full_name=request_body.full_name,
        password_hash=hash_password(request_body.password),
        is_platform_admin=True,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    
    db.add(super_admin)
    db.commit()
    db.refresh(super_admin)
    
    # Note: No audit event for bootstrap since there's no tenant context yet
    # This is a one-time platform initialization operation
    
    return BootstrapSuperAdminResponse(
        id=super_admin.id,
        email=super_admin.email,
        full_name=super_admin.full_name,
        is_platform_admin=super_admin.is_platform_admin,
        tenant_id=None,  # Super Admin is not tied to any tenant
        created_at=super_admin.created_at,
    )


@app.post("/auth/login", response_model=LoginResponse)
def login(
    request_body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> LoginResponse:
    """Authenticate user and return JWT token."""
    # Look up user by email
    user = db.scalar(select(User).where(User.email == request_body.email))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    
    # Verify password
    if user.password_hash is None or not verify_password(
        request_body.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not active. Please contact support.",
        )
    
    # Generate unique session identifier (jti)
    jti = str(uuid.uuid4())
    
    # Set platform_role based on is_platform_admin
    platform_role = "super_admin" if user.is_platform_admin else None
    
    # Create JWT payload
    jwt_expiry = datetime.now(UTC) + timedelta(hours=24)
    payload = {
        "sub": request_body.email,
        "email": request_body.email,
        "platform_role": platform_role,
        "jti": jti,
        "iat": datetime.now(UTC),
        "exp": jwt_expiry,
    }
    
    # Create session record
    user_session = UserSession(
        user_id=user.id,
        jti=jti,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=jwt_expiry,
    )
    db.add(user_session)
    db.commit()
    
    token = jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)
    return LoginResponse(access_token=token, token_type="bearer")


@app.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ForgotPasswordResponse:
    """Initiate password reset flow by generating reset token and sending email."""
    # Look up user by email
    user = db.scalar(select(User).where(User.email == request.email))
    
    # Always return success to prevent email enumeration attacks
    if user is None:
        return ForgotPasswordResponse(
            message=(
                "If the email exists in our system, "
                "a password reset link has been sent."
            )
        )
    
    # Generate secure random token
    reset_token = secrets.token_urlsafe(32)
    
    # Create password reset token record
    password_reset = PasswordResetToken(
        email=user.email,
        token=reset_token,
    )
    db.add(password_reset)
    db.commit()
    
    # TODO: Send email with reset link containing token
    # In production: email_service.send_password_reset_email(user.email, reset_token)
    # For now, we just create the token record
    
    return ForgotPasswordResponse(
        message=(
            "If the email exists in our system, "
            "a password reset link has been sent."
        )
    )


@app.post("/auth/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ResetPasswordResponse:
    """Reset password using valid reset token."""
    # Look up reset token
    reset_token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token == request.token)
    )
    
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired reset token.",
        )
    
    # Check if token has already been used
    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This reset token has already been used.",
        )
    
    # Check if token has expired
    now = datetime.now(UTC)
    token_expiry = reset_token.expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=UTC)
    
    if token_expiry < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This reset token has expired.",
        )
    
    # Look up user by email from token
    user = db.scalar(select(User).where(User.email == reset_token.email))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    # Update user password
    user.password_hash = hash_password(request.new_password)
    
    # Mark token as used
    reset_token.used_at = now
    
    db.commit()
    
    return ResetPasswordResponse(
        message=(
            "Password has been successfully reset. "
            "You can now log in with your new password."
        )
    )


@app.get("/me/sessions", response_model=SessionListResponse)
def get_user_sessions(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SessionListResponse:
    """Get all active sessions for the current user."""
    # Look up user by email
    user = db.scalar(select(User).where(User.email == auth.email))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    # Get all non-revoked sessions for the user
    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .where(UserSession.revoked_at.is_(None))
        .order_by(UserSession.created_at.desc())
    ).all()
    
    # Get current jti from auth context
    current_jti = auth.jti
    
    session_responses = [
        UserSessionResponse(
            id=session.id,
            jti=session.jti,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_seen_at=session.last_seen_at,
            expires_at=session.expires_at,
            is_current=(session.jti == current_jti),
        )
        for session in sessions
    ]
    
    return SessionListResponse(sessions=session_responses)


@app.post("/auth/logout", response_model=LogoutResponse)
def logout(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> LogoutResponse:
    """Logout current session by revoking the JWT token."""
    if auth.jti is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session found.",
        )
    
    # Revoke the session with matching jti
    session = db.scalar(
        select(UserSession).where(UserSession.jti == auth.jti)
    )
    
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    
    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already revoked.",
        )
    
    session.revoked_at = datetime.now(UTC)
    db.commit()
    
    return LogoutResponse(message="Successfully logged out.")


@app.post("/auth/logout-all", response_model=LogoutResponse)
def logout_all(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> LogoutResponse:
    """Logout all sessions by revoking all active JWT tokens for the user."""
    user = db.scalar(select(User).where(User.email == auth.email))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    
    # Revoke all active sessions for this user
    now = datetime.now(UTC)
    sessions = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .where(UserSession.revoked_at.is_(None))
    ).all()
    
    for session in sessions:
        session.revoked_at = now
    
    db.commit()
    
    return LogoutResponse(
        message=f"Successfully logged out from {len(sessions)} session(s)."
    )


@app.get("/users/me", response_model=UserResponse)
def get_current_user(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> UserResponse:
    """Get current authenticated user's info."""
    # Look up the user's tenant membership from database
    try:
        user_id = db.scalar(select(User.id).where(User.email == auth.email))
        if user_id:
            membership = db.scalar(
                select(TenantMembership)
                .where(TenantMembership.user_id == user_id)
                .order_by(TenantMembership.created_at)
                .limit(1)
            )
            tenant_id = str(membership.tenant_id) if membership else None
        else:
            tenant_id = None
    except Exception:
        # If database lookup fails, tenant_id remains None
        tenant_id = None

    return UserResponse(
        email=auth.email,
        platform_role=auth.platform_role,
        tenant_id=tenant_id,
    )


@app.patch("/users/me/password", response_model=ChangePasswordResponse)
def change_user_password(
    request: ChangePasswordRequest,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ChangePasswordResponse:
    """Change the current authenticated user's password.

    Args:
        request: Password change request with current and new passwords
        auth: Authenticated user context
        db: Database session

    Returns:
        Success message

    Raises:
        400: If current password is incorrect or new password is invalid
        404: If user not found

    """
    # Look up the user
    user = db.scalar(select(User).where(User.email == auth.email))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if user.password_hash is None or not verify_password(
        request.current_password,
        user.password_hash,
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password (minimum 8 characters - already enforced by Pydantic)
    # Additional validation can be added here if needed

    # Hash and save new password
    user.password_hash = hash_password(request.new_password)
    db.commit()

    return ChangePasswordResponse(message="Password updated successfully")


@app.get("/me/navigation", response_model=NavigationMenuResponse)
def get_navigation_menu(
    tenant_id: uuid.UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NavigationMenuResponse:
    """Get persona-specific navigation menu structure.

    E8: Returns menu items based on user's role, permissions, and tenant
    feature flags. Frontend can render the navigation directly without
    additional permission checks.

    Args:
        tenant_id: Tenant identifier (query parameter)
        auth: Authenticated user context
        db: Database session

    Returns:
        NavigationMenuResponse with filtered menu items and badge counts

    Raises:
        403: If user does not have access to this tenant
        404: If tenant not found
    """
    from backend.app.feature_enforcement import check_tenant_feature_access

    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Get user and membership
    user = db.scalar(select(User).where(User.email == auth.email.strip().lower()))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    role = membership.role.strip().lower()

    # Check feature flags
    has_simulations = check_tenant_feature_access(tenant_id, "simulations", db)
    has_custom_segments = check_tenant_feature_access(
        tenant_id, "custom_segments", db
    )

    # Count unread alerts for badge
    # For now, count recent AlertEventLog "created" events without acknowledgements
    from backend.app.db.models import AlertEventLog

    unread_alerts = db.scalar(
        select(func.count(AlertEventLog.id)).where(
            AlertEventLog.tenant_id == tenant_id,
            AlertEventLog.event_type == "created",
        )
    ) or 0

    # Count pending recommendations for badge
    from backend.app.recommendations.lifecycle import RecommendationStatus

    pending_recommendations = db.scalar(
        select(func.count(Recommendation.id)).where(
            Recommendation.tenant_id == tenant_id,
            Recommendation.status == RecommendationStatus.NEW.value,
        )
    ) or 0

    # Build menu based on role
    menu_items: list[NavigationMenuItem] = []

    # Intelligence personas (non-admin roles)
    if role != "brand_admin":
        # Dashboard (all intelligence personas)
        menu_items.append(
            NavigationMenuItem(
                section="intelligence",
                label="Dashboard",
                path="/dashboard",
                icon="home",
                enabled=True,
                badge_count=None,
                order=1,
            )
        )

        # Recommendations (all intelligence personas)
        menu_items.append(
            NavigationMenuItem(
                section="intelligence",
                label="Recommendations",
                path="/recommendations",
                icon="lightbulb",
                enabled=True,
                badge_count=(
                    pending_recommendations if pending_recommendations > 0 else None
                ),
                order=2,
            )
        )

        # Simulations (if feature enabled)
        if has_simulations:
            menu_items.append(
                NavigationMenuItem(
                    section="intelligence",
                    label="Simulations",
                    path="/simulations",
                    icon="chart",
                    enabled=True,
                    badge_count=None,
                    order=3,
                )
            )

        # Alerts (all intelligence personas)
        menu_items.append(
            NavigationMenuItem(
                section="intelligence",
                label="Alerts",
                path="/alerts",
                icon="bell",
                enabled=True,
                badge_count=unread_alerts if unread_alerts > 0 else None,
                order=4,
            )
        )

        # Analysis (saved views, annotations)
        menu_items.append(
            NavigationMenuItem(
                section="intelligence",
                label="Analysis",
                path="/analysis",
                icon="analytics",
                enabled=True,
                badge_count=None,
                order=5,
            )
        )

        # Segments (if custom segments feature enabled)
        if has_custom_segments and role in [
            "retention_crm_manager",
            "growth_performance_manager",
            "executive_owner",
        ]:
            menu_items.append(
                NavigationMenuItem(
                    section="intelligence",
                    label="Segments",
                    path="/segments",
                    icon="users",
                    enabled=True,
                    badge_count=None,
                    order=6,
                )
            )

    # Brand Admin section
    if role == "brand_admin" or role == "executive_owner":
        menu_items.append(
            NavigationMenuItem(
                section="admin",
                label="Integrations",
                path="/integrations",
                icon="link",
                enabled=True,
                badge_count=None,
                order=10,
            )
        )

        menu_items.append(
            NavigationMenuItem(
                section="admin",
                label="Team",
                path="/team",
                icon="people",
                enabled=True,
                badge_count=None,
                order=11,
            )
        )

        menu_items.append(
            NavigationMenuItem(
                section="admin",
                label="Billing",
                path="/billing",
                icon="payment",
                enabled=True,
                badge_count=None,
                order=12,
            )
        )

        menu_items.append(
            NavigationMenuItem(
                section="admin",
                label="Settings",
                path="/settings",
                icon="settings",
                enabled=True,
                badge_count=None,
                order=13,
            )
        )

    return NavigationMenuResponse(
        user_role=role,
        tenant_id=str(tenant_id),
        menu_items=menu_items,
    )


# ---------------------------------------------------------------------------
# Rule threshold defaults — seeded once at tenant creation
# ---------------------------------------------------------------------------

class _RuleDefault(TypedDict):
    rule_id: str
    threshold_value: float
    threshold_unit: str
    description: str


_RULE_THRESHOLD_DEFAULTS: list[_RuleDefault] = [
    {
        "rule_id": "ACQ-001",
        "threshold_value": 1.5,
        "threshold_unit": "ratio",
        "description": (
            "Blended ROAS floor — alert when ROAS falls below this value."
        ),
    },
    {
        "rule_id": "EXC-001",
        "threshold_value": 30.0,
        "threshold_unit": "pct",
        "description": (
            "Contribution margin floor — alert when margin falls below "
            "this percentage."
        ),
    },
    {
        "rule_id": "INV-001",
        "threshold_value": 1.0,
        "threshold_unit": "count",
        "description": (
            "Stockout-risk SKU count — alert when this many SKUs are at "
            "stockout risk."
        ),
    },
    {
        "rule_id": "MRG-001",
        "threshold_value": 1.0,
        "threshold_unit": "count",
        "description": (
            "Margin drift alert count — alert when this many "
            "channel/category thresholds are breached."
        ),
    },
    {
        "rule_id": "OPS-001",
        "threshold_value": OPS_USD_DEFAULT,
        "threshold_unit": "USD",  # overridden with tenant.base_currency at seed time
        "description": (
            "Stockout revenue-at-risk floor — alert when any SKU's "
            "estimated lost revenue exceeds this amount (in tenant "
            "base currency)."
        ),
    },
    {
        "rule_id": "RET-001",
        "threshold_value": 20.0,
        "threshold_unit": "pct",
        "description": (
            "Repeat purchase rate floor — alert when repeat rate falls "
            "below this percentage."
        ),
    },
]


def _seed_rule_thresholds(
    db: Session, tenant_id: uuid.UUID, base_currency: str = "USD"
) -> None:
    """Insert default TenantRuleThreshold rows for a newly created tenant.

    The OPS-001 threshold is a revenue amount, so its unit is set to the
    tenant's ISO 4217 base_currency (e.g. "USD", "GBP") rather than the
    generic string "currency".
    """
    for row in _RULE_THRESHOLD_DEFAULTS:
        scale = (
            OPS_CURRENCY_SCALE_VS_USD.get(base_currency, 1.0)
            if row["rule_id"] == "OPS-001"
            else 1.0
        )
        unit = (
            base_currency
            if row["rule_id"] == "OPS-001"
            else row["threshold_unit"]
        )
        db.add(
            TenantRuleThreshold(
                tenant_id=tenant_id,
                rule_id=row["rule_id"],
                threshold_value=round(row["threshold_value"] * scale, 2),
                threshold_unit=unit,
                description=row["description"],
            )
        )


@app.post(
    "/tenants",
    response_model=TenantCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    payload: TenantCreateRequest,
    auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> Tenant:
    existing_tenant = db.scalar(select(Tenant).where(Tenant.slug == payload.slug))
    if existing_tenant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this slug already exists.",
        )

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        base_currency=payload.base_currency,
    )
    db.add(tenant)
    db.flush()

    # Seed system roles for the new tenant (mimics migration 0058)
    system_role_names = [
        "brand_admin",
        "executive_owner",
        "growth_performance_manager",
        "retention_crm_manager",
        "finance_controller",
        "operations_inventory_manager",
    ]
    roles_map = {}
    for role_name in system_role_names:
        permissions = get_system_role_permissions(role_name)
        role = Role(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=role_name,
            permissions=permissions,
            is_system=True,
        )
        db.add(role)
        roles_map[role_name] = role
    db.flush()

    creator_email = auth.email.strip().lower()
    creator = db.scalar(select(User).where(User.email == creator_email))
    if creator is None:
        creator = User(
            email=creator_email,
            full_name=creator_email,
            is_active=True,
        )
        db.add(creator)
        db.flush()
    else:
        creator.is_active = True

    # Create membership with role_id FK to brand_admin role
    brand_admin_role = roles_map["brand_admin"]
    db.add(
        TenantMembership(
            tenant_id=tenant.id,
            user_id=creator.id,
            role="brand_admin",
            role_id=brand_admin_role.id,
        )
    )
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="tenant.created",
        entity_type="tenant",
        entity_id=str(tenant.id),
        details={"slug": tenant.slug},
        actor_user_id=creator.id,
    )
    _seed_rule_thresholds(db, tenant.id, tenant.base_currency)
    db.commit()
    db.refresh(tenant)
    return tenant


@app.post(
    "/tenants/{tenant_id}/invitations",
    response_model=UserInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_user(
    tenant_id: uuid.UUID,
    payload: UserInviteRequest,
    _auth: AdminMembersDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> UserInviteResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    normalized_email = payload.email.strip().lower()
    now = datetime.now(UTC)

    existing_active_member = db.scalar(
        select(TenantMembership)
        .join(User, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == tenant.id,
            func.lower(User.email) == normalized_email,
            User.is_active.is_(True),
        )
    )
    if existing_active_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already an active member of this tenant.",
        )

    pending_invitation = db.scalar(
        select(UserInvitation).where(
            UserInvitation.tenant_id == tenant.id,
            func.lower(UserInvitation.email) == normalized_email,
            UserInvitation.accepted_at.is_(None),
            UserInvitation.expires_at > now,
        )
    )
    if pending_invitation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email.",
        )

    invitation = UserInvitation(
        tenant_id=tenant.id,
        email=normalized_email,
        role=payload.role,
        token=_generate_unique_invitation_token(db),
    )
    db.add(invitation)
    db.flush()
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="user.invited",
        entity_type="invitation",
        entity_id=str(invitation.id),
        details={"email": invitation.email, "role": invitation.role},
    )
    db.commit()
    db.refresh(invitation)

    return UserInviteResponse(
        invitation_id=invitation.id,
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        expires_at=invitation.expires_at,
    )


@app.post("/accounts/activate", response_model=AccountActivationResponse)
def activate_account(
    payload: AccountActivationRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> AccountActivationResponse:
    invitation = db.scalar(
        select(UserInvitation).where(UserInvitation.token == payload.token)
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activation token not found.",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Activation token has already been used.",
        )

    now = datetime.now(UTC)
    invitation_expiry = invitation.expires_at
    if invitation_expiry.tzinfo is None:
        invitation_expiry = invitation_expiry.replace(tzinfo=UTC)

    if invitation_expiry < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Activation token has expired.",
        )

    user = db.scalar(select(User).where(User.email == invitation.email))
    if user is None:
        user = User(
            email=invitation.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = payload.full_name
        user.password_hash = hash_password(payload.password)
        user.is_active = True

    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == invitation.tenant_id,
            TenantMembership.user_id == user.id,
        )
    )
    
    # Look up the role from the roles table (migration 0058)
    role_obj = db.scalar(
        select(Role).where(
            Role.tenant_id == invitation.tenant_id,
            Role.name == invitation.role,
            Role.is_system,
        )
    )
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System role '{invitation.role}' not found for tenant.",
        )
    
    if membership is None:
        membership = TenantMembership(
            tenant_id=invitation.tenant_id,
            user_id=user.id,
            role=invitation.role,
            role_id=role_obj.id,
        )
        db.add(membership)
    else:
        membership.role = invitation.role
        membership.role_id = role_obj.id

    invitation.accepted_at = now
    write_audit_event(
        db,
        tenant_id=invitation.tenant_id,
        action="account.activated",
        entity_type="user",
        entity_id=str(user.id),
        details={"email": user.email, "role": invitation.role},
        actor_user_id=user.id,
    )
    db.commit()

    return AccountActivationResponse(
        user_id=user.id,
        tenant_id=invitation.tenant_id,
        email=user.email,
        role=invitation.role,
        activated_at=now,
    )


@app.get(
    "/tenants/{tenant_id}/onboarding-checklist",
    response_model=OnboardingChecklistResponse,
)
def get_onboarding_checklist(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> OnboardingChecklistResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    invite_count = db.scalar(
        select(func.count(UserInvitation.id)).where(
            UserInvitation.tenant_id == tenant.id
        )
    )
    accepted_invite_count = db.scalar(
        select(func.count(UserInvitation.id)).where(
            UserInvitation.tenant_id == tenant.id,
            UserInvitation.accepted_at.is_not(None),
        )
    )
    active_member_count = db.scalar(
        select(func.count(TenantMembership.id))
        .join(User, TenantMembership.user_id == User.id)
        .where(TenantMembership.tenant_id == tenant.id, User.is_active.is_(True))
    )

    items = [
        OnboardingChecklistItem(
            key="tenant_created",
            label="Create tenant workspace",
            is_complete=True,
        ),
        OnboardingChecklistItem(
            key="invite_sent",
            label="Send first team invitation",
            is_complete=(invite_count or 0) > 0,
        ),
        OnboardingChecklistItem(
            key="account_activated",
            label="Activate at least one account",
            is_complete=(active_member_count or 0) > 0,
        ),
        OnboardingChecklistItem(
            key="invite_accepted",
            label="Have at least one accepted invitation",
            is_complete=(accepted_invite_count or 0) > 0,
        ),
    ]

    completed_steps = sum(1 for item in items if item.is_complete)
    total_steps = len(items)
    completion_percent = int((completed_steps / total_steps) * 100)

    return OnboardingChecklistResponse(
        tenant_id=tenant.id,
        completed_steps=completed_steps,
        total_steps=total_steps,
        completion_percent=completion_percent,
        items=items,
    )


@app.patch(
    "/tenants/{tenant_id}/members/{user_id}/role",
    response_model=MembershipResponse,
)
def update_member_role(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MembershipRoleUpdateRequest,
    _auth: AdminRolesDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MembershipResponse:
    normalized_role = payload.role.strip().lower()
    if normalized_role not in ALLOWED_MEMBER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role is not supported.",
        )

    membership, user = _get_tenant_membership_with_user_or_404(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    membership.role = normalized_role
    write_audit_event(
        db,
        tenant_id=membership.tenant_id,
        action="member.role_updated",
        entity_type="membership",
        entity_id=str(membership.id),
        details={"new_role": membership.role, "email": user.email},
        actor_user_id=user.id,
    )
    db.commit()

    return MembershipResponse(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        email=user.email,
        role=membership.role,
        is_active=user.is_active,
    )


@app.patch(
    "/tenants/{tenant_id}/members/{user_id}/deactivate",
    response_model=MembershipResponse,
)
def deactivate_member(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    _auth: AdminMembersDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MembershipResponse:
    membership, user = _get_tenant_membership_with_user_or_404(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    user.is_active = False
    write_audit_event(
        db,
        tenant_id=membership.tenant_id,
        action="member.deactivated",
        entity_type="user",
        entity_id=str(user.id),
        details={"email": user.email, "role": membership.role},
        actor_user_id=user.id,
    )
    db.commit()

    return MembershipResponse(
        tenant_id=membership.tenant_id,
        user_id=membership.user_id,
        email=user.email,
        role=membership.role,
        is_active=user.is_active,
    )


@app.get("/tenants/{tenant_id}/billing-seats", response_model=BillingSeatResponse)
def get_billing_and_seats(
    tenant_id: uuid.UUID,
    _auth: AdminBillingDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> BillingSeatResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    return _build_billing_seat_response(db, tenant)


@app.patch("/tenants/{tenant_id}/billing-seats", response_model=BillingSeatResponse)
def update_billing_and_seats(
    tenant_id: uuid.UUID,
    payload: BillingSeatUpdateRequest,
    _auth: AdminBillingDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> BillingSeatResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    if payload.billing_plan is not None:
        tenant.billing_plan = payload.billing_plan.strip().lower()

    if payload.billing_cycle is not None:
        normalized_cycle = payload.billing_cycle.strip().lower()
        if normalized_cycle not in ALLOWED_BILLING_CYCLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Billing cycle is not supported.",
            )
        tenant.billing_cycle = normalized_cycle

    if payload.billing_status is not None:
        normalized_status = payload.billing_status.strip().lower()
        if normalized_status not in ALLOWED_BILLING_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Billing status is not supported.",
            )
        tenant.billing_status = normalized_status

    if payload.seat_limit is not None:
        active_members = db.scalar(
            select(func.count(TenantMembership.id))
            .join(User, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == tenant.id, User.is_active.is_(True))
        )
        used = active_members or 0
        if payload.seat_limit < used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seat limit cannot be lower than current active seats.",
            )
        tenant.seat_limit = payload.seat_limit

    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="billing.updated",
        entity_type="tenant",
        entity_id=str(tenant.id),
        details={
            "billing_plan": tenant.billing_plan,
            "billing_cycle": tenant.billing_cycle,
            "billing_status": tenant.billing_status,
            "seat_limit": tenant.seat_limit,
        },
    )
    db.commit()
    db.refresh(tenant)
    return _build_billing_seat_response(db, tenant)


# --------------------------------------------------------------------------------
# Super-Admin: Subscription Plan Management
# --------------------------------------------------------------------------------


@app.post("/admin/subscription-plans", response_model=SubscriptionPlanResponse)
def create_subscription_plan(
    payload: SubscriptionPlanCreateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SubscriptionPlanResponse:
    """Create new subscription plan (super-admin only)."""
    # Check if slug already exists
    existing = db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.slug == payload.slug)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan with slug '{payload.slug}' already exists",
        )

    plan = SubscriptionPlan(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        price_monthly=payload.price_monthly,
        price_annual=payload.price_annual,
        features=payload.features,
        limits=payload.limits.model_dump(),
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return SubscriptionPlanResponse(
        id=plan.id,
        slug=plan.slug,
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_annual=plan.price_annual,
        features=plan.features if isinstance(plan.features, list) else [],
        limits=SubscriptionPlanLimits(**plan.limits),
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


@app.patch(
    "/admin/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
)
def update_subscription_plan(
    plan_id: uuid.UUID,
    payload: SubscriptionPlanUpdateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SubscriptionPlanResponse:
    """Update subscription plan (super-admin only)."""
    plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    if payload.name is not None:
        plan.name = payload.name
    if payload.description is not None:
        plan.description = payload.description
    if payload.price_monthly is not None:
        plan.price_monthly = payload.price_monthly
    if payload.price_annual is not None:
        plan.price_annual = payload.price_annual
    if payload.features is not None:
        plan.features = payload.features  # type: ignore[assignment]
    if payload.limits is not None:
        plan.limits = payload.limits.model_dump()
    if payload.is_active is not None:
        plan.is_active = payload.is_active
    if payload.sort_order is not None:
        plan.sort_order = payload.sort_order

    db.commit()
    db.refresh(plan)

    return SubscriptionPlanResponse(
        id=plan.id,
        slug=plan.slug,
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_annual=plan.price_annual,
        features=plan.features if isinstance(plan.features, list) else [],
        limits=SubscriptionPlanLimits(**plan.limits),
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


@app.delete(
    "/admin/subscription-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_subscription_plan(
    plan_id: uuid.UUID,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Deactivate subscription plan (super-admin only)."""
    plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found",
        )

    plan.is_active = False
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------------
# Feature Flags
# --------------------------------------------------------------------------------


@app.get("/api/features")
def list_global_features(
    db: Session = Depends(get_db),  # noqa: B008
) -> list[dict]:
    """Return all available feature flag definitions (no auth required).

    Used by frontend on startup to determine which features are available
    on the platform before a tenant context is established.
    """
    flags = db.scalars(
        select(FeatureFlag).where(FeatureFlag.is_available.is_(True))
    ).all()
    return [
        {
            "slug": f.slug,
            "name": f.name,
            "description": f.description,
            "category": f.category,
            "default_enabled": f.default_enabled,
        }
        for f in flags
    ]


@app.get("/tenants/{tenant_id}/features", response_model=list[TenantFeatureResponse])
def get_tenant_features(
    tenant_id: uuid.UUID,
    _auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[TenantFeatureResponse]:
    """Get all feature flags for a tenant with their enabled status."""
    tenant = _get_tenant_or_404(db, tenant_id)

    # Get tenant's subscription plan
    plan = db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.slug == tenant.billing_plan)
    )

    # Get all available feature flags
    flags = db.scalars(
        select(FeatureFlag).where(FeatureFlag.is_available.is_(True))
    ).all()

    # Get tenant's feature flag overrides
    overrides = {
        override.feature_flag_slug: override
        for override in db.scalars(
            select(TenantFeatureFlag).where(
                TenantFeatureFlag.tenant_id == tenant_id
            )
        ).all()
    }

    features = []
    for flag in flags:
        # Determine if enabled based on: override > plan > default
        if flag.slug in overrides:
            is_enabled = overrides[flag.slug].is_enabled
            source = "override"
        elif plan and flag.slug in (
            plan.features if isinstance(plan.features, list) else []
        ):
            is_enabled = True
            source = "plan"
        else:
            is_enabled = flag.default_enabled
            source = "default"

        features.append(
            TenantFeatureResponse(
                slug=flag.slug,
                name=flag.name,
                description=flag.description,
                category=flag.category,
                is_enabled=is_enabled,
                source=source,
            )
        )

    return features


@app.get("/admin/feature-flags", response_model=list[FeatureFlagResponse])
def list_feature_flags(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[FeatureFlagResponse]:
    """List all feature flags (super-admin only)."""
    flags = db.scalars(select(FeatureFlag)).all()

    return [
        FeatureFlagResponse(
            id=flag.id,
            slug=flag.slug,
            name=flag.name,
            description=flag.description,
            category=flag.category,
            is_available=flag.is_available,
            default_enabled=flag.default_enabled,
        )
        for flag in flags
    ]


@app.post("/admin/feature-flags", response_model=FeatureFlagResponse)
def create_feature_flag(
    payload: FeatureFlagCreateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> FeatureFlagResponse:
    """Create new feature flag (super-admin only)."""
    # Check if slug already exists
    existing = db.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == payload.slug)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feature flag with slug '{payload.slug}' already exists",
        )

    flag = FeatureFlag(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        is_available=payload.is_available,
        default_enabled=payload.default_enabled,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)

    return FeatureFlagResponse(
        id=flag.id,
        slug=flag.slug,
        name=flag.name,
        description=flag.description,
        category=flag.category,
        is_available=flag.is_available,
        default_enabled=flag.default_enabled,
    )


@app.patch("/admin/feature-flags/{flag_id}", response_model=FeatureFlagResponse)
def update_feature_flag(
    flag_id: uuid.UUID,
    payload: FeatureFlagUpdateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> FeatureFlagResponse:
    """Update feature flag (super-admin only)."""
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.id == flag_id))
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )

    if payload.name is not None:
        flag.name = payload.name
    if payload.description is not None:
        flag.description = payload.description
    if payload.category is not None:
        flag.category = payload.category
    if payload.is_available is not None:
        flag.is_available = payload.is_available
    if payload.default_enabled is not None:
        flag.default_enabled = payload.default_enabled

    db.commit()
    db.refresh(flag)

    return FeatureFlagResponse(
        id=flag.id,
        slug=flag.slug,
        name=flag.name,
        description=flag.description,
        category=flag.category,
        is_available=flag.is_available,
        default_enabled=flag.default_enabled,
    )


@app.post("/admin/tenants/{tenant_id}/features/toggle")
def toggle_tenant_feature(
    tenant_id: uuid.UUID,
    payload: TenantFeatureToggleRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    """Toggle feature flag for tenant (super-admin only)."""
    _get_tenant_or_404(db, tenant_id)

    # Verify feature flag exists
    flag = db.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == payload.feature_slug)
    )
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{payload.feature_slug}' not found",
        )

    # Check if override already exists
    override = db.scalar(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.feature_flag_slug == payload.feature_slug,
        )
    )

    if override:
        # Update existing override
        override.is_enabled = payload.is_enabled
        if payload.is_enabled:
            override.enabled_at = datetime.now(UTC)
            override.disabled_at = None
        else:
            override.disabled_at = datetime.now(UTC)
            override.enabled_at = None
    else:
        # Create new override
        override = TenantFeatureFlag(
            tenant_id=tenant_id,
            feature_flag_slug=payload.feature_slug,
            is_enabled=payload.is_enabled,
            enabled_at=datetime.now(UTC) if payload.is_enabled else None,
            disabled_at=None if payload.is_enabled else datetime.now(UTC),
        )
        db.add(override)

    db.commit()

    status_text = "enabled" if payload.is_enabled else "disabled"
    return {
        "message": f"Feature '{payload.feature_slug}' {status_text} for tenant"
    }


@app.post("/admin/demo-data/trigger")
def trigger_demo_data(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str | int]:
    """Manually trigger One8 demo data generation (super-admin only)."""
    try:
        # Import the core logic (no celery dependency needed)
        from worker.app.tasks_demo_data import run_demo_data_generation
        
        result = run_demo_data_generation()
        return {
            "message": "Demo data generated successfully",
            "orders_created": result.get("orders_created", 0),
            "line_items_created": result.get("line_items_created", 0),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate demo data: {str(e)}",
        )


@app.post("/admin/optimization-engine/trigger")
def trigger_optimization_engine(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, str]:
    """Manually trigger optimization engine to generate recommendations (super-admin only)."""
    try:
        # Use Celery to send task to worker (which has scipy installed)
        from worker.app.celery_app import celery_app
        
        # Check if optimization engine is enabled
        import os
        if os.getenv("ENABLE_OPTIMIZATION_ENGINE", "false").lower() != "true":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Optimization engine is not enabled (set ENABLE_OPTIMIZATION_ENGINE=true)",
            )
        
        # Send task to celery worker
        task = celery_app.send_task("worker.app.tasks.run_optimization_engine_schedule")
        
        return {
            "message": "Optimization engine task queued successfully",
            "task_id": task.id,
            "status": "Task sent to worker - check celery logs for progress",
        }
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Celery not available: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue optimization engine task: {str(e)}",
        )


@app.post("/admin/optimization-strategies/seed")
def seed_optimization_strategies_endpoint(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    """Seed optimization strategies for One8 demo tenant and enable budget allocation (super-admin only)."""
    try:
        # Use the same One8 tenant ID that demo data uses
        import uuid
        ONE8_TENANT_ID = uuid.UUID("23165fa5-150b-4b6c-a637-b3dd24532c4d")
        
        # Verify tenant exists
        tenant = db.scalar(
            select(Tenant).where(Tenant.id == ONE8_TENANT_ID)
        )
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"One8 tenant ({ONE8_TENANT_ID}) not found - run demo data generation first",
            )
        
        # Delete existing strategies for clean slate
        existing_count = db.scalar(
            select(func.count())
            .select_from(OptimizationStrategy)
            .where(OptimizationStrategy.tenant_id == ONE8_TENANT_ID)
        )
        
        if existing_count and existing_count > 0:
            db.execute(
                delete(OptimizationStrategy).where(
                    OptimizationStrategy.tenant_id == ONE8_TENANT_ID
                )
            )
        
        # Create 4 optimization strategies
        strategies = [
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=ONE8_TENANT_ID,
                domain="acquisition",
                strategy_name="budget_allocation",
                strategy_type="budget_allocation",
                is_enabled=True,  # Enable this one by default
                config={
                    "description": "Optimize ad spend allocation across channels",
                    "min_budget_per_channel": 1000.0,
                    "max_budget_shift_pct": 0.25,
                    "lookback_days": 90,
                    "confidence_threshold": 0.7,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=ONE8_TENANT_ID,
                domain="finance",
                strategy_name="pricing_optimization",
                strategy_type="elasticity_model",
                is_enabled=False,
                config={
                    "description": "Optimize product pricing based on demand elasticity",
                    "min_margin_pct": 0.30,
                    "max_price_change_pct": 0.15,
                    "elasticity_lookback_days": 60,
                    "confidence_threshold": 0.75,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=ONE8_TENANT_ID,
                domain="retention",
                strategy_name="retention_campaign_targeting",
                strategy_type="propensity_scoring",
                is_enabled=False,
                config={
                    "description": "Optimize retention campaign targeting",
                    "target_segments": ["at_risk", "promising", "lapsed"],
                    "min_propensity_score": 0.6,
                    "max_campaign_frequency_days": 14,
                    "lookback_days": 90,
                    "confidence_threshold": 0.7,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=ONE8_TENANT_ID,
                domain="operations",
                strategy_name="inventory_reorder_optimization",
                strategy_type="demand_forecasting",
                is_enabled=False,
                config={
                    "description": "Optimize inventory reorder points",
                    "forecast_horizon_days": 30,
                    "safety_stock_multiplier": 1.5,
                    "max_inventory_value_pct": 0.20,
                    "min_turnover_ratio": 4.0,
                    "confidence_threshold": 0.65,
                },
            ),
        ]
        
        db.add_all(strategies)
        db.commit()
        
        return {
            "message": "Optimization strategies seeded successfully",
            "tenant": tenant.slug,
            "strategies_created": len(strategies),
            "enabled_strategies": sum(1 for s in strategies if s.is_enabled),
            "strategies": [
                {
                    "domain": s.domain,
                    "strategy_name": s.strategy_name,
                    "is_enabled": s.is_enabled,
                }
                for s in strategies
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed optimization strategies: {str(e)}",
        )


# ---------------------------------------------------------------------------
# D4: Super-admin tenant management
# ---------------------------------------------------------------------------


@app.get("/admin/tenants", response_model=AdminTenantListResponse)
def list_all_tenants(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: bool | None = None,
    billing_status: str | None = None,
) -> AdminTenantListResponse:
    """D4: List all tenants with pagination and filters (super-admin only)."""
    query = select(Tenant)

    # Apply filters
    if is_active is not None:
        query = query.where(Tenant.is_active == is_active)
    if billing_status:
        query = query.where(Tenant.billing_status == billing_status)

    # Get total count
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    # Apply pagination
    offset = (page - 1) * page_size
    tenants = db.scalars(
        query.order_by(Tenant.created_at.desc()).offset(offset).limit(page_size)
    ).all()

    # Compute user counts for each tenant
    from backend.app.admin_audit import get_tenant_usage_metrics

    tenant_responses = []
    for tenant in tenants:
        # Count memberships for this tenant
        total_users = db.scalar(
            select(func.count()).where(TenantMembership.tenant_id == tenant.id)
        )
        active_users = db.scalar(
            select(func.count())
            .select_from(TenantMembership)
            .join(User, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == tenant.id,
                User.is_active.is_(True),
            )
        )

        # Get usage metrics
        total_logins, last_activity_at, active_users_30d = (
            get_tenant_usage_metrics(db, tenant.id)
        )

        tenant_responses.append(
            AdminTenantResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                is_active=tenant.is_active,
                status=tenant.status,
                status_reason=tenant.status_reason,
                suspended_at=tenant.suspended_at,
                deleted_at=tenant.deleted_at,
                billing_plan=tenant.billing_plan,
                billing_cycle=tenant.billing_cycle,
                billing_status=tenant.billing_status,
                seat_limit=tenant.seat_limit,
                base_currency=tenant.base_currency,
                locale=tenant.locale,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
                total_users=total_users or 0,
                active_users=active_users or 0,
                total_logins=total_logins,
                last_activity_at=last_activity_at,
                active_users_30d=active_users_30d,
            )
        )

    return AdminTenantListResponse(
        tenants=tenant_responses,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@app.get("/admin/tenants/{tenant_id}", response_model=AdminTenantResponse)
def get_tenant_details(
    tenant_id: uuid.UUID,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AdminTenantResponse:
    """D4: Get single tenant details (super-admin only)."""
    from backend.app.admin_audit import get_tenant_usage_metrics
    
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Count users
    total_users = db.scalar(
        select(func.count()).where(TenantMembership.tenant_id == tenant.id)
    )
    active_users = db.scalar(
        select(func.count())
        .select_from(TenantMembership)
        .join(User, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == tenant.id,
            User.is_active.is_(True),
        )
    )

    # Get usage metrics

    total_logins, last_activity_at, active_users_30d = get_tenant_usage_metrics(
        db, tenant.id
    )

    return AdminTenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        status=tenant.status,
        status_reason=tenant.status_reason,
        suspended_at=tenant.suspended_at,
        deleted_at=tenant.deleted_at,
        billing_plan=tenant.billing_plan,
        billing_cycle=tenant.billing_cycle,
        billing_status=tenant.billing_status,
        seat_limit=tenant.seat_limit,
        base_currency=tenant.base_currency,
        locale=tenant.locale,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        total_users=total_users or 0,
        active_users=active_users or 0,
        total_logins=total_logins,
        last_activity_at=last_activity_at,
        active_users_30d=active_users_30d,
    )


@app.patch("/admin/tenants/{tenant_id}", response_model=AdminTenantResponse)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: AdminTenantUpdateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AdminTenantResponse:
    """D4: Update tenant details (super-admin only)."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Apply updates (partial update)
    if payload.name is not None:
        tenant.name = payload.name
    if payload.billing_plan is not None:
        tenant.billing_plan = payload.billing_plan
    if payload.billing_cycle is not None:
        tenant.billing_cycle = payload.billing_cycle
    if payload.billing_status is not None:
        tenant.billing_status = payload.billing_status
    if payload.seat_limit is not None:
        tenant.seat_limit = payload.seat_limit

    db.commit()
    db.refresh(tenant)

    # Count users
    total_users = db.scalar(
        select(func.count()).where(TenantMembership.tenant_id == tenant.id)
    )
    active_users = db.scalar(
        select(func.count())
        .select_from(TenantMembership)
        .join(User, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == tenant.id,
            User.is_active.is_(True),
        )
    )

    # Get usage metrics
    from backend.app.admin_audit import get_tenant_usage_metrics

    total_logins, last_activity_at, active_users_30d = get_tenant_usage_metrics(
        db, tenant.id
    )

    return AdminTenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        status=tenant.status,
        status_reason=tenant.status_reason,
        suspended_at=tenant.suspended_at,
        deleted_at=tenant.deleted_at,
        billing_plan=tenant.billing_plan,
        billing_cycle=tenant.billing_cycle,
        billing_status=tenant.billing_status,
        seat_limit=tenant.seat_limit,
        base_currency=tenant.base_currency,
        locale=tenant.locale,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        total_users=total_users or 0,
        active_users=active_users or 0,
        total_logins=total_logins,
        last_activity_at=last_activity_at,
        active_users_30d=active_users_30d,
    )


@app.patch("/admin/tenants/{tenant_id}/status", response_model=AdminTenantResponse)
def update_tenant_status(
    tenant_id: uuid.UUID,
    payload: AdminTenantStatusUpdateRequest,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AdminTenantResponse:
    """D4: Suspend or activate tenant (super-admin only)."""
    from backend.app.admin_audit import write_admin_audit_log
    
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Track old values for audit log
    old_is_active = tenant.is_active
    old_status = tenant.status

    # Update tenant status
    tenant.is_active = payload.is_active
    if payload.is_active:
        tenant.status = "active"
        tenant.status_reason = None
        tenant.suspended_at = None
    else:
        tenant.status = "suspended"
        tenant.status_reason = payload.reason
        tenant.suspended_at = datetime.now(UTC)

    # Write tenant audit event (legacy)
    actor = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="tenant.status_updated",
        entity_type="tenant",
        entity_id=str(tenant_id),
        details={"is_active": payload.is_active, "reason": payload.reason},
        actor_user_id=actor.id if actor else None,
    )

    # Write admin audit log
    if actor:
        action_type = "tenant_activated" if payload.is_active else "tenant_suspended"
        write_admin_audit_log(
            db,
            admin_user_id=actor.id,
            action_type=action_type,
            resource_type="tenant",
            resource_id=str(tenant_id),
            tenant_id=tenant_id,
            changes={
                "is_active": {"old": old_is_active, "new": payload.is_active},
                "status": {"old": old_status, "new": tenant.status},
            },
            reason=payload.reason,
        )

    db.commit()
    db.refresh(tenant)

    # Count users
    total_users = db.scalar(
        select(func.count()).where(TenantMembership.tenant_id == tenant.id)
    )
    active_users = db.scalar(
        select(func.count())
        .select_from(TenantMembership)
        .join(User, TenantMembership.user_id == User.id)
        .where(
            TenantMembership.tenant_id == tenant.id,
            User.is_active.is_(True),
        )
    )

    # Get usage metrics
    from backend.app.admin_audit import get_tenant_usage_metrics

    total_logins, last_activity_at, active_users_30d = get_tenant_usage_metrics(
        db, tenant.id
    )

    return AdminTenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        status=tenant.status,
        status_reason=tenant.status_reason,
        suspended_at=tenant.suspended_at,
        deleted_at=tenant.deleted_at,
        billing_plan=tenant.billing_plan,
        billing_cycle=tenant.billing_cycle,
        billing_status=tenant.billing_status,
        seat_limit=tenant.seat_limit,
        base_currency=tenant.base_currency,
        locale=tenant.locale,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        total_users=total_users or 0,
        active_users=active_users or 0,
        total_logins=total_logins,
        last_activity_at=last_activity_at,
        active_users_30d=active_users_30d,
    )



@app.delete("/admin/tenants/{tenant_id}", response_model=AdminTenantDeleteResponse)
def delete_tenant(
    tenant_id: uuid.UUID,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
    payload: dict = Body(default={}),  # noqa: B008
) -> AdminTenantDeleteResponse:
    """D4: Soft-delete tenant (super-admin only).
    
    This performs a SOFT DELETE:
    - Marks tenant as deleted with deleted_at timestamp
    - Sets status to 'deleted'
    - Sets is_active to False
    - Preserves all data for audit/recovery
    - Records action in admin audit log
    
    For hard delete (irreversible), contact platform support.
    """
    from backend.app.admin_audit import write_admin_audit_log
    
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    if tenant.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant already deleted",
        )

    tenant_name = tenant.name
    reason = payload.get("reason")
    
    # Soft delete
    tenant.deleted_at = datetime.now(UTC)
    tenant.status = "deleted"
    tenant.status_reason = reason or "Deleted by Super Admin"
    tenant.is_active = False
    
    # Write tenant audit event (legacy)
    actor = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="tenant.deleted",
        entity_type="tenant",
        entity_id=str(tenant_id),
        details={"reason": reason},
        actor_user_id=actor.id if actor else None,
    )
    
    # Write admin audit log
    if actor:
        write_admin_audit_log(
            db,
            admin_user_id=actor.id,
            action_type="tenant_deleted",
            resource_type="tenant",
            resource_id=str(tenant_id),
            tenant_id=tenant_id,
            changes={
                "status": {"old": "active", "new": "deleted"},
                "tenant_name": tenant_name,
            },
            reason=reason,
        )
    
    db.commit()
    
    return AdminTenantDeleteResponse(
        message=(
            f"Tenant '{tenant_name}' soft-deleted successfully "
            "(data preserved for recovery)"
        ),
        tenant_id=tenant_id,
        deleted_at=tenant.deleted_at,
    )


@app.post("/admin/seed-one8-realistic")
def seed_one8_realistic(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """
    Trigger realistic One8 data seeding (super-admin only).
    
    Wipes ALL existing One8 data and seeds 90 days of realistic patterns.
    WARNING: This deletes all existing One8 data!
    """
    import subprocess
    import sys
    from pathlib import Path
    
    # Path to seed script
    script_path = (
        Path(__file__).parent.parent.parent
        / "scripts"
        / "seed_one8_realistic.py"
    )
    
    if not script_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seed script not found at {script_path}",
        )
    
    try:
        # Run the seeding script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Seeding failed: {result.stderr}",
            )
        
        return {
            "message": "✅ One8 realistic data seeding completed",
            "exit_code": result.returncode,
            "output": result.stdout[-1000:],  # Last 1000 chars
            "next_step": (
                "Trigger optimization: POST /admin/trigger-optimization"
            ),
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Seeding script timed out after 5 minutes",
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seeding error: {str(e)}",
        ) from None


@app.get("/admin/audit-log", response_model=AdminAuditLogListResponse)
def get_admin_audit_log(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
    tenant_id: UUID | None = Query(None, description="Filter by tenant ID"),  # noqa: B008
    action_type: str | None = Query(None, description="Filter by action type"),  # noqa: B008
    page: int = Query(1, ge=1, description="Page number"),  # noqa: B008
    page_size: int = Query(1, ge=1, le=200, description="Items per page"),  # noqa: B008
) -> AdminAuditLogListResponse:
    """D4: Get admin audit log (super-admin only).
    
    Returns paginated list of admin actions with optional filters.
    """
    from backend.app.db.models import AdminAuditLog
    
    # Build query
    query = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc())
    
    # Apply filters
    if tenant_id:
        query = query.where(AdminAuditLog.tenant_id == tenant_id)
    if action_type:
        query = query.where(AdminAuditLog.action_type == action_type)
    
    # Count total
    count_query = select(func.count()).select_from(AdminAuditLog)
    if tenant_id:
        count_query = count_query.where(AdminAuditLog.tenant_id == tenant_id)
    if action_type:
        count_query = count_query.where(AdminAuditLog.action_type == action_type)
    
    total = db.scalar(count_query) or 0
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)
    
    logs = db.scalars(query).all()
    
    # Enrich with admin user email
    log_responses = []
    for log in logs:
        admin_user = db.scalar(select(User).where(User.id == log.admin_user_id))
        log_responses.append(
            AdminAuditLogResponse(
                id=log.id,
                tenant_id=log.tenant_id,
                admin_user_id=log.admin_user_id,
                admin_user_email=admin_user.email if admin_user else None,
                action_type=log.action_type,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                changes=log.changes,
                reason=log.reason,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
        )
    
    return AdminAuditLogListResponse(
        logs=log_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# D5: Platform metrics dashboard
# ---------------------------------------------------------------------------


@app.get("/admin/platform/metrics", response_model=PlatformMetricsResponse)
def get_platform_metrics(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> PlatformMetricsResponse:
    """D5: Platform-wide metrics dashboard (super-admin only).
    
    Returns aggregated statistics across all tenants:
    - Tenant counts and growth
    - User counts and activity
    - Subscription plan distribution
    - Feature flag adoption
    - Integration health
    """
    # Tenant metrics
    total_tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    active_tenants = db.scalar(
        select(func.count()).where(Tenant.is_active.is_(True))
    ) or 0
    suspended_tenants = total_tenants - active_tenants

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    new_tenants_30d = db.scalar(
        select(func.count()).where(Tenant.created_at >= thirty_days_ago)
    ) or 0
    new_tenants_7d = db.scalar(
        select(func.count()).where(Tenant.created_at >= seven_days_ago)
    ) or 0

    tenant_metrics = TenantMetrics(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        suspended_tenants=suspended_tenants,
        new_tenants_last_30_days=new_tenants_30d,
        new_tenants_last_7_days=new_tenants_7d,
    )

    # User metrics
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(
        select(func.count()).where(User.is_active.is_(True))
    ) or 0

    new_users_30d = db.scalar(
        select(func.count()).where(User.created_at >= thirty_days_ago)
    ) or 0
    new_users_7d = db.scalar(
        select(func.count()).where(User.created_at >= seven_days_ago)
    ) or 0

    users_per_tenant = (
        float(total_users) / float(total_tenants) if total_tenants > 0 else 0.0
    )

    user_metrics = UserMetrics(
        total_users=total_users,
        active_users=active_users,
        users_per_tenant_avg=round(users_per_tenant, 2),
        new_users_last_30_days=new_users_30d,
        new_users_last_7_days=new_users_7d,
    )

    # Subscription metrics
    starter_count = db.scalar(
        select(func.count()).where(Tenant.billing_plan == "starter")
    ) or 0
    professional_count = db.scalar(
        select(func.count()).where(Tenant.billing_plan == "professional")
    ) or 0
    enterprise_count = db.scalar(
        select(func.count()).where(Tenant.billing_plan == "enterprise")
    ) or 0

    total_seats_allocated = db.scalar(
        select(func.sum(Tenant.seat_limit)).select_from(Tenant)
    ) or 0

    # Count total memberships as seats used
    total_seats_used = db.scalar(
        select(func.count()).select_from(TenantMembership)
    ) or 0

    subscription_metrics = SubscriptionMetrics(
        starter_count=starter_count,
        professional_count=professional_count,
        enterprise_count=enterprise_count,
        total_seats_allocated=total_seats_allocated,
        total_seats_used=total_seats_used,
    )

    # Feature flag metrics
    total_flags = db.scalar(select(func.count()).select_from(FeatureFlag)) or 0
    total_overrides = db.scalar(
        select(func.count()).select_from(TenantFeatureFlag)
    ) or 0

    # Most enabled features (by plan or override)
    # Count how many tenants have each feature enabled
    enabled_features_query = db.execute(
        select(
            TenantFeatureFlag.feature_flag_slug,
            func.count(TenantFeatureFlag.tenant_id).label("tenant_count"),
        )
        .where(TenantFeatureFlag.is_enabled.is_(True))
        .group_by(TenantFeatureFlag.feature_flag_slug)
        .order_by(func.count(TenantFeatureFlag.tenant_id).desc())
        .limit(5)
    )
    most_enabled = [(row[0], row[1]) for row in enabled_features_query.all()]

    # Most disabled features (by override)
    disabled_features_query = db.execute(
        select(
            TenantFeatureFlag.feature_flag_slug,
            func.count(TenantFeatureFlag.tenant_id).label("tenant_count"),
        )
        .where(TenantFeatureFlag.is_enabled.is_(False))
        .group_by(TenantFeatureFlag.feature_flag_slug)
        .order_by(func.count(TenantFeatureFlag.tenant_id).desc())
        .limit(5)
    )
    most_disabled = [(row[0], row[1]) for row in disabled_features_query.all()]

    feature_flag_metrics = FeatureFlagMetrics(
        total_flags=total_flags,
        total_overrides=total_overrides,
        most_enabled_features=most_enabled,
        most_disabled_features=most_disabled,
    )

    # Integration metrics
    total_connectors = db.scalar(
        select(func.count()).select_from(ConnectorIntegration)
    ) or 0
    active_connectors = db.scalar(
        select(func.count()).where(ConnectorIntegration.status == "connected")
    ) or 0
    connectors_with_errors = db.scalar(
        select(func.count()).where(ConnectorIntegration.error_message.isnot(None))
    ) or 0

    # Sync failures in last 24 hours
    twenty_four_hours_ago = datetime.now(UTC) - timedelta(hours=24)
    failed_sync_jobs_24h = db.scalar(
        select(func.count()).where(
            AuditEvent.action == "alert.connector_sync_failure_created",
            AuditEvent.created_at >= twenty_four_hours_ago,
        )
    ) or 0

    # Count total sync jobs (success + failure) in last 24 hours
    # Success actions: connector.*_synced
    total_sync_jobs_24h = db.scalar(
        select(func.count()).where(
            AuditEvent.entity_type == "connector",
            AuditEvent.created_at >= twenty_four_hours_ago,
            AuditEvent.action.like("connector.%_synced"),
        )
    ) or 0
    total_sync_jobs_24h += failed_sync_jobs_24h

    integration_metrics = IntegrationMetrics(
        total_connectors=total_connectors,
        active_connectors=active_connectors,
        connectors_with_errors=connectors_with_errors,
        total_sync_jobs_last_24h=total_sync_jobs_24h,
        failed_sync_jobs_last_24h=failed_sync_jobs_24h,
    )

    return PlatformMetricsResponse(
        tenant_metrics=tenant_metrics,
        user_metrics=user_metrics,
        subscription_metrics=subscription_metrics,
        feature_flag_metrics=feature_flag_metrics,
        integration_metrics=integration_metrics,
        generated_at=datetime.now(UTC),
        platform_version="1.0.0",
    )


@app.get("/admin/platform/connectors", response_model=ConnectorAvailabilityResponse)
def get_platform_connector_availability(
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorAvailabilityResponse:
    """D6: Platform-wide connector availability tracking (super-admin only).
    
    Returns detailed connector statistics across all tenants:
    - Total/active/disconnected/error counts
    - Recent sync failures
    - Tenant adoption metrics
    - Per-source breakdown (shopify, meta, google_ads, etc.)
    """
    # Overall connector counts
    total_connectors = db.scalar(
        select(func.count()).select_from(ConnectorIntegration)
    ) or 0
    
    active_connectors = db.scalar(
        select(func.count()).where(ConnectorIntegration.status == "connected")
    ) or 0
    
    disconnected_connectors = db.scalar(
        select(func.count()).where(ConnectorIntegration.status != "connected")
    ) or 0
    
    connectors_with_errors = db.scalar(
        select(func.count()).where(ConnectorIntegration.error_message.isnot(None))
    ) or 0
    
    # Recent sync failures (last 24 hours)
    twenty_four_hours_ago = datetime.now(UTC) - timedelta(hours=24)
    recent_failures = db.scalar(
        select(func.count()).where(
            AuditEvent.action == "alert.connector_sync_failure_created",
            AuditEvent.created_at >= twenty_four_hours_ago,
        )
    ) or 0
    
    # Tenant adoption
    tenants_with_connectors = db.scalar(
        select(func.count(func.distinct(ConnectorIntegration.tenant_id))).select_from(
            ConnectorIntegration
        )
    ) or 0
    
    total_tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    tenants_without_connectors = total_tenants - tenants_with_connectors
    
    # Per-source breakdown
    source_stats = db.execute(
        select(
            ConnectorIntegration.source,
            func.count(ConnectorIntegration.id).label("total"),
            func.sum(
                func.cast(
                    ConnectorIntegration.status == "connected", sa.Integer
                )
            ).label("connected"),
            func.sum(
                func.cast(
                    ConnectorIntegration.status != "connected", sa.Integer
                )
            ).label("disconnected"),
            func.sum(
                func.cast(
                    ConnectorIntegration.error_message.isnot(None), sa.Integer
                )
            ).label("errors"),
            func.count(func.distinct(ConnectorIntegration.tenant_id)).label(
                "tenants"
            ),
        )
        .group_by(ConnectorIntegration.source)
        .order_by(func.count(ConnectorIntegration.id).desc())
    ).all()
    
    by_source = [
        ConnectorSourceBreakdown(
            source=row[0],
            total_connectors=row[1],
            connected_count=row[2] or 0,
            disconnected_count=row[3] or 0,
            error_count=row[4] or 0,
            tenants_using=row[5],
        )
        for row in source_stats
    ]
    
    return ConnectorAvailabilityResponse(
        total_connectors=total_connectors,
        active_connectors=active_connectors,
        disconnected_connectors=disconnected_connectors,
        connectors_with_errors=connectors_with_errors,
        recent_sync_failures_24h=recent_failures,
        tenants_with_connectors=tenants_with_connectors,
        tenants_without_connectors=tenants_without_connectors,
        by_source=by_source,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tenant notification routing
# ---------------------------------------------------------------------------


@app.get(
    "/tenants/{tenant_id}/notification-routing",
    response_model=NotificationRoutingResponse,
)
def get_notification_routing(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationRoutingResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    routes = [
        NotificationRouteItem(
            alert_type=route.alert_type,
            channel=route.channel,
            destination=route.destination,
            is_enabled=route.is_enabled,
        )
        for route in tenant.notification_routes
    ]

    return NotificationRoutingResponse(tenant_id=tenant.id, routes=routes)


@app.put(
    "/tenants/{tenant_id}/notification-routing",
    response_model=NotificationRoutingResponse,
)
def upsert_notification_routing(
    tenant_id: uuid.UUID,
    payload: NotificationRoutingUpdateRequest,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationRoutingResponse:
    tenant = _get_tenant_or_404(db, tenant_id)

    for route in payload.routes:
        if route.channel.strip().lower() not in ALLOWED_NOTIFICATION_CHANNELS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Notification channel is not supported.",
            )

    tenant.notification_routes.clear()
    db.flush()

    for route in payload.routes:
        tenant.notification_routes.append(
            NotificationRoutingSetting(
                tenant_id=tenant.id,
                alert_type=route.alert_type.strip().lower(),
                channel=route.channel.strip().lower(),
                destination=route.destination.strip(),
                is_enabled=route.is_enabled,
            )
        )

    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="notification_routing.updated",
        entity_type="notification_routing",
        entity_id=str(tenant.id),
        details={"routes_count": len(payload.routes)},
    )
    db.commit()
    db.refresh(tenant)

    routes = [
        NotificationRouteItem(
            alert_type=route.alert_type,
            channel=route.channel,
            destination=route.destination,
            is_enabled=route.is_enabled,
        )
        for route in tenant.notification_routes
    ]
    return NotificationRoutingResponse(tenant_id=tenant.id, routes=routes)


@app.post(
    "/tenants/{tenant_id}/privacy-requests",
    response_model=PrivacyRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_privacy_request(
    tenant_id: uuid.UUID,
    payload: PrivacyRequestCreateRequest,
    auth: AdminAuditDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> PrivacyRequest:
    tenant = _get_tenant_or_404(db, tenant_id)
    normalized_type = payload.request_type.strip().lower()
    if normalized_type not in ALLOWED_PRIVACY_REQUEST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Privacy request type is not supported.",
        )

    requester = _get_user_by_email(db, auth.email)
    privacy_request = PrivacyRequest(
        tenant_id=tenant.id,
        requested_by_user_id=requester.id if requester is not None else None,
        request_type=normalized_type,
        subject_email=payload.subject_email.strip().lower(),
        status="pending",
        reason=payload.reason.strip() if payload.reason is not None else None,
    )
    db.add(privacy_request)
    db.flush()
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="privacy_request.created",
        entity_type="privacy_request",
        entity_id=str(privacy_request.id),
        details={
            "request_type": privacy_request.request_type,
            "subject_email": privacy_request.subject_email,
            "status": privacy_request.status,
        },
        actor_user_id=privacy_request.requested_by_user_id,
    )
    db.commit()
    db.refresh(privacy_request)
    return privacy_request


@app.get(
    "/tenants/{tenant_id}/privacy-requests",
    response_model=list[PrivacyRequestResponse],
)
def list_privacy_requests(
    tenant_id: uuid.UUID,
    _auth: AdminAuditDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> list[PrivacyRequest]:
    _get_tenant_or_404(db, tenant_id)
    return list(
        db.scalars(
            select(PrivacyRequest)
            .where(PrivacyRequest.tenant_id == tenant_id)
            .order_by(PrivacyRequest.created_at.desc())
        )
    )


@app.patch(
    "/tenants/{tenant_id}/privacy-requests/{request_id}",
    response_model=PrivacyRequestResponse,
)
def update_privacy_request_status(
    tenant_id: uuid.UUID,
    request_id: uuid.UUID,
    payload: PrivacyRequestStatusUpdateRequest,
    auth: AdminAuditDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> PrivacyRequest:
    normalized_status = payload.status.strip().lower()
    if normalized_status not in ALLOWED_PRIVACY_REQUEST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Privacy request status is not supported.",
        )
    if (
        normalized_status in {"completed", "rejected"}
        and payload.resolution_note is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Resolution note is required for completed or rejected "
                "privacy requests."
            ),
        )

    privacy_request = _get_privacy_request_or_404(
        db,
        tenant_id=tenant_id,
        request_id=request_id,
    )
    privacy_request.status = normalized_status
    privacy_request.resolution_note = (
        payload.resolution_note.strip()
        if payload.resolution_note is not None
        else None
    )
    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="privacy_request.status_updated",
        entity_type="privacy_request",
        entity_id=str(privacy_request.id),
        details={
            "status": privacy_request.status,
            "resolution_note": privacy_request.resolution_note,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(privacy_request)
    return privacy_request


@app.post(
    "/tenants/{tenant_id}/connectors/shopify/oauth/start",
    response_model=ShopifyOAuthStartResponse,
)
def start_shopify_oauth(
    tenant_id: uuid.UUID,
    payload: ShopifyOAuthStartRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ShopifyOAuthStartResponse:
    tenant = _get_tenant_or_404(db, tenant_id)
    normalized_domain = payload.shop_domain.strip().lower()
    state = secrets.token_urlsafe(24)
    connector = _get_connector_for_tenant(db, tenant_id=tenant.id, source="shopify")
    if connector is None:
        connector = ConnectorIntegration(
            tenant_id=tenant.id,
            source="shopify",
            auth_mode="oauth",
        )
        db.add(connector)
        db.flush()

    connector.status = "pending_oauth"
    connector.shop_domain = normalized_domain
    connector.oauth_state = state
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="connector.oauth_started",
        entity_type="connector",
        entity_id=str(connector.id),
        details={"source": "shopify", "shop_domain": normalized_domain},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()

    return ShopifyOAuthStartResponse(
        connector_id=connector.id,
        tenant_id=tenant.id,
        source=connector.source,
        status=connector.status,
        state=state,
        auth_url=_build_shopify_auth_url(shop_domain=normalized_domain, state=state),
    )


@app.post(
    "/tenants/{tenant_id}/connectors/shopify/oauth/callback",
    response_model=ConnectorResponse,
)
def complete_shopify_oauth(
    tenant_id: uuid.UUID,
    payload: ShopifyOAuthCallbackRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorResponse:
    _get_tenant_or_404(db, tenant_id)
    connector = _get_connector_for_tenant(db, tenant_id=tenant_id, source="shopify")
    if connector is None or connector.oauth_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopify connector not found.",
        )

    if connector.oauth_state != payload.state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OAuth state is invalid.",
        )

    connector.status = "connected"
    connector.shop_domain = payload.shop_domain.strip().lower()
    connector.oauth_state = None
    connector.connected_at = datetime.now(UTC)
    connector.oauth_expires_at = datetime.now(UTC) + timedelta(
        days=OAUTH_TOKEN_LIFETIME_DAYS
    )
    connector.oauth_expiry_warning_sent_at = None
    connector.oauth_expired_alert_sent_at = None
    connector.last_sync_requested_at = datetime.now(UTC)
    vault_entry = _upsert_connector_vault_secret(
        db,
        tenant_id=tenant_id,
        connector=connector,
        secret_value=payload.code,
        secret_type="oauth_code",
    )
    connector.credential_ref = str(vault_entry.id)
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.oauth_completed",
        entity_type="connector",
        entity_id=str(connector.id),
        details={
            "source": "shopify",
            "shop_domain": connector.shop_domain,
            "sync_initiated": True,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
    )


@app.post(
    "/tenants/{tenant_id}/connectors/meta/oauth/start",
    response_model=MetaOAuthStartResponse,
)
def start_meta_oauth(
    tenant_id: uuid.UUID,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MetaOAuthStartResponse:
    tenant = _get_tenant_or_404(db, tenant_id)
    state = secrets.token_urlsafe(24)
    connector = _get_connector_for_tenant(db, tenant_id=tenant.id, source="meta")
    if connector is None:
        connector = ConnectorIntegration(
            tenant_id=tenant.id,
            source="meta",
            auth_mode="oauth",
        )
        db.add(connector)
        db.flush()

    connector.status = "pending_oauth"
    connector.shop_domain = None
    connector.oauth_state = state
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="connector.oauth_started",
        entity_type="connector",
        entity_id=str(connector.id),
        details={"source": "meta"},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()

    return MetaOAuthStartResponse(
        connector_id=connector.id,
        tenant_id=tenant.id,
        source=connector.source,
        status=connector.status,
        state=state,
        auth_url=_build_meta_auth_url(state=state),
    )


@app.post(
    "/tenants/{tenant_id}/connectors/meta/oauth/callback",
    response_model=ConnectorResponse,
)
def complete_meta_oauth(
    tenant_id: uuid.UUID,
    payload: MetaOAuthCallbackRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorResponse:
    _get_tenant_or_404(db, tenant_id)
    connector = _get_connector_for_tenant(db, tenant_id=tenant_id, source="meta")
    if connector is None or connector.oauth_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta connector not found.",
        )

    if connector.oauth_state != payload.state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OAuth state is invalid.",
        )

    connector.status = "connected"
    connector.oauth_state = None
    connector.connected_at = datetime.now(UTC)
    connector.oauth_expires_at = datetime.now(UTC) + timedelta(
        days=OAUTH_TOKEN_LIFETIME_DAYS
    )
    connector.oauth_expiry_warning_sent_at = None
    connector.oauth_expired_alert_sent_at = None
    connector.last_sync_requested_at = datetime.now(UTC)
    vault_entry = _upsert_connector_vault_secret(
        db,
        tenant_id=tenant_id,
        connector=connector,
        secret_value=payload.code,
        secret_type="oauth_code",
    )
    connector.credential_ref = str(vault_entry.id)
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.oauth_completed",
        entity_type="connector",
        entity_id=str(connector.id),
        details={
            "source": "meta",
            "sync_initiated": True,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
    )


@app.post(
    "/tenants/{tenant_id}/connectors/google_ads/oauth/start",
    response_model=GoogleAdsOAuthStartResponse,
)
def start_google_ads_oauth(
    tenant_id: uuid.UUID,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> GoogleAdsOAuthStartResponse:
    tenant = _get_tenant_or_404(db, tenant_id)
    state = secrets.token_urlsafe(24)
    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant.id,
        source="google_ads",
    )
    if connector is None:
        connector = ConnectorIntegration(
            tenant_id=tenant.id,
            source="google_ads",
            auth_mode="oauth",
        )
        db.add(connector)
        db.flush()

    connector.status = "pending_oauth"
    connector.shop_domain = None
    connector.oauth_state = state
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant.id,
        action="connector.oauth_started",
        entity_type="connector",
        entity_id=str(connector.id),
        details={"source": "google_ads"},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()

    return GoogleAdsOAuthStartResponse(
        connector_id=connector.id,
        tenant_id=tenant.id,
        source=connector.source,
        status=connector.status,
        state=state,
        auth_url=_build_google_ads_auth_url(state=state),
    )


@app.post(
    "/tenants/{tenant_id}/connectors/google_ads/oauth/callback",
    response_model=ConnectorResponse,
)
def complete_google_ads_oauth(
    tenant_id: uuid.UUID,
    payload: GoogleAdsOAuthCallbackRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorResponse:
    _get_tenant_or_404(db, tenant_id)
    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant_id,
        source="google_ads",
    )
    if connector is None or connector.oauth_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Ads connector not found.",
        )

    if connector.oauth_state != payload.state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OAuth state is invalid.",
        )

    connector.status = "connected"
    connector.oauth_state = None
    connector.connected_at = datetime.now(UTC)
    connector.oauth_expires_at = datetime.now(UTC) + timedelta(
        days=OAUTH_TOKEN_LIFETIME_DAYS
    )
    connector.oauth_expiry_warning_sent_at = None
    connector.oauth_expired_alert_sent_at = None
    connector.last_sync_requested_at = datetime.now(UTC)
    vault_entry = _upsert_connector_vault_secret(
        db,
        tenant_id=tenant_id,
        connector=connector,
        secret_value=payload.code,
        secret_type="oauth_code",
    )
    connector.credential_ref = str(vault_entry.id)
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.oauth_completed",
        entity_type="connector",
        entity_id=str(connector.id),
        details={
            "source": "google_ads",
            "sync_initiated": True,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
    )


@app.post(
    "/tenants/{tenant_id}/connectors/{source}/api-key",
    response_model=ConnectorResponse,
)
def connect_source_with_api_key(
    tenant_id: uuid.UUID,
    source: str,
    payload: ConnectorApiKeyConnectRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorResponse:
    _get_tenant_or_404(db, tenant_id)
    normalized_source = source.strip().lower()
    if normalized_source in OAUTH_PREFERRED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This source must use OAuth.",
        )
    if normalized_source not in API_KEY_SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Connector source is not supported.",
        )

    api_key = _validate_api_key_or_422(payload.api_key)
    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant_id,
        source=normalized_source,
    )
    if connector is None:
        connector = ConnectorIntegration(
            tenant_id=tenant_id,
            source=normalized_source,
            auth_mode="api_key",
        )
        db.add(connector)
        db.flush()

    connector.auth_mode = "api_key"
    connector.status = "connected"
    connector.shop_domain = None
    connector.oauth_state = None
    connector.connected_at = datetime.now(UTC)
    connector.last_sync_requested_at = datetime.now(UTC)
    vault_entry = _upsert_connector_vault_secret(
        db,
        tenant_id=tenant_id,
        connector=connector,
        secret_value=api_key,
        secret_type="api_key",
    )
    connector.credential_ref = str(vault_entry.id)
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.api_key_connected",
        entity_type="connector",
        entity_id=str(connector.id),
        details={"source": normalized_source, "sync_initiated": True},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
    )


@app.post(
    "/tenants/{tenant_id}/connectors/{source}/reauthorize",
    response_model=ConnectorResponse,
)
def reauthorize_oauth_connector(
    tenant_id: uuid.UUID,
    source: str,
    payload: ConnectorOAuthReauthorizeRequest,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorResponse:
    _get_tenant_or_404(db, tenant_id)
    normalized_source = source.strip().lower()
    if normalized_source not in OAUTH_PREFERRED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This source does not support OAuth reauthorization.",
        )

    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant_id,
        source=normalized_source,
    )
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found.",
        )
    if connector.auth_mode != "oauth":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Connector is not configured for OAuth.",
        )

    previous_credential_ref = connector.credential_ref
    if payload.shop_domain is not None:
        connector.shop_domain = payload.shop_domain.strip().lower()
    connector.status = "connected"
    connector.connected_at = connector.connected_at or datetime.now(UTC)
    connector.oauth_expires_at = datetime.now(UTC) + timedelta(
        days=OAUTH_TOKEN_LIFETIME_DAYS
    )
    connector.oauth_expiry_warning_sent_at = None
    connector.oauth_expired_alert_sent_at = None
    connector.last_sync_requested_at = datetime.now(UTC)
    connector.error_message = None

    vault_entry = _upsert_connector_vault_secret(
        db,
        tenant_id=tenant_id,
        connector=connector,
        secret_value=payload.authorization_code,
        secret_type="oauth_code",
    )
    connector.credential_ref = str(vault_entry.id)

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.oauth_reauthorized",
        entity_type="connector",
        entity_id=str(connector.id),
        details={
            "source": normalized_source,
            "previous_credential_ref": previous_credential_ref,
            "new_credential_ref": connector.credential_ref,
            "credential_rotated": True,
            "sync_resumed": True,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
    )


@app.post(
    "/tenants/{tenant_id}/connectors/{source}/resync",
    response_model=ConnectorManualResyncResponse,
)
def trigger_connector_manual_resync(
    tenant_id: uuid.UUID,
    source: str,
    auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorManualResyncResponse:
    _get_tenant_or_404(db, tenant_id)
    normalized_source = source.strip().lower()
    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant_id,
        source=normalized_source,
    )
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found.",
        )
    if connector.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connector must be connected before resync.",
        )

    queued_tasks = _queue_manual_resync_tasks(source=normalized_source)
    requested_at = datetime.now(UTC)
    connector.last_sync_requested_at = requested_at
    connector.error_message = None

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="connector.manual_resync_triggered",
        entity_type="connector",
        entity_id=str(connector.id),
        details={
            "source": normalized_source,
            "queued_task_count": len(queued_tasks),
            "queued_tasks": queued_tasks,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(connector)

    return ConnectorManualResyncResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        status=connector.status,
        last_sync_requested_at=connector.last_sync_requested_at
        if connector.last_sync_requested_at is not None
        else requested_at,
        queued_tasks=queued_tasks,
    )


@app.get(
    "/tenants/{tenant_id}/connectors/{source}/status",
    response_model=ConnectorIntegrationStatusResponse,
)
def get_connector_integration_status(
    tenant_id: uuid.UUID,
    source: str,
    _auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ConnectorIntegrationStatusResponse:
    _get_tenant_or_404(db, tenant_id)
    normalized_source = source.strip().lower()
    connector = _get_connector_for_tenant(
        db,
        tenant_id=tenant_id,
        source=normalized_source,
    )
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found.",
        )

    request_now = datetime.now(UTC)
    stale_data_gate, stale_data_reason = _derive_stale_data_gate(
        connector, now=request_now
    )
    (
        sync_jobs_total_7d,
        sync_jobs_success_7d,
        sync_jobs_failed_7d,
        sync_uptime_percentage_7d,
        sync_failure_rate_percentage_7d,
    ) = _derive_sync_metrics(db, connector=connector, now=request_now)

    return ConnectorIntegrationStatusResponse(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        source=connector.source,
        auth_mode=connector.auth_mode,
        status=connector.status,
        shop_domain=connector.shop_domain,
        connected_at=connector.connected_at,
        last_synced_at=connector.last_synced_at,
        last_sync_requested_at=connector.last_sync_requested_at,
        error_message=connector.error_message,
        sync_progress=_derive_sync_progress(connector),
        freshness_label=_derive_freshness_label(connector, now=request_now),
        stale_data_gate=stale_data_gate,
        stale_data_reason=stale_data_reason,
        sync_jobs_total_7d=sync_jobs_total_7d,
        sync_jobs_success_7d=sync_jobs_success_7d,
        sync_jobs_failed_7d=sync_jobs_failed_7d,
        sync_uptime_percentage_7d=sync_uptime_percentage_7d,
        sync_failure_rate_percentage_7d=sync_failure_rate_percentage_7d,
    )


# ---------------------------------------------------------------------------
# E3: Workspace health aggregation endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/tenants/{tenant_id}/workspace-health",
    response_model=WorkspaceHealthResponse,
)
def get_workspace_health(
    tenant_id: uuid.UUID,
    _auth: AdminIntegrationsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> WorkspaceHealthResponse:
    """Get aggregated health status for all connectors in workspace (E3).

    Provides overview of connector health for Brand Admin to monitor
    integration status and data quality.

    Args:
        tenant_id: Tenant identifier

    Returns:
        WorkspaceHealthResponse with aggregated health metrics

    Raises:
        404: If tenant not found
    """
    _get_tenant_or_404(db, tenant_id)

    # Fetch all connectors for tenant
    connectors = list(
        db.scalars(
            select(ConnectorIntegration).where(
                ConnectorIntegration.tenant_id == tenant_id
            )
        ).all()
    )

    request_now = datetime.now(UTC)
    connector_summaries: list[ConnectorHealthSummary] = []
    health_counts = {"healthy": 0, "degraded": 0, "critical": 0, "unknown": 0}

    for connector in connectors:
        health_status = _compute_connector_health_status(connector, now=request_now)
        sync_progress = _derive_sync_progress(connector)
        freshness_label = _derive_freshness_label(connector, now=request_now)

        # Update connector health_status in database
        connector.health_status = health_status

        connector_summaries.append(
            ConnectorHealthSummary(
                connector_id=connector.id,
                source=connector.source,
                health_status=health_status,
                status=connector.status,
                last_synced_at=connector.last_synced_at,
                error_message=connector.error_message,
                sync_progress=sync_progress,
                freshness_label=freshness_label,
            )
        )

        # Track health counts
        if health_status in health_counts:
            health_counts[health_status] += 1

    # Commit health_status updates
    db.commit()

    # Compute overall workspace health
    overall_health_status = "unknown"
    if not connectors:
        overall_health_status = "healthy"  # No connectors is considered healthy
    elif health_counts["critical"] > 0:
        overall_health_status = "critical"  # Any critical makes workspace critical
    elif health_counts["degraded"] > 0:
        overall_health_status = "degraded"  # Any degraded makes workspace degraded
    elif health_counts["healthy"] == len(connectors):
        overall_health_status = "healthy"  # All healthy

    return WorkspaceHealthResponse(
        tenant_id=tenant_id,
        overall_health_status=overall_health_status,
        connectors=connector_summaries,
        total_connectors=len(connectors),
        healthy_count=health_counts["healthy"],
        degraded_count=health_counts["degraded"],
        critical_count=health_counts["critical"],
        unknown_count=health_counts["unknown"],
        last_updated_at=request_now,
    )


# ---------------------------------------------------------------------------
# E4: Support tickets (FR-092, FR-093, FR-099, FR-100, FR-101)
# ---------------------------------------------------------------------------


@app.post("/support-tickets", response_model=SupportTicketResponse)
def create_support_ticket(
    payload: SupportTicketCreate,
    auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SupportTicketResponse:
    """Create a new support ticket (E4, FR-092).

    Args:
        payload: Ticket creation details

    Returns:
        Created ticket

    Raises:
        404: If tenant or creator user not found
    """
    # Verify tenant exists
    _get_tenant_or_404(db, payload.tenant_id)

    # Verify creator exists
    creator = _get_user_by_email(db, auth.email)
    if creator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creator user not found.",
        )

    ticket = SupportTicket(
        tenant_id=payload.tenant_id,
        priority=payload.priority,
        issue_type=payload.issue_type,
        title=payload.title,
        description=payload.description,
        created_by_user_id=creator.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return SupportTicketResponse.model_validate(ticket)


@app.get("/support-tickets", response_model=SupportTicketListResponse)
def list_support_tickets(
    auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
    status_filter: str | None = None,
    priority: str | None = None,
    tenant_id: uuid.UUID | None = None,
) -> SupportTicketListResponse:
    """List support tickets with optional filters (E4, FR-092).

    Args:
        status_filter: Filter by status (open, in_progress, resolved, closed)
        priority: Filter by priority (low, medium, high, urgent)
        tenant_id: Filter by tenant

    Returns:
        Paginated ticket list
    """
    query = select(SupportTicket)

    if status_filter:
        query = query.where(SupportTicket.status == status_filter)
    if priority:
        query = query.where(SupportTicket.priority == priority)
    if tenant_id:
        query = query.where(SupportTicket.tenant_id == tenant_id)

    query = query.order_by(SupportTicket.created_at.desc())

    tickets = list(db.scalars(query).all())
    return SupportTicketListResponse(
        tickets=[SupportTicketResponse.model_validate(t) for t in tickets],
        total=len(tickets),
    )


@app.get("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_support_ticket(
    ticket_id: uuid.UUID,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SupportTicketResponse:
    """Get a single support ticket (E4, FR-092).

    Args:
        ticket_id: Ticket identifier

    Returns:
        Ticket details

    Raises:
        404: If ticket not found
    """
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    return SupportTicketResponse.model_validate(ticket)


@app.patch("/support-tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(
    ticket_id: uuid.UUID,
    payload: SupportTicketUpdate,
    auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SupportTicketResponse:
    """Update support ticket (assign, change status, add notes) (E4, FR-093, FR-099).

    Args:
        ticket_id: Ticket identifier
        payload: Update fields

    Returns:
        Updated ticket

    Raises:
        404: If ticket or assigned user not found
        409: If trying to update a closed ticket
    """
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    if ticket.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a closed ticket.",
        )

    # Update fields if provided
    if payload.status is not None:
        # Don't allow direct close via PATCH (must use close endpoint)
        if payload.status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /support-tickets/{id}/close endpoint to close tickets.",
            )
        ticket.status = payload.status

    if payload.priority is not None:
        ticket.priority = payload.priority

    if payload.assigned_to_user_id is not None:
        # FR-093: Assignment changes logged via updated_at
        assigned_user = db.get(User, payload.assigned_to_user_id)
        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found.",
            )
        ticket.assigned_to_user_id = payload.assigned_to_user_id

    if payload.due_date is not None:
        ticket.due_date = payload.due_date

    if payload.internal_notes is not None:
        # FR-099: Append to internal notes with timestamp
        timestamp = datetime.now(UTC).isoformat()
        new_note = f"[{timestamp}] {payload.internal_notes}"
        if ticket.internal_notes:
            ticket.internal_notes += f"\n\n{new_note}"
        else:
            ticket.internal_notes = new_note

    ticket.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(ticket)

    return SupportTicketResponse.model_validate(ticket)


@app.patch("/support-tickets/{ticket_id}/close", response_model=SupportTicketResponse)
def close_support_ticket(
    ticket_id: uuid.UUID,
    payload: SupportTicketClose,
    _auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SupportTicketResponse:
    """Close support ticket with mandatory resolution (E4, FR-100, FR-101).

    Args:
        ticket_id: Ticket identifier
        payload: Resolution summary and category (required)

    Returns:
        Closed ticket

    Raises:
        404: If ticket not found
        409: If ticket already closed
    """
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    if ticket.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is already closed.",
        )

    # FR-100, FR-101: Mandatory resolution fields
    ticket.status = "closed"
    ticket.resolution_summary = payload.resolution_summary
    ticket.resolution_category = payload.resolution_category
    ticket.closed_at = datetime.now(UTC)
    ticket.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(ticket)

    return SupportTicketResponse.model_validate(ticket)


# ---------------------------------------------------------------------------
# E5: User notification preferences and inbox (FR-007, FR-108, FR-123-125)
# ---------------------------------------------------------------------------


@app.post(
    "/user-notification-preferences",
    response_model=UserNotificationPreferenceResponse,
)
def create_user_notification_preference(
    payload: UserNotificationPreferenceCreate,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> UserNotificationPreferenceResponse:
    """Create user notification preference (E5, FR-007, FR-108).

    Args:
        payload: Preference creation details

    Returns:
        Created preference

    Raises:
        409: If preference already exists for this alert category
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check for existing preference
    existing = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user.id,
            UserNotificationPreference.tenant_id == payload.tenant_id,
            UserNotificationPreference.alert_category == payload.alert_category,
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Preference already exists for this alert category.",
        )

    preference = UserNotificationPreference(
        user_id=user.id,
        tenant_id=payload.tenant_id,
        alert_category=payload.alert_category,
        channel=payload.channel,
        is_enabled=payload.is_enabled,
    )
    db.add(preference)
    db.commit()
    db.refresh(preference)

    return UserNotificationPreferenceResponse.model_validate(preference)


@app.get(
    "/user-notification-preferences",
    response_model=UserNotificationPreferenceListResponse,
)
def list_user_notification_preferences(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
    tenant_id: UUID | None = None,
) -> UserNotificationPreferenceListResponse:
    """List user's notification preferences (E5, FR-007, FR-108).

    Args:
        tenant_id: Optional tenant filter

    Returns:
        List of user preferences
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    stmt = select(UserNotificationPreference).where(
        UserNotificationPreference.user_id == user.id
    )
    if tenant_id:
        stmt = stmt.where(UserNotificationPreference.tenant_id == tenant_id)

    stmt = stmt.order_by(UserNotificationPreference.alert_category)
    preferences = list(db.scalars(stmt).all())

    return UserNotificationPreferenceListResponse(
        preferences=[
            UserNotificationPreferenceResponse.model_validate(p) for p in preferences
        ],
        total=len(preferences),
    )


@app.patch(
    "/user-notification-preferences/{preference_id}",
    response_model=UserNotificationPreferenceResponse,
)
def update_user_notification_preference(
    preference_id: UUID,
    payload: UserNotificationPreferenceUpdate,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> UserNotificationPreferenceResponse:
    """Update user notification preference (E5, FR-007, FR-108).

    Args:
        preference_id: Preference ID
        payload: Update fields

    Returns:
        Updated preference

    Raises:
        404: If preference not found
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    preference = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.id == preference_id,
            UserNotificationPreference.user_id == user.id,
        )
    )
    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found.")

    if payload.channel is not None:
        preference.channel = payload.channel
    if payload.is_enabled is not None:
        preference.is_enabled = payload.is_enabled

    preference.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(preference)

    return UserNotificationPreferenceResponse.model_validate(preference)


@app.delete("/user-notification-preferences/{preference_id}")
def delete_user_notification_preference(
    preference_id: UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Delete user notification preference (E5, FR-007, FR-108).

    Args:
        preference_id: Preference ID

    Returns:
        204 on success

    Raises:
        404: If preference not found
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    preference = db.scalar(
        select(UserNotificationPreference).where(
            UserNotificationPreference.id == preference_id,
            UserNotificationPreference.user_id == user.id,
        )
    )
    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found.")

    db.delete(preference)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/notifications", response_model=NotificationResponse)
def create_notification(
    payload: NotificationCreate,
    auth: SuperAdminDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationResponse:
    """Create notification (E5, FR-123, internal use).

    Args:
        payload: Notification details

    Returns:
        Created notification
    """
    notification = Notification(
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        notification_type=payload.notification_type,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        deep_link=payload.deep_link,
        context_data=payload.context_data,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return NotificationResponse.model_validate(notification)


@app.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
    status_filter: str | None = None,
    notification_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationListResponse:
    """List user notifications (E5, FR-123).

    Args:
        status_filter: Filter by status (unread, read, dismissed)
        notification_type: Filter by notification type
        severity: Filter by severity
        limit: Max results (default 50, max 100)
        offset: Pagination offset

    Returns:
        List of notifications and unread count
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    stmt = select(Notification).where(Notification.user_id == user.id)

    if status_filter:
        stmt = stmt.where(Notification.status == status_filter)
    if notification_type:
        stmt = stmt.where(Notification.notification_type == notification_type)
    if severity:
        stmt = stmt.where(Notification.severity == severity)

    stmt = stmt.order_by(Notification.created_at.desc())

    # Count total and unread
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(total_stmt) or 0

    unread_stmt = select(func.count()).where(
        Notification.user_id == user.id, Notification.status == "unread"
    )
    unread_count = db.scalar(unread_stmt) or 0

    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)
    notifications = list(db.scalars(stmt).all())

    return NotificationListResponse(
        notifications=[
            NotificationResponse.model_validate(n) for n in notifications
        ],
        total=total,
        unread_count=unread_count,
    )


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationResponse:
    """Mark notification as read (E5, FR-123).

    Args:
        notification_id: Notification ID

    Returns:
        Updated notification

    Raises:
        404: If notification not found
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.status = "read"
    notification.read_at = datetime.now(UTC)
    db.commit()
    db.refresh(notification)

    return NotificationResponse.model_validate(notification)


@app.patch("/notifications/{notification_id}/dismiss")
def mark_notification_dismissed(
    notification_id: UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationResponse:
    """Mark notification as dismissed (E5, FR-123).

    Args:
        notification_id: Notification ID

    Returns:
        Updated notification

    Raises:
        404: If notification not found
    """
    user = _get_user_by_email(db, auth.email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.status = "dismissed"
    notification.dismissed_at = datetime.now(UTC)
    db.commit()
    db.refresh(notification)

    return NotificationResponse.model_validate(notification)


# ---------------------------------------------------------------------------
# Finance: cost drivers and margin drift (T-047)
# ---------------------------------------------------------------------------


@app.get(
    "/tenants/{tenant_id}/finance/cost-drivers",
    response_model=CostDriverListResponse,
)
def get_cost_drivers(
    tenant_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CostDriverListResponse:
    _get_tenant_or_404(db, tenant_id)

    latest_date: date | None = db.scalar(
        select(CostDriverSnapshot.snapshot_date)
        .where(CostDriverSnapshot.tenant_id == tenant_id)
        .order_by(CostDriverSnapshot.snapshot_date.desc())
    )
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cost driver snapshots found for this tenant.",
        )

    drivers = list(
        db.scalars(
            select(CostDriverSnapshot).where(
                CostDriverSnapshot.tenant_id == tenant_id,
                CostDriverSnapshot.snapshot_date == latest_date,
            )
        )
    )
    return CostDriverListResponse(
        snapshot_date=latest_date,
        drivers=[CostDriverSnapshotResponse.model_validate(d) for d in drivers],
    )


@app.get(
    "/tenants/{tenant_id}/finance/margin-drift-thresholds",
    response_model=MarginDriftThresholdListResponse,
)
def list_margin_drift_thresholds(
    tenant_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MarginDriftThresholdListResponse:
    _get_tenant_or_404(db, tenant_id)

    thresholds = list(
        db.scalars(
            select(MarginDriftThreshold).where(
                MarginDriftThreshold.tenant_id == tenant_id,
            )
        )
    )
    return MarginDriftThresholdListResponse(
        thresholds=[MarginDriftThresholdResponse.model_validate(t) for t in thresholds]
    )


@app.post(
    "/tenants/{tenant_id}/finance/margin-drift-thresholds",
    response_model=MarginDriftThresholdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_margin_drift_threshold(
    tenant_id: uuid.UUID,
    body: MarginDriftThresholdCreateRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MarginDriftThresholdResponse:
    _get_tenant_or_404(db, tenant_id)

    existing = db.scalar(
        select(MarginDriftThreshold).where(
            MarginDriftThreshold.tenant_id == tenant_id,
            MarginDriftThreshold.channel == body.channel,
            MarginDriftThreshold.category == body.category,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A threshold for this channel/category already exists.",
        )

    threshold = MarginDriftThreshold(
        tenant_id=tenant_id,
        channel=body.channel,
        category=body.category,
        threshold_pct=body.threshold_pct,
        is_active=True,
        created_by_user_id=None,
        effective_date=body.effective_date,
    )
    db.add(threshold)
    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.margin_drift_threshold_created",
        entity_type="margin_drift_threshold",
        entity_id=str(threshold.id),
        details={
            "channel": body.channel,
            "category": body.category,
            "threshold_pct": body.threshold_pct,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(threshold)
    return MarginDriftThresholdResponse.model_validate(threshold)


@app.put(
    "/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}",
    response_model=MarginDriftThresholdResponse,
)
def update_margin_drift_threshold(
    tenant_id: uuid.UUID,
    threshold_id: uuid.UUID,
    body: MarginDriftThresholdUpdateRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MarginDriftThresholdResponse:
    _get_tenant_or_404(db, tenant_id)

    threshold = db.scalar(
        select(MarginDriftThreshold).where(
            MarginDriftThreshold.id == threshold_id,
            MarginDriftThreshold.tenant_id == tenant_id,
        )
    )
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Margin drift threshold not found.",
        )

    if body.threshold_pct is not None:
        threshold.threshold_pct = body.threshold_pct
    if body.is_active is not None:
        threshold.is_active = body.is_active
    if body.effective_date is not None:
        threshold.effective_date = body.effective_date

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.margin_drift_threshold_updated",
        entity_type="margin_drift_threshold",
        entity_id=str(threshold_id),
        details={
            "threshold_pct": threshold.threshold_pct,
            "is_active": threshold.is_active,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(threshold)
    return MarginDriftThresholdResponse.model_validate(threshold)


@app.delete(
    "/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_margin_drift_threshold(
    tenant_id: uuid.UUID,
    threshold_id: uuid.UUID,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    _get_tenant_or_404(db, tenant_id)

    threshold = db.scalar(
        select(MarginDriftThreshold).where(
            MarginDriftThreshold.id == threshold_id,
            MarginDriftThreshold.tenant_id == tenant_id,
        )
    )
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Margin drift threshold not found.",
        )

    threshold.is_active = False
    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.margin_drift_threshold_deactivated",
        entity_type="margin_drift_threshold",
        entity_id=str(threshold_id),
        details={"channel": threshold.channel, "category": threshold.category},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()


@app.get(
    "/tenants/{tenant_id}/finance/margin-drift",
    response_model=MarginDriftListResponse,
)
def get_margin_drift(
    tenant_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MarginDriftListResponse:
    _get_tenant_or_404(db, tenant_id)

    latest_date: date | None = db.scalar(
        select(MarginDriftSnapshot.snapshot_date)
        .where(MarginDriftSnapshot.tenant_id == tenant_id)
        .order_by(MarginDriftSnapshot.snapshot_date.desc())
    )
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No margin drift snapshots found for this tenant.",
        )

    snapshots = list(
        db.scalars(
            select(MarginDriftSnapshot).where(
                MarginDriftSnapshot.tenant_id == tenant_id,
                MarginDriftSnapshot.snapshot_date == latest_date,
            )
        )
    )
    return MarginDriftListResponse(
        snapshot_date=latest_date,
        snapshots=[MarginDriftSnapshotResponse.model_validate(s) for s in snapshots],
    )


# ---------------------------------------------------------------------------
# T-048: Tiered cost inputs (FR-050 / FR-051)
# ---------------------------------------------------------------------------

_HIGH_IMPACT_TYPES: frozenset[str] = frozenset({"cogs"})


def _write_cost_input_version(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    cost_input_id: uuid.UUID,
    action: str,
    prior_amount: float | None,
    new_amount: float,
    prior_unit: str | None,
    new_unit: str,
    effective_date: date,
    variance_reason: str | None,
    actor_user_id: uuid.UUID | None,
) -> None:
    max_ver: int | None = db.scalar(
        select(func.max(CostInputVersion.version_number)).where(
            CostInputVersion.cost_input_id == cost_input_id
        )
    )
    next_ver = 1 if max_ver is None else max_ver + 1
    db.add(
        CostInputVersion(
            tenant_id=tenant_id,
            cost_input_id=cost_input_id,
            version_number=next_ver,
            action=action,
            prior_amount=prior_amount,
            new_amount=new_amount,
            prior_unit=prior_unit,
            new_unit=new_unit,
            effective_date=effective_date,
            variance_reason=variance_reason,
            actor_user_id=actor_user_id,
        )
    )


@app.get(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
    response_model=CostInputResponse,
)
def get_cost_input(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CostInputResponse:
    """FR-051: Fetch a single cost input to review its confirmation status."""
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )

    return CostInputResponse.model_validate(row)


@app.get(
    "/tenants/{tenant_id}/finance/cost-inputs",
    response_model=CostInputListResponse,
)
def list_cost_inputs(
    tenant_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    input_type: str | None = None,
    pending_confirmation: bool | None = None,
) -> CostInputListResponse:
    _get_tenant_or_404(db, tenant_id)

    stmt = (
        select(CostInput)
        .where(
            CostInput.tenant_id == tenant_id,
            CostInput.is_active.is_(True),
        )
        .order_by(CostInput.input_type, CostInput.created_at)
    )
    if input_type is not None:
        stmt = stmt.where(CostInput.input_type == input_type)
    if pending_confirmation is True:
        stmt = stmt.where(CostInput.confirmation_required.is_(True))
    elif pending_confirmation is False:
        stmt = stmt.where(CostInput.confirmation_required.is_(False))

    rows = list(db.scalars(stmt))
    return CostInputListResponse(
        cost_inputs=[CostInputResponse.model_validate(r) for r in rows]
    )


@app.post(
    "/tenants/{tenant_id}/finance/cost-inputs",
    response_model=CostInputResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cost_input(
    tenant_id: uuid.UUID,
    body: CostInputCreateRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CostInputResponse:
    _get_tenant_or_404(db, tenant_id)

    actor = _get_user_by_email(db, auth.email)
    needs_confirmation = body.input_type in _HIGH_IMPACT_TYPES

    row = CostInput(
        tenant_id=tenant_id,
        input_type=body.input_type,
        tier_label=body.tier_label,
        weight_min_kg=body.weight_min_kg,
        weight_max_kg=body.weight_max_kg,
        destination_zone=body.destination_zone,
        amount=body.amount,
        unit=body.unit,
        effective_date=body.effective_date,
        is_active=True,
        confirmation_required=needs_confirmation,
        created_by_user_id=actor.id if actor is not None else None,
    )
    db.add(row)
    db.flush()

    _write_cost_input_version(
        db,
        tenant_id=tenant_id,
        cost_input_id=row.id,
        action="created",
        prior_amount=None,
        new_amount=row.amount,
        prior_unit=None,
        new_unit=row.unit,
        effective_date=row.effective_date,
        variance_reason=body.variance_reason,
        actor_user_id=actor.id if actor is not None else None,
    )

    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.cost_input_created",
        entity_type="cost_input",
        entity_id=str(row.id),
        details={
            "input_type": row.input_type,
            "tier_label": row.tier_label,
            "amount": row.amount,
            "unit": row.unit,
            "confirmation_required": needs_confirmation,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(row)
    return CostInputResponse.model_validate(row)


@app.put(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
    response_model=CostInputResponse,
)
def update_cost_input(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    body: CostInputUpdateRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CostInputResponse:
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )

    prior_amount: float = row.amount
    prior_unit: str = row.unit

    if body.tier_label is not None:
        row.tier_label = body.tier_label
    if body.weight_min_kg is not None:
        row.weight_min_kg = body.weight_min_kg
    if body.weight_max_kg is not None:
        row.weight_max_kg = body.weight_max_kg
    if body.destination_zone is not None:
        row.destination_zone = body.destination_zone
    if body.amount is not None:
        row.amount = body.amount
    if body.unit is not None:
        row.unit = body.unit
    if body.effective_date is not None:
        row.effective_date = body.effective_date
    if body.is_active is not None:
        row.is_active = body.is_active

    if row.input_type in _HIGH_IMPACT_TYPES:
        row.confirmation_required = True
        row.confirmed_at = None
        row.confirmed_by_user_id = None

    actor = _get_user_by_email(db, auth.email)
    _write_cost_input_version(
        db,
        tenant_id=tenant_id,
        cost_input_id=row.id,
        action="updated",
        prior_amount=prior_amount,
        new_amount=row.amount,
        prior_unit=prior_unit,
        new_unit=row.unit,
        effective_date=row.effective_date,
        variance_reason=body.variance_reason,
        actor_user_id=actor.id if actor is not None else None,
    )
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.cost_input_updated",
        entity_type="cost_input",
        entity_id=str(row.id),
        details={
            "input_type": row.input_type,
            "confirmation_required": row.confirmation_required,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(row)
    return CostInputResponse.model_validate(row)


@app.post(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
)
def confirm_cost_input(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )
    if not row.confirmation_required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cost input does not require confirmation.",
        )

    actor = _get_user_by_email(db, auth.email)
    row.confirmation_required = False
    row.confirmed_at = datetime.now(tz=UTC)
    row.confirmed_by_user_id = actor.id if actor is not None else None

    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.cost_input_confirmed",
        entity_type="cost_input",
        entity_id=str(row.id),
        details={"input_type": row.input_type},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()


@app.post(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reject_cost_input(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    body: CostInputRejectRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """FR-051: Reject a pending cost input confirmation.
    
    Resets the confirmation_required flag and logs the rejection with reason.
    Cost input remains in database for history tracking.
    """
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )
    if not row.confirmation_required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cost input does not require confirmation.",
        )

    actor = _get_user_by_email(db, auth.email)
    row.confirmation_required = False
    row.confirmed_at = None
    row.confirmed_by_user_id = None

    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.cost_input_rejected",
        entity_type="cost_input",
        entity_id=str(row.id),
        details={
            "input_type": row.input_type,
            "rejection_reason": body.reason,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()


@app.delete(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_cost_input(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )

    row.is_active = False
    actor = _get_user_by_email(db, auth.email)
    _write_cost_input_version(
        db,
        tenant_id=tenant_id,
        cost_input_id=row.id,
        action="deactivated",
        prior_amount=row.amount,
        new_amount=row.amount,
        prior_unit=row.unit,
        new_unit=row.unit,
        effective_date=row.effective_date,
        variance_reason=None,
        actor_user_id=actor.id if actor is not None else None,
    )
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.cost_input_deactivated",
        entity_type="cost_input",
        entity_id=str(row.id),
        details={"input_type": row.input_type, "tier_label": row.tier_label},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()


@app.get(
    "/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history",
    response_model=CostInputHistoryResponse,
)
def get_cost_input_history(
    tenant_id: uuid.UUID,
    input_id: uuid.UUID,
    _auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CostInputHistoryResponse:
    _get_tenant_or_404(db, tenant_id)

    row = db.scalar(
        select(CostInput).where(
            CostInput.id == input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )

    versions = list(
        db.scalars(
            select(CostInputVersion)
            .where(CostInputVersion.cost_input_id == input_id)
            .order_by(CostInputVersion.version_number)
        )
    )
    return CostInputHistoryResponse(
        cost_input_id=input_id,
        versions=[CostInputVersionResponse.model_validate(v) for v in versions],
    )


@app.post(
    "/tenants/{tenant_id}/finance/restatements",
    response_model=HistoricalRestatementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_historical_restatement(
    tenant_id: uuid.UUID,
    body: HistoricalRestatementRequest,
    auth: FinanceEditCostsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> HistoricalRestatementResponse:
    """FR-056: Restate historical margin under prior vs new cost input versions.
    
    Finance Controller uses this for audit comparison and governance review.
    Computes what margin would have been under different cost scenarios.
    """
    _get_tenant_or_404(db, tenant_id)

    # Get cost input
    cost_input = db.scalar(
        select(CostInput).where(
            CostInput.id == body.cost_input_id,
            CostInput.tenant_id == tenant_id,
        )
    )
    if cost_input is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cost input not found."
        )

    # Get prior and new versions
    prior_version = db.scalar(
        select(CostInputVersion).where(
            CostInputVersion.cost_input_id == body.cost_input_id,
            CostInputVersion.version_number == body.prior_version_number,
        )
    )
    if prior_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prior version {body.prior_version_number} not found.",
        )

    new_version = db.scalar(
        select(CostInputVersion).where(
            CostInputVersion.cost_input_id == body.cost_input_id,
            CostInputVersion.version_number == body.new_version_number,
        )
    )
    if new_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"New version {body.new_version_number} not found.",
        )

    # For now, compute a simple impact metric based on the cost delta
    # In production, this would recalculate all margin metrics for the period
    prior_amount = (
        prior_version.prior_amount
        if prior_version.prior_amount
        else prior_version.new_amount
    )
    new_amount = new_version.new_amount

    # Simple approximation: assume margin impact scales linearly with cost change
    # This is a placeholder for actual margin recalculation logic
    cost_delta = new_amount - prior_amount

    # Estimate margin impact (conservative: assume 10% of cost delta flows to margin)
    prior_margin_total = 1000.0  # Placeholder
    margin_delta_absolute = cost_delta * 0.1
    new_margin_total = prior_margin_total + margin_delta_absolute
    margin_delta_pct = (
        (margin_delta_absolute / prior_margin_total * 100)
        if prior_margin_total != 0
        else 0
    )

    prior_unit = prior_version.prior_unit or prior_version.new_unit
    variance_note = (
        f"Cost input '{cost_input.tier_label}' changed from {prior_amount} "
        f"{prior_unit} to {new_amount} {new_version.new_unit} effective "
        f"{body.period_start}. Estimated margin impact: "
        f"{margin_delta_absolute:+.2f} ({margin_delta_pct:+.1f}%)"
    )

    actor = _get_user_by_email(db, auth.email)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="finance.historical_restatement_created",
        entity_type="cost_input",
        entity_id=str(body.cost_input_id),
        details={
            "period_start": body.period_start.isoformat(),
            "period_end": body.period_end.isoformat(),
            "prior_version": body.prior_version_number,
            "new_version": body.new_version_number,
            "margin_delta": margin_delta_absolute,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()

    return HistoricalRestatementResponse(
        period_start=body.period_start,
        period_end=body.period_end,
        cost_input_id=body.cost_input_id,
        cost_input_type=cost_input.input_type,
        cost_input_label=cost_input.tier_label,
        prior_version_number=body.prior_version_number,
        new_version_number=body.new_version_number,
        prior_amount=prior_amount,
        new_amount=new_amount,
        prior_unit=prior_unit,
        new_unit=new_version.new_unit,
        prior_margin_total=prior_margin_total,
        new_margin_total=new_margin_total,
        margin_delta_absolute=margin_delta_absolute,
        margin_delta_pct=margin_delta_pct,
        variance_note=variance_note,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# T-050: Inventory risk endpoints (FR-058 to FR-062)
# ---------------------------------------------------------------------------


@app.get(
    "/tenants/{tenant_id}/inventory/risk",
    response_model=InventoryRiskListResponse,
)
def get_inventory_risk(
    tenant_id: uuid.UUID,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    status_filter: str | None = None,
) -> InventoryRiskListResponse:
    """Return the latest inventory risk snapshot for the tenant."""
    latest_date: date | None = db.scalar(
        select(func.max(InventoryRiskSnapshot.snapshot_date)).where(
            InventoryRiskSnapshot.tenant_id == tenant_id
        )
    )
    if latest_date is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No inventory risk snapshots found.",
        )
    q = select(InventoryRiskSnapshot).where(
        InventoryRiskSnapshot.tenant_id == tenant_id,
        InventoryRiskSnapshot.snapshot_date == latest_date,
    )
    if status_filter is not None:
        q = q.where(InventoryRiskSnapshot.status == status_filter)
    rows = list(db.scalars(q.order_by(InventoryRiskSnapshot.sku)))
    from backend.app.schemas.inventory import InventoryRiskSnapshotResponse as _Resp

    return InventoryRiskListResponse(
        snapshot_date=latest_date,
        snapshots=[_Resp.model_validate(r) for r in rows],
    )


@app.get(
    "/tenants/{tenant_id}/inventory/risk-thresholds",
    response_model=InventoryRiskThresholdListResponse,
)
def list_inventory_risk_thresholds(
    tenant_id: uuid.UUID,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> InventoryRiskThresholdListResponse:
    rows = list(
        db.scalars(
            select(InventoryRiskThreshold)
            .where(InventoryRiskThreshold.tenant_id == tenant_id)
            .order_by(InventoryRiskThreshold.category)
        )
    )
    return InventoryRiskThresholdListResponse(
        thresholds=[InventoryRiskThresholdResponse.model_validate(r) for r in rows]
    )


@app.post(
    "/tenants/{tenant_id}/inventory/risk-thresholds",
    response_model=InventoryRiskThresholdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_risk_threshold(
    tenant_id: uuid.UUID,
    body: InventoryRiskThresholdCreateRequest,
    auth: OperationsInventoryDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> InventoryRiskThresholdResponse:
    actor = _get_user_by_email(db, auth.email)
    row = InventoryRiskThreshold(
        tenant_id=tenant_id,
        category=body.category,
        stockout_alert_days=body.stockout_alert_days,
        overstock_weeks_threshold=body.overstock_weeks_threshold,
        slow_moving_min_qty=body.slow_moving_min_qty,
        slow_moving_min_weeks_cover=body.slow_moving_min_weeks_cover,
        slow_moving_min_capital=body.slow_moving_min_capital,
        effective_date=body.effective_date,
        created_by_user_id=actor.id if actor is not None else None,
    )
    db.add(row)
    try:
        db.flush()
    except Exception as exc:
        db.rollback()
        if "inventory_risk_thresholds" in str(exc) and (
            "uq_inventory_risk_threshold_per_tenant_category" in str(exc)
            or "UNIQUE constraint failed" in str(exc)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A threshold for this category already exists.",
            ) from exc
        raise
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="inventory.risk_threshold_created",
        entity_type="inventory_risk_threshold",
        entity_id=str(row.id),
        details={"category": body.category},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(row)
    return InventoryRiskThresholdResponse.model_validate(row)


@app.put(
    "/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}",
    response_model=InventoryRiskThresholdResponse,
)
def update_inventory_risk_threshold(
    tenant_id: uuid.UUID,
    threshold_id: uuid.UUID,
    body: InventoryRiskThresholdUpdateRequest,
    auth: OperationsInventoryDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> InventoryRiskThresholdResponse:
    row = db.scalar(
        select(InventoryRiskThreshold).where(
            InventoryRiskThreshold.id == threshold_id,
            InventoryRiskThreshold.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory risk threshold not found.",
        )
    actor = _get_user_by_email(db, auth.email)
    patch = body.model_dump(exclude_unset=True)
    for field, val in patch.items():
        setattr(row, field, val)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="inventory.risk_threshold_updated",
        entity_type="inventory_risk_threshold",
        entity_id=str(row.id),
        details={"patch": patch},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(row)
    return InventoryRiskThresholdResponse.model_validate(row)


@app.delete(
    "/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory_risk_threshold(
    tenant_id: uuid.UUID,
    threshold_id: uuid.UUID,
    auth: OperationsInventoryDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    row = db.scalar(
        select(InventoryRiskThreshold).where(
            InventoryRiskThreshold.id == threshold_id,
            InventoryRiskThreshold.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory risk threshold not found.",
        )
    actor = _get_user_by_email(db, auth.email)
    row.is_active = False
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="inventory.risk_threshold_deactivated",
        entity_type="inventory_risk_threshold",
        entity_id=str(row.id),
        details={"category": row.category},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()


# Warehouse/Location inventory endpoints (T-069)


@app.get(
    "/tenants/{tenant_id}/inventory/warehouses",
    response_model=MultiWarehouseInventoryResponse,
)
def list_warehouse_inventory(
    tenant_id: uuid.UUID,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> MultiWarehouseInventoryResponse:
    """List inventory health across all warehouses/locations.
    
    Returns aggregated inventory health. In Phase 2, will support
    per-location inventory tracking when ShopifyInventoryItem.location_id
    is synced with snapshot data.
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    snapshot_date = datetime.now(UTC).date()
    inventory_items = db.scalars(
        select(InventoryRiskSnapshot).where(
            InventoryRiskSnapshot.tenant_id == tenant_id,
            InventoryRiskSnapshot.snapshot_date == snapshot_date,
        )
    ).all()

    warehouse_views = []
    data_confidence = "high"

    if inventory_items:
        total_skus = len(inventory_items)
        total_quantity = sum(item.current_quantity for item in inventory_items)
        critical_stockout_risk = sum(
            1
            for item in inventory_items
            if item.status == "critical_stockout_risk"
        )
        stockout_alert_days_count = sum(
            1
            for item in inventory_items
            if item.days_to_stockout is not None
            and item.days_to_stockout <= 7
        )
        overstock_count = sum(
            1
            for item in inventory_items
            if item.status == "overstock"
        )
        slow_moving_count = sum(
            1
            for item in inventory_items
            if item.status == "slow_moving"
        )
        capital_at_risk = sum(
            item.capital_at_risk or 0 for item in inventory_items
        )
        days_to_stockout_list = [
            item.days_to_stockout
            for item in inventory_items
            if item.days_to_stockout is not None
        ]
        average_days_to_stockout = (
            sum(days_to_stockout_list) / len(days_to_stockout_list)
            if days_to_stockout_list
            else None
        )

        warehouse_views.append(
            WarehouseInventoryHealthResponse(
                location=LocationResponse(
                    id=uuid.uuid4(),
                    external_location_id="aggregate",
                    name="All Locations (Aggregate)",
                    address=None,
                    location_type="aggregate",
                    synced_at=datetime.now(UTC),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                ),
                total_skus=total_skus,
                total_quantity=total_quantity,
                critical_stockout_risk=critical_stockout_risk,
                stockout_alert_days_count=stockout_alert_days_count,
                overstock_count=overstock_count,
                slow_moving_count=slow_moving_count,
                capital_at_risk=capital_at_risk,
                average_days_to_stockout=average_days_to_stockout,
                data_freshness="complete",
                snapshot_date=snapshot_date,
            )
        )

    aggregate_total_skus = sum(wv.total_skus for wv in warehouse_views)
    aggregate_total_quantity = sum(wv.total_quantity for wv in warehouse_views)
    aggregate_critical_risk = sum(
        wv.critical_stockout_risk for wv in warehouse_views
    )

    return MultiWarehouseInventoryResponse(
        warehouse_views=warehouse_views,
        aggregate_total_skus=aggregate_total_skus,
        aggregate_total_quantity=aggregate_total_quantity,
        aggregate_critical_risk=aggregate_critical_risk,
        snapshot_date=snapshot_date,
        data_confidence=data_confidence,
    )


@app.get(
    "/tenants/{tenant_id}/inventory/skus/{sku_id}/stockout-impact",
    response_model=StockoutImpactResponse,
)
def get_sku_stockout_impact(
    tenant_id: uuid.UUID,
    sku_id: str,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> StockoutImpactResponse:
    """Get estimated revenue and repeat purchase impact of SKU stockout."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    snapshot_date = datetime.now(UTC).date()
    sku_snapshots = db.scalars(
        select(InventoryRiskSnapshot).where(
            InventoryRiskSnapshot.tenant_id == tenant_id,
            InventoryRiskSnapshot.sku == sku_id,
            InventoryRiskSnapshot.snapshot_date == snapshot_date,
        )
    ).all()

    if not sku_snapshots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found in inventory.",
        )

    first_snapshot = sku_snapshots[0]
    total_units = sum(s.current_quantity for s in sku_snapshots)

    estimated_lost_revenue_7d = total_units * 50.0
    estimated_lost_revenue_30d = total_units * 200.0
    repeat_purchase_risk_customers = int(total_units * 0.4)

    days_to_stockout_by_location = {}
    for snapshot in sku_snapshots:
        location_id = getattr(snapshot, "location_id", "unknown")
        days_to_stockout_by_location[str(location_id)] = snapshot.days_to_stockout

    priority = (
        "critical"
        if any(s.status == "critical_stockout_risk" for s in sku_snapshots)
        else (
            "high"
            if any(
                s.days_to_stockout and s.days_to_stockout <= 7
                for s in sku_snapshots
            )
            else "medium"
        )
    )

    reorder_recommendation = (
        "Reorder immediately to prevent stockout" if priority == "critical"
        else "Reorder within 3 days" if priority == "high"
        else "Monitor stock levels"
    )

    return StockoutImpactResponse(
        sku=sku_id,
        product_title=first_snapshot.product_title,
        variant_title=first_snapshot.variant_title,
        estimated_lost_revenue_7d=estimated_lost_revenue_7d,
        estimated_lost_revenue_30d=estimated_lost_revenue_30d,
        repeat_purchase_risk_customers=repeat_purchase_risk_customers,
        days_to_stockout_by_location=days_to_stockout_by_location,
        total_units_across_locations=total_units,
        reorder_recommendation=reorder_recommendation,
        priority=priority,
    )


@app.get(
    "/tenants/{tenant_id}/inventory/skus/{sku_id}/logistics-costs",
    response_model=LogisticsCostBreakdownResponse,
)
def get_sku_logistics_costs(
    tenant_id: uuid.UUID,
    sku_id: str,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> LogisticsCostBreakdownResponse:
    """Get estimated logistics cost breakdown for a SKU."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    snapshot_date = datetime.now(UTC).date()
    sku_snapshots = db.scalars(
        select(InventoryRiskSnapshot).where(
            InventoryRiskSnapshot.tenant_id == tenant_id,
            InventoryRiskSnapshot.sku == sku_id,
            InventoryRiskSnapshot.snapshot_date == snapshot_date,
        )
    ).all()

    if not sku_snapshots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found in inventory.",
        )

    first_snapshot = sku_snapshots[0]
    total_units = sum(s.current_quantity for s in sku_snapshots)

    inbound_cost_per_unit = 2.50
    outbound_cost_per_unit = 3.75
    storage_cost_per_unit_per_day = 0.05
    return_processing_cost_per_unit = 1.50

    total_estimated_logistics_cost = (
        (inbound_cost_per_unit + outbound_cost_per_unit) * total_units
        + storage_cost_per_unit_per_day * 30 * total_units
        + return_processing_cost_per_unit * total_units * 0.1
    )

    margin_impact_pct = (total_estimated_logistics_cost / (total_units * 100)) * 100

    cost_reduction_opportunity = (
        "High: Consider vendor consolidation" if margin_impact_pct > 5
        else "Medium: Optimize return processing" if margin_impact_pct > 2
        else "Low: Current costs are acceptable"
    )

    optimization_notes = (
        "Review inbound carrier selection for cost reduction."
        if inbound_cost_per_unit is not None and inbound_cost_per_unit > 2.0
        else None
    )

    return LogisticsCostBreakdownResponse(
        sku=sku_id,
        product_title=first_snapshot.product_title,
        inbound_cost_per_unit=inbound_cost_per_unit,
        outbound_cost_per_unit=outbound_cost_per_unit,
        storage_cost_per_unit_per_day=storage_cost_per_unit_per_day,
        return_processing_cost_per_unit=return_processing_cost_per_unit,
        total_estimated_logistics_cost=total_estimated_logistics_cost,
        margin_impact_pct=margin_impact_pct,
        cost_reduction_opportunity=cost_reduction_opportunity,
        optimization_notes=optimization_notes,
    )


@app.get(
    "/tenants/{tenant_id}/operational/impact",
    response_model=OperationalImpactListResponse,
)
def list_operational_impact_snapshots(
    tenant_id: uuid.UUID,
    _auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    sku: str | None = None,
) -> OperationalImpactListResponse:
    stmt = (
        select(OperationalImpactSnapshot)
        .where(
            OperationalImpactSnapshot.tenant_id == tenant_id,
            OperationalImpactSnapshot.snapshot_date
            == select(func.max(OperationalImpactSnapshot.snapshot_date))
            .where(OperationalImpactSnapshot.tenant_id == tenant_id)
            .scalar_subquery(),
        )
        .order_by(OperationalImpactSnapshot.sku)
    )
    if sku is not None:
        stmt = stmt.where(OperationalImpactSnapshot.sku == sku)
    rows = list(db.scalars(stmt))
    snap_date = rows[0].snapshot_date if rows else date.today()
    return OperationalImpactListResponse(
        snapshot_date=snap_date,
        snapshots=[
            OperationalImpactSnapshotResponse.model_validate(r) for r in rows
        ],
    )


@app.get(
    "/tenants/{tenant_id}/locale",
    response_model=TenantLocaleResponse,
)
def get_tenant_locale(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> TenantLocaleResponse:
    """Return the tenant's base currency and locale settings."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )
    return TenantLocaleResponse.model_validate(tenant)


@app.patch(
    "/tenants/{tenant_id}/locale",
    response_model=TenantLocaleResponse,
)
def update_tenant_locale(
    tenant_id: uuid.UUID,
    body: TenantLocaleUpdateRequest,
    auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> TenantLocaleResponse:
    """Update base_currency and/or locale for a tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )
    changed: dict[str, str] = {}
    if body.base_currency is not None:
        changed["base_currency"] = body.base_currency
        tenant.base_currency = body.base_currency
        # Recalibrate OPS-001 to the new currency if the tenant has not
        # customised it manually.  Reset suggested_value so the engine
        # recomputes it in the new currency on its next run.
        ops_row = db.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant_id,
                TenantRuleThreshold.rule_id == "OPS-001",
                TenantRuleThreshold.is_customised.is_(False),
            )
        )
        if ops_row is not None:
            new_scale = OPS_CURRENCY_SCALE_VS_USD.get(body.base_currency, 1.0)
            ops_row.threshold_value = round(OPS_USD_DEFAULT * new_scale, 2)
            ops_row.threshold_unit = body.base_currency
            ops_row.suggested_value = None
    if body.locale is not None:
        changed["locale"] = body.locale
        tenant.locale = body.locale
    if changed:
        actor = _get_user_by_email(db, auth.email)
        write_audit_event(
            db,
            tenant_id=tenant_id,
            action="tenant.locale_updated",
            entity_type="tenant",
            entity_id=str(tenant_id),
            details=changed,
            actor_user_id=actor.id if actor is not None else None,
        )
        db.commit()
    db.refresh(tenant)
    return TenantLocaleResponse.model_validate(tenant)


@app.get(
    "/tenants/{tenant_id}/recommendations",
    response_model=RecommendationListResponse,
)
def get_tenant_recommendations(
    tenant_id: uuid.UUID,
    _auth: IntelRecommendationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    domain: str | None = None,
    rec_status: str | None = None,
    gap_flag: str | None = None,
    has_outcome: bool | None = None,
) -> RecommendationListResponse:
    """FR-071, FR-076, FR-077 / T-062, T-063: List recommendations with filters.

    gap_flag: filter to "warning" or "escalated" implementation gap status.
    has_outcome: if True, show only recs with outcome_observed_at populated.
    """
    stmt = select(Recommendation).where(Recommendation.tenant_id == tenant_id)
    if domain is not None:
        stmt = stmt.where(Recommendation.domain == domain)
    if rec_status is not None:
        stmt = stmt.where(Recommendation.status == rec_status)
    if gap_flag is not None:
        stmt = stmt.where(Recommendation.implementation_gap_flag == gap_flag)
    if has_outcome is not None:
        if has_outcome:
            stmt = stmt.where(Recommendation.outcome_observed_at.isnot(None))
        else:
            stmt = stmt.where(Recommendation.outcome_observed_at.is_(None))
    stmt = stmt.order_by(Recommendation.priority, Recommendation.created_at.desc())
    items = list(db.scalars(stmt))
    
    # Filter out low-confidence recommendations (< 20% confidence)
    MIN_CONFIDENCE = 0.20
    filtered_items = [
        r for r in items
        if r.source == "threshold" or r.confidence_score >= MIN_CONFIDENCE
    ]
    
    # Deduplicate threshold-based recommendations by signal_summary
    seen_signals: set[str] = set()
    deduplicated_items = []
    for r in filtered_items:
        if r.source == "threshold":
            if r.signal_summary not in seen_signals:
                seen_signals.add(r.signal_summary)
                deduplicated_items.append(r)
        else:
            deduplicated_items.append(r)
    
    return RecommendationListResponse(
        items=[RecommendationResponse.model_validate(r) for r in deduplicated_items],
        total=len(deduplicated_items),
    )


@app.get(
    "/tenants/{tenant_id}/recommendations/{recommendation_id}",
    response_model=RecommendationDetailResponse,
)
def get_recommendation_detail(
    tenant_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    _auth: IntelRecommendationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> RecommendationDetailResponse:
    """E6 / FR-126: Get recommendation with full provenance of spawned simulations.

    Returns the recommendation along with all simulations that were launched
    from it, allowing users to see the complete history of scenario analysis
    for this recommendation.
    """
    # Fetch recommendation
    rec = db.scalar(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id,
        )
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )

    # Fetch all simulations spawned from this recommendation
    simulations = db.scalars(
        select(Simulation)
        .where(
            Simulation.recommendation_id == recommendation_id,
            Simulation.tenant_id == tenant_id,
            Simulation.is_deleted.is_(False),
        )
        .order_by(Simulation.created_at.desc())
    ).all()

    # Convert simulations to dict for response
    simulation_list = [
        {
            "id": str(sim.id),
            "name": sim.name,
            "description": sim.description,
            "domain": sim.domain,
            "simulation_type": sim.simulation_type,
            "confidence_level": sim.confidence_level,
            "created_at": sim.created_at.isoformat(),
            "updated_at": sim.updated_at.isoformat(),
        }
        for sim in simulations
    ]

    return RecommendationDetailResponse(
        recommendation=RecommendationResponse.model_validate(rec),
        simulations=simulation_list,
        simulation_count=len(simulation_list),
    )


@app.get(
    "/tenants/{tenant_id}/recommendations/{recommendation_id}/simulations",
    response_model=SimulationListResponse,
)
def list_simulations_for_recommendation(
    tenant_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    _auth: IntelSimulationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    include_deleted: bool = False,
) -> SimulationListResponse:
    """E6 / FR-126: List all simulations spawned from a recommendation.

    Returns all simulations that were created from this recommendation,
    ordered by creation time (most recent first). Useful for comparing
    multiple simulation attempts with different parameters.

    Query parameters:
    - include_deleted: If true, include soft-deleted simulations (default: false)
    """
    # Verify recommendation exists
    rec = db.scalar(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id,
        )
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )

    # Build query for simulations
    stmt = select(Simulation).where(
        Simulation.recommendation_id == recommendation_id,
        Simulation.tenant_id == tenant_id,
    )

    if not include_deleted:
        stmt = stmt.where(Simulation.is_deleted.is_(False))

    stmt = stmt.order_by(Simulation.created_at.desc())

    simulations = db.scalars(stmt).all()

    return SimulationListResponse(
        simulations=[SimulationResponse.model_validate(s) for s in simulations],
        total_count=len(simulations),
    )


@app.patch(
    "/tenants/{tenant_id}/recommendations/{recommendation_id}/status",
    response_model=RecommendationResponse,
)
def update_recommendation_status(
    tenant_id: uuid.UUID,
    recommendation_id: uuid.UUID,
    body: RecommendationStatusUpdateRequest,
    auth: IntelRecommendationsReviewDep,
    db: Session = Depends(get_db),  # noqa: B008  # noqa: B008
) -> Recommendation:
    """FR-073 / T-059: Transition a recommendation's status.

    Enforces the lifecycle state machine from T-058.  Any illegal transition
    returns 422.  Every successful transition is recorded as an audit event.
    """
    rec = db.scalar(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.tenant_id == tenant_id,
        )
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )

    try:
        new_status = transition(rec.status, body.to_status)
    except (ValueError, InvalidTransitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    old_status = rec.status
    rec.status = new_status
    if body.note is not None:
        rec.review_note = body.note

    # FR-076 / T-062: Stamp approved_at when recommendation is approved
    if new_status == RecommendationStatus.APPROVED:
        rec.approved_at = datetime.now(UTC)

    # FR-069, FR-077 / T-063: Stamp implemented_at when recommendation
    # transitions to implemented_externally status. Outcome service will
    # capture metrics snapshots and perform impact analysis after window.
    if new_status == RecommendationStatus.IMPLEMENTED_EXTERNALLY:
        rec.implemented_at = datetime.now(UTC)
        # Capture before snapshot from current tenant metrics (placeholder).
        # Real implementation queries actual synced metric snapshots.
        rec.outcome_metrics_before = {
            "contribution_margin_pct": 0.0,
            "cac_payback_period": 0.0,
            "blended_roas": 0.0,
            "return_rate_pct": 0.0,
            "repeat_purchase_rate_pct": 0.0,
            "cac_by_channel": 0.0,
            "time_to_insight": 0.0,
        }

    # FR-069, FR-077 / T-063: Stamp outcome_observed_at when recommendation
    # transitions to outcome_observed status. outcome_metrics_after and
    # outcome_impact_summary should already be populated by the outcome service.
    if new_status == RecommendationStatus.OUTCOME_OBSERVED:
        rec.outcome_observed_at = datetime.now(UTC)

    if new_status == RecommendationStatus.REJECTED:
        record_rejection(db, tenant_id=tenant_id, rule_id=rec.rule_id)

    actor = db.scalar(
        select(User).where(User.email == auth.email)
    )
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="recommendation.status_changed",
        entity_type="recommendation",
        entity_id=str(recommendation_id),
        details={
            "from_status": old_status,
            "to_status": str(new_status),
            "note": body.note,
        },
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(rec)
    return rec


@app.post(
    "/tenants/{tenant_id}/recommendations/{recommendation_id}/simulate",
    response_model=RecommendationSimulationLaunchResponse,
)
def launch_simulation_from_recommendation(
    tenant_id: UUID,
    recommendation_id: UUID,
    _auth: IntelSimulationsRunDep,
    db: Session = Depends(get_db),  # noqa: B008
    request_body: RecommendationSimulationLaunchRequest | None = Body(  # noqa: B008
        default=None
    ),
) -> RecommendationSimulationLaunchResponse:
    """FR-126 / T-117: Launch simulation pre-populated from a recommendation.

    When a user clicks "Simulate" on a recommendation, this endpoint:
    1. Accepts the recommendation ID
    2. Launches a simulation with parameters extracted from the recommendation
    3. Returns the newly created simulation with all three scenarios

    Allows users to test what-if scenarios based on recommendation insights
    without manually entering all the parameters.

    Request body (optional):
    - override_parameters: Dict of parameter overrides (user-provided adjustments)

    Returns: RecommendationSimulationLaunchResponse with created simulation
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Launch simulation from recommendation
    from backend.app.simulation_service import SimulationService

    service = SimulationService(db)

    try:
        override_params = None
        if request_body and request_body.override_parameters:
            override_params = request_body.override_parameters

        simulation, parameters_used = service.launch_simulation_from_recommendation(
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            override_parameters=override_params,
        )
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Build response
    sim_response = SimulationResponse.model_validate(simulation)
    domain_name = simulation.domain.capitalize()

    return RecommendationSimulationLaunchResponse(
        simulation=sim_response,
        recommendation_id=recommendation_id,
        parameters_used=parameters_used,
        message=(
            f"Simulation launched with {domain_name} parameters "
            "from recommendation."
        ),
    )


# ========== T-119: LLM Narration Layer for Recommendations ==========


@app.post(
    "/tenants/{tenant_id}/recommendations/{recommendation_id}/narrate",
    response_model=NarrationResponse,
)
def generate_narration_for_recommendation(
    tenant_id: UUID,
    recommendation_id: UUID,
    _auth: IntelRecommendationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    request_body: NarrationRequest | None = Body(  # noqa: B008
        default=None
    ),
) -> NarrationResponse:
    """FR-071, FR-079 / T-119: Generate LLM narration for a recommendation.

    When a user views a recommendation, this endpoint generates a human-readable
    narrative that explains:
    - Why this matters now (urgency context)
    - What to do (action description)
    - What could go wrong (risk framing)

    All numerical values are cited back to the simulation payload, ensuring
    full audit trail and source verification. The LLM generates words only;
    all numbers come exclusively from simulation output.

    Request body (optional):
    - override_tone: 'urgent', 'balanced', or 'cautious' (default: inferred from impact)

    Returns: NarrationResponse with narration, citations, and LLM metadata
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Generate narration from recommendation
    from backend.app.simulation_service import SimulationService

    service = SimulationService(db)

    try:
        override_tone = None
        if request_body:
            override_tone = request_body.override_tone

        narration_data = service.generate_narration_for_recommendation(
            tenant_id=tenant_id,
            recommendation_id=recommendation_id,
            override_tone=override_tone,
        )
    except ValueError as exc:
        if "found" in str(exc).lower() or "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # LLM failures, API errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Narration generation failed: {str(exc)}",
        ) from exc

    # Fetch simulation to get domain and IDs
    sim = db.scalar(
        select(Simulation).where(
            (Simulation.recommendation_id == recommendation_id)
            & (Simulation.tenant_id == tenant_id)
        )
    )
    if sim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked simulation not found.",
        )

    # Build response
    from backend.app.schemas.simulation import Citation

    citations = [
        Citation(**c) if isinstance(c, dict) else c
        for c in narration_data.get("citations", [])
    ]

    return NarrationResponse(
        recommendation_id=recommendation_id,
        simulation_id=sim.id,
        domain=sim.domain,
        urgency_context=narration_data.get("urgency_context", ""),
        action_description=narration_data.get("action_description", ""),
        risk_framing=narration_data.get("risk_framing", ""),
        citations=citations,
        narration_metadata=narration_data.get("narration_metadata", {}),
        generated_at=datetime.now(UTC),
    )


@app.get(
    "/tenants/{tenant_id}/recommendation-suppressions",
    response_model=SuppressionStateListResponse,
)
def list_recommendation_suppressions(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SuppressionStateListResponse:
    """FR-074 / T-060: List all suppression states for a tenant."""
    rows = list(
        db.scalars(
            select(RecommendationSuppressionState)
            .where(RecommendationSuppressionState.tenant_id == tenant_id)
            .order_by(RecommendationSuppressionState.rule_id)
        )
    )
    return SuppressionStateListResponse(
        items=[SuppressionStateResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@app.post(
    "/tenants/{tenant_id}/recommendation-suppressions/{rule_id}/override",
    response_model=SuppressionStateResponse,
)
def override_recommendation_suppression(
    tenant_id: uuid.UUID,
    rule_id: str,
    auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> RecommendationSuppressionState:
    """FR-074 / T-060: Lift an active suppression window for a rule.

    Brand Admins can override a suppression at any time.  The rejection
    counter is reset to 0 so subsequent rejections start a fresh cycle.
    """
    row = lift_suppression(db, tenant_id=tenant_id, rule_id=rule_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active suppression found for this rule.",
        )

    actor = db.scalar(select(User).where(User.email == auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="recommendation_suppression.overridden",
        entity_type="recommendation_suppression",
        entity_id=rule_id,
        details={"rule_id": rule_id},
        actor_user_id=actor.id if actor is not None else None,
    )
    db.commit()
    db.refresh(row)
    return row



@app.post(
    "/tenants/{tenant_id}/delegation-rules",
    response_model=DelegationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delegation_rule(
    tenant_id: uuid.UUID,
    body: DelegationRuleCreateRequest,
    auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> DelegationRule:
    """FR-075 / T-061: Create a delegation rule.

    Brand Admin delegates recommendation approval authority for a domain to
    another tenant member for a bounded date range.  The delegatee must be a
    current tenant member.  Multiple active delegations for the same domain
    are allowed.
    """
    delegatee_membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == body.delegatee_user_id,
        )
    )
    if delegatee_membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delegatee is not a member of this tenant.",
        )

    delegator = db.scalar(select(User).where(User.email == auth.email))
    rule = DelegationRule(
        tenant_id=tenant_id,
        delegator_user_id=delegator.id if delegator is not None else None,
        delegatee_user_id=body.delegatee_user_id,
        domain=body.domain,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    db.add(rule)
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="delegation_rule.created",
        entity_type="delegation_rule",
        entity_id=str(rule.id),
        details={
            "delegatee_user_id": str(body.delegatee_user_id),
            "domain": body.domain,
            "valid_from": str(body.valid_from),
            "valid_until": str(body.valid_until),
        },
        actor_user_id=delegator.id if delegator is not None else None,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.get(
    "/tenants/{tenant_id}/delegation-rules",
    response_model=DelegationRuleListResponse,
)
def list_delegation_rules(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
    active_only: bool = False,
) -> DelegationRuleListResponse:
    """FR-075 / T-061: List all delegation rules for a tenant.

    Pass active_only=true to filter to rules that have not been revoked.
    """
    q = select(DelegationRule).where(DelegationRule.tenant_id == tenant_id)
    if active_only:
        q = q.where(DelegationRule.is_active.is_(True))
    rows = list(db.scalars(q.order_by(DelegationRule.created_at)))
    return DelegationRuleListResponse(
        items=[DelegationRuleResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@app.post(
    "/tenants/{tenant_id}/delegation-rules/{delegation_id}/revoke",
    response_model=DelegationRuleResponse,
)
def revoke_delegation_rule(
    tenant_id: uuid.UUID,
    delegation_id: uuid.UUID,
    auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> DelegationRule:
    """FR-075 / T-061: Revoke an active delegation rule.

    Any Brand Admin can revoke any delegation for the tenant.  Returns 409
    if the rule is already revoked.
    """
    rule = db.scalar(
        select(DelegationRule).where(
            DelegationRule.id == delegation_id,
            DelegationRule.tenant_id == tenant_id,
        )
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delegation rule not found.",
        )
    if not rule.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delegation rule is already revoked.",
        )

    revoker = db.scalar(select(User).where(User.email == auth.email))
    rule.is_active = False
    rule.revoked_at = datetime.now(UTC)
    rule.revoked_by_user_id = revoker.id if revoker is not None else None
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="delegation_rule.revoked",
        entity_type="delegation_rule",
        entity_id=str(delegation_id),
        details={"domain": rule.domain},
        actor_user_id=revoker.id if revoker is not None else None,
    )
    db.commit()
    db.refresh(rule)
    return rule


@app.get(
    "/tenants/{tenant_id}/rule-thresholds",
    response_model=RuleThresholdListResponse,
)
def get_rule_thresholds(
    tenant_id: uuid.UUID,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> RuleThresholdListResponse:
    """FR-071 / T-054: List all rule thresholds for a tenant."""
    rows = list(
        db.scalars(
            select(TenantRuleThreshold)
            .where(TenantRuleThreshold.tenant_id == tenant_id)
            .order_by(TenantRuleThreshold.rule_id)
        )
    )
    return RuleThresholdListResponse(
        items=[RuleThresholdResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@app.patch(
    "/tenants/{tenant_id}/rule-thresholds/{rule_id}",
    response_model=RuleThresholdResponse,
)
def update_rule_threshold(
    tenant_id: uuid.UUID,
    rule_id: str,
    body: RuleThresholdUpdateRequest,
    _auth: AdminSettingsDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> TenantRuleThreshold:
    """FR-071 / T-054: Update the threshold value for a specific rule."""
    row = db.scalar(
        select(TenantRuleThreshold).where(
            TenantRuleThreshold.tenant_id == tenant_id,
            TenantRuleThreshold.rule_id == rule_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule threshold '{rule_id}' not found for this tenant.",
        )
    row.threshold_value = body.threshold_value
    row.is_customised = True
    db.commit()
    db.refresh(row)
    return row


# ============================================================================
# Saved Analysis Views (FR-032, FR-034 / T-064)
# ============================================================================


@app.post(
    "/tenants/{tenant_id}/analysis-views",
    response_model=SavedAnalysisViewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_view(
    tenant_id: uuid.UUID,
    body: SavedAnalysisViewCreateRequest,
    auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SavedAnalysisView:
    """FR-032 / T-064: Create and save a custom analysis view."""
    user = db.scalar(select(User).where(User.email == auth.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    view = SavedAnalysisView(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by_id=user.id,
        name=body.name,
        description=body.description,
        filters_config=body.filters_config,
    )
    db.add(view)
    db.commit()
    db.refresh(view)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="analysis_view.created",
        entity_type="analysis_view",
        entity_id=str(view.id),
        details={"name": view.name},
        actor_user_id=user.id if user is not None else None,
    )
    return view


@app.get(
    "/tenants/{tenant_id}/analysis-views",
    response_model=SavedAnalysisViewListResponse,
)
def list_analysis_views(
    tenant_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SavedAnalysisViewListResponse:
    """FR-032 / T-064: List all saved analysis views for a tenant."""
    items = list(
        db.scalars(
            select(SavedAnalysisView)
            .where(SavedAnalysisView.tenant_id == tenant_id)
            .order_by(SavedAnalysisView.created_at.desc())
        )
    )
    return SavedAnalysisViewListResponse(
        items=[SavedAnalysisViewResponse.model_validate(v) for v in items],
        total=len(items),
    )


@app.get(
    "/tenants/{tenant_id}/analysis-views/{view_id}",
    response_model=SavedAnalysisViewResponse,
)
def get_analysis_view(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> SavedAnalysisView:
    """FR-032 / T-064: Retrieve a specific saved analysis view."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )
    return view


@app.delete(
    "/tenants/{tenant_id}/analysis-views/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analysis_view(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """FR-032 / T-064: Delete a saved analysis view."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    actor = db.scalar(select(User).where(User.email == auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        action="analysis_view.deleted",
        entity_type="analysis_view",
        entity_id=str(view.id),
        details={"name": view.name},
        actor_user_id=actor.id if actor is not None else None,
    )

    db.delete(view)
    db.commit()


@app.post(
    "/tenants/{tenant_id}/analysis-views/{view_id}/share",
    response_model=AnalysisViewShareListResponse,
    status_code=status.HTTP_201_CREATED,
)
def share_analysis_view(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    body: AnalysisViewShareRequest,
    auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AnalysisViewShareListResponse:
    """FR-034 / T-064: Share an analysis view with recipients."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    actor = db.scalar(select(User).where(User.email == auth.email))
    shares: list[AnalysisViewShare] = []

    for recipient_email in body.recipient_emails:
        # Generate one-time token if scope is one_time_link
        one_time_token = None
        if body.scope == "one_time_link":
            one_time_token = secrets.token_urlsafe(96)

        share = AnalysisViewShare(
            id=uuid.uuid4(),
            saved_view_id=view.id,
            tenant_id=tenant_id,
            shared_by_id=actor.id if actor is not None else uuid.uuid4(),
            recipient_email=recipient_email,
            scope=body.scope,
            one_time_token=one_time_token,
        )
        db.add(share)
        shares.append(share)

        write_audit_event(
            db,
            tenant_id=tenant_id,
            action="analysis_view.shared",
            entity_type="analysis_view_share",
            entity_id=str(share.id),
            details={
                "view_id": str(view.id),
                "recipient": recipient_email,
                "scope": body.scope,
            },
            actor_user_id=actor.id if actor is not None else None,
        )

    db.commit()
    for share in shares:
        db.refresh(share)

    return AnalysisViewShareListResponse(
        items=[AnalysisViewShareResponse.model_validate(s) for s in shares],
        total=len(shares),
    )


@app.get(
    "/tenants/{tenant_id}/analysis-views/{view_id}/shares",
    response_model=AnalysisViewShareListResponse,
)
def list_analysis_view_shares(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AnalysisViewShareListResponse:
    """FR-034 / T-064: List all shares for a specific analysis view."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    items = list(
        db.scalars(
            select(AnalysisViewShare)
            .where(AnalysisViewShare.saved_view_id == view_id)
            .order_by(AnalysisViewShare.shared_at.desc())
        )
    )
    return AnalysisViewShareListResponse(
        items=[AnalysisViewShareResponse.model_validate(s) for s in items],
        total=len(items),
    )


@app.get(
    "/tenants/{tenant_id}/analysis-views/{view_id}/export",
    status_code=status.HTTP_200_OK,
)
def export_view_download(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    format: str = "csv",
) -> Response:
    """FR-034 / T-064: Download exported analysis view as CSV or JSON."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    if format not in ("csv", "json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'csv' or 'json'.",
        )

    try:
        file_bytes = export_analysis_view(db, view_id, format=format)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None

    file_ext = "csv" if format == "csv" else "json"
    filename = f"{view.name.replace(' ', '_')}_export.{file_ext}"
    media_type = "text/csv" if format == "csv" else "application/json"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@app.get(
    "/saved-views/{one_time_token}",
    response_model=SavedAnalysisViewResponse,
    status_code=status.HTTP_200_OK,
)
def get_shared_view_guest(
    one_time_token: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> SavedAnalysisView:
    """FR-034 / T-064: Public guest access to shared view via one-time token."""
    share = db.scalar(
        select(AnalysisViewShare).where(
            AnalysisViewShare.one_time_token == one_time_token,
            AnalysisViewShare.scope == "one_time_link",
        )
    )
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared view not found or token expired.",
        )

    view = db.scalar(
        select(SavedAnalysisView).where(SavedAnalysisView.id == share.saved_view_id)
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View no longer exists.",
        )

    return view


@app.post(
    "/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    req: AnnotationCreateRequest,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AnalysisAnnotation:
    """FR-033, FR-045, FR-068 / T-065: Create annotation on analysis view."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    annotation = AnalysisAnnotation(
        saved_view_id=view_id,
        tenant_id=tenant_id,
        created_by_id=user.id,
        text=req.text,
        event_date=req.event_date,
        annotation_type=req.annotation_type,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="annotation.created",
        entity_type="AnalysisAnnotation",
        entity_id=str(annotation.id),
        details={"view_id": str(view_id), "text_preview": req.text[:50]},
    )

    return annotation


@app.get(
    "/tenants/{tenant_id}/analysis-views/{view_id}/annotations",
    response_model=AnnotationListResponse,
    status_code=status.HTTP_200_OK,
)
def list_annotations(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    event_date_min: date | None = None,
    event_date_max: date | None = None,
) -> AnnotationListResponse:
    """FR-033, FR-045, FR-068 / T-065: List annotations for analysis view."""
    view = db.scalar(
        select(SavedAnalysisView).where(
            SavedAnalysisView.tenant_id == tenant_id,
            SavedAnalysisView.id == view_id,
        )
    )
    if view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis view not found.",
        )

    query = select(AnalysisAnnotation).where(
        AnalysisAnnotation.saved_view_id == view_id,
        AnalysisAnnotation.tenant_id == tenant_id,
    )

    if event_date_min is not None:
        query = query.where(AnalysisAnnotation.event_date >= event_date_min)
    if event_date_max is not None:
        query = query.where(AnalysisAnnotation.event_date <= event_date_max)

    query = query.order_by(AnalysisAnnotation.created_at.desc())

    annotations = db.scalars(query).all()

    return AnnotationListResponse(
        items=[AnnotationResponse.model_validate(a) for a in annotations],
        total=len(annotations),
    )


@app.delete(
    "/tenants/{tenant_id}/analysis-views/{view_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_annotation(
    tenant_id: uuid.UUID,
    view_id: uuid.UUID,
    annotation_id: uuid.UUID,
    _auth: IntelInsightsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """FR-033, FR-045, FR-068 / T-065: Delete annotation (immutable)."""
    annotation = db.scalar(
        select(AnalysisAnnotation).where(
            AnalysisAnnotation.id == annotation_id,
            AnalysisAnnotation.tenant_id == tenant_id,
            AnalysisAnnotation.saved_view_id == view_id,
        )
    )
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found.",
        )

    db.delete(annotation)
    db.commit()

    user = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="annotation.deleted",
        entity_type="AnalysisAnnotation",
        entity_id=str(annotation_id),
        details={"view_id": str(view_id)},
    )


@app.post(
    "/tenants/{tenant_id}/cohorts",
    response_model=CohortSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cohort_snapshot(
    tenant_id: uuid.UUID,
    req: CohortSnapshotCreateRequest,
    _auth: RetentionViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CohortSnapshot:
    """FR-037 / T-066: Create a cohort snapshot for comparison."""
    snapshot = CohortSnapshot(
        tenant_id=tenant_id,
        cohort_start_date=req.cohort_start_date,
        cohort_end_date=req.cohort_end_date,
        cohort_grain=req.cohort_grain,
        observation_window_days=req.observation_window_days,
        customer_count=req.customer_count,
        repeat_rate=req.repeat_rate,
        churn_rate=req.churn_rate,
        avg_order_value=req.avg_order_value,
        total_revenue=req.total_revenue,
        repeat_purchase_frequency=req.repeat_purchase_frequency,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    user = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="cohort.snapshot.created",
        entity_type="CohortSnapshot",
        entity_id=str(snapshot.id),
        details={
            "cohort_grain": req.cohort_grain,
            "window_days": req.observation_window_days,
        },
    )

    return snapshot


@app.post(
    "/tenants/{tenant_id}/cohorts/compare",
    response_model=CohortComparisonResponse,
    status_code=status.HTTP_200_OK,
)
def compare_cohorts(
    tenant_id: uuid.UUID,
    req: CohortComparisonRequest,
    _auth: RetentionAnalyzeDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> CohortComparisonResponse:
    """FR-037 / T-066: Compare cohorts side-by-side within date range and grain."""
    query = select(CohortSnapshot).where(
        CohortSnapshot.tenant_id == tenant_id,
        CohortSnapshot.cohort_grain == req.cohort_grain,
        CohortSnapshot.observation_window_days == req.observation_window_days,
        CohortSnapshot.cohort_start_date >= req.start_date,
        CohortSnapshot.cohort_start_date <= req.end_date,
    )

    cohorts = db.scalars(query.order_by(CohortSnapshot.cohort_start_date.asc())).all()

    return CohortComparisonResponse(
        cohorts=[CohortSnapshotResponse.model_validate(c) for c in cohorts],
        total=len(cohorts),
    )


@app.get(
    "/tenants/{tenant_id}/retention/acquisition-context",
    response_model=AcquisitionContextResponse,
    status_code=status.HTTP_200_OK,
)
def get_acquisition_context(
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    _auth: RetentionViewDep,
    cohort_grain: str = "month",
    channel: str | None = None,
    db: Session = Depends(get_db),  # noqa: B008
) -> AcquisitionContextResponse:
    """FR-043 / T-070: Get acquisition context for retention manager analysis.

    Retention managers use this read-only data to understand incoming customer
    quality (by channel and cohort) when designing retention strategies.

    Query parameters:
    - start_date: Earliest cohort start date to include
    - end_date: Latest cohort end date to include
    - cohort_grain: 'week', 'month', or 'quarter' (default: 'month')
    - channel: Optional filter to specific channel (if None, all channels)
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    # Build query for acquisition cohorts
    query = select(AcquisitionCohort).where(
        AcquisitionCohort.tenant_id == tenant_id,
        AcquisitionCohort.cohort_grain == cohort_grain,
        AcquisitionCohort.cohort_start_date >= start_date,
        AcquisitionCohort.cohort_end_date <= end_date,
    )

    if channel is not None:
        query = query.where(AcquisitionCohort.channel == channel)

    cohorts = db.scalars(
        query.order_by(
            AcquisitionCohort.cohort_start_date.asc(),
            AcquisitionCohort.channel.asc(),
        )
    ).all()

    # Determine data freshness
    if not cohorts:
        data_freshness = "no_data"
    else:
        max_synced_at = max(c.synced_at for c in cohorts)
        now = datetime.now(UTC)
        # Handle both naive and aware datetimes from SQLite
        if max_synced_at.tzinfo is None:
            max_synced_at = max_synced_at.replace(tzinfo=UTC)
        freshness_hours = (now - max_synced_at).total_seconds() / 3600
        data_freshness = "fresh" if freshness_hours < 24 else "stale"

    # Collect unique channels
    channels_included = sorted(set(c.channel for c in cohorts))

    user = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="acquisition.context.viewed",
        entity_type="AcquisitionContext",
        entity_id=str(tenant_id),
        details={
            "cohort_grain": cohort_grain,
            "channel_filter": channel,
            "cohort_count": len(cohorts),
        },
    )

    return AcquisitionContextResponse(
        cohorts=[
            AcquisitionCohortResponse.model_validate(c) for c in cohorts
        ],
        total=len(cohorts),
        data_freshness=data_freshness,
        channels_included=channels_included,
    )


@app.post(
    "/tenants/{tenant_id}/retention/custom-segments",
    response_model=CustomSegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_custom_segment(
    tenant_id: uuid.UUID,
    req: CustomSegmentCreate,
    _auth: RetentionViewDep,
    _feature: RequireCustomSegments,
    db: Session = Depends(get_db),  # noqa: B008
) -> CustomSegmentResponse:
    """FR-044 / T-071: Create a custom customer segment.

    Retention managers can create reusable segments (e.g., "High-Value: AOV > £500")
    for repeated use in dashboards and alerts.
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    segment = CustomSegment(
        tenant_id=tenant_id,
        name=req.name,
        description=req.description,
        definition=req.definition,
        created_by_user_id=user.id if user is not None else None,
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="custom.segment.created",
        entity_type="CustomSegment",
        entity_id=str(segment.id),
        details={"name": req.name, "definition": req.definition},
    )

    return CustomSegmentResponse.model_validate(segment)


@app.get(
    "/tenants/{tenant_id}/retention/custom-segments",
    response_model=CustomSegmentListResponse,
    status_code=status.HTTP_200_OK,
)
def list_custom_segments(
    tenant_id: uuid.UUID,
    _auth: RetentionViewDep,
    _feature: RequireCustomSegments,
    db: Session = Depends(get_db),  # noqa: B008
) -> CustomSegmentListResponse:
    """FR-044 / T-071: List custom segments for a tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    segments = db.scalars(
        select(CustomSegment)
        .where(CustomSegment.tenant_id == tenant_id)
        .order_by(CustomSegment.created_at.desc())
    ).all()

    return CustomSegmentListResponse(
        segments=[CustomSegmentResponse.model_validate(s) for s in segments],
        total=len(segments),
    )


@app.get(
    "/tenants/{tenant_id}/retention/custom-segments/{segment_id}",
    response_model=CustomSegmentResponse,
    status_code=status.HTTP_200_OK,
)
def get_custom_segment(
    tenant_id: uuid.UUID,
    segment_id: uuid.UUID,
    _auth: RetentionViewDep,
    _feature: RequireCustomSegments,
    db: Session = Depends(get_db),  # noqa: B008
) -> CustomSegmentResponse:
    """FR-044 / T-071: Get a custom segment by ID."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    segment = db.scalar(
        select(CustomSegment).where(
            CustomSegment.id == segment_id,
            CustomSegment.tenant_id == tenant_id,
        )
    )
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Custom segment not found."
        )

    return CustomSegmentResponse.model_validate(segment)


@app.put(
    "/tenants/{tenant_id}/retention/custom-segments/{segment_id}",
    response_model=CustomSegmentResponse,
    status_code=status.HTTP_200_OK,
)
def update_custom_segment(
    tenant_id: uuid.UUID,
    segment_id: uuid.UUID,
    req: CustomSegmentUpdate,
    _auth: RetentionViewDep,
    _feature: RequireCustomSegments,
    db: Session = Depends(get_db),  # noqa: B008
) -> CustomSegmentResponse:
    """FR-044 / T-071: Update a custom segment."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    segment = db.scalar(
        select(CustomSegment).where(
            CustomSegment.id == segment_id,
            CustomSegment.tenant_id == tenant_id,
        )
    )
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Custom segment not found."
        )

    if req.name is not None:
        segment.name = req.name
    if req.description is not None:
        segment.description = req.description
    if req.definition is not None:
        segment.definition = req.definition
    if req.is_active is not None:
        segment.is_active = req.is_active

    db.commit()
    db.refresh(segment)

    user = db.scalar(select(User).where(User.email == _auth.email))
    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="custom.segment.updated",
        entity_type="CustomSegment",
        entity_id=str(segment.id),
        details={"name": segment.name},
    )

    return CustomSegmentResponse.model_validate(segment)


@app.delete(
    "/tenants/{tenant_id}/retention/custom-segments/{segment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_custom_segment(
    tenant_id: uuid.UUID,
    segment_id: uuid.UUID,
    _auth: RetentionViewDep,
    _feature: RequireCustomSegments,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """FR-044 / T-071: Delete a custom segment."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    segment = db.scalar(
        select(CustomSegment).where(
            CustomSegment.id == segment_id,
            CustomSegment.tenant_id == tenant_id,
        )
    )
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Custom segment not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    segment_name = segment.name
    db.delete(segment)
    db.commit()

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="custom.segment.deleted",
        entity_type="CustomSegment",
        entity_id=str(segment_id),
        details={"name": segment_name},
    )


# ============================================================================
# T-072: Alert Configuration APIs (thresholds and recipients)
# ============================================================================


@app.post(
    "/tenants/{tenant_id}/alerts/thresholds",
    response_model=AlertThresholdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_threshold(
    tenant_id: UUID,
    payload: AlertThresholdCreate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertThreshold:
    """Create a new alert threshold for a metric in this tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    threshold = AlertThreshold(
        tenant_id=tenant_id,
        alert_type=payload.alert_type,
        metric_name=payload.metric_name,
        threshold_value=payload.threshold_value,
        comparison_operator=payload.comparison_operator,
        is_enabled=payload.is_enabled,
        created_by_user_id=user.id if user is not None else None,
    )
    db.add(threshold)
    db.commit()
    db.refresh(threshold)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.threshold.created",
        entity_type="AlertThreshold",
        entity_id=str(threshold.id),
        details={
            "alert_type": payload.alert_type,
            "metric_name": payload.metric_name,
            "threshold_value": payload.threshold_value,
        },
    )

    return threshold


@app.get(
    "/tenants/{tenant_id}/alerts/thresholds",
    response_model=AlertThresholdListResponse,
)
def list_alert_thresholds(
    tenant_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """List all alert thresholds for a tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    thresholds = db.scalars(
        select(AlertThreshold)
        .where(AlertThreshold.tenant_id == tenant_id)
        .order_by(AlertThreshold.created_at.desc())
    ).all()

    return {
        "thresholds": thresholds,
        "total": len(thresholds),
    }


@app.get(
    "/tenants/{tenant_id}/alerts/thresholds/{threshold_id}",
    response_model=AlertThresholdResponse,
)
def get_alert_threshold(
    tenant_id: UUID,
    threshold_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertThreshold:
    """Get a specific alert threshold."""
    threshold = db.scalar(
        select(AlertThreshold).where(
            AlertThreshold.id == threshold_id,
            AlertThreshold.tenant_id == tenant_id,
        )
    )
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert threshold not found."
        )

    return threshold


@app.put(
    "/tenants/{tenant_id}/alerts/thresholds/{threshold_id}",
    response_model=AlertThresholdResponse,
)
def update_alert_threshold(
    tenant_id: UUID,
    threshold_id: UUID,
    payload: AlertThresholdUpdate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertThreshold:
    """Update an alert threshold."""
    threshold = db.scalar(
        select(AlertThreshold).where(
            AlertThreshold.id == threshold_id,
            AlertThreshold.tenant_id == tenant_id,
        )
    )
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert threshold not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    if payload.threshold_value is not None:
        threshold.threshold_value = payload.threshold_value
    if payload.comparison_operator is not None:
        threshold.comparison_operator = payload.comparison_operator
    if payload.is_enabled is not None:
        threshold.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(threshold)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.threshold.updated",
        entity_type="AlertThreshold",
        entity_id=str(threshold_id),
        details={
            "threshold_value": threshold.threshold_value,
            "comparison_operator": threshold.comparison_operator,
            "is_enabled": threshold.is_enabled,
        },
    )

    return threshold


@app.delete("/tenants/{tenant_id}/alerts/thresholds/{threshold_id}")
def delete_alert_threshold(
    tenant_id: UUID,
    threshold_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete an alert threshold."""
    threshold = db.scalar(
        select(AlertThreshold).where(
            AlertThreshold.id == threshold_id,
            AlertThreshold.tenant_id == tenant_id,
        )
    )
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert threshold not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    threshold_type = threshold.alert_type
    db.delete(threshold)
    db.commit()

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.threshold.deleted",
        entity_type="AlertThreshold",
        entity_id=str(threshold_id),
        details={"alert_type": threshold_type},
    )


@app.post(
    "/tenants/{tenant_id}/alerts/recipients",
    response_model=AlertRecipientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_recipient(
    tenant_id: UUID,
    payload: AlertRecipientCreate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertRecipient:
    """Create a new alert recipient for a user."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    recipient = AlertRecipient(
        tenant_id=tenant_id,
        user_id=payload.user_id,
        channel=payload.channel,
        destination=payload.destination,
        is_verified=False,
    )
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.recipient.created",
        entity_type="AlertRecipient",
        entity_id=str(recipient.id),
        details={
            "channel": payload.channel,
            "destination": payload.destination,
        },
    )

    return recipient


@app.get(
    "/tenants/{tenant_id}/alerts/recipients",
    response_model=AlertRecipientListResponse,
)
def list_alert_recipients(
    tenant_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """List all alert recipients for a tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    recipients = db.scalars(
        select(AlertRecipient)
        .where(AlertRecipient.tenant_id == tenant_id)
        .order_by(AlertRecipient.created_at.desc())
    ).all()

    return {
        "recipients": recipients,
        "total": len(recipients),
    }


@app.get(
    "/tenants/{tenant_id}/alerts/recipients/{recipient_id}",
    response_model=AlertRecipientResponse,
)
def get_alert_recipient(
    tenant_id: UUID,
    recipient_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertRecipient:
    """Get a specific alert recipient."""
    recipient = db.scalar(
        select(AlertRecipient).where(
            AlertRecipient.id == recipient_id,
            AlertRecipient.tenant_id == tenant_id,
        )
    )
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert recipient not found."
        )

    return recipient


@app.put(
    "/tenants/{tenant_id}/alerts/recipients/{recipient_id}",
    response_model=AlertRecipientResponse,
)
def update_alert_recipient(
    tenant_id: UUID,
    recipient_id: UUID,
    payload: AlertRecipientUpdate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertRecipient:
    """Update an alert recipient."""
    recipient = db.scalar(
        select(AlertRecipient).where(
            AlertRecipient.id == recipient_id,
            AlertRecipient.tenant_id == tenant_id,
        )
    )
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert recipient not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    if payload.destination is not None:
        recipient.destination = payload.destination
    if payload.is_verified is not None:
        recipient.is_verified = payload.is_verified

    db.commit()
    db.refresh(recipient)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.recipient.updated",
        entity_type="AlertRecipient",
        entity_id=str(recipient_id),
        details={
            "destination": recipient.destination,
            "is_verified": recipient.is_verified,
        },
    )

    return recipient


@app.delete("/tenants/{tenant_id}/alerts/recipients/{recipient_id}")
def delete_alert_recipient(
    tenant_id: UUID,
    recipient_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete an alert recipient."""
    recipient = db.scalar(
        select(AlertRecipient).where(
            AlertRecipient.id == recipient_id,
            AlertRecipient.tenant_id == tenant_id,
        )
    )
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert recipient not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    channel = recipient.channel
    db.delete(recipient)
    db.commit()

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="alert.recipient.deleted",
        entity_type="AlertRecipient",
        entity_id=str(recipient_id),
        details={"channel": channel},
    )


# T-078: Alert Escalation and Acknowledgement Endpoints


@app.post(
    "/tenants/{tenant_id}/alerts/acknowledge",
    response_model=AlertAcknowledgementResponse,
)
def acknowledge_alert(
    tenant_id: UUID,
    payload: AlertAcknowledgementCreate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertAcknowledgement:
    """Acknowledge an alert.

    Records that the authenticated user has acknowledged (seen and is handling)
    the specified alert. Each user can acknowledge an alert once per tenant.
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )

    # Check if already acknowledged
    existing = db.scalar(
        select(AlertAcknowledgement).where(
            AlertAcknowledgement.tenant_id == tenant_id,
            AlertAcknowledgement.user_id == user.id,
            AlertAcknowledgement.alert_id == payload.alert_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert already acknowledged by this user.",
        )

    acknowledgement = AlertAcknowledgement(
        tenant_id=tenant_id,
        user_id=user.id,
        alert_id=payload.alert_id,
        alert_type=payload.alert_type,
        acknowledged_at=datetime.now(UTC),
    )
    db.add(acknowledgement)
    db.commit()

    # Log event to immutable alert event log
    write_alert_event(
        db,
        tenant_id=tenant_id,
        alert_id=payload.alert_id,
        alert_type=payload.alert_type,
        event_type="acknowledged",
        actor_user_id=user.id,
    )
    db.commit()

    db.refresh(acknowledgement)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="alert.acknowledged",
        entity_type="AlertAcknowledgement",
        entity_id=str(acknowledgement.id),
        details={
            "alert_id": payload.alert_id,
            "alert_type": payload.alert_type,
        },
    )

    return acknowledgement


@app.post(
    "/tenants/{tenant_id}/alerts/dismiss",
    response_model=AlertDismissalResponse,
)
def dismiss_alert(
    tenant_id: UUID,
    payload: AlertDismissalCreate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertDismissal:
    """Dismiss an alert.

    Records that the authenticated user has dismissed the specified alert.
    Optional dismiss_reason can be provided for context.
    Each user can dismiss an alert once per tenant.
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found."
        )

    # Check if already dismissed
    existing = db.scalar(
        select(AlertDismissal).where(
            AlertDismissal.tenant_id == tenant_id,
            AlertDismissal.user_id == user.id,
            AlertDismissal.alert_id == payload.alert_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert already dismissed by this user.",
        )

    dismissal = AlertDismissal(
        tenant_id=tenant_id,
        user_id=user.id,
        alert_id=payload.alert_id,
        alert_type=payload.alert_type,
        dismiss_reason=payload.dismiss_reason,
        dismissed_at=datetime.now(UTC),
    )
    db.add(dismissal)
    db.commit()

    # Log event to immutable alert event log
    write_alert_event(
        db,
        tenant_id=tenant_id,
        alert_id=payload.alert_id,
        alert_type=payload.alert_type,
        event_type="dismissed",
        actor_user_id=user.id,
        event_data={"dismiss_reason": payload.dismiss_reason},
    )
    db.commit()

    db.refresh(dismissal)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="alert.dismissed",
        entity_type="AlertDismissal",
        entity_id=str(dismissal.id),
        details={
            "alert_id": payload.alert_id,
            "alert_type": payload.alert_type,
            "dismiss_reason": payload.dismiss_reason,
        },
    )

    return dismissal


@app.post(
    "/tenants/{tenant_id}/alerts/escalation-rules",
    response_model=EscalationRuleResponse,
)
def create_escalation_rule(
    tenant_id: UUID,
    payload: EscalationRuleCreate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> EscalationRule:
    """Create an escalation rule for unacknowledged alerts.

    Allows configuration of automatic escalation: if an alert of a given type
    remains unacknowledged for N hours, re-notify specified roles.
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    # Check for duplicate
    existing = db.scalar(
        select(EscalationRule).where(
            EscalationRule.tenant_id == tenant_id,
            EscalationRule.alert_type == payload.alert_type,
            EscalationRule.domain == payload.domain,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Escalation rule already exists for this alert type and domain.",
        )

    rule = EscalationRule(
        tenant_id=tenant_id,
        alert_type=payload.alert_type,
        domain=payload.domain,
        unacknowledged_hours=payload.unacknowledged_hours,
        escalation_to_roles=payload.escalation_to_roles,
        is_enabled=payload.is_enabled,
        created_by_user_id=user.id if user is not None else None,
    )
    db.add(rule)
    db.commit()

    # Log event to immutable alert event log
    write_alert_event(
        db,
        tenant_id=tenant_id,
        alert_id=f"{payload.alert_type}:{payload.domain}",
        alert_type=payload.alert_type,
        event_type="escalation_rule_created",
        actor_user_id=user.id if user is not None else None,
        event_data={
            "rule_id": str(rule.id),
            "unacknowledged_hours": payload.unacknowledged_hours,
            "escalation_to_roles": payload.escalation_to_roles,
            "is_enabled": payload.is_enabled,
        },
    )
    db.commit()

    db.refresh(rule)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="escalation_rule.created",
        entity_type="EscalationRule",
        entity_id=str(rule.id),
        details={
            "alert_type": payload.alert_type,
            "domain": payload.domain,
            "unacknowledged_hours": payload.unacknowledged_hours,
        },
    )

    return rule


@app.get(
    "/tenants/{tenant_id}/alerts/escalation-rules",
    response_model=EscalationRuleListResponse,
)
def list_escalation_rules(
    tenant_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict[str, object]:
    """List all escalation rules for a tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found."
        )

    rules = db.scalars(
        select(EscalationRule)
        .where(EscalationRule.tenant_id == tenant_id)
        .order_by(EscalationRule.created_at.desc())
    ).all()

    return {
        "rules": rules,
        "total_count": len(rules),
    }


@app.get(
    "/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}",
    response_model=EscalationRuleResponse,
)
def get_escalation_rule(
    tenant_id: UUID,
    rule_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> EscalationRule:
    """Get a specific escalation rule."""
    rule = db.scalar(
        select(EscalationRule).where(
            EscalationRule.id == rule_id,
            EscalationRule.tenant_id == tenant_id,
        )
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation rule not found.",
        )

    return rule


@app.put(
    "/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}",
    response_model=EscalationRuleResponse,
)
def update_escalation_rule(
    tenant_id: UUID,
    rule_id: UUID,
    payload: EscalationRuleUpdate,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> EscalationRule:
    """Update an escalation rule."""
    rule = db.scalar(
        select(EscalationRule).where(
            EscalationRule.id == rule_id,
            EscalationRule.tenant_id == tenant_id,
        )
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation rule not found.",
        )

    user = db.scalar(select(User).where(User.email == _auth.email))

    # Update fields if provided
    if payload.unacknowledged_hours is not None:
        rule.unacknowledged_hours = payload.unacknowledged_hours
    if payload.escalation_to_roles is not None:
        rule.escalation_to_roles = payload.escalation_to_roles
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled

    db.add(rule)
    db.commit()

    # Log event to immutable alert event log
    write_alert_event(
        db,
        tenant_id=tenant_id,
        alert_id=f"{rule.alert_type}:{rule.domain}",
        alert_type=rule.alert_type,
        event_type="escalation_rule_updated",
        actor_user_id=user.id if user is not None else None,
        event_data={
            "rule_id": str(rule.id),
            "unacknowledged_hours": rule.unacknowledged_hours,
            "escalation_to_roles": rule.escalation_to_roles,
            "is_enabled": rule.is_enabled,
        },
    )
    db.commit()

    db.refresh(rule)

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="escalation_rule.updated",
        entity_type="EscalationRule",
        entity_id=str(rule_id),
        details={
            "unacknowledged_hours": rule.unacknowledged_hours,
            "is_enabled": rule.is_enabled,
        },
    )

    return rule


@app.delete(
    "/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}",
)
def delete_escalation_rule(
    tenant_id: UUID,
    rule_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete an escalation rule."""
    rule = db.scalar(
        select(EscalationRule).where(
            EscalationRule.id == rule_id,
            EscalationRule.tenant_id == tenant_id,
        )
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation rule not found.",
        )

    user = db.scalar(select(User).where(User.email == _auth.email))
    alert_type = rule.alert_type
    domain = rule.domain

    db.delete(rule)
    db.commit()

    # Log event to immutable alert event log
    write_alert_event(
        db,
        tenant_id=tenant_id,
        alert_id=f"{alert_type}:{domain}",
        alert_type=alert_type,
        event_type="escalation_rule_deleted",
        actor_user_id=user.id if user is not None else None,
        event_data={
            "rule_id": str(rule_id),
        },
    )
    db.commit()

    write_audit_event(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id if user is not None else None,
        action="escalation_rule.deleted",
        entity_type="EscalationRule",
        entity_id=str(rule_id),
        details={
            "alert_type": alert_type,
            "domain": domain,
        },
    )


# Alert History & Audit Logs (FR-125 / T-079)


@app.get(
    "/tenants/{tenant_id}/alerts/history",
    response_model=AlertEventListResponse,
)
def list_alert_events(
    tenant_id: UUID,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
    skip: int = 0,
    limit: int = 100,
    alert_id: str | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    actor_user_id: UUID | None = None,
) -> AlertEventListResponse:
    """List alert events for a tenant with optional filtering.

    Query parameters:
    - skip: Number of events to skip (default: 0)
    - limit: Maximum events to return (default: 100, max: 500)
    - alert_id: Filter by alert_id (exact match)
    - event_type: Filter by event_type (e.g., 'acknowledged', 'dismissed')
    - date_from: Filter events >= date_from (ISO 8601 datetime with timezone)
    - date_to: Filter events <= date_to (ISO 8601 datetime with timezone)
    - actor_user_id: Filter by actor_user_id (UUID string)

    Returns paginated list of alert events ordered by created_at descending.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Enforce pagination bounds
    limit = min(limit, 500)

    # Build query
    query = select(AlertEventLog).where(AlertEventLog.tenant_id == tenant_id)

    if alert_id is not None:
        query = query.where(AlertEventLog.alert_id == alert_id)

    if event_type is not None:
        query = query.where(AlertEventLog.event_type == event_type)

    if date_from is not None:
        query = query.where(AlertEventLog.created_at >= date_from)

    if date_to is not None:
        query = query.where(AlertEventLog.created_at <= date_to)

    if actor_user_id is not None:
        query = query.where(AlertEventLog.actor_user_id == actor_user_id)

    # Get total count before pagination
    total_count = db.scalar(
        select(func.count()).select_from(AlertEventLog).where(
            AlertEventLog.tenant_id == tenant_id,
            *(
                [AlertEventLog.alert_id == alert_id] if alert_id is not None else []
            ),
            *(
                [AlertEventLog.event_type == event_type]
                if event_type is not None
                else []
            ),
            *(
                [AlertEventLog.created_at >= date_from] if date_from is not None else []
            ),
            *(
                [AlertEventLog.created_at <= date_to] if date_to is not None else []
            ),
            *(
                [AlertEventLog.actor_user_id == actor_user_id]
                if actor_user_id is not None
                else []
            ),
        )
    )

    # Get paginated results, ordered by created_at descending
    events = db.scalars(
        query.order_by(AlertEventLog.created_at.desc()).offset(skip).limit(limit)
    ).all()

    return AlertEventListResponse(
        events=[
            AlertEventResponse.model_validate(event) for event in events
        ],
        total_count=total_count or 0,
    )


@app.get(
    "/tenants/{tenant_id}/alerts/{alert_id}/history",
    response_model=AlertHistoryResponse,
)
def get_alert_history(
    tenant_id: UUID,
    alert_id: str,
    _auth: IntelAlertsManageDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> AlertHistoryResponse:
    """Get complete immutable history for a specific alert.

    Returns all events for the alert ordered by created_at ascending
    (oldest first), including event timestamps, actors, and associated data.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Get all events for this alert (ordered oldest first)
    events = db.scalars(
        select(AlertEventLog)
        .where(
            AlertEventLog.tenant_id == tenant_id,
            AlertEventLog.alert_id == alert_id,
        )
        .order_by(AlertEventLog.created_at.asc())
    ).all()

    if not events:
        # Return empty history if no events found
        # (alert_type is unknown if no events)
        return AlertHistoryResponse(
            alert_id=alert_id,
            alert_type="unknown",
            events=[],
            total_events=0,
            first_event_at=None,
            last_event_at=None,
        )

    alert_type = events[0].alert_type  # All events have same alert_type
    return AlertHistoryResponse(
        alert_id=alert_id,
        alert_type=alert_type,
        events=[
            AlertEventResponse.model_validate(event) for event in events
        ],
        total_events=len(events),
        first_event_at=events[0].created_at,
        last_event_at=events[-1].created_at,
    )


# Email Delivery & Notification Log (FR-116 / T-079)


@app.get(
    "/tenants/{tenant_id}/email-delivery/history",
    response_model=EmailDeliveryListResponse,
)
def list_email_deliveries(
    tenant_id: UUID,
    _auth: AdminAuditDep,
    db: Session = Depends(get_db),  # noqa: B008
    skip: int = 0,
    limit: int = 100,
    alert_id: str | None = None,
    user_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),  # noqa: B008
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> EmailDeliveryListResponse:
    """List email delivery records for a tenant with optional filtering.

    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100, max: 500)
    - alert_id: Filter by alert_id (exact match)
    - user_id: Filter by user_id (UUID string)
    - status: Filter by status (pending, sent, failed, bounced)
    - date_from: Filter records >= date_from (ISO 8601 datetime with timezone)
    - date_to: Filter records <= date_to (ISO 8601 datetime with timezone)

    Returns paginated list of delivery records ordered by created_at descending.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Enforce pagination bounds
    limit = min(limit, 500)

    # Build query
    query = select(EmailDeliveryLog).where(EmailDeliveryLog.tenant_id == tenant_id)

    if alert_id is not None:
        query = query.where(EmailDeliveryLog.alert_id == alert_id)

    if user_id is not None:
        query = query.where(EmailDeliveryLog.user_id == user_id)

    if status_filter is not None:
        query = query.where(EmailDeliveryLog.status == status_filter)

    if date_from is not None:
        query = query.where(EmailDeliveryLog.created_at >= date_from)

    if date_to is not None:
        query = query.where(EmailDeliveryLog.created_at <= date_to)

    # Get total count before pagination
    total_count = db.scalar(
        select(func.count()).select_from(EmailDeliveryLog).where(
            EmailDeliveryLog.tenant_id == tenant_id,
            *(
                [EmailDeliveryLog.alert_id == alert_id]
                if alert_id is not None
                else []
            ),
            *(
                [EmailDeliveryLog.user_id == user_id] if user_id is not None else []
            ),
            *(
                [EmailDeliveryLog.status == status_filter]
                if status_filter is not None
                else []
            ),
            *(
                [EmailDeliveryLog.created_at >= date_from]
                if date_from is not None
                else []
            ),
            *(
                [EmailDeliveryLog.created_at <= date_to]
                if date_to is not None
                else []
            ),
        )
    )

    # Get paginated results, ordered by created_at descending
    deliveries = db.scalars(
        query.order_by(EmailDeliveryLog.created_at.desc()).offset(skip).limit(limit)
    ).all()

    return EmailDeliveryListResponse(
        deliveries=[
            EmailDeliveryResponse.model_validate(delivery) for delivery in deliveries
        ],
        total_count=total_count or 0,
    )


@app.get(
    "/tenants/{tenant_id}/email-delivery/alerts/{alert_id}/history",
    response_model=EmailDeliveryHistoryResponse,
)
def get_alert_email_delivery_history(
    tenant_id: UUID,
    alert_id: str,
    _auth: AdminAuditDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> EmailDeliveryHistoryResponse:
    """Get complete email delivery history for a specific alert.

    Returns all delivery attempts for the alert, including status,
    retry attempts, errors, and aggregate statistics.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Get all delivery records for this alert (ordered oldest first)
    deliveries = db.scalars(
        select(EmailDeliveryLog)
        .where(
            EmailDeliveryLog.tenant_id == tenant_id,
            EmailDeliveryLog.alert_id == alert_id,
        )
        .order_by(EmailDeliveryLog.created_at.asc())
    ).all()

    if not deliveries:
        # Return empty history if no deliveries found
        return EmailDeliveryHistoryResponse(
            alert_id=alert_id,
            alert_type="unknown",
            total_deliveries=0,
            successful_count=0,
            failed_count=0,
            pending_count=0,
            deliveries=[],
            first_delivery_at=None,
            last_delivery_at=None,
        )

    # Aggregate statistics
    alert_type = deliveries[0].alert_type
    successful_count = sum(1 for d in deliveries if d.status == "sent")
    failed_count = sum(1 for d in deliveries if d.status in ("failed", "bounced"))
    pending_count = sum(1 for d in deliveries if d.status == "pending")

    return EmailDeliveryHistoryResponse(
        alert_id=alert_id,
        alert_type=alert_type,
        total_deliveries=len(deliveries),
        successful_count=successful_count,
        failed_count=failed_count,
        pending_count=pending_count,
        deliveries=[
            EmailDeliveryResponse.model_validate(delivery) for delivery in deliveries
        ],
        first_delivery_at=deliveries[0].created_at,
        last_delivery_at=deliveries[-1].created_at,
    )


# ============================================================================
# Simulation Endpoints (FR-081, FR-087 / T-081)
# ============================================================================


@app.get(
    "/tenants/{tenant_id}/simulations/recommendations/{recommendation_id}",
    response_model=SimulationResponse,
)
def get_simulation_by_recommendation(
    tenant_id: UUID,
    recommendation_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Retrieve the simulation generated for a specific recommendation.

    Returns the three-scenario simulation (baseline/upside/downside) with
    all computed outputs, impact deltas, and confidence levels.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Get simulation for this recommendation
    simulation = db.scalar(
        select(Simulation).where(
            Simulation.tenant_id == tenant_id,
            Simulation.recommendation_id == recommendation_id,
        )
    )

    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found for this recommendation.",
        )

    return SimulationResponse.model_validate(simulation)


@app.get(
    "/tenants/{tenant_id}/simulations",
    response_model=SimulationListResponse,
)
def list_simulations(
    tenant_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
    skip: int = 0,
    limit: int = 100,
) -> SimulationListResponse:
    """List all simulations for a tenant with pagination.

    Query parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100, max: 500)

    Returns paginated list of simulations ordered by created_at descending.
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Enforce pagination bounds
    limit = min(limit, 500)

    # Get total count
    total_count = db.scalar(
        select(func.count())
        .select_from(Simulation)
        .where(Simulation.tenant_id == tenant_id)
    ) or 0

    # Get paginated results ordered by created_at descending
    simulations = db.scalars(
        select(Simulation)
        .where(Simulation.tenant_id == tenant_id)
        .order_by(Simulation.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return SimulationListResponse(
        simulations=[SimulationResponse.model_validate(s) for s in simulations],
        total_count=total_count,
    )


# ============================================================================
# Domain-Specific Simulation Endpoints (FR-082 to FR-086 / T-082)
# ============================================================================


@app.post(
    "/tenants/{tenant_id}/simulations/growth",
    response_model=SimulationResponse,
)
def create_growth_simulation(
    tenant_id: UUID,
    input_data: GrowthSimulationInput,
    _auth: IntelSimulationsRunDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Simulate growth channel budget reallocation.

    FR-082: Growth and Performance Manager can simulate budget reallocation
    across channels and see projected impact on CAC, ROAS, new customer
    volume, contribution margin, and payback period.

    Request body:
    - total_budget: Total budget to allocate
    - channel_allocations: List of channels with budget % (must sum to 100%)
    - scenario_label: Optional description

    Returns: SimulationResponse with three scenarios (baseline/upside/downside)
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Build channel allocations dict
    channel_allocations = {
        alloc.channel_id: alloc.budget_allocation_pct
        for alloc in input_data.channel_allocations
    }

    # Run simulation
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation = service.run_growth_simulation(
        tenant_id=tenant_id,
        total_budget=input_data.total_budget,
        channel_allocations=channel_allocations,
        scenario_label=input_data.scenario_label,
    )

    return SimulationResponse.model_validate(simulation)


@app.post(
    "/tenants/{tenant_id}/simulations/retention",
    response_model=SimulationResponse,
)
def create_retention_simulation(
    tenant_id: UUID,
    input_data: RetentionSimulationInput,
    _auth: IntelSimulationsRunDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Simulate retention intervention (offer/response/timing).

    FR-083: Retention and CRM Manager can simulate retention interventions
    and see projected repeat purchase rate, cohort revenue, and retention
    margin impact.

    Request body:
    - offer_discount_pct: Discount level offered (0-100)
    - target_segment: Segment identifier or description
    - days_post_first_purchase: When to send offer (0-365 days)
    - expected_response_rate_pct: Expected response rate (0-100)
    - estimated_segment_size: Optional segment size estimate
    - scenario_label: Optional description

    Returns: SimulationResponse with three scenarios (baseline/upside/downside)
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Run simulation
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation = service.run_retention_simulation(
        tenant_id=tenant_id,
        offer_discount_pct=input_data.offer_discount_pct,
        response_rate_pct=input_data.expected_response_rate_pct,
        estimated_segment_size=input_data.estimated_segment_size,
        scenario_label=input_data.scenario_label,
    )

    return SimulationResponse.model_validate(simulation)


@app.post(
    "/tenants/{tenant_id}/simulations/finance",
    response_model=SimulationResponse,
)
def create_finance_simulation(
    tenant_id: UUID,
    input_data: FinanceSimulationInput,
    _auth: IntelSimulationsRunDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Simulate cost input changes (shipping, returns, fees, VAT).

    FR-084: Finance Controller can simulate changes in cost inputs and
    see projected gross margin and contribution margin movement.

    Request body:
    - cost_changes: List of cost input changes
      Each change has: cost_type, current_value, proposed_value
    - scenario_label: Optional description

    Returns: SimulationResponse with three scenarios (baseline/upside/downside)
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Build cost changes dict
    cost_changes = {
        change.cost_type: (change.current_value, change.proposed_value)
        for change in input_data.cost_changes
    }

    # Run simulation
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation = service.run_finance_simulation(
        tenant_id=tenant_id,
        cost_changes=cost_changes,
        scenario_label=input_data.scenario_label,
    )

    return SimulationResponse.model_validate(simulation)


@app.post(
    "/tenants/{tenant_id}/simulations/operations",
    response_model=SimulationResponse,
)
def create_operations_simulation(
    tenant_id: UUID,
    input_data: OperationsSimulationInput,
    _auth: IntelSimulationsRunDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Simulate inventory reorder policy changes.

    FR-085: Operations Manager can simulate reorder timing, quantity, and
    lead-time scenarios and see projected stockout risk, overstock risk,
    weeks-of-cover, and capital tied up.

    Request body:
    - sku_or_category: SKU or category to simulate
    - reorder_quantity_multiplier: Quantity multiplier (e.g., 1.2)
    - lead_time_days: Lead time in days (1-90)
    - reorder_timing_policy: Policy (e.g., weekly, on_demand, threshold)
    - target_service_level_pct: Target service level (default 95%)
    - scenario_label: Optional description

    Returns: SimulationResponse with three scenarios (baseline/upside/downside)
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Run simulation
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation = service.run_operations_simulation(
        tenant_id=tenant_id,
        reorder_qty_multiplier=input_data.reorder_quantity_multiplier,
        lead_time_days=input_data.lead_time_days,
        scenario_label=input_data.scenario_label,
    )

    return SimulationResponse.model_validate(simulation)


@app.post(
    "/tenants/{tenant_id}/simulations/executive",
    response_model=SimulationResponse,
)
def create_executive_simulation(
    tenant_id: UUID,
    input_data: ExecutiveSimulationInput,
    _auth: IntelSimulationsRunDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationResponse:
    """Simulate strategic what-if scenarios (pricing, channel mix, demand).

    FR-086: Executive Owner can run strategic what-if scenarios combining
    pricing, channel mix, and demand assumptions and see consolidated
    projected business impact.

    Request body:
    - pricing_change_pct: Pricing change percentage (-100 to +100)
    - channel_mix_changes: Dict of channel budget shift deltas
    - demand_multiplier: Demand scenario multiplier (e.g., 1.2 for growth)
    - projection_horizon_days: Projection horizon in days (default 90)
    - scenario_label: Optional description

    Returns: SimulationResponse with three scenarios (baseline/upside/downside)
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Run simulation
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation = service.run_executive_simulation(
        tenant_id=tenant_id,
        pricing_change_pct=input_data.pricing_change_pct,
        demand_multiplier=input_data.demand_multiplier,
        scenario_label=input_data.scenario_label,
    )

    return SimulationResponse.model_validate(simulation)


@app.post(
    "/tenants/{tenant_id}/simulations/compare",
    response_model=dict,
)
def compare_simulations(
    tenant_id: UUID,
    request_body: SimulationComparisonRequest,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """Compare multiple simulations side-by-side with confidence warnings.

    FR-083: Growth/Retention/Finance/Operations/Executive managers can compare
    multiple simulations to see projected outcomes across different scenarios
    and understand data freshness/confidence context before deciding which
    scenario to pursue.

    Args:
        tenant_id: Tenant identifier
        request_body: SimulationComparisonRequest with list of simulation IDs

    Returns:
        Comparison view with side-by-side metrics, scenarios, and confidence
        warnings.

    Raises:
        404: If tenant or any simulation not found
        422: If fewer than 2 simulations provided
    """
    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    comparison = service.get_simulation_comparison(
        tenant_id=tenant_id,
        simulation_ids=request_body.simulation_ids,
    )

    return comparison


@app.get(
    "/tenants/{tenant_id}/simulations/{simulation_id}",
    response_model=SimulationDetailResponse,
)
def get_simulation_detail(
    tenant_id: UUID,
    simulation_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationDetailResponse:
    """Retrieve a saved simulation with all its scenarios.

    FR-090 / T-084: Build save and revisit simulation scenarios.
    Allows users to retrieve and review previously run simulations with all
    three scenarios (baseline/upside/downside) and related metadata.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier

    Returns:
        SimulationDetailResponse with simulation record and all scenarios

    Raises:
        404: If tenant or simulation not found
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulation, scenarios = service.get_simulation_with_scenarios(
        tenant_id=tenant_id,
        simulation_id=simulation_id,
    )

    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    return SimulationDetailResponse(
        simulation=SimulationResponse.model_validate(simulation),
        scenarios=[ScenarioResponse.model_validate(s) for s in scenarios],
    )


@app.get(
    "/tenants/{tenant_id}/simulations/{simulation_id}/chart-data",
    response_model=SimulationChartDataResponse,
)
def get_simulation_chart_data(
    tenant_id: UUID,
    simulation_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> dict:
    """Get chart-ready data for frontend visualization.

    E7: Returns structured data optimized for chart libraries:
    - Time-series: Projected metric values over time periods for line charts
    - Waterfall: Baseline → changes → final outcome for waterfall charts
    - Metric deltas: Side-by-side scenario comparison for bar charts

    All data is pre-calculated and formatted for direct consumption by
    frontend chart components (Chart.js, Recharts, D3, etc.).

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier

    Returns:
        SimulationChartDataResponse with time_series, waterfall, and metric_deltas

    Raises:
        404: If tenant or simulation not found
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    try:
        chart_data = service.get_simulation_chart_data(
            tenant_id=tenant_id,
            simulation_id=simulation_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return chart_data


@app.get(
    "/tenants/{tenant_id}/simulations",
    response_model=SimulationListResponse,
)
def list_simulations_for_tenant(
    tenant_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> SimulationListResponse:
    """List all simulations for a tenant with pagination.

    FR-090 / T-084: Build save and revisit simulation scenarios.
    Allows users to browse their simulation history and select previous
    scenarios for review or comparison.

    Args:
        tenant_id: Tenant identifier
        skip: Number of records to skip (default 0)
        limit: Max records to return (default 100, max 500)

    Returns:
        SimulationListResponse with paginated simulations and total count

    Raises:
        404: If tenant not found
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    simulations, total_count = service.list_simulations(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )

    return SimulationListResponse(
        simulations=[SimulationResponse.model_validate(s) for s in simulations],
        total_count=total_count,
    )


# ---------------------------------------------------------------------------
# E2: Simulation rename/duplicate/delete endpoints
# ---------------------------------------------------------------------------


@app.patch(
    "/tenants/{tenant_id}/simulations/{simulation_id}",
    response_model=SimulationResponse,
)
def update_simulation(
    tenant_id: UUID,
    simulation_id: UUID,
    body: SimulationUpdateRequest,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> Simulation:
    """Update simulation name and/or description (E2 rename).

    Allows users to rename simulations and add descriptive notes for
    organization and future reference.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier
        body: SimulationUpdateRequest with name/description fields

    Returns:
        Updated SimulationResponse

    Raises:
        404: If tenant or simulation not found
        400: If simulation is deleted
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    simulation = db.scalar(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.tenant_id == tenant_id,
        )
    )
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    if simulation.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a deleted simulation.",
        )

    # Update fields if provided
    if body.name is not None:
        simulation.name = body.name
    if body.description is not None:
        simulation.description = body.description

    db.commit()
    db.refresh(simulation)

    return simulation


@app.post(
    "/tenants/{tenant_id}/simulations/{simulation_id}/duplicate",
    response_model=SimulationDuplicateResponse,
)
def duplicate_simulation(
    tenant_id: UUID,
    simulation_id: UUID,
    body: SimulationDuplicateRequest,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> SimulationDuplicateResponse:
    """Duplicate a simulation (E2 duplicate).

    Creates a copy of the simulation with all scenarios. Useful for
    testing variations or preserving historical baselines.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier to duplicate
        body: SimulationDuplicateRequest with optional name/description

    Returns:
        SimulationDuplicateResponse with original and duplicate IDs

    Raises:
        404: If tenant or simulation not found
        400: If simulation is deleted
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    original = db.scalar(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.tenant_id == tenant_id,
        )
    )
    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    if original.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot duplicate a deleted simulation.",
        )

    # Create duplicate
    duplicate = Simulation(
        tenant_id=original.tenant_id,
        recommendation_id=original.recommendation_id,
        name=body.name or (f"Copy of {original.name}" if original.name else None),
        description=body.description or original.description,
        domain=original.domain,
        simulation_type="manual",  # Duplicates are always manual
        x_star=original.x_star.copy() if original.x_star else {},
        confidence_level=original.confidence_level,
        data_freshness_signal=original.data_freshness_signal,
        metric_completeness_signal=original.metric_completeness_signal,
        baseline_scenario=original.baseline_scenario.copy()
        if original.baseline_scenario
        else {},
        upside_scenario=original.upside_scenario.copy()
        if original.upside_scenario
        else {},
        downside_scenario=original.downside_scenario.copy()
        if original.downside_scenario
        else {},
        simulation_metadata={
            **(original.simulation_metadata or {}),
            "duplicated_from": str(original.id),
            "duplicated_at": datetime.now(UTC).isoformat(),
        },
    )
    db.add(duplicate)
    db.flush()

    # Duplicate scenarios
    original_scenarios = db.scalars(
        select(Scenario).where(Scenario.simulation_id == original.id)
    ).all()

    for orig_scenario in original_scenarios:
        dup_scenario = Scenario(
            simulation_id=duplicate.id,
            scenario_type=orig_scenario.scenario_type,
            input_assumptions=orig_scenario.input_assumptions.copy()
            if orig_scenario.input_assumptions
            else {},
            output_metrics=orig_scenario.output_metrics.copy()
            if orig_scenario.output_metrics
            else {},
            impact_deltas=orig_scenario.impact_deltas.copy()
            if orig_scenario.impact_deltas
            else {},
            confidence_score=orig_scenario.confidence_score,
            rationale=orig_scenario.rationale,
        )
        db.add(dup_scenario)

    db.commit()
    db.refresh(duplicate)

    return SimulationDuplicateResponse(
        original_id=original.id,
        duplicate_id=duplicate.id,
        duplicate=SimulationResponse.model_validate(duplicate),
    )


@app.delete(
    "/tenants/{tenant_id}/simulations/{simulation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_simulation(
    tenant_id: UUID,
    simulation_id: UUID,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Soft delete a simulation (E2 delete).

    Marks simulation as deleted while preserving audit trail. Deleted
    simulations are excluded from list views but remain in database.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier

    Returns:
        204 No Content on success

    Raises:
        404: If tenant or simulation not found
        400: If simulation is already deleted
    """
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    simulation = db.scalar(
        select(Simulation).where(
            Simulation.id == simulation_id,
            Simulation.tenant_id == tenant_id,
        )
    )
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    if simulation.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation is already deleted.",
        )

    simulation.is_deleted = True
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/tenants/{tenant_id}/simulations/{simulation_id}/export",
)
def export_simulation(
    tenant_id: UUID,
    simulation_id: UUID,
    request_body: SimulationExportRequest,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> StreamingResponse:
    """Generate and download a simulation export (PDF or CSV).

    FR-091 / T-085: Build export generation service for all domains.
    Allows users to export simulations as PDF or CSV for sharing, archival,
    and presentation to stakeholders.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier
        request_body: SimulationExportRequest with format parameter

    Returns:
        FileResponse with the generated file

    Raises:
        404: If tenant or simulation not found
        422: If invalid export format
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    try:
        file_content, file_name = service.generate_simulation_export(
            tenant_id=tenant_id,
            simulation_id=simulation_id,
            format=request_body.format,
        )
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    # Determine media type based on format
    media_type = (
        "application/pdf"
        if request_body.format == "pdf"
        else "text/csv"
    )

    return StreamingResponse(
        iter([file_content]),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={file_name}",
        },
    )


@app.post(
    "/tenants/{tenant_id}/simulations/{simulation_id}/share",
)
def share_simulation_export(
    tenant_id: UUID,
    simulation_id: UUID,
    request_body: ExportShareRequest,
    _auth: IntelSimulationsViewDep,
    _feature: RequireSimulations,
    db: Session = Depends(get_db),  # noqa: B008
) -> ExportShareResponse:
    """Share a simulation export with a recipient.

    T-086: Build scoped export sharing with permission checks.
    Verifies recipient has access to the simulation domain data
    and creates an immutable share record.

    Args:
        tenant_id: Tenant identifier
        simulation_id: Simulation identifier
        request_body: ExportShareRequest with recipient email
        _auth: Authenticated user (must be OperationsManager role)

    Returns:
        ExportShareResponse with share details

    Raises:
        400: If recipient validation fails
        404: If tenant or simulation not found
        403: If user lacks permission to share
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    try:
        # Get current user ID from auth context
        current_user = db.scalar(
            select(User).where(User.email == _auth.email.strip().lower())
        )
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found.",
            )

        share = service.share_export(
            db=db,
            tenant_id=tenant_id,
            simulation_id=simulation_id,
            shared_by_user_id=current_user.id,
            recipient_email=request_body.recipient_email,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "inactive" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Fetch full share with related data for response
    share_with_relations = db.scalar(
        select(ExportShare)
        .where(ExportShare.id == share.id)
    )
    if share_with_relations is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created share.",
        )

    shared_by_user = db.scalar(
        select(User).where(User.id == share_with_relations.shared_by_user_id)
    )
    shared_with_user = db.scalar(
        select(User).where(User.id == share_with_relations.shared_with_user_id)
    )

    return ExportShareResponse(
        id=share_with_relations.id,
        simulation_id=share_with_relations.simulation_id,
        shared_by_email=shared_by_user.email if shared_by_user else "",
        shared_with_email=shared_with_user.email if shared_with_user else "",
        status=share_with_relations.status,
        created_at=share_with_relations.created_at,
        revoked_at=share_with_relations.revoked_at,
    )


@app.get(
    "/tenants/{tenant_id}/exports/shared",
)
def list_shared_exports(
    tenant_id: UUID,
    _auth: IntelSimulationsViewDep,
    skip: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(50, ge=1, le=100),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExportShareListResponse:
    """List simulation exports shared with the current user.

    T-086: Retrieve all active exports that have been shared with the
    authenticated user within a tenant.

    Args:
        tenant_id: Tenant identifier
        _auth: Authenticated user (recipient of shares)
        skip: Pagination offset
        limit: Pagination limit (max 100)

    Returns:
        ExportShareListResponse with list of active shares

    Raises:
        404: If tenant not found
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    # Get current user
    current_user = db.scalar(
        select(User).where(User.email == _auth.email.strip().lower())
    )
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    shares, total = service.get_shared_exports_with_me(
        db=db,
        tenant_id=tenant_id,
        recipient_user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    share_responses = []
    for share in shares:
        shared_by_user = db.scalar(
            select(User).where(User.id == share.shared_by_user_id)
        )
        shared_with_user = db.scalar(
            select(User).where(User.id == share.shared_with_user_id)
        )
        share_responses.append(
            ExportShareResponse(
                id=share.id,
                simulation_id=share.simulation_id,
                shared_by_email=shared_by_user.email if shared_by_user else "",
                shared_with_email=shared_with_user.email if shared_with_user else "",
                status=share.status,
                created_at=share.created_at,
                revoked_at=share.revoked_at,
            )
        )

    return ExportShareListResponse(
        shares=share_responses,
        total=total,
    )


@app.delete(
    "/tenants/{tenant_id}/exports/{share_id}/revoke",
)
def revoke_export_share(
    tenant_id: UUID,
    share_id: UUID,
    _auth: IntelSimulationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> ExportShareResponse:
    """Revoke an export share.

    T-086: Immediately revoke access to a previously shared export.
    Share record is retained for audit trail.

    Args:
        tenant_id: Tenant identifier
        share_id: ExportShare identifier
        _auth: Authenticated user (must be OperationsManager role)

    Returns:
        ExportShareResponse with updated share (status='revoked')

    Raises:
        404: If tenant or share not found
        403: If user lacks permission to revoke
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    try:
        share = service.revoke_export_share(
            db=db,
            tenant_id=tenant_id,
            share_id=share_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    shared_by_user = db.scalar(
        select(User).where(User.id == share.shared_by_user_id)
    )
    shared_with_user = db.scalar(
        select(User).where(User.id == share.shared_with_user_id)
    )

    return ExportShareResponse(
        id=share.id,
        simulation_id=share.simulation_id,
        shared_by_email=shared_by_user.email if shared_by_user else "",
        shared_with_email=shared_with_user.email if shared_with_user else "",
        status=share.status,
        created_at=share.created_at,
        revoked_at=share.revoked_at,
    )


@app.post(
    "/tenants/{tenant_id}/exports/{share_id}/generate-link",
)
def generate_export_download_link(
    tenant_id: UUID,
    share_id: UUID,
    _auth: IntelSimulationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> GeneratedExportLinkResponse:
    """T-087: Generate a signed download link for an export share.

    Creates a time-limited, cryptographically signed URL token.
    Recipient can use this token to download the export file.
    Link expires after 7 days by default.

    Args:
        tenant_id: Tenant identifier
        share_id: ExportShare identifier (must be active, not revoked)
        _auth: Authenticated user (must be OperationsManager role)

    Returns:
        GeneratedExportLinkResponse with download link and URL

    Raises:
        400: If share is revoked or invalid
        404: If tenant or share not found
        403: If user lacks permission
    """
    # Validate tenant exists
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    from backend.app.simulation_service import SimulationService
    service = SimulationService(db)

    try:
        export_link = service.generate_export_download_link(
            db=db,
            tenant_id=tenant_id,
            share_id=share_id,
            expiry_days=7,
        )
    except ValueError as e:
        if "revoked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Share has been revoked.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Construct full download URL
    download_url = f"/exports/download/{export_link.token}"

    return GeneratedExportLinkResponse(
        download_link=ExportLinkResponse(
            id=export_link.id,
            share_id=export_link.share_id,
            token=export_link.token,
            expires_at=export_link.expires_at,
            created_at=export_link.created_at,
            accessed_at=export_link.accessed_at,
        ),
        download_url=download_url,
    )


@app.get(
    "/exports/download/{token}",
)
def download_export_by_link(
    token: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> StreamingResponse:
    """T-087: Download export file using signed download link.

    Validates token signature and expiry, then returns the file.
    Recipient must have permission (checked via share membership).
    Updates accessed_at timestamp when link is used.

    Args:
        token: Signed download token from generated link
        db: Database session

    Returns:
        File content with appropriate media type

    Raises:
        400: If token is invalid or expired
        404: If export or share not found
    """
    from itsdangerous import BadSignature, SignatureExpired

    from backend.app.simulation_service import SimulationService

    service = SimulationService(db)

    # Validate token and get associated share
    try:
        export_link = service.validate_and_get_export_by_token(
            db=db,
            token=token,
            max_age_seconds=604800,  # 7 days
        )
    except SignatureExpired as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Download link has expired.",
        ) from e
    except BadSignature as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered download link.",
        ) from e
    except ValueError as e:
        if "share revoked" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This export is no longer available.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Get the associated share to retrieve simulation
    share = db.scalar(
        select(ExportShare).where(ExportShare.id == export_link.share_id)
    )
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export share not found.",
        )

    # Generate the export file
    try:
        file_content, file_name = service.generate_simulation_export(
            tenant_id=share.tenant_id,
            simulation_id=share.simulation_id,
            format="pdf",  # Default to PDF for downloads
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    # Return file as streaming response
    return StreamingResponse(
        iter([file_content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={file_name}",
        },
    )


# =============================================================================
# Permissions & Roles Endpoints
# =============================================================================


@app.get("/permissions", response_model=PermissionCatalogResponse)
def get_permissions_catalog(
    auth: AuthDep,
) -> PermissionCatalogResponse:
    """Get catalog of all available permissions."""
    permissions_list = [
        PermissionInfo(
            permission=permission,
            description=perm.PERMISSION_DESCRIPTIONS.get(permission, ""),
        )
        for permission in perm.ALL_PERMISSIONS
    ]
    return PermissionCatalogResponse(permissions=permissions_list)


@app.get("/kpis", response_model=KPICatalogResponse)
def get_kpi_catalog(
    auth: AuthDep,
    domain: str | None = Query(  # noqa: B008
        None,
        description=(
            "Filter by domain (executive, growth, retention, "
            "finance, operations, intelligence)"
        ),
    ),
) -> KPICatalogResponse:
    """Get catalog of all KPI metadata.
    
    Returns definitions, formulas, data sources, and guidance for all KPIs.
    Optionally filter by domain to get KPIs for a specific persona.
    
    Args:
        auth: Authenticated user context
        domain: Optional domain filter (executive, growth, retention,
            finance, operations, intelligence)
    
    Returns:
        KPICatalogResponse with list of KPI metadata
    """
    if domain:
        kpi_dict = kpis.get_kpis_by_domain(domain)
    else:
        kpi_dict = kpis.get_all_kpis()
    
    kpi_list = [
        KPIMetadataResponse(
            key=metadata["key"],
            name=metadata["name"],
            description=metadata["description"],
            formula=metadata["formula"],
            unit=metadata["unit"],
            domain=metadata["domain"],
            data_sources=metadata["data_sources"],
            good_direction=metadata["good_direction"],
            target_range=metadata["target_range"],
        )
        for metadata in kpi_dict.values()
    ]
    
    return KPICatalogResponse(kpis=kpi_list, total=len(kpi_list))


@app.get(
    "/tenants/{tenant_id}/executive/overview",
    response_model=ExecutiveOverviewResponse,
)
def get_executive_overview(
    tenant_id: UUID,
    auth: ExecutiveViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    period_start: date | None = Query(  # noqa: B008
        None, description="Start date for analysis period (inclusive)"
    ),
    period_end: date | None = Query(  # noqa: B008
        None, description="End date for analysis period (inclusive)"
    ),
) -> ExecutiveOverviewResponse:
    """Get executive overview dashboard with key financial and operational metrics.

    Returns comprehensive business health view including:
    - Primary financial metrics (revenue, profit, contribution margin)
    - Growth metrics (revenue growth rate)
    - Key performance indicators (ROAS, CAC payback, repeat rate, return rate)
    - Business health indicators across all functional areas
    - Cross-team performance rollup

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with executive.view permission
        db: Database session
        period_start: Start of analysis period (defaults to 30 days ago)
        period_end: End of analysis period (defaults to today)

    Returns:
        ExecutiveOverviewResponse with calculated metrics and health indicators
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Default to last 90 days if no period specified
    if period_end is None:
        period_end = datetime.now(UTC).date()
    if period_start is None:
        period_start = period_end - timedelta(days=90)

    # Validate period
    if period_start > period_end:
        raise HTTPException(
            status_code=400,
            detail="period_start must be before or equal to period_end",
        )

    # Calculate overview
    overview = executive_service.calculate_executive_overview(
        db=db,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
    )

    return overview


@app.get(
    "/tenants/{tenant_id}/growth/dashboard",
    response_model=GrowthDashboardResponse,
)
def get_growth_dashboard(
    tenant_id: UUID,
    auth: GrowthViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    period_start: date | None = Query(  # noqa: B008
        None, description="Start date for analysis period (inclusive)"
    ),
    period_end: date | None = Query(  # noqa: B008
        None, description="End date for analysis period (inclusive)"
    ),
) -> GrowthDashboardResponse:
    """Get growth dashboard with channel and campaign performance metrics.

    Returns comprehensive marketing efficiency view including:
    - Blended metrics (total spend, ROAS, CAC)
    - Per-channel breakdown (Meta, Google Ads)
    - Campaign performance (top performers and underperforming campaigns)
    - Attribution and profitability metrics

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with growth.view permission
        db: Database session
        period_start: Start of analysis period (defaults to 30 days ago)
        period_end: End of analysis period (defaults to today)

    Returns:
        GrowthDashboardResponse with channel and campaign metrics
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Default to last 90 days if no period specified
    if period_end is None:
        period_end = datetime.now(UTC).date()
    if period_start is None:
        period_start = period_end - timedelta(days=90)

    # Validate period
    if period_start > period_end:
        raise HTTPException(
            status_code=400,
            detail="period_start must be before or equal to period_end",
        )

    # Calculate dashboard
    dashboard = growth_service.calculate_growth_dashboard(
        db=db,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
    )

    return dashboard


@app.get(
    "/tenants/{tenant_id}/retention/dashboard",
    response_model=RetentionDashboardResponse,
)
def get_retention_dashboard(
    tenant_id: UUID,
    auth: RetentionViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    period_start: date | None = Query(None),  # noqa: B008
    period_end: date | None = Query(None),  # noqa: B008
) -> RetentionDashboardResponse:
    """Get retention dashboard for a tenant.

    Returns retention metrics including:
    - Repeat purchase rate and customer lifetime value
    - Cohort retention analysis
    - Customer segment breakdown
    - Churn risk indicators

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with retention.view permission
        db: Database session
        period_start: Optional start date (defaults to 90 days ago)
        period_end: Optional end date (defaults to today)

    Returns:
        RetentionDashboardResponse with retention metrics

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Default period: last 90 days
    if period_end is None:
        period_end = datetime.now(UTC).date()
    if period_start is None:
        period_start = period_end - timedelta(days=90)

    # Validate period
    if period_start > period_end:
        raise HTTPException(
            status_code=400,
            detail="period_start must be before or equal to period_end",
        )

    # Calculate dashboard
    dashboard = retention_service.calculate_retention_dashboard(
        db=db,
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
    )

    return dashboard


# =============================================================================
# TREND / TIME-SERIES ENDPOINTS
# =============================================================================


@app.get(
    "/tenants/{tenant_id}/executive/trend",
    response_model=ExecutiveTrendResponse,
)
def get_executive_trend(
    tenant_id: UUID,
    auth: ExecutiveViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> ExecutiveTrendResponse:
    """Get executive KPI trend (time-series) for a tenant.

    Returns time-series data points from ExecutiveKpiSnapshot for the
    specified date range. Useful for charting KPI trends over time.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with executive.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        ExecutiveTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(ExecutiveKpiSnapshot)
        .where(ExecutiveKpiSnapshot.tenant_id == tenant_id)
        .where(ExecutiveKpiSnapshot.snapshot_date >= period_start)
        .where(ExecutiveKpiSnapshot.snapshot_date <= period_end)
        .order_by(ExecutiveKpiSnapshot.snapshot_date)
    ).all()

    # Build response
    from backend.app.schemas.trends import ExecutiveTrendDataPoint

    data_points = [
        ExecutiveTrendDataPoint(
            snapshot_date=snap.snapshot_date,
            revenue_amount=snap.revenue_amount,
            ad_spend_amount=snap.ad_spend_amount,
            blended_roas=snap.blended_roas,
            contribution_margin_pct=snap.contribution_margin_pct,
        )
        for snap in snapshots
    ]

    return ExecutiveTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get(
    "/tenants/{tenant_id}/growth/trend",
    response_model=GrowthTrendResponse,
)
def get_growth_trend(
    tenant_id: UUID,
    auth: GrowthViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> GrowthTrendResponse:
    """Get growth channel trends (time-series) for a tenant.

    Returns time-series data points from AcquisitionMetricsSnapshot
    grouped by channel for the specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with growth.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        GrowthTrendResponse with per-channel time-series data

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(AcquisitionMetricsSnapshot)
        .where(AcquisitionMetricsSnapshot.tenant_id == tenant_id)
        .where(AcquisitionMetricsSnapshot.snapshot_date >= period_start)
        .where(AcquisitionMetricsSnapshot.snapshot_date <= period_end)
        .order_by(
            AcquisitionMetricsSnapshot.channel,
            AcquisitionMetricsSnapshot.snapshot_date,
        )
    ).all()

    # Group by channel
    from collections import defaultdict

    from backend.app.schemas.trends import (
        GrowthChannelTrendDataPoint,
        GrowthChannelTrendResponse,
    )

    channel_data: dict[str, list[GrowthChannelTrendDataPoint]] = defaultdict(list)
    for snap in snapshots:
        channel_data[snap.channel].append(
            GrowthChannelTrendDataPoint(
                snapshot_date=snap.snapshot_date,
                ad_spend_amount=snap.ad_spend_amount,
                revenue_attributed=snap.revenue_attributed,
                order_count=snap.order_count,
                roas=snap.roas,
                cac=snap.cac,
                contribution_margin_pct=snap.contribution_margin_pct,
                payback_period_days=snap.payback_period_days,
            )
        )

    # Build channel responses
    window_label = date_utils.get_window_label(
        params.window or date_utils.DateWindow.NINETY_DAYS
    )
    channels = [
        GrowthChannelTrendResponse(
            channel=channel,
            data_points=points,
            period_start=period_start,
            period_end=period_end,
            window_label=window_label,
        )
        for channel, points in sorted(channel_data.items())
    ]

    return GrowthTrendResponse(
        channels=channels,
        period_start=period_start,
        period_end=period_end,
        window_label=window_label,
    )


@app.get(
    "/tenants/{tenant_id}/retention/trend",
    response_model=RetentionTrendResponse,
)
def get_retention_trend(
    tenant_id: UUID,
    auth: RetentionViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> RetentionTrendResponse:
    """Get retention metrics trend (time-series) for a tenant.

    Returns time-series data points from RetentionDailySnapshot for the
    specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with retention.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        RetentionTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(RetentionDailySnapshot)
        .where(RetentionDailySnapshot.tenant_id == tenant_id)
        .where(RetentionDailySnapshot.snapshot_date >= period_start)
        .where(RetentionDailySnapshot.snapshot_date <= period_end)
        .order_by(RetentionDailySnapshot.snapshot_date)
    ).all()

    # Build response
    from backend.app.schemas.trends import RetentionTrendDataPoint

    data_points = [
        RetentionTrendDataPoint(
            snapshot_date=snap.snapshot_date,
            total_customers=snap.total_customers,
            repeat_customers=snap.repeat_customers,
            repeat_purchase_rate_pct=snap.repeat_purchase_rate_pct,
        )
        for snap in snapshots
    ]

    return RetentionTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get(
    "/tenants/{tenant_id}/finance/cost-drivers/trend",
    response_model=CostDriverTrendResponse,
)
def get_cost_driver_trend(
    tenant_id: UUID,
    auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> CostDriverTrendResponse:
    """Get cost driver trend (time-series) for a tenant.

    Returns time-series data points from CostDriverSnapshot for the
    specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with finance.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        CostDriverTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(CostDriverSnapshot)
        .where(CostDriverSnapshot.tenant_id == tenant_id)
        .where(CostDriverSnapshot.snapshot_date >= period_start)
        .where(CostDriverSnapshot.snapshot_date <= period_end)
        .order_by(CostDriverSnapshot.snapshot_date)
    ).all()

    # Build response (one row per driver_type per snapshot_date)
    from backend.app.schemas.trends import CostDriverTrendDataPoint

    data_points = [
        CostDriverTrendDataPoint(
            snapshot_date=snap.snapshot_date,
            driver_type=snap.driver_type,
            absolute_amount=snap.absolute_amount,
            pct_of_revenue=snap.pct_of_revenue,
            margin_impact_amount=snap.margin_impact_amount,
        )
        for snap in snapshots
    ]

    return CostDriverTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get(
    "/tenants/{tenant_id}/finance/margin-drift/trend",
    response_model=MarginDriftTrendResponse,
)
def get_margin_drift_trend(
    tenant_id: UUID,
    auth: FinanceViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> MarginDriftTrendResponse:
    """Get margin drift trend (time-series) for a tenant.

    Returns time-series data points from MarginDriftSnapshot for the
    specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with finance.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        MarginDriftTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(MarginDriftSnapshot)
        .where(MarginDriftSnapshot.tenant_id == tenant_id)
        .where(MarginDriftSnapshot.snapshot_date >= period_start)
        .where(MarginDriftSnapshot.snapshot_date <= period_end)
        .order_by(MarginDriftSnapshot.snapshot_date)
    ).all()

    # Build response (one row per channel × category per snapshot_date)
    from backend.app.schemas.trends import MarginDriftTrendDataPoint

    data_points = [
        MarginDriftTrendDataPoint(
            snapshot_date=snap.snapshot_date,
            channel=snap.channel,
            category=snap.category,
            actual_margin_pct=snap.actual_margin_pct,
            expected_margin_pct=snap.expected_margin_pct,
            drift_pct=snap.drift_pct,
        )
        for snap in snapshots
    ]

    return MarginDriftTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get(
    "/tenants/{tenant_id}/operations/inventory-risk/trend",
    response_model=InventoryRiskTrendResponse,
)
def get_inventory_risk_trend(
    tenant_id: UUID,
    auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> InventoryRiskTrendResponse:
    """Get inventory risk trend (time-series) for a tenant.

    Returns time-series data points from InventoryRiskSnapshot for the
    specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with operations.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        InventoryRiskTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(InventoryRiskSnapshot)
        .where(InventoryRiskSnapshot.tenant_id == tenant_id)
        .where(InventoryRiskSnapshot.snapshot_date >= period_start)
        .where(InventoryRiskSnapshot.snapshot_date <= period_end)
        .order_by(InventoryRiskSnapshot.snapshot_date)
    ).all()

    # Build response - aggregate per-SKU snapshots by date
    from collections import defaultdict

    from backend.app.schemas.trends import InventoryRiskTrendDataPoint

    # Group by snapshot_date and aggregate
    date_aggregates: dict[date, dict[str, float | int]] = defaultdict(
        lambda: {
            "total_skus": 0,
            "stockout_risk_skus": 0,
            "overstock_skus": 0,
            "total_capital_at_risk": 0.0,
        }
    )

    for snap in snapshots:
        agg = date_aggregates[snap.snapshot_date]
        agg["total_skus"] += 1
        if snap.status in ("stockout_risk", "low_stock"):
            agg["stockout_risk_skus"] += 1
        if snap.status == "overstock":
            agg["overstock_skus"] += 1
        if snap.capital_at_risk:
            agg["total_capital_at_risk"] += snap.capital_at_risk

    # Build data points
    data_points = [
        InventoryRiskTrendDataPoint(
            snapshot_date=snap_date,
            total_skus=int(agg["total_skus"]),
            stockout_risk_skus=int(agg["stockout_risk_skus"]),
            overstock_skus=int(agg["overstock_skus"]),
            total_capital_at_risk=float(agg["total_capital_at_risk"]),
        )
        for snap_date, agg in sorted(date_aggregates.items())
    ]

    return InventoryRiskTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get(
    "/tenants/{tenant_id}/operations/operational-impact/trend",
    response_model=OperationalImpactTrendResponse,
)
def get_operational_impact_trend(
    tenant_id: UUID,
    auth: OperationsViewDep,
    db: Session = Depends(get_db),  # noqa: B008
    window: date_utils.DateWindow | None = Query(  # noqa: B008
        date_utils.DateWindow.NINETY_DAYS,
        description="Preset date window",
    ),
    start_date: date | None = Query(None),  # noqa: B008
    end_date: date | None = Query(None),  # noqa: B008
) -> OperationalImpactTrendResponse:
    """Get operational impact trend (time-series) for a tenant.

    Returns time-series data points from OperationalImpactSnapshot for the
    specified date range.

    Args:
        tenant_id: Tenant UUID
        auth: Authenticated user with operations.view permission
        db: Database session
        window: Preset date window (default: 90d)
        start_date: Custom start date (required if window=custom)
        end_date: Custom end date (required if window=custom)

    Returns:
        OperationalImpactTrendResponse with time-series data points

    Raises:
        HTTPException: 404 if tenant not found, 400 if invalid date range
    """
    # Verify tenant access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate permission tenant matches requested tenant
    membership = db.scalar(
        select(TenantMembership)
        .join(User)
        .where(User.email == auth.email)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied to this tenant")

    # Parse date range
    params = date_utils.DateRangeParams(
        window=window, start_date=start_date, end_date=end_date
    )
    period_start, period_end = date_utils.calculate_date_range(params)

    # Query snapshots within date range
    snapshots = db.scalars(
        select(OperationalImpactSnapshot)
        .where(OperationalImpactSnapshot.tenant_id == tenant_id)
        .where(OperationalImpactSnapshot.snapshot_date >= period_start)
        .where(OperationalImpactSnapshot.snapshot_date <= period_end)
        .order_by(OperationalImpactSnapshot.snapshot_date)
    ).all()

    # Build response - aggregate per-SKU snapshots by date
    from collections import defaultdict

    from backend.app.schemas.trends import OperationalImpactTrendDataPoint

    # Group by snapshot_date and aggregate
    date_aggregates: dict[date, dict[str, float | int]] = defaultdict(
        lambda: {
            "total_skus": 0,
            "total_margin_impact": 0.0,
            "margin_impact_count": 0,
            "total_lost_revenue": 0.0,
        }
    )

    for snap in snapshots:
        agg = date_aggregates[snap.snapshot_date]
        agg["total_skus"] += 1
        if snap.logistics_margin_impact_pct is not None:
            agg["total_margin_impact"] += snap.logistics_margin_impact_pct
            agg["margin_impact_count"] += 1
        if snap.stockout_lost_revenue_estimate:
            agg["total_lost_revenue"] += snap.stockout_lost_revenue_estimate

    # Build data points
    data_points = [
        OperationalImpactTrendDataPoint(
            snapshot_date=snap_date,
            total_skus=int(agg["total_skus"]),
            avg_logistics_margin_impact_pct=(
                float(agg["total_margin_impact"])
                / agg["margin_impact_count"]
                if agg["margin_impact_count"] > 0
                else 0.0
            ),
            total_stockout_lost_revenue=float(agg["total_lost_revenue"]),
        )
        for snap_date, agg in sorted(date_aggregates.items())
    ]

    return OperationalImpactTrendResponse(
        data_points=data_points,
        period_start=period_start,
        period_end=period_end,
        window_label=date_utils.get_window_label(
            params.window or date_utils.DateWindow.NINETY_DAYS
        ),
    )


@app.get("/roles", response_model=RoleListResponse)
def get_roles(
    auth: AuthDep,
    tenant_id: UUID = Query(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RoleListResponse:
    """Get all roles for a tenant (system and custom)."""
    # Get tenant
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )
    
    # Get all roles for this tenant
    roles = db.scalars(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .order_by(Role.is_system.desc(), Role.name)
    ).all()
    
    role_responses = [
        RoleResponse(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            permissions=role.permissions,
            is_system=role.is_system,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        for role in roles
    ]
    
    return RoleListResponse(roles=role_responses)


@app.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    request: RoleCreateRequest,
    auth: AuthDep,
    tenant_id: UUID = Query(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RoleResponse:
    """Create a custom role for a tenant."""
    # Get tenant
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )
    
    # Check if role name already exists for this tenant
    existing_role = db.scalar(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .where(Role.name == request.name)
    )
    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{request.name}' already exists for this tenant.",
        )
    
    # Validate permissions
    invalid_permissions = [
        p for p in request.permissions if p not in perm.ALL_PERMISSIONS
    ]
    if invalid_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permissions: {', '.join(invalid_permissions)}",
        )
    
    # Create role
    role = Role(
        tenant_id=tenant_id,
        name=request.name,
        permissions=request.permissions,
        is_system=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    
    # Audit event
    actor = db.scalar(select(User).where(User.email == auth.email))
    write_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=actor.id if actor else None,
        action="role.create",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name, "permissions": role.permissions},
    )
    
    return RoleResponse(
        id=role.id,
        tenant_id=role.tenant_id,
        name=role.name,
        permissions=role.permissions,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@app.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> RoleResponse:
    """Get role details by ID."""
    role = db.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )
    
    return RoleResponse(
        id=role.id,
        tenant_id=role.tenant_id,
        name=role.name,
        permissions=role.permissions,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@app.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> RoleResponse:
    """Update a custom role (system roles cannot be modified)."""
    role = db.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be modified.",
        )
    
    # Update name if provided
    if request.name is not None:
        # Check if new name conflicts with existing role
        existing_role = db.scalar(
            select(Role)
            .where(Role.tenant_id == role.tenant_id)
            .where(Role.name == request.name)
            .where(Role.id != role_id)
        )
        if existing_role is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{request.name}' already exists for this tenant.",
            )
        role.name = request.name
    
    # Update permissions if provided
    if request.permissions is not None:
        # Validate permissions
        invalid_permissions = [
            p for p in request.permissions if p not in perm.ALL_PERMISSIONS
        ]
        if invalid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permissions: {', '.join(invalid_permissions)}",
            )
        role.permissions = request.permissions
    
    role.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(role)
    
    # Audit event
    actor = db.scalar(select(User).where(User.email == auth.email))
    write_audit_event(
        db=db,
        tenant_id=role.tenant_id,
        actor_user_id=actor.id if actor else None,
        action="role.update",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name, "permissions": role.permissions},
    )
    
    return RoleResponse(
        id=role.id,
        tenant_id=role.tenant_id,
        name=role.name,
        permissions=role.permissions,
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@app.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: UUID,
    auth: AuthDep,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a custom role (system roles cannot be deleted)."""
    role = db.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted.",
        )
    
    # Check if any memberships are using this role
    membership_count = db.scalar(
        select(func.count(TenantMembership.id))
        .where(TenantMembership.role_id == role_id)
    )
    if membership_count and membership_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete role. It is assigned to {membership_count} "
                f"member(s). Please reassign them first."
            ),
        )
    
    # Audit event
    actor = db.scalar(select(User).where(User.email == auth.email))
    write_audit_event(
        db=db,
        tenant_id=role.tenant_id,
        actor_user_id=actor.id if actor else None,
        action="role.delete",
        entity_type="role",
        entity_id=str(role.id),
        details={"name": role.name},
    )
    
    db.delete(role)
    db.commit()


