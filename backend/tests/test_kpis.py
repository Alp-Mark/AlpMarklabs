"""Tests for KPI metadata endpoint."""

from __future__ import annotations

from collections.abc import Generator

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client() -> Generator[TestClient]:
    """Get a FastAPI test client with the test database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator:
        session = local_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _make_auth_header(email: str = "test@example.com") -> dict[str, str]:
    """Generate JWT auth header."""
    token = jwt.encode(
        {"sub": email, "email": email, "platform_role": "user"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_get_kpi_catalog_returns_all_kpis(client: TestClient) -> None:
    """GET /kpis returns all KPI metadata."""
    response = client.get("/kpis", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    assert "kpis" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["kpis"]) == data["total"]
    
    # Verify KPI structure
    kpi = data["kpis"][0]
    assert "key" in kpi
    assert "name" in kpi
    assert "description" in kpi
    assert "formula" in kpi
    assert "unit" in kpi
    assert "domain" in kpi
    assert "data_sources" in kpi
    assert "good_direction" in kpi
    assert "target_range" in kpi
    
    # Verify good_direction is valid
    assert kpi["good_direction"] in ["higher", "lower"]


def test_get_kpi_catalog_filter_by_domain_executive(client: TestClient) -> None:
    """GET /kpis?domain=executive returns only executive KPIs."""
    response = client.get("/kpis?domain=executive", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have executive domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "executive"
    
    # Should include contribution margin
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "contribution_margin_pct" in kpi_keys


def test_get_kpi_catalog_filter_by_domain_growth(client: TestClient) -> None:
    """GET /kpis?domain=growth returns only growth KPIs."""
    response = client.get("/kpis?domain=growth", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have growth domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "growth"
    
    # Should include CAC payback period
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "cac_payback_period" in kpi_keys
    assert "cac_by_channel" in kpi_keys


def test_get_kpi_catalog_filter_by_domain_retention(client: TestClient) -> None:
    """GET /kpis?domain=retention returns only retention KPIs."""
    response = client.get("/kpis?domain=retention", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have retention domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "retention"
    
    # Should include repeat purchase rate
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "repeat_purchase_rate" in kpi_keys


def test_get_kpi_catalog_filter_by_domain_finance(client: TestClient) -> None:
    """GET /kpis?domain=finance returns only finance KPIs."""
    response = client.get("/kpis?domain=finance", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have finance domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "finance"
    
    # Should include gross profit margin
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "gross_profit_margin" in kpi_keys
    assert "return_rate_pct" in kpi_keys


def test_get_kpi_catalog_filter_by_domain_operations(client: TestClient) -> None:
    """GET /kpis?domain=operations returns only operations KPIs."""
    response = client.get("/kpis?domain=operations", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have operations domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "operations"
    
    # Should include inventory metrics
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "inventory_turnover" in kpi_keys
    assert "days_of_inventory" in kpi_keys


def test_get_kpi_catalog_filter_by_domain_intelligence(client: TestClient) -> None:
    """GET /kpis?domain=intelligence returns only intelligence KPIs."""
    response = client.get("/kpis?domain=intelligence", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned KPIs should have intelligence domain
    for kpi in data["kpis"]:
        assert kpi["domain"] == "intelligence"
    
    # Should include platform metrics
    kpi_keys = [kpi["key"] for kpi in data["kpis"]]
    assert "time_to_insight" in kpi_keys
    assert "recommendation_acceptance_rate" in kpi_keys


def test_get_kpi_catalog_requires_authentication(client: TestClient) -> None:
    """GET /kpis requires authentication."""
    response = client.get("/kpis")
    
    assert response.status_code == 401


def test_get_kpi_catalog_invalid_domain_returns_empty(client: TestClient) -> None:
    """GET /kpis?domain=invalid returns empty list."""
    response = client.get("/kpis?domain=invalid", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["kpis"]) == 0


def test_kpi_metadata_has_all_required_fields(client: TestClient) -> None:
    """All KPIs have required metadata fields populated."""
    response = client.get("/kpis", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    for kpi in data["kpis"]:
        # All fields should be non-empty
        assert kpi["key"]
        assert kpi["name"]
        assert kpi["description"]
        assert kpi["formula"]
        assert kpi["unit"]
        assert kpi["domain"]
        assert len(kpi["data_sources"]) > 0
        assert kpi["good_direction"] in ["higher", "lower"]
        assert kpi["target_range"]


def test_kpi_data_sources_are_valid(client: TestClient) -> None:
    """KPI data sources reference known connectors or platform sources."""
    response = client.get("/kpis", headers=_make_auth_header())
    
    assert response.status_code == 200
    data = response.json()
    
    valid_sources = [
        "Shopify Orders",
        "Shopify Inventory",
        "Meta Ads",
        "Google Ads",
        "Cost Inputs",
        "Platform Activity Logs",
        "Platform Recommendation Logs",
    ]
    
    for kpi in data["kpis"]:
        for source in kpi["data_sources"]:
            assert source in valid_sources, f"Unknown data source: {source}"
