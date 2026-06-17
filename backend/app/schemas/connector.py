import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ShopifyOAuthStartRequest(BaseModel):
    shop_domain: str = Field(min_length=5, max_length=255)


class ShopifyOAuthStartResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    status: str
    state: str
    auth_url: str


class ShopifyOAuthCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=8, max_length=255)
    shop_domain: str = Field(min_length=5, max_length=255)


class MetaOAuthStartResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    status: str
    state: str
    auth_url: str


class MetaOAuthCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=8, max_length=255)


class GoogleAdsOAuthStartResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    status: str
    state: str
    auth_url: str


class GoogleAdsOAuthCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=8, max_length=255)


class ConnectorApiKeyConnectRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=512)


class ConnectorOAuthReauthorizeRequest(BaseModel):
    authorization_code: str = Field(min_length=8, max_length=255)
    shop_domain: str | None = Field(default=None, min_length=5, max_length=255)


class ConnectorResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    auth_mode: str
    status: str
    shop_domain: str | None
    connected_at: datetime | None
    last_synced_at: datetime | None
    last_sync_requested_at: datetime | None
    error_message: str | None


class ConnectorManualResyncResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    status: str
    last_sync_requested_at: datetime
    queued_tasks: list[str]


class ConnectorIntegrationStatusResponse(BaseModel):
    connector_id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    auth_mode: str
    status: str
    shop_domain: str | None
    connected_at: datetime | None
    last_synced_at: datetime | None
    last_sync_requested_at: datetime | None
    error_message: str | None
    sync_progress: str
    freshness_label: str
    stale_data_gate: str
    stale_data_reason: str | None
    sync_jobs_total_7d: int
    sync_jobs_success_7d: int
    sync_jobs_failed_7d: int
    sync_uptime_percentage_7d: float
    sync_failure_rate_percentage_7d: float
