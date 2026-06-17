import uuid

from pydantic import BaseModel


class OnboardingChecklistItem(BaseModel):
    key: str
    label: str
    is_complete: bool


class OnboardingChecklistResponse(BaseModel):
    tenant_id: uuid.UUID
    completed_steps: int
    total_steps: int
    completion_percent: int
    items: list[OnboardingChecklistItem]
