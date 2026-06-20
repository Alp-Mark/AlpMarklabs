"""Feature flag enforcement for endpoint access control."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import FeatureFlag, SubscriptionPlan, TenantFeatureFlag
from backend.app.db.session import get_db
from backend.app.security import AuthContext, get_current_auth


def check_tenant_feature_access(
    tenant_id: uuid.UUID,
    feature_slug: str,
    db: Session,
) -> bool:
    """Check if tenant has access to a feature.

    Resolution order: override > plan > default
    """
    # Get feature flag
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.slug == feature_slug))
    if not flag or not flag.is_available:
        return False

    # Check for tenant override
    override = db.scalar(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.feature_flag_slug == feature_slug,
        )
    )
    if override:
        return override.is_enabled

    # Check tenant's subscription plan
    from backend.app.db.models import Tenant

    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if tenant and tenant.billing_plan:
        plan = db.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.slug == tenant.billing_plan
            )
        )
        if plan and isinstance(plan.features, list) and feature_slug in plan.features:
            return True

    # Fall back to default
    return flag.default_enabled


def require_feature(feature_slug: str) -> Callable[..., AuthContext]:
    """Create a dependency that requires a specific feature flag.

    Usage:
        @app.get("/endpoint")
        def endpoint(
            tenant_id: uuid.UUID,
            _feature: Annotated[None, Depends(require_feature("simulations"))],
            ...
        ):
            ...
    """

    def _check_feature(
        tenant_id: uuid.UUID,
        auth: Annotated[AuthContext, Depends(get_current_auth)],
        db: Session = Depends(get_db),  # noqa: B008
    ) -> AuthContext:
        has_access = check_tenant_feature_access(tenant_id, feature_slug, db)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_slug}' is not enabled for this tenant",
            )
        return auth

    return _check_feature


# Predefined dependencies for common features
RequireSimulations = Annotated[AuthContext, Depends(require_feature("simulations"))]
RequireAdvancedRecommendations = Annotated[
    AuthContext, Depends(require_feature("advanced_recommendations"))
]
RequireCustomSegments = Annotated[
    AuthContext, Depends(require_feature("custom_segments"))
]
RequireAPIAccess = Annotated[AuthContext, Depends(require_feature("api_access"))]
RequireSlackAlerts = Annotated[AuthContext, Depends(require_feature("slack_alerts"))]
