import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.locale import _SUPPORTED_CURRENCIES


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    base_currency: str = Field(default="USD")

    @field_validator("base_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in _SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. "
                f"Supported: {sorted(_SUPPORTED_CURRENCIES)}"
            )
        return upper


class TenantCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    base_currency: str
    created_at: datetime
