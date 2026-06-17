"""FR-023, FR-075 / T-061: Pydantic schemas for delegation rule endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class DelegationRuleCreateRequest(BaseModel):
    delegatee_user_id: UUID
    domain: str
    valid_from: date
    valid_until: date

    @model_validator(mode="after")
    def valid_until_not_before_valid_from(self) -> "DelegationRuleCreateRequest":
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until must be on or after valid_from")
        return self


class DelegationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    delegator_user_id: UUID | None
    delegatee_user_id: UUID
    domain: str
    valid_from: date
    valid_until: date
    is_active: bool
    revoked_at: datetime | None
    revoked_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class DelegationRuleListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[DelegationRuleResponse]
    total: int
