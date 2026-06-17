import uuid

from pydantic import BaseModel, Field


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
