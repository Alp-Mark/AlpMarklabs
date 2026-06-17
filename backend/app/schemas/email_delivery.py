"""Pydantic schemas for email delivery log endpoints (FR-116 / T-079).

Schemas for tracking and retrieving email notification delivery status,
including delivery attempts, retries, and error details.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailDeliveryResponse(BaseModel):
    """Response schema for a single email delivery record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    alert_id: str
    alert_type: str
    email_address: str
    status: str  # "pending", "sent", "failed", "bounced"
    attempt_count: int
    last_attempt_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailDeliveryListResponse(BaseModel):
    """Response schema for paginated email delivery list."""

    deliveries: list[EmailDeliveryResponse]
    total_count: int


class EmailDeliveryHistoryResponse(BaseModel):
    """Response schema for complete delivery history of an alert."""

    alert_id: str
    alert_type: str
    total_deliveries: int
    successful_count: int
    failed_count: int
    pending_count: int
    deliveries: list[EmailDeliveryResponse]
    first_delivery_at: datetime | None
    last_delivery_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
