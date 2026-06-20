"""Tests for warehouse/location inventory endpoints (T-069)."""

from __future__ import annotations

import uuid
from datetime import date

import jwt
from backend.app.db.models import (
    ConnectorIntegration,
    InventoryRiskSnapshot,
    Location,
    Role,
    TenantMembership,
    User,
)
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

client = TestClient(app)


def _make_auth_token(payload: dict) -> str:
    return jwt.encode(
        payload,
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def _create_tenant_and_get_id(
    client: TestClient,
    tenant_name: str,
    tenant_slug: str,
) -> tuple[str, str]:
    """Create a tenant and return (tenant_id, auth_token)."""
    email = f"admin-{tenant_slug}@test.local"
    token = _make_auth_token({
        "sub": "admin",
        "email": email,
        "platform_role": "super_admin",
    })
    response = client.post(
        "/tenants",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": tenant_name,
            "slug": tenant_slug,
        },
    )
    assert response.status_code == 201, f"Failed to create tenant: {response.text}"
    tenant_id = response.json()["id"]
    
    # Upgrade to operations_inventory_manager (has all permissions)
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        # Get the operations_inventory_manager role for this tenant
        ops_role = db.scalar(
            select(Role).where(
                Role.tenant_id == uuid.UUID(tenant_id),
                Role.name == "operations_inventory_manager",
                Role.is_system,
            )
        )
        
        # Update the membership to use operations_inventory_manager role
        membership = db.scalar(
            select(TenantMembership)
            .join(User, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == uuid.UUID(tenant_id),
                User.email == email,
            )
        )
        if membership and ops_role:
            membership.role = "operations_inventory_manager"
            membership.role_id = ops_role.id
            db.commit()
    finally:
        db.close()
    
    return tenant_id, token


