from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class InventoryRiskThresholdCreateRequest(BaseModel):
    category: str
    stockout_alert_days: float = 7.0
    overstock_weeks_threshold: float = 12.0
    slow_moving_min_qty: int = 5
    slow_moving_min_weeks_cover: float = 4.0
    slow_moving_min_capital: float = 0.0
    effective_date: date


class InventoryRiskThresholdUpdateRequest(BaseModel):
    stockout_alert_days: float | None = None
    overstock_weeks_threshold: float | None = None
    slow_moving_min_qty: int | None = None
    slow_moving_min_weeks_cover: float | None = None
    slow_moving_min_capital: float | None = None
    is_active: bool | None = None
    effective_date: date | None = None


class InventoryRiskThresholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    stockout_alert_days: float
    overstock_weeks_threshold: float
    slow_moving_min_qty: int
    slow_moving_min_weeks_cover: float
    slow_moving_min_capital: float
    is_active: bool
    effective_date: date
    created_at: datetime
    updated_at: datetime


class InventoryRiskThresholdListResponse(BaseModel):
    thresholds: list[InventoryRiskThresholdResponse]


class InventoryRiskSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_date: date
    sku: str
    product_title: str
    variant_title: str | None
    current_quantity: int
    reorder_point: int | None
    status: str
    daily_velocity_30d: float
    days_to_stockout: float | None
    weekly_velocity_90d: float
    weeks_of_cover: float | None
    days_since_last_sale: int | None
    capital_at_risk: float | None
    seasonal_adjustment_applied: bool
    confidence: str
    data_completeness: str


class InventoryRiskListResponse(BaseModel):
    snapshot_date: date
    snapshots: list[InventoryRiskSnapshotResponse]


# Warehouse/Location schemas (T-069)


class LocationResponse(BaseModel):
    """Warehouse or fulfillment location metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_location_id: str
    name: str
    address: str | None
    location_type: str | None
    synced_at: datetime
    created_at: datetime
    updated_at: datetime


class WarehouseInventoryHealthResponse(BaseModel):
    """Aggregated inventory health for a single warehouse/location."""
    model_config = ConfigDict(from_attributes=True)

    location: LocationResponse
    total_skus: int
    total_quantity: int
    critical_stockout_risk: int
    stockout_alert_days_count: int
    overstock_count: int
    slow_moving_count: int
    capital_at_risk: float
    average_days_to_stockout: float | None
    data_freshness: str
    snapshot_date: date


class MultiWarehouseInventoryResponse(BaseModel):
    """Multi-warehouse inventory health overview."""
    warehouse_views: list[WarehouseInventoryHealthResponse]
    aggregate_total_skus: int
    aggregate_total_quantity: int
    aggregate_critical_risk: int
    snapshot_date: date
    data_confidence: str


class StockoutImpactResponse(BaseModel):
    """Estimated impact of SKU stockout across locations."""
    sku: str
    product_title: str
    variant_title: str | None
    estimated_lost_revenue_7d: float
    estimated_lost_revenue_30d: float
    repeat_purchase_risk_customers: int
    days_to_stockout_by_location: dict[str, float | None]
    total_units_across_locations: int
    reorder_recommendation: str
    priority: str


class LogisticsCostBreakdownResponse(BaseModel):
    """Estimated logistics cost impact for a SKU across locations."""
    sku: str
    product_title: str
    inbound_cost_per_unit: float | None
    outbound_cost_per_unit: float | None
    storage_cost_per_unit_per_day: float | None
    return_processing_cost_per_unit: float | None
    total_estimated_logistics_cost: float
    margin_impact_pct: float
    cost_reduction_opportunity: str
    optimization_notes: str | None
