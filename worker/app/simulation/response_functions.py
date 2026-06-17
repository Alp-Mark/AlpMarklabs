"""FR-071 / T-118: Response function fitting per simulation domain.

Fits a smooth polynomial response curve from historical snapshot data for each
simulation domain.  The fitted ResponseFunction is consumed by the T-081
scipy.optimize continuous optimizer, which requires a differentiable function
rather than raw noisy snapshot data.

Data gate
---------
MIN_DATA_WINDOW_DAYS calendar days of data must span the supplied data points
before any fit is attempted.  If either the window or the minimum sample count
is not met, DataGateError is raised to prevent the optimizer from operating on
insufficient signal.

Domains and (control variable → target metric) pairs
-----------------------------------------------------
acquisition  ad_spend_amount       → roas
margin       cost_pct_of_revenue   → margin_impact_pct
retention    day_index             → repeat_purchase_rate_pct  (CRM lever proxy)
inventory    reorder_point         → days_to_stockout
operations   units_sold_30d        → logistics_cost_per_unit
executive    ad_spend_amount       → contribution_margin_pct

NOTE — retention domain: no direct CRM lever column exists in
RetentionDailySnapshot at this stage.  day_index (0-based chronological
position of each snapshot) is used as a proxy for the passage of CRM
intervention time.  This should be revisited when explicit CRM cadence or
send-frequency data is available in the schema.

All fit functions accept a list of (x, y) float tuples and a data_window_days
integer representing the calendar span of the supplied data.  No DB I/O
occurs inside this module — callers are responsible for fetching and preparing
data before calling these functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_DATA_WINDOW_DAYS: int = 90
MIN_SAMPLE_COUNT: int = 5  # secondary gate alongside the calendar-day gate


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class DataGateError(Exception):
    """Raised when insufficient data is available to fit a response function.

    Callers should catch this and surface a data-freshness warning rather than
    propagating it as an unhandled error.
    """


# ---------------------------------------------------------------------------
# ResponseFunction dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseFunction:
    """Fitted polynomial response curve for one simulation domain.

    Attributes
    ----------
    domain:           Simulation domain name (e.g. "acquisition").
    control_variable: Name of the x axis variable (e.g. "ad_spend_amount").
    target_metric:    Name of the y axis variable (e.g. "roas").
    degree:           Effective polynomial degree used for the fit.
    coefficients:     Polynomial coefficients, highest power first
                      (numpy convention — pass directly to np.polyval).
    sample_count:     Number of (x, y) pairs used to fit the curve.
    x_min, x_max:     Observed range of the control variable.  Inputs outside
                      this range are extrapolations; use in_range() to check.
    r_squared:        Coefficient of determination for the fit.  Values close
                      to 1.0 indicate a good fit; values near 0 or negative
                      indicate the polynomial does not explain the variance.
    fitted_at:        UTC timestamp of when the fit was computed.
    """

    domain: str
    control_variable: str
    target_metric: str
    degree: int
    coefficients: tuple[float, ...]
    sample_count: int
    x_min: float
    x_max: float
    r_squared: float
    fitted_at: datetime

    def predict(self, x: float) -> float:
        """Evaluate the fitted polynomial at x."""
        return float(np.polyval(self.coefficients, x))

    def in_range(self, x: float) -> bool:
        """Return True if x is within the observed control variable range."""
        return self.x_min <= x <= self.x_max


# ---------------------------------------------------------------------------
# Internal fitting core
# ---------------------------------------------------------------------------


def _fit(
    domain: str,
    control_variable: str,
    target_metric: str,
    data_points: list[tuple[float, float]],
    data_window_days: int,
    degree: int = 2,
) -> ResponseFunction:
    """Fit a polynomial to data_points and return a ResponseFunction.

    Parameters
    ----------
    domain, control_variable, target_metric:
        Metadata attached to the returned ResponseFunction.
    data_points:
        List of (x, y) float tuples.  x is the control variable; y is the
        target metric.  Points with non-finite values are dropped silently.
    data_window_days:
        Calendar span of the data (end_date - start_date).days.  Must be
        >= MIN_DATA_WINDOW_DAYS or DataGateError is raised.
    degree:
        Requested polynomial degree.  Clamped to len(data_points) - 1 if
        the sample count would otherwise make the system under-determined.

    Raises
    ------
    DataGateError:
        If data_window_days < MIN_DATA_WINDOW_DAYS or
        len(valid_points) < MIN_SAMPLE_COUNT.
    """
    if data_window_days < MIN_DATA_WINDOW_DAYS:
        raise DataGateError(
            f"{domain}: data window is {data_window_days} days — "
            f"minimum required is {MIN_DATA_WINDOW_DAYS} days."
        )

    # Drop non-finite values before fitting
    valid = [
        (x, y)
        for x, y in data_points
        if np.isfinite(x) and np.isfinite(y)
    ]

    if len(valid) < MIN_SAMPLE_COUNT:
        raise DataGateError(
            f"{domain}: only {len(valid)} valid sample(s) after filtering — "
            f"minimum required is {MIN_SAMPLE_COUNT}."
        )

    xs = np.array([p[0] for p in valid], dtype=float)
    ys = np.array([p[1] for p in valid], dtype=float)

    # Clamp degree so the system is never under-determined
    effective_degree = min(degree, len(valid) - 1)

    coeffs = np.polyfit(xs, ys, effective_degree)

    y_pred = np.polyval(coeffs, xs)
    ss_res = float(np.sum((ys - y_pred) ** 2))
    ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0.0 else 0.0

    return ResponseFunction(
        domain=domain,
        control_variable=control_variable,
        target_metric=target_metric,
        degree=effective_degree,
        coefficients=tuple(float(c) for c in coeffs),
        sample_count=len(valid),
        x_min=float(xs.min()),
        x_max=float(xs.max()),
        r_squared=r_squared,
        fitted_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Domain-specific fit functions
# ---------------------------------------------------------------------------


def fit_acquisition(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit ROAS as a function of ad spend.

    data_points: list of (ad_spend_amount, roas) tuples drawn from
    AcquisitionMetricsSnapshot rows ordered by snapshot_date.
    """
    return _fit(
        "acquisition",
        "ad_spend_amount",
        "roas",
        data_points,
        data_window_days,
    )


