from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from jwt.types import Options
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Tenant, TenantMembership, User
from app.db.session import get_db

AUTH_JWT_SECRET = os.getenv(
    "AUTH_JWT_SECRET",
    "alpmark-dev-secret-alpmark-dev-secret-2026",
)
AUTH_JWT_ALGORITHM = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
AUTH_JWT_ISSUER = os.getenv("AUTH_JWT_ISSUER")
AUTH_JWT_AUDIENCE = os.getenv("AUTH_JWT_AUDIENCE")

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    subject: str
    email: str
    platform_role: str | None


def get_current_auth(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        options: Options = {
            "verify_aud": AUTH_JWT_AUDIENCE is not None,
            "verify_iss": AUTH_JWT_ISSUER is not None,
        }

        if AUTH_JWT_ISSUER is not None and AUTH_JWT_AUDIENCE is not None:
            payload = jwt.decode(
                credentials.credentials,
                AUTH_JWT_SECRET,
                algorithms=[AUTH_JWT_ALGORITHM],
                issuer=AUTH_JWT_ISSUER,
                audience=AUTH_JWT_AUDIENCE,
                options=options,
            )
        elif AUTH_JWT_ISSUER is not None:
            payload = jwt.decode(
                credentials.credentials,
                AUTH_JWT_SECRET,
                algorithms=[AUTH_JWT_ALGORITHM],
                issuer=AUTH_JWT_ISSUER,
                options=options,
            )
        elif AUTH_JWT_AUDIENCE is not None:
            payload = jwt.decode(
                credentials.credentials,
                AUTH_JWT_SECRET,
                algorithms=[AUTH_JWT_ALGORITHM],
                audience=AUTH_JWT_AUDIENCE,
                options=options,
            )
        else:
            payload = jwt.decode(
                credentials.credentials,
                AUTH_JWT_SECRET,
                algorithms=[AUTH_JWT_ALGORITHM],
                options=options,
            )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    subject = str(payload.get("sub") or "")
    email = str(payload.get("email") or "")
    platform_role_claim = payload.get("platform_role")
    platform_role = (
        str(platform_role_claim).strip().lower() if platform_role_claim else None
    )

    if not subject or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing required claims.",
        )

    return AuthContext(
        subject=subject,
        email=email,
        platform_role=platform_role,
    )


AuthDep = Annotated[AuthContext, Depends(get_current_auth)]
DbDep = Annotated[Session, Depends(get_db)]


def require_platform_roles(*allowed_roles: str) -> Callable[..., AuthContext]:
    normalized_roles = {role.strip().lower() for role in allowed_roles}

    def dependency(auth: AuthDep) -> AuthContext:
        if auth.platform_role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return auth

    return dependency


def require_tenant_roles(*allowed_roles: str) -> Callable[..., AuthContext]:
    normalized_roles = {role.strip().lower() for role in allowed_roles}

    def dependency(
        tenant_id: uuid.UUID,
        auth: AuthDep,
        db: DbDep,
    ) -> AuthContext:
        tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found.",
            )

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
        if (
            membership is None
            or membership.role.strip().lower() not in normalized_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return auth

    return dependency
