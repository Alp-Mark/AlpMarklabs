from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OperationalImpactSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_date: date
    sku: str
    product_title: str
    variant_title: str | None

    # FR-064
    inventory_status: str
    daily_velocity_30d: float
    avg_unit_price: float
    days_to_restock_estimate: float
    stockout_lost_revenue_estimate: float | None
    repeat_purchase_risk: str

    # FR-065
    logistics_cost_per_unit: float | None
    logistics_cost_total_30d: float | None
    logistics_margin_impact_pct: float | None

    # FR-066
    units_sold_30d: int
    return_quantity_30d: int
    return_rate_30d_pct: float
    return_cost_per_unit: float | None
    return_cost_total_30d: float | None

    confidence: str
    data_completeness: str
    created_at: datetime
    updated_at: datetime


class OperationalImpactListResponse(BaseModel):
    snapshot_date: date
    snapshots: list[OperationalImpactSnapshotResponse]