class TestWarehouseInventory:
    """Test warehouse-level inventory views."""

    def test_list_warehouse_inventory_no_locations(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test listing warehouse inventory when no locations exist.
        
        Fallback to aggregate view of all inventory.
        """
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand",
        )

        snapshot_date = date.today()
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                snapshot_date=snapshot_date,
                sku="SKU001",
                product_title="Widget A",
                variant_title=None,
                current_quantity=100,
                reorder_point=20,
                status="healthy",
                daily_velocity_30d=5.0,
                days_to_stockout=20.0,
                weekly_velocity_90d=35.0,
                weeks_of_cover=2.86,
                days_since_last_sale=0,
                capital_at_risk=5000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/inventory/warehouses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "warehouse_views" in data
        assert len(data["warehouse_views"]) == 1
        assert data["warehouse_views"][0]["location"]["location_type"] == "aggregate"
        assert data["warehouse_views"][0]["total_skus"] == 1
        assert data["warehouse_views"][0]["total_quantity"] == 100
        assert data["data_confidence"] == "high"

    def test_list_warehouse_inventory_with_locations(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test listing warehouse inventory with locations defined.
        
        Currently returns aggregate inventory (Phase 2 will support
        per-location inventory tracking).
        """
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand-2",
        )

        connector = ConnectorIntegration(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            source="shopify",
            auth_mode="oauth",
            status="connected",
        )
        db_session.add(connector)
        db_session.flush()

        location_1 = Location(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            connector_id=connector.id,
            external_location_id="loc_001",
            name="Warehouse A",
            address="123 Main St",
            location_type="warehouse",
        )
        location_2 = Location(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            connector_id=connector.id,
            external_location_id="loc_002",
            name="Warehouse B",
            address="456 Oak Ave",
            location_type="warehouse",
        )
        db_session.add(location_1)
        db_session.add(location_2)
        db_session.flush()

        snapshot_date = date.today()
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                snapshot_date=snapshot_date,
                sku="SKU001",
                product_title="Widget A",
                variant_title=None,
                current_quantity=100,
                reorder_point=20,
                status="healthy",
                daily_velocity_30d=5.0,
                days_to_stockout=20.0,
                weekly_velocity_90d=35.0,
                weeks_of_cover=2.86,
                days_since_last_sale=0,
                capital_at_risk=5000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                snapshot_date=snapshot_date,
                sku="SKU002",
                product_title="Widget B",
                variant_title="Red",
                current_quantity=50,
                reorder_point=15,
                status="critical_stockout_risk",
                daily_velocity_30d=3.0,
                days_to_stockout=3.0,
                weekly_velocity_90d=21.0,
                weeks_of_cover=0.43,
                days_since_last_sale=1,
                capital_at_risk=2000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/inventory/warehouses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "warehouse_views" in data
        assert len(data["warehouse_views"]) == 1
        assert data["warehouse_views"][0]["location"]["location_type"] == "aggregate"
        assert data["aggregate_total_skus"] == 2
        assert data["aggregate_total_quantity"] == 150
        assert data["aggregate_critical_risk"] == 1

    def test_list_warehouse_inventory_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        """Test that unauthorized users cannot list warehouse inventory."""
        tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/tenants/{tenant_id}/inventory/warehouses",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_get_sku_stockout_impact(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test getting stockout impact for a SKU."""
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand-3",
        )

        snapshot_date = date.today()
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                snapshot_date=snapshot_date,
                sku="CRITICAL-SKU",
                product_title="Best Seller",
                variant_title="Large",
                current_quantity=200,
                reorder_point=50,
                status="critical_stockout_risk",
                daily_velocity_30d=10.0,
                days_to_stockout=2.0,
                weekly_velocity_90d=70.0,
                weeks_of_cover=0.29,
                days_since_last_sale=0,
                capital_at_risk=10000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/inventory/skus/CRITICAL-SKU/stockout-impact",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["sku"] == "CRITICAL-SKU"
        assert data["product_title"] == "Best Seller"
        assert data["priority"] == "critical"
        assert "Reorder immediately" in data["reorder_recommendation"]
        assert data["estimated_lost_revenue_7d"] > 0
        assert data["estimated_lost_revenue_30d"] > 0
        assert data["repeat_purchase_risk_customers"] > 0

    def test_get_sku_stockout_impact_nonexistent(
        self,
        client: TestClient,
    ) -> None:
        """Test that nonexistent SKU returns 404."""
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand-4",
        )

        response = client.get(
            f"/tenants/{tenant_id}/inventory/skus/NONEXISTENT-SKU/stockout-impact",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_sku_logistics_costs(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test getting logistics cost breakdown for a SKU."""
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand-5",
        )

        snapshot_date = date.today()
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                snapshot_date=snapshot_date,
                sku="LOGISTICS-SKU",
                product_title="Expensive Item",
                variant_title=None,
                current_quantity=500,
                reorder_point=100,
                status="healthy",
                daily_velocity_30d=8.0,
                days_to_stockout=62.5,
                weekly_velocity_90d=56.0,
                weeks_of_cover=8.93,
                days_since_last_sale=0,
                capital_at_risk=50000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.commit()

        response = client.get(
            f"/tenants/{tenant_id}/inventory/skus/LOGISTICS-SKU/logistics-costs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["sku"] == "LOGISTICS-SKU"
        assert data["product_title"] == "Expensive Item"
        assert data["inbound_cost_per_unit"] == 2.50
        assert data["outbound_cost_per_unit"] == 3.75
        assert data["storage_cost_per_unit_per_day"] == 0.05
        assert data["return_processing_cost_per_unit"] == 1.50
        assert data["total_estimated_logistics_cost"] > 0
        assert data["margin_impact_pct"] > 0
        assert data["cost_reduction_opportunity"] is not None

    def test_get_sku_logistics_costs_nonexistent(
        self,
        client: TestClient,
    ) -> None:
        """Test that nonexistent SKU returns 404."""
        tenant_id, token = _create_tenant_and_get_id(
            client,
            "Test Brand",
            "test-brand-6",
        )

        response = client.get(
            f"/tenants/{tenant_id}/inventory/skus/NONEXISTENT-SKU/logistics-costs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_warehouse_inventory_cross_tenant_isolation(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test that warehouse inventory data is isolated per tenant."""
        tenant_1_id, token_1 = _create_tenant_and_get_id(
            client,
            "Tenant 1",
            "tenant-1",
        )
        tenant_2_id, token_2 = _create_tenant_and_get_id(
            client,
            "Tenant 2",
            "tenant-2",
        )

        snapshot_date = date.today()
        db_session.add(
            InventoryRiskSnapshot(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_1_id),
                snapshot_date=snapshot_date,
                sku="TENANT-1-SKU",
                product_title="Tenant 1 Product",
                variant_title=None,
                current_quantity=1000,
                reorder_point=200,
                status="healthy",
                daily_velocity_30d=20.0,
                days_to_stockout=50.0,
                weekly_velocity_90d=140.0,
                weeks_of_cover=7.14,
                days_since_last_sale=0,
                capital_at_risk=100000.0,
                seasonal_adjustment_applied=False,
                confidence="high",
                data_completeness="complete",
            )
        )
        db_session.commit()

        response_1 = client.get(
            f"/tenants/{tenant_1_id}/inventory/warehouses",
            headers={"Authorization": f"Bearer {token_1}"},
        )
        response_2 = client.get(
            f"/tenants/{tenant_2_id}/inventory/warehouses",
            headers={"Authorization": f"Bearer {token_2}"},
        )

        assert response_1.status_code == 200
        assert response_2.status_code == 200

        data_1 = response_1.json()
        data_2 = response_2.json()

        assert data_1.get("aggregate_total_quantity", 0) == 1000
        assert data_2.get("aggregate_total_quantity", 0) == 0
