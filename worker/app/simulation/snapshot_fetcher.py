"""Fetch (x, y) data from snapshot tables for response function fitting (T-118).

This module pulls historical snapshot data from the database for each simulation
domain and prepares it in (control_variable, target_metric) tuples for fitting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.app.db.models import (
    AcquisitionMetricsSnapshot,
    CostDriverSnapshot,
    ExecutiveKpiSnapshot,
    InventoryRiskSnapshot,
    OperationalImpactSnapshot,
    RetentionDailySnapshot,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


def fetch_acquisition_data(
    db: Session, tenant_id: Any, lookback_days: int = 120
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (ad_spend_amount, roas) pairs from AcquisitionMetricsSnapshot.

    Returns (data_points, calendar_window_days).
    Calendar window is computed as end_date - start_date of the returned data.
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(AcquisitionMetricsSnapshot)
        .where(
            AcquisitionMetricsSnapshot.tenant_id == tenant_id,
            AcquisitionMetricsSnapshot.snapshot_date >= start_date,
            AcquisitionMetricsSnapshot.snapshot_date <= end_date,
        )
        .order_by(AcquisitionMetricsSnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for snap in snapshots:
        if snap.ad_spend_amount is not None and snap.roas is not None:
            data_points.append((float(snap.ad_spend_amount), float(snap.roas)))

    window_days = (end_date - start_date).days
    return data_points, window_days


def fetch_margin_data(
    db: Session,
    tenant_id: Any,
    driver_type: str,
    lookback_days: int = 120,
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (cost_pct_of_revenue, margin_impact_pct) from CostDriverSnapshot.

    Returns (data_points, calendar_window_days) for a specific driver_type.
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(CostDriverSnapshot)
        .where(
            CostDriverSnapshot.tenant_id == tenant_id,
            CostDriverSnapshot.driver_type == driver_type,
            CostDriverSnapshot.snapshot_date >= start_date,
            CostDriverSnapshot.snapshot_date <= end_date,
        )
        .order_by(CostDriverSnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for snap in snapshots:
        if (
            snap.cost_pct_of_revenue is not None
            and snap.margin_impact_pct is not None
        ):
            data_points.append(
                (float(snap.cost_pct_of_revenue), float(snap.margin_impact_pct))
            )

    window_days = (end_date - start_date).days
    return data_points, window_days


def fetch_retention_data(
    db: Session, tenant_id: Any, lookback_days: int = 120
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (day_index, repeat_purchase_rate_pct) from RetentionDailySnapshot.

    day_index is the 0-based chronological position in the returned data.
    Returns (data_points, calendar_window_days).
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(RetentionDailySnapshot)
        .where(
            RetentionDailySnapshot.tenant_id == tenant_id,
            RetentionDailySnapshot.snapshot_date >= start_date,
            RetentionDailySnapshot.snapshot_date <= end_date,
        )
        .order_by(RetentionDailySnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for day_index, snap in enumerate(snapshots):
        if snap.repeat_purchase_rate_pct is not None:
            data_points.append((float(day_index), float(snap.repeat_purchase_rate_pct)))

    window_days = (end_date - start_date).days
    return data_points, window_days


def fetch_inventory_data(
    db: Session, tenant_id: Any, sku_id: Any, lookback_days: int = 120
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (reorder_point, days_to_stockout) from InventoryRiskSnapshot.

    Returns (data_points, calendar_window_days) for a specific SKU.
    Only includes rows where both fields are non-null.
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(InventoryRiskSnapshot)
        .where(
            InventoryRiskSnapshot.tenant_id == tenant_id,
            InventoryRiskSnapshot.sku_id == sku_id,
            InventoryRiskSnapshot.snapshot_date >= start_date,
            InventoryRiskSnapshot.snapshot_date <= end_date,
        )
        .order_by(InventoryRiskSnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for snap in snapshots:
        if (snap.reorder_point is not None and snap.days_to_stockout is not None):
            data_points.append(
                (float(snap.reorder_point), float(snap.days_to_stockout))
            )

    window_days = (end_date - start_date).days
    return data_points, window_days


def fetch_operations_data(
    db: Session, tenant_id: Any, lookback_days: int = 120
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (units_sold_30d, logistics_cost_per_unit) from OperationalImpactSnapshot.

    Returns (data_points, calendar_window_days).
    Only includes rows where logistics_cost_per_unit is non-null.
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(OperationalImpactSnapshot)
        .where(
            OperationalImpactSnapshot.tenant_id == tenant_id,
            OperationalImpactSnapshot.snapshot_date >= start_date,
            OperationalImpactSnapshot.snapshot_date <= end_date,
        )
        .order_by(OperationalImpactSnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for snap in snapshots:
        if (
            snap.units_sold_30d is not None
            and snap.logistics_cost_per_unit is not None
        ):
            data_points.append(
                (float(snap.units_sold_30d), float(snap.logistics_cost_per_unit))
            )

    window_days = (end_date - start_date).days
    return data_points, window_days


def fetch_executive_data(
    db: Session, tenant_id: Any, lookback_days: int = 120
) -> tuple[list[tuple[float, float]], int]:
    """Fetch (ad_spend_amount, contribution_margin_pct) from ExecutiveKpiSnapshot.

    Returns (data_points, calendar_window_days).
    """
    end_date = datetime.now(UTC).date()
    start_date = (datetime.now(UTC) - timedelta(days=lookback_days)).date()

    snapshots = db.scalars(
        select(ExecutiveKpiSnapshot)
        .where(
            ExecutiveKpiSnapshot.tenant_id == tenant_id,
            ExecutiveKpiSnapshot.snapshot_date >= start_date,
            ExecutiveKpiSnapshot.snapshot_date <= end_date,
        )
        .order_by(ExecutiveKpiSnapshot.snapshot_date.asc())
    ).all()

    data_points = []
    for snap in snapshots:
        if (
            snap.ad_spend_amount is not None
            and snap.contribution_margin_pct is not None
        ):
            data_points.append(
                (float(snap.ad_spend_amount), float(snap.contribution_margin_pct))
            )

    window_days = (end_date - start_date).days
    return data_points, window_days
