import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationRouteItem(BaseModel):
    alert_type: str = Field(min_length=3, max_length=100)
    channel: str = Field(min_length=3, max_length=20)
    destination: str = Field(min_length=3, max_length=255)
    is_enabled: bool = True


class NotificationRoutingUpdateRequest(BaseModel):
    routes: list[NotificationRouteItem]


class NotificationRoutingResponse(BaseModel):
    tenant_id: uuid.UUID
    routes: list[NotificationRouteItem]


# E5: User Notification Preferences
class UserNotificationPreferenceCreate(BaseModel):
    """Create user notification preference."""

    tenant_id: uuid.UUID
    alert_category: str = Field(
        description="Alert category: kpi_drift, stockout_risk, etc."
    )
    channel: str = Field(
        default="both", description="Channel: in_app, email, both"
    )
    is_enabled: bool = Field(default=True)


class UserNotificationPreferenceUpdate(BaseModel):
    """Update user notification preference."""

    channel: str | None = Field(
        default=None, description="Channel: in_app, email, both"
    )
    is_enabled: bool | None = None


class UserNotificationPreferenceResponse(BaseModel):
    """User notification preference response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    alert_category: str
    channel: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class UserNotificationPreferenceListResponse(BaseModel):
    """List of user notification preferences."""

    preferences: list[UserNotificationPreferenceResponse]
    total: int


# E5: Notifications (Inbox)
class NotificationCreate(BaseModel):
    """Create notification (internal use)."""

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    title: str = Field(max_length=200)
    message: str
    severity: str = Field(
        default="info", description="Severity: info, warning, critical"
    )
    deep_link: str | None = Field(default=None, max_length=500)
    context_data: dict | None = None


class NotificationMarkRead(BaseModel):
    """Mark notification as read."""

    pass  # No fields needed, action is implicit


class NotificationMarkDismissed(BaseModel):
    """Mark notification as dismissed."""

    pass  # No fields needed, action is implicit


class NotificationResponse(BaseModel):
    """Notification response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    title: str
    message: str
    severity: str
    status: str
    deep_link: str | None
    context_data: dict | None
    read_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """List of notifications."""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int
