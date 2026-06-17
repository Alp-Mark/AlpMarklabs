"""Tests for worker.app.simulation.response_functions (T-118)."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest
from worker.app.simulation.response_functions import (
    FIT_REGISTRY,
    MIN_DATA_WINDOW_DAYS,
    MIN_SAMPLE_COUNT,
    DataGateError,
    ResponseFunction,
    fit_acquisition,
    fit_executive,
    fit_inventory,
    fit_margin,
    fit_operations,
    fit_retention,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_WINDOW = MIN_DATA_WINDOW_DAYS  # exactly meets the gate
_SHORT_WINDOW = MIN_DATA_WINDOW_DAYS - 1


def _linear_points(
    n: int, slope: float = 1.0, intercept: float = 0.0
) -> list[tuple[float, float]]:
    """Generate n perfectly linear (x, y) pairs."""
    return [(float(i), slope * i + intercept) for i in range(n)]


def _noisy_points(
    n: int, slope: float = 2.0, intercept: float = 5.0, noise: float = 0.1
) -> list[tuple[float, float]]:
    """Generate n linear points with small Gaussian noise."""
    rng = np.random.default_rng(seed=42)
    xs = np.linspace(0, 100, n)
    ys = slope * xs + intercept + rng.normal(0, noise, n)
    return [(float(x), float(y)) for x, y in zip(xs, ys, strict=True)]


# ---------------------------------------------------------------------------
# Data gate tests
# ---------------------------------------------------------------------------


def test_data_gate_window_too_short() -> None:
    """DataGateError raised when data_window_days < MIN_DATA_WINDOW_DAYS."""
    points = _linear_points(20)
    with pytest.raises(DataGateError, match="minimum required is"):
        fit_acquisition(points, _SHORT_WINDOW)


def test_data_gate_too_few_samples() -> None:
    """DataGateError raised when fewer than MIN_SAMPLE_COUNT valid points."""
    points = _linear_points(MIN_SAMPLE_COUNT - 1)
    with pytest.raises(DataGateError, match="minimum required is"):
        fit_acquisition(points, _VALID_WINDOW)


def test_data_gate_non_finite_values_filtered() -> None:
    """Non-finite (x, y) pairs are dropped; gate fires if remaining count is too low."""
    # 3 valid + inf/nan fillers — valid count below MIN_SAMPLE_COUNT
    points = [
        (1.0, 2.0),
        (2.0, 4.0),
        (3.0, 6.0),
        (float("inf"), 0.0),
        (4.0, float("nan")),
    ]
    with pytest.raises(DataGateError, match="valid sample"):
        fit_acquisition(points, _VALID_WINDOW)


def test_data_gate_passes_with_exactly_minimum() -> None:
    """No error when both window and sample count exactly meet the minimums."""
    points = _linear_points(MIN_SAMPLE_COUNT)
    rf = fit_acquisition(points, _VALID_WINDOW)
    assert rf.sample_count == MIN_SAMPLE_COUNT


# ---------------------------------------------------------------------------
# ResponseFunction structure tests
# ---------------------------------------------------------------------------


def test_response_function_fields_acquisition() -> None:
    """fit_acquisition returns a ResponseFunction with correct metadata."""
    points = _linear_points(20)
    rf = fit_acquisition(points, _VALID_WINDOW)

    assert rf.domain == "acquisition"
    assert rf.control_variable == "ad_spend_amount"
    assert rf.target_metric == "roas"
    assert rf.sample_count == 20
    assert len(rf.coefficients) == rf.degree + 1
    assert rf.x_min == 0.0
    assert rf.x_max == 19.0
    assert rf.fitted_at is not None


def test_r_squared_near_one_for_linear_data() -> None:
    """A quadratic fit on perfectly linear data should yield r² ≈ 1.0."""
    points = _linear_points(30, slope=3.0, intercept=10.0)
    rf = fit_acquisition(points, _VALID_WINDOW)
    assert rf.r_squared == pytest.approx(1.0, abs=1e-6)


def test_r_squared_between_zero_and_one_for_noisy_data() -> None:
    """r² should be positive and < 1 for noisy (but correlated) data."""
    points = _noisy_points(50)
    rf = fit_acquisition(points, _VALID_WINDOW)
    assert 0.0 <= rf.r_squared <= 1.0


# ---------------------------------------------------------------------------
# predict() and in_range() tests
# ---------------------------------------------------------------------------


def test_predict_linear_fit() -> None:
    """predict() should return the polynomial value at the given x."""
    # y = 2x + 5 exactly, fit should recover these coefficients
    points = [(float(i), 2.0 * i + 5.0) for i in range(20)]
    rf = fit_executive(points, _VALID_WINDOW)
    # For a perfect linear data set, predict(10) should equal 25.0
    assert rf.predict(10.0) == pytest.approx(25.0, abs=1e-6)


def test_in_range_within_bounds() -> None:
    """in_range returns True for x within [x_min, x_max]."""
    points = _linear_points(20)  # x from 0 to 19
    rf = fit_acquisition(points, _VALID_WINDOW)
    assert rf.in_range(0.0) is True
    assert rf.in_range(10.0) is True
    assert rf.in_range(19.0) is True


def test_in_range_outside_bounds() -> None:
    """in_range returns False for x outside [x_min, x_max]."""
    points = _linear_points(20)  # x from 0 to 19
    rf = fit_acquisition(points, _VALID_WINDOW)
    assert rf.in_range(-1.0) is False
    assert rf.in_range(20.0) is False


# ---------------------------------------------------------------------------
# All six domain fit functions — smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn, expected_domain, expected_x, expected_y",
    [
        (fit_acquisition, "acquisition", "ad_spend_amount", "roas"),
        (fit_margin, "margin", "cost_pct_of_revenue", "margin_impact_pct"),
        (fit_retention, "retention", "day_index", "repeat_purchase_rate_pct"),
        (fit_inventory, "inventory", "reorder_point", "days_to_stockout"),
        (fit_operations, "operations", "units_sold_30d", "logistics_cost_per_unit"),
        (fit_executive, "executive", "ad_spend_amount", "contribution_margin_pct"),
    ],
)
def test_all_domain_fit_functions(
    fn: Callable[[list[tuple[float, float]], int], ResponseFunction],
    expected_domain: str,
    expected_x: str,
    expected_y: str,
) -> None:
    """Each domain fit function returns a ResponseFunction with correct metadata."""
    points = _noisy_points(30)
    rf = fn(points, _VALID_WINDOW)

    assert isinstance(rf, ResponseFunction)
    assert rf.domain == expected_domain
    assert rf.control_variable == expected_x
    assert rf.target_metric == expected_y
    assert rf.sample_count == 30
    assert math.isfinite(rf.r_squared)


# ---------------------------------------------------------------------------
# FIT_REGISTRY test
# ---------------------------------------------------------------------------


def test_fit_registry_covers_all_domains() -> None:
    """FIT_REGISTRY contains exactly the six expected domain keys."""
    expected = {
        "acquisition",
        "margin",
        "retention",
        "inventory",
        "operations",
        "executive",
    }
    assert set(FIT_REGISTRY.keys()) == expected


def test_fit_registry_callables_return_response_function() -> None:
    """Every function in FIT_REGISTRY produces a valid ResponseFunction."""
    points = _linear_points(20)
    for domain, fn in FIT_REGISTRY.items():
        rf = fn(points, _VALID_WINDOW)
        assert rf.domain == domain


# ---------------------------------------------------------------------------
# Degree clamping test
# ---------------------------------------------------------------------------


def test_degree_clamped_to_sample_count_minus_one() -> None:
    """With exactly MIN_SAMPLE_COUNT points the degree is clamped."""
    points = _linear_points(MIN_SAMPLE_COUNT)
    rf = fit_acquisition(points, _VALID_WINDOW)
    # degree must be at most len(points) - 1
    assert rf.degree <= MIN_SAMPLE_COUNT - 1
    assert len(rf.coefficients) == rf.degree + 1
