"""FR-118 / T-076: Early Warning and Operational Anomaly Alerts.

Early warning alerts flag metric trajectory toward a threshold breach.
Operational anomaly alerts surface unusual patterns detected by z-score.

Two alert types:
1. Early Warning: metric trending toward threshold breach. Fires before breach.
2. Operational Anomaly: z-score > threshold (unusual pattern). Fires without
   threshold config, based on statistical anomaly alone.

Both types use confidence scoring and prediction windows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DataFreshnessMetadata:
    """Freshness and confidence context for alert data.

    Attributes:
        last_synced_at: ISO timestamp when data source was last synced.
        domain: Source domain (e.g., "shopify", "meta_ads", "google_ads").
        is_stale: True if data age exceeds staleness threshold.
        staleness_hours: Age of data in hours.
        confidence_penalty: Confidence reduction (0.0-1.0) due to staleness.
    """

    last_synced_at: datetime
    domain: str
    is_stale: bool
    staleness_hours: float
    confidence_penalty: float


@dataclass
class TrajectoryMetrics:
    """Trajectory metrics for early warning calculation.

    Attributes:
        slope: Rate of change per period (negative = declining, positive =
               improving).
        r_squared: Goodness of fit (0.0-1.0). Higher = more confident trend.
        periods_analyzed: Number of periods used to compute slope.
        current_value: Current metric value.
        baseline_value: Expected/baseline value.
        prediction_window_days: Days until threshold breach at current slope.
    """

    slope: float
    r_squared: float
    periods_analyzed: int
    current_value: float
    baseline_value: float
    prediction_window_days: float


@dataclass
class EarlyWarningResult:
    """Result of early warning detection.

    Represents a metric trending toward a threshold breach.

    Attributes:
        is_warning: True if early warning should fire (trajectory confident).
        confidence: Confidence score (0.0-1.0). Combines r_squared and
                   prediction urgency. May be adjusted for data staleness.
        trajectory: TrajectoryMetrics with slope and trend analysis.
        reasoning: Plain-English explanation of the warning.
        days_to_breach: Estimated days until threshold crossed at current
                       slope.
        freshness_metadata: Optional list of data source freshness details.
        original_confidence: Pre-staleness-adjustment confidence (for audit).
    """

    is_warning: bool
    confidence: float
    trajectory: TrajectoryMetrics
    reasoning: str
    days_to_breach: float
    freshness_metadata: list[DataFreshnessMetadata] = field(
        default_factory=list
    )
    original_confidence: float | None = None


@dataclass
class OperationalAnomalyAlertResult:
    """Result of operational anomaly alert evaluation.

    Represents an unusual pattern detected without threshold config.

    Attributes:
        is_anomalous_alert: True if operational anomaly alert should fire.
        confidence: Z-score based confidence (0.0-1.0). May be adjusted for
                   data staleness.
        z_score: Statistical distance from baseline.
        reasoning: Plain-English explanation of the anomaly.
        domain: Business domain (e.g., "operations", "inventory").
        freshness_metadata: Optional list of data source freshness details.
        original_confidence: Pre-staleness-adjustment confidence (for audit).
    """

    is_anomalous_alert: bool
    confidence: float
    z_score: float
    reasoning: str
    domain: str
    freshness_metadata: list[DataFreshnessMetadata] = field(
        default_factory=list
    )
    original_confidence: float | None = None


class EarlyWarningDetector:
    """Detects early warnings: metrics trending toward threshold breach."""

    MIN_SLOPE_PERIODS = 3
    MIN_R_SQUARED = 0.5
    PREDICTION_WINDOW_DAYS_THRESHOLD = 30

    @staticmethod
    def compute_trajectory(
        historical_values: Sequence[float], periods_in_days: int = 1
    ) -> TrajectoryMetrics | None:
        """Compute trajectory (slope) from historical values.

        Uses linear regression (least squares) to fit a line to historical
        data. Returns None if insufficient data or poor fit.

        Args:
            historical_values: Recent metric values, oldest first. Must be
                             >= MIN_SLOPE_PERIODS.
            periods_in_days: Interval between values (default 1 = daily).

        Returns:
            TrajectoryMetrics with slope, r_squared, and prediction window,
            or None if data insufficient.
        """
        if len(historical_values) < EarlyWarningDetector.MIN_SLOPE_PERIODS:
            return None

        n = len(historical_values)
        x_values = list(range(n))
        y_values = historical_values

        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum(
            (x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n)
        )
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope_per_period = numerator / denominator
        slope = slope_per_period / periods_in_days

        y_pred = [
            y_mean + slope_per_period * (x_values[i] - x_mean) for i in range(n)
        ]
        ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))

        if ss_tot == 0:
            r_squared = 0.0
        else:
            r_squared = 1.0 - (ss_res / ss_tot)

        current_value = y_values[-1]
        baseline_value = y_mean

        return TrajectoryMetrics(
            slope=slope,
            r_squared=max(0.0, r_squared),
            periods_analyzed=n,
            current_value=current_value,
            baseline_value=baseline_value,
            prediction_window_days=0.0,
        )

    @staticmethod
    def predict_breach_window(
        current_value: float,
        threshold_value: float,
        slope: float,
        comparison_operator: str,
    ) -> float:
        """Predict days until metric crosses threshold at current slope.

        For monitoring constraints, predicts when metric will cross threshold.
        Returns 0 if already crossed and moving away, infinity if moving away
        before crossing, or days to cross if moving toward threshold.

        Args:
            current_value: Current metric value.
            threshold_value: Alert threshold.
            slope: Slope (change per day).
            comparison_operator: Comparison operator ("<", ">", "<=", ">=",
                               "==", "!=").

        Returns:
            Days until metric crosses threshold. Returns 0.0 if already
            crossed and safe. Returns inf if will never cross or if safe.
        """
        if slope == 0:
            return float("inf")

        distance = abs(current_value - threshold_value)

        if comparison_operator == "<":
            # Constraint: metric < threshold
            # Safe: current < threshold
            # Breach: current >= threshold
            if current_value < threshold_value and slope <= 0:
                # Safe and moving away
                return 0.0 if distance < 1.0 else float("inf")
            if current_value < threshold_value and slope > 0:
                return distance / slope  # Safe but moving toward breach
            if current_value >= threshold_value and slope < 0:
                return distance / abs(slope)  # Not safe, moving toward safety
            return float("inf")  # Not safe and moving away
        elif comparison_operator == ">":
            # Constraint: metric > threshold
            # Safe: current > threshold
            # Breach: current <= threshold
            if current_value > threshold_value and slope >= 0:
                # Safe and moving away from breach
                return 0.0 if distance < 1.0 else float("inf")
            if current_value > threshold_value and slope < 0:
                return distance / abs(slope)  # Safe but moving toward breach
            if current_value <= threshold_value and slope > 0:
                return distance / slope  # Not safe, moving toward safety
            return float("inf")  # Not safe and moving away
        elif comparison_operator == "<=":
            # Constraint: metric <= threshold
            # Safe: current <= threshold
            # Breach: current > threshold
            if current_value <= threshold_value and slope <= 0:
                return 0.0  # Safe and moving away
            if current_value <= threshold_value and slope > 0:
                return distance / slope  # Safe but moving toward breach
            if current_value > threshold_value and slope < 0:
                return distance / abs(slope)  # Not safe, moving toward safety
            return float("inf")  # Not safe and moving away
        elif comparison_operator == ">=":
            # Constraint: metric >= threshold
            # Safe: current >= threshold
            # Breach: current < threshold
            if current_value >= threshold_value and slope >= 0:
                return 0.0  # Safe and moving away
            if current_value >= threshold_value and slope < 0:
                return distance / abs(slope)  # Safe but moving toward breach
            if current_value < threshold_value and slope > 0:
                return distance / slope  # Not safe, moving toward safety
            return float("inf")  # Not safe and moving away
        else:
            return float("inf")

    @staticmethod
    def detect_early_warning(
        historical_values: Sequence[float],
        current_value: float,
        threshold_value: float,
        comparison_operator: str,
        metric_name: str = "metric",
        periods_in_days: int = 1,
    ) -> EarlyWarningResult:
        """Detect early warning: metric trending toward threshold breach.

        Computes trajectory, predicts breach window, and fires warning if:
        1. Trajectory is confident (r_squared >= MIN_R_SQUARED)
        2. Breach window is imminent (< PREDICTION_WINDOW_DAYS_THRESHOLD)
        3. Slope is in breach direction (not improving)

        Args:
            historical_values: Recent metric values, oldest first.
            current_value: Current metric value (should match last of
                         historical_values).
            threshold_value: Alert threshold.
            comparison_operator: Comparison operator.
            metric_name: Metric name for reasoning text.
            periods_in_days: Interval between values (default 1 = daily).

        Returns:
            EarlyWarningResult with is_warning flag and confidence.
        """
        trajectory = EarlyWarningDetector.compute_trajectory(
            historical_values, periods_in_days
        )

        if trajectory is None:
            return EarlyWarningResult(
                is_warning=False,
                confidence=0.0,
                trajectory=TrajectoryMetrics(
                    slope=0.0,
                    r_squared=0.0,
                    periods_analyzed=len(historical_values),
                    current_value=current_value,
                    baseline_value=0.0,
                    prediction_window_days=0.0,
                ),
                reasoning="Insufficient historical data for trajectory analysis.",
                days_to_breach=float("inf"),
            )

        days_to_breach = EarlyWarningDetector.predict_breach_window(
            current_value, threshold_value, trajectory.slope, comparison_operator
        )

        is_warning = (
            trajectory.r_squared >= EarlyWarningDetector.MIN_R_SQUARED
            and 0 < days_to_breach
            < EarlyWarningDetector.PREDICTION_WINDOW_DAYS_THRESHOLD
        )

        if is_warning:
            confidence = min(
                (trajectory.r_squared + min(days_to_breach, 30.0) / 30.0) / 2.0, 1.0
            )
            direction = "declining" if trajectory.slope < 0 else "improving"
            reasoning = (
                f"Early Warning: {metric_name} is {direction} with slope "
                f"{trajectory.slope:.4f}/day. "
                f"Predicted breach in {days_to_breach:.1f} days at current trend. "
                f"Trajectory confidence: {trajectory.r_squared:.2f}."
            )
        else:
            confidence = 0.0
            reasoning = (
                f"No early warning: {metric_name} trajectory not concerning. "
                f"R-squared: {trajectory.r_squared:.2f}, "
                f"Days to breach: {days_to_breach:.1f}."
            )

        trajectory.prediction_window_days = days_to_breach

        return EarlyWarningResult(
            is_warning=is_warning,
            confidence=confidence,
            trajectory=trajectory,
            reasoning=reasoning,
            days_to_breach=days_to_breach,
        )


class OperationalAnomalyAlertHandler:
    """Fires operational anomaly alerts based on z-score without threshold."""

    Z_SCORE_THRESHOLD = 2.0

    @staticmethod
    def create_operational_anomaly_alert(
        z_score: float,
        current_value: float,
        baseline_value: float,
        metric_name: str,
        domain: str,
    ) -> OperationalAnomalyAlertResult:
        """Create operational anomaly alert from z-score.

        Fires when z-score indicates unusual pattern, independent of
        threshold configuration. Intended for catching operational surprises.

        Args:
            z_score: Z-score from anomaly detector (T-073).
            current_value: Current metric value.
            baseline_value: Baseline/expected value.
            metric_name: Metric name for reasoning text.
            domain: Business domain (kpi, acquisition, margin, retention,
                   inventory, operations).

        Returns:
            OperationalAnomalyAlertResult with is_anomalous_alert flag.
        """
        is_anomalous = abs(z_score) > OperationalAnomalyAlertHandler.Z_SCORE_THRESHOLD

        if is_anomalous:
            confidence = min(abs(z_score) / 3.0, 1.0)
            direction = "elevated" if z_score > 0 else "depressed"
            reasoning = (
                f"Operational Anomaly Alert ({domain}): {metric_name} "
                f"is {direction} at {current_value:.2f} "
                f"(baseline {baseline_value:.2f}, z-score {z_score:.2f}). "
                f"This is unusual and warrants investigation."
            )
        else:
            confidence = 0.0
            reasoning = (
                f"No operational anomaly: {metric_name} within expected range "
                f"(z-score {z_score:.2f})."
            )

        return OperationalAnomalyAlertResult(
            is_anomalous_alert=is_anomalous,
            confidence=confidence,
            z_score=z_score,
            reasoning=reasoning,
            domain=domain,
        )
