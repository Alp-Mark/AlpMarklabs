import uuid

from pydantic import BaseModel, Field


class BillingSeatUpdateRequest(BaseModel):
    billing_plan: str | None = Field(default=None, min_length=2, max_length=50)
    billing_cycle: str | None = Field(default=None, min_length=3, max_length=20)
    billing_status: str | None = Field(default=None, min_length=3, max_length=20)
    seat_limit: int | None = Field(default=None, ge=1, le=10000)


class BillingSeatResponse(BaseModel):
    tenant_id: uuid.UUID
    billing_plan: str
    billing_cycle: str
    billing_status: str
    seat_limit: int
    seats_used: int
    seats_available: int
    can_invite: bool
