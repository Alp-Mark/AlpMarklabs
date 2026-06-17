"""Unit tests for response function orchestrator (T-118 integration layer).

These tests verify that the orchestrator correctly:
- Calls fit functions with fetched data
- Handles DataGateError gracefully
- Returns None on insufficient data
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from worker.app.simulation.fit_orchestrator import ResponseFunctionFitter
from worker.app.simulation.response_functions import DataGateError, ResponseFunction


@pytest.fixture
def mock_db() -> MagicMock:
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def sample_rf() -> ResponseFunction:
    """Create a sample ResponseFunction for mocking."""
    from datetime import UTC, datetime

    return ResponseFunction(
        domain="acquisition",
        control_variable="ad_spend_amount",
        target_metric="roas",
        degree=2,
        coefficients=(1.0, 2.0, 3.0),
        sample_count=10,
        x_min=100.0,
        x_max=1000.0,
        r_squared=0.92,
        fitted_at=datetime.now(UTC),
    )


def test_fit_acquisition_no_data(mock_db: MagicMock) -> None:
    """Return None when no acquisition data available."""
    tenant_id = uuid4()

    with patch(
        "worker.app.simulation.fit_orchestrator.fetch_acquisition_data"
    ) as mock_fetch:
        mock_fetch.return_value = ([], 30)  # Empty data, 30-day window

        fitter = ResponseFunctionFitter(mock_db, tenant_id, lookback_days=30)
        result = fitter.fit_acquisition()

    assert result is None
    mock_fetch.assert_called_once_with(mock_db, tenant_id, 30)


def test_fit_acquisition_data_gate_error(mock_db: MagicMock) -> None:
    """Return None when data gate fails."""
    tenant_id = uuid4()

    with patch(
        "worker.app.simulation.fit_orchestrator.fetch_acquisition_data"
    ) as mock_fetch, patch(
        "worker.app.simulation.fit_orchestrator.fit_acquisition"
    ) as mock_fit:
        # Data fetched successfully but fit fails data gate
        mock_fetch.return_value = ([(1000.0, 2.5)], 20)
        mock_fit.side_effect = DataGateError("Insufficient data window")

        fitter = ResponseFunctionFitter(mock_db, tenant_id, lookback_days=30)
        result = fitter.fit_acquisition()

    assert result is None


def test_fit_acquisition_success(
    mock_db: MagicMock, sample_rf: ResponseFunction
) -> None:
    """Return ResponseFunction on successful fit."""
    tenant_id = uuid4()

    with patch(
        "worker.app.simulation.fit_orchestrator.fetch_acquisition_data"
    ) as mock_fetch, patch(
        "worker.app.simulation.fit_orchestrator.fit_acquisition"
    ) as mock_fit:
        mock_fetch.return_value = ([(1000.0, 2.5), (2000.0, 3.0)], 120)
        mock_fit.return_value = sample_rf

        fitter = ResponseFunctionFitter(mock_db, tenant_id, lookback_days=120)
        result = fitter.fit_acquisition()

    assert result is sample_rf
    mock_fetch.assert_called_once()
    mock_fit.assert_called_once_with([(1000.0, 2.5), (2000.0, 3.0)], 120)


def test_fit_retention_success(
    mock_db: MagicMock, sample_rf: ResponseFunction
) -> None:
    """Fit retention returns ResponseFunction on success."""
    tenant_id = uuid4()
    rf_retention = ResponseFunction(
        domain="retention",
        control_variable="day_index",
        target_metric="repeat_purchase_rate_pct",
        degree=1,
        coefficients=(0.5, 15.0),
        sample_count=30,
        x_min=0.0,
        x_max=30.0,
        r_squared=0.88,
        fitted_at=sample_rf.fitted_at,
    )

    with patch(
        "worker.app.simulation.fit_orchestrator.fetch_retention_data"
    ) as mock_fetch, patch(
        "worker.app.simulation.fit_orchestrator.fit_retention"
    ) as mock_fit:
        mock_fetch.return_value = ([(i, 15.0 + i * 0.5) for i in range(30)], 120)
        mock_fit.return_value = rf_retention

        fitter = ResponseFunctionFitter(mock_db, tenant_id, lookback_days=120)
        result = fitter.fit_retention()

    assert result is rf_retention
    assert result.domain == "retention"


def test_fit_all_domains(mock_db: MagicMock, sample_rf: ResponseFunction) -> None:
    """fit_all_domains attempts all domains and returns dict."""
    tenant_id = uuid4()

    with patch(
        "worker.app.simulation.fit_orchestrator.fetch_acquisition_data"
    ) as mock_fetch_acq, patch(
        "worker.app.simulation.fit_orchestrator.fit_acquisition"
    ) as mock_fit_acq, patch(
        "worker.app.simulation.fit_orchestrator.fetch_margin_data"
    ) as mock_fetch_margin, patch(
        "worker.app.simulation.fit_orchestrator.fit_margin"
    ) as mock_fit_margin, patch(
        "worker.app.simulation.fit_orchestrator.fetch_retention_data"
    ) as mock_fetch_ret, patch(
        "worker.app.simulation.fit_orchestrator.fit_retention"
    ) as mock_fit_ret, patch(
        "worker.app.simulation.fit_orchestrator.fetch_operations_data"
    ) as mock_fetch_ops, patch(
        "worker.app.simulation.fit_orchestrator.fit_operations"
    ) as mock_fit_ops, patch(
        "worker.app.simulation.fit_orchestrator.fetch_executive_data"
    ) as mock_fetch_exec, patch(
        "worker.app.simulation.fit_orchestrator.fit_executive"
    ) as mock_fit_exec:

        # Set up returns: acquisition succeeds, others fail or return None
        mock_fetch_acq.return_value = ([(1000.0, 2.5)], 120)
        mock_fit_acq.return_value = sample_rf

        mock_fetch_margin.return_value = ([], 30)
        mock_fit_margin.return_value = None

        mock_fetch_ret.return_value = ([(i, 15.0) for i in range(10)], 120)
        mock_fit_ret.return_value = None

        mock_fetch_ops.return_value = ([], 30)
        mock_fetch_exec.return_value = ([(1000.0, 35.0)], 120)
        mock_fit_exec.return_value = sample_rf

        fitter = ResponseFunctionFitter(mock_db, tenant_id, lookback_days=120)
        results = fitter.fit_all_domains()

    assert isinstance(results, dict)
    assert "acquisition" in results
    assert "margin" in results
    assert "retention" in results
    assert "operations" in results
    assert "executive" in results

    # Verify results match mocked returns
    assert results["acquisition"] is sample_rf
    assert results["margin"] is None
    assert results["operations"] is None
    assert results["executive"] is sample_rf
