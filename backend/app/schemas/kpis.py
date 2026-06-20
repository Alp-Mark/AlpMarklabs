"""Pydantic schemas for KPI metadata endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPIMetadataResponse(BaseModel):
    """Single KPI metadata response."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    description: str
    formula: str
    unit: str
    domain: str
    data_sources: list[str]
    good_direction: str
    target_range: str


class KPICatalogResponse(BaseModel):
    """KPI catalog response with all KPIs."""

    model_config = ConfigDict(from_attributes=True)

    kpis: list[KPIMetadataResponse]
    total: int