def fit_margin(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit margin impact % as a function of cost driver % of revenue.

    data_points: list of (pct_of_revenue, margin_impact_pct) tuples drawn
    from CostDriverSnapshot rows for a single driver_type, ordered by
    snapshot_date.
    """
    return _fit(
        "margin",
        "cost_pct_of_revenue",
        "margin_impact_pct",
        data_points,
        data_window_days,
    )


def fit_retention(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit repeat purchase rate as a function of chronological day index.

    data_points: list of (day_index, repeat_purchase_rate_pct) tuples where
    day_index is the 0-based position of the snapshot in date-ascending order
    (derived from RetentionDailySnapshot rows).

    NOTE: day_index is used as a proxy for CRM intervention cadence because
    direct CRM lever data is not yet present in the snapshot schema.  This
    should be replaced with actual CRM send-frequency or cadence data once
    available.
    """
    return _fit(
        "retention",
        "day_index",
        "repeat_purchase_rate_pct",
        data_points,
        data_window_days,
    )


def fit_inventory(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit days_to_stockout as a function of reorder_point.

    data_points: list of (reorder_point, days_to_stockout) tuples drawn from
    InventoryRiskSnapshot rows for a single SKU, ordered by snapshot_date.
    Only rows where both reorder_point and days_to_stockout are non-null
    should be included by the caller.
    """
    return _fit(
        "inventory",
        "reorder_point",
        "days_to_stockout",
        data_points,
        data_window_days,
    )


def fit_operations(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit logistics cost per unit as a function of units sold in 30 days.

    data_points: list of (units_sold_30d, logistics_cost_per_unit) tuples
    drawn from OperationalImpactSnapshot rows, ordered by snapshot_date.
    Only rows where logistics_cost_per_unit is non-null should be included.
    """
    return _fit(
        "operations",
        "units_sold_30d",
        "logistics_cost_per_unit",
        data_points,
        data_window_days,
    )


def fit_executive(
    data_points: list[tuple[float, float]],
    data_window_days: int,
) -> ResponseFunction:
    """Fit contribution margin % as a function of ad spend.

    data_points: list of (ad_spend_amount, contribution_margin_pct) tuples
    drawn from ExecutiveKpiSnapshot rows, ordered by snapshot_date.
    """
    return _fit(
        "executive",
        "ad_spend_amount",
        "contribution_margin_pct",
        data_points,
        data_window_days,
    )


# ---------------------------------------------------------------------------
# Domain registry — used by T-081 optimizer to look up fit functions by name
# ---------------------------------------------------------------------------

FIT_REGISTRY: dict[
    str, Callable[[list[tuple[float, float]], int], ResponseFunction]
] = {
    "acquisition": fit_acquisition,
    "margin": fit_margin,
    "retention": fit_retention,
    "inventory": fit_inventory,
    "operations": fit_operations,
    "executive": fit_executive,
}
