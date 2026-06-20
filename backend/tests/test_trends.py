"""Tests for trend/time-series endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import jwt
from backend.app.db.models import (
    AcquisitionMetricsSnapshot,
    CostDriverSnapshot,
    ExecutiveKpiSnapshot,
    InventoryRiskSnapshot,
    MarginDriftSnapshot,
    OperationalImpactSnapshot,
    RetentionDailySnapshot,
)
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def test_executive_trend_success(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/executive/trend with 90-day window."""
    # Create executive KPI snapshots for last 7 days
    today = date.today()
    for i in range(7):
        snap_date = today - timedelta(days=6 - i)
        snapshot = ExecutiveKpiSnapshot(
            tenant_id=tenant.id,
            snapshot_date=snap_date,
            period_start_date=snap_date - timedelta(days=30),
            period_end_date=snap_date,
            revenue_amount=10000.0 + i * 1000,
            ad_spend_amount=2000.0 + i * 100,
            blended_roas=5.0 + i * 0.1,
            contribution_margin_pct=30.0 + i,
        )
        db_session.add(snapshot)
    db_session.commit()

    # Create JWT token for operations_inventory_manager (has all permissions)
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request with 7d window
    response = client.get(
        f"/tenants/{tenant.id}/executive/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 7
    assert data["window_label"] == "Last 7 Days"
    assert data["period_start"] == str(today - timedelta(days=6))
    assert data["period_end"] == str(today)

    # Verify data point structure
    first_point = data["data_points"][0]
    assert "snapshot_date" in first_point
    assert "revenue_amount" in first_point
    assert "ad_spend_amount" in first_point
    assert "blended_roas" in first_point
    assert "contribution_margin_pct" in first_point

def test_growth_trend_by_channel(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/growth/trend with channel breakdown."""
    # Create acquisition metrics snapshots for 3 channels over 3 days
    today = date.today()
    channels = ["Meta", "Google", "TikTok"]
    for i in range(3):
        snap_date = today - timedelta(days=2 - i)
        for channel in channels:
            snapshot = AcquisitionMetricsSnapshot(
                tenant_id=tenant.id,
                channel=channel,
                snapshot_date=snap_date,
                period_start_date=snap_date - timedelta(days=30),
                period_end_date=snap_date,
                ad_spend_amount=1000.0 + i * 100,
                revenue_attributed=5000.0 + i * 500,
                order_count=100 + i * 10,
                roas=5.0 + i * 0.5,
                cac=50.0 + i * 5,
                contribution_margin_pct=25.0 + i,
                payback_period_days=30.0 + i * 5,
            )
            db_session.add(snapshot)
    db_session.commit()

    # Create JWT token
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/growth/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["channels"]) == 3
    assert data["channels"][0]["channel"] == "Google"  # Sorted alphabetically
    assert data["channels"][1]["channel"] == "Meta"
    assert data["channels"][2]["channel"] == "TikTok"
    assert len(data["channels"][0]["data_points"]) == 3


def test_retention_trend_success(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/retention/trend."""
    # Create retention snapshots for 5 days
    today = date.today()
    for i in range(5):
        snap_date = today - timedelta(days=4 - i)
        snapshot = RetentionDailySnapshot(
            tenant_id=tenant.id,
            snapshot_date=snap_date,
            total_customers=100 + i * 10,
            repeat_customers=30 + i * 5,
            repeat_purchase_rate_pct=30.0 + i,
        )
        db_session.add(snapshot)
    db_session.commit()

    # Create JWT token
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/retention/trend?window=30d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 5
    assert data["window_label"] == "Last 30 Days"

    # Verify data point fields
    point = data["data_points"][0]
    assert "total_customers" in point
    assert "repeat_customers" in point
    assert "repeat_purchase_rate_pct" in point


def test_cost_driver_trend_by_driver_type(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/finance/cost-drivers/trend."""
    # Create cost driver snapshots for 3 driver types over 2 days
    today = date.today()
    driver_types = ["cogs", "shipping", "returns"]
    for i in range(2):
        snap_date = today - timedelta(days=1 - i)
        for driver_type in driver_types:
            snapshot = CostDriverSnapshot(
                tenant_id=tenant.id,
                driver_type=driver_type,
                snapshot_date=snap_date,
                period_start_date=snap_date - timedelta(days=30),
                period_end_date=snap_date,
                absolute_amount=5000.0 + i * 500,
                revenue=20000.0,
                pct_of_revenue=25.0,
                margin_impact_amount=1000.0,
                source="shopify",
                source_platform="Shopify",
                last_updated_at=snap_date,
                confidence_score=0.9,
                confidence_label="High",
            )
            db_session.add(snapshot)
    db_session.commit()

    # Create JWT token for finance_controller
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/finance/cost-drivers/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # 3 driver types × 2 days = 6 data points
    assert len(data["data_points"]) == 6

    # Verify data point fields
    point = data["data_points"][0]
    assert "driver_type" in point
    assert "absolute_amount" in point
    assert "pct_of_revenue" in point
    assert "margin_impact_amount" in point


def test_margin_drift_trend_success(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/finance/margin-drift/trend."""
    # Create margin drift snapshots
    today = date.today()
    snapshot = MarginDriftSnapshot(
        tenant_id=tenant.id,
        snapshot_date=today,
        channel="Online",
        category="Electronics",
        actual_margin_pct=35.0,
        expected_margin_pct=40.0,
        drift_pct=-5.0,
        threshold_exceeded=True,
        variance_reason="increased_cogs",
        data_completeness="complete",
    )
    db_session.add(snapshot)
    db_session.commit()

    # Create JWT token for finance_controller
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/finance/margin-drift/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 1

    # Verify data point fields
    point = data["data_points"][0]
    assert point["channel"] == "Online"
    assert point["category"] == "Electronics"
    assert point["actual_margin_pct"] == 35.0
    assert point["expected_margin_pct"] == 40.0
    assert point["drift_pct"] == -5.0


def test_inventory_risk_trend_aggregated(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/operations/inventory-risk/trend (aggregated)."""
    # Create inventory risk snapshots for 3 SKUs on same day
    today = date.today()
    statuses = ["stockout_risk", "overstock", "in_stock"]
    for i, status in enumerate(statuses):
        if status == "in_stock":
            quantity = 100
        elif status == "stockout_risk":
            quantity = 0
        else:
            quantity = 500

        snapshot = InventoryRiskSnapshot(
            tenant_id=tenant.id,
            snapshot_date=today,
            sku=f"SKU-{i}",
            product_title=f"Product {i}",
            current_quantity=quantity,
            status=status,
            daily_velocity_30d=5.0,
            capital_at_risk=1000.0 if status == "overstock" else 500.0,
            confidence="high",
            data_completeness="complete",
        )
        db_session.add(snapshot)
    db_session.commit()

    # Create JWT token for operations_manager
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/operations/inventory-risk/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 1  # Aggregated by date

    # Verify aggregation
    point = data["data_points"][0]
    assert point["total_skus"] == 3
    assert point["stockout_risk_skus"] == 1
    assert point["overstock_skus"] == 1
    assert point["total_capital_at_risk"] == 2000.0


def test_operational_impact_trend_aggregated(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test GET /tenants/{id}/operations/operational-impact/trend (aggregated)."""
    # Create operational impact snapshots for 2 SKUs on same day
    today = date.today()
    for i in range(2):
        snapshot = OperationalImpactSnapshot(
            tenant_id=tenant.id,
            snapshot_date=today,
            sku=f"SKU-{i}",
            product_title=f"Product {i}",
            inventory_status="low_stock" if i == 0 else "in_stock",
            daily_velocity_30d=5.0,
            avg_unit_price=50.0,
            days_to_restock_estimate=7.0,
            stockout_lost_revenue_estimate=1000.0 if i == 0 else 0.0,
            repeat_purchase_risk="high" if i == 0 else "low",
            logistics_margin_impact_pct=5.0 + i,  # 5% and 6%
            confidence="high",  # Add required field
            data_completeness="complete",  # Add required field
        )
        db_session.add(snapshot)
    db_session.commit()

    # Create JWT token for operations_manager
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request
    response = client.get(
        f"/tenants/{tenant.id}/operations/operational-impact/trend?window=7d",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 1  # Aggregated by date

    # Verify aggregation
    point = data["data_points"][0]
    assert point["total_skus"] == 2
    assert point["avg_logistics_margin_impact_pct"] == 5.5  # Average of 5 and 6
    assert point["total_stockout_lost_revenue"] == 1000.0


def test_trend_custom_date_range(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test trend endpoint with custom date range."""
    # Create snapshots across a wider range
    start = date(2026, 6, 1)
    for i in range(10):
        snap_date = start + timedelta(days=i)
        snapshot = ExecutiveKpiSnapshot(
            tenant_id=tenant.id,
            snapshot_date=snap_date,
            period_start_date=snap_date - timedelta(days=30),
            period_end_date=snap_date,
            revenue_amount=10000.0,
            ad_spend_amount=2000.0,
            blended_roas=5.0,
            contribution_margin_pct=30.0,
        )
        db_session.add(snapshot)
    db_session.commit()

    # Create JWT token
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request with custom date range
    response = client.get(
        f"/tenants/{tenant.id}/executive/trend?window=custom&start_date=2026-06-01&end_date=2026-06-10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 10
    assert data["window_label"] == "Custom Range"
    assert data["period_start"] == "2026-06-01"
    assert data["period_end"] == "2026-06-10"


def test_trend_empty_data(
    db_session: Any, client: Any, tenant: Any, user: Any
) -> None:
    """Test trend endpoint with no snapshot data."""
    # Create JWT token
    token = jwt.encode(
        {"sub": user.email, "email": user.email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    # Make request - no snapshots exist
    response = client.get(
        f"/tenants/{tenant.id}/executive/trend",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data_points"]) == 0  # Empty but valid
