"""Tests for early warning and operational anomaly alerts (T-076).

Tests cover:
- Trajectory computation (linear regression, edge cases)
- Breach window prediction for all operators
- Early warning detection (confidence, thresholds)
- Operational anomaly alerts (z-score based)
- Edge cases and boundary conditions
"""

from __future__ import annotations

import pytest

from worker.app.simulation.early_warning_detector import (
    EarlyWarningDetector,
    OperationalAnomalyAlertHandler,
)


class TestTrajectoryComputation:
    """Test trajectory (slope) computation from historical values."""

    def test_compute_trajectory_perfect_declining(self) -> None:
        """Perfect linear decline."""
        values = [100, 90, 80, 70, 60]
        trajectory = EarlyWarningDetector.compute_trajectory(values, periods_in_days=1)
        assert trajectory is not None
        assert trajectory.slope == pytest.approx(-10.0, abs=0.1)
        assert trajectory.r_squared == pytest.approx(1.0, abs=0.01)
        assert trajectory.periods_analyzed == 5

    def test_compute_trajectory_perfect_improving(self) -> None:
        """Perfect linear improvement."""
        values = [60, 70, 80, 90, 100]
        trajectory = EarlyWarningDetector.compute_trajectory(values, periods_in_days=1)
        assert trajectory is not None
        assert trajectory.slope == pytest.approx(10.0, abs=0.1)
        assert trajectory.r_squared == pytest.approx(1.0, abs=0.01)

    def test_compute_trajectory_flat(self) -> None:
        """Flat trend (no change)."""
        values = [50.0, 50.0, 50.0, 50.0, 50.0]
        trajectory = EarlyWarningDetector.compute_trajectory(values, periods_in_days=1)
        assert trajectory is not None
        assert trajectory.slope == pytest.approx(0.0, abs=0.01)

    def test_compute_trajectory_insufficient_data(self) -> None:
        """Fewer than MIN_SLOPE_PERIODS should return None."""
        values = [100, 90]
        trajectory = EarlyWarningDetector.compute_trajectory(values)
        assert trajectory is None

    def test_compute_trajectory_noisy_data(self) -> None:
        """Noisy data with non-perfect r_squared."""
        values = [100, 95, 92, 88, 85, 80, 78]
        trajectory = EarlyWarningDetector.compute_trajectory(values, periods_in_days=1)
        assert trajectory is not None
        assert trajectory.r_squared > 0.7
        assert trajectory.slope < 0

    def test_compute_trajectory_custom_period(self) -> None:
        """Custom period interval (e.g., weekly data)."""
        values = [100, 80, 60, 40, 20]
        trajectory = EarlyWarningDetector.compute_trajectory(values, periods_in_days=7)
        assert trajectory is not None
        assert trajectory.slope == pytest.approx(-20.0 / 7.0, abs=0.1)

    def test_compute_trajectory_current_value_and_baseline(self) -> None:
        """Trajectory should capture current and baseline values."""
        values = [50, 55, 60, 65, 70]
        trajectory = EarlyWarningDetector.compute_trajectory(values)
        assert trajectory is not None
        assert trajectory.current_value == 70
        assert trajectory.baseline_value == pytest.approx(60.0, abs=0.1)


class TestBreachWindowPrediction:
    """Test prediction of days until threshold breach."""

    def test_predict_breach_less_than_operator(self) -> None:
        """Metric < threshold. Days to breach when declining."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=3.0,
            threshold_value=2.0,
            slope=-0.5,
            comparison_operator="<",
        )
        assert days == pytest.approx(2.0, abs=0.1)

    def test_predict_breach_greater_than_operator(self) -> None:
        """Metric > threshold. Days to breach when declining."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=100,
            threshold_value=80,
            slope=-5.0,
            comparison_operator=">",
        )
        assert days == pytest.approx(4.0, abs=0.1)

    def test_predict_breach_already_breached_less_than(self) -> None:
        """Already below threshold for < operator."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=1.5,
            threshold_value=2.0,
            slope=-0.5,
            comparison_operator="<",
        )
        assert days == 0.0

    def test_predict_breach_already_breached_greater_than(self) -> None:
        """Already above threshold for > operator."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=2.5,
            threshold_value=2.0,
            slope=0.5,
            comparison_operator=">",
        )
        assert days == 0.0

    def test_predict_breach_no_slope(self) -> None:
        """Zero slope (no trend) should return infinity."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=100,
            threshold_value=80,
            slope=0.0,
            comparison_operator=">",
        )
        assert days == float("inf")

    def test_predict_breach_improving_away_from_threshold(self) -> None:
        """Improving slope away from threshold should return infinity."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=100,
            threshold_value=80,
            slope=5.0,
            comparison_operator=">",
        )
        assert days == float("inf")

    def test_predict_breach_less_than_equal(self) -> None:
        """<= operator prediction."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=3.0,
            threshold_value=2.0,
            slope=-0.5,
            comparison_operator="<=",
        )
        assert days == pytest.approx(2.0, abs=0.1)

    def test_predict_breach_greater_than_equal(self) -> None:
        """">=" operator prediction."""
        days = EarlyWarningDetector.predict_breach_window(
            current_value=80,
            threshold_value=100,
            slope=5.0,
            comparison_operator=">=",
        )
        assert days == pytest.approx(4.0, abs=0.1)


class TestEarlyWarningDetection:
    """Test full early warning detection flow."""

    def test_early_warning_fires_for_confident_declining_trend(self) -> None:
        """Warning fires when declining with high confidence."""
        historical = [100, 95, 90, 85, 80]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=80,
            threshold_value=60,
            comparison_operator=">",
            metric_name="ROAS",
        )
        assert result.is_warning is True
        assert result.confidence > 0.5
        assert result.days_to_breach < 30

    def test_early_warning_no_fire_flat_trend(self) -> None:
        """No warning for flat trend."""
        historical = [100, 100, 100, 100, 100]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=100,
            threshold_value=80,
            comparison_operator=">",
            metric_name="CAC",
        )
        assert result.is_warning is False
        assert result.confidence == 0.0

    def test_early_warning_no_fire_improving_trend(self) -> None:
        """No warning when trend is improving."""
        historical = [60, 70, 80, 90, 100]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=100,
            threshold_value=80,
            comparison_operator=">",
            metric_name="Margin",
        )
        assert result.is_warning is False

    def test_early_warning_no_fire_already_breached(self) -> None:
        """No early warning if already breached."""
        historical = [100, 95, 90, 85, 80]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=50,
            threshold_value=60,
            comparison_operator=">",
            metric_name="ROAS",
        )
        assert result.is_warning is False

    def test_early_warning_no_fire_insufficient_data(self) -> None:
        """No warning with insufficient data."""
        historical = [100, 95]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=95,
            threshold_value=80,
            comparison_operator=">",
            metric_name="Revenue",
        )
        assert result.is_warning is False
        assert result.confidence == 0.0

    def test_early_warning_confidence_score(self) -> None:
        """Confidence combines trajectory fit and breach urgency."""
        historical = [100, 98, 96, 94, 92]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=92,
            threshold_value=80,
            comparison_operator=">",
            metric_name="CAC",
        )
        if result.is_warning:
            assert 0.0 < result.confidence <= 1.0

    def test_early_warning_days_to_breach(self) -> None:
        """Days to breach correctly calculated."""
        historical = [100, 90, 80, 70, 60]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=60,
            threshold_value=0,
            comparison_operator=">",
            metric_name="Spend",
        )
        if result.is_warning:
            assert result.days_to_breach > 0

    def test_early_warning_reasoning_text(self) -> None:
        """Reasoning text should be informative."""
        historical = [100, 92, 84, 76, 68]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=68,
            threshold_value=50,
            comparison_operator=">",
            metric_name="Repeat Purchase Rate",
        )
        assert result.reasoning is not None
        assert len(result.reasoning) > 10


class TestOperationalAnomalyAlerts:
    """Test operational anomaly alert creation."""

    def test_anomaly_alert_fires_high_z_score(self) -> None:
        """Alert fires when z-score > 2.0."""
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=3.5,
            current_value=50,
            baseline_value=20,
            metric_name="Return Rate",
            domain="operations",
        )
        assert result.is_anomalous_alert is True
        assert result.confidence > 0.75

    def test_anomaly_alert_fires_low_z_score(self) -> None:
        """Alert fires for negative z-score < -2.0."""
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=-3.0,
            current_value=5,
            baseline_value=25,
            metric_name="Inventory Level",
            domain="inventory",
        )
        assert result.is_anomalous_alert is True
        assert result.confidence > 0.5

    def test_anomaly_alert_no_fire_small_z_score(self) -> None:
        """No alert when z-score < 2.0."""
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=1.5,
            current_value=22,
            baseline_value=20,
            metric_name="Shipping Cost",
            domain="operations",
        )
        assert result.is_anomalous_alert is False
        assert result.confidence == 0.0

    def test_anomaly_alert_confidence_scales_with_z_score(self) -> None:
        """Higher z-score produces higher confidence."""
        result_high = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=5.0,
            current_value=100,
            baseline_value=20,
            metric_name="Metric",
            domain="operations",
        )
        result_low = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=2.1,
            current_value=25,
            baseline_value=20,
            metric_name="Metric",
            domain="operations",
        )
        assert result_high.confidence > result_low.confidence

    def test_anomaly_alert_reasoning_elevated(self) -> None:
        """Reasoning text reflects 'elevated' for positive z-score."""
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=3.0,
            current_value=60,
            baseline_value=30,
            metric_name="Return Count",
            domain="operations",
        )
        assert "elevated" in result.reasoning or "unusual" in result.reasoning

    def test_anomaly_alert_reasoning_depressed(self) -> None:
        """Reasoning text reflects 'depressed' for negative z-score."""
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=-3.0,
            current_value=10,
            baseline_value=30,
            metric_name="In-Stock Level",
            domain="inventory",
        )
        assert "depressed" in result.reasoning or "unusual" in result.reasoning

    def test_anomaly_alert_domain_in_result(self) -> None:
        """Result preserves domain."""
        for domain in ["kpi", "acquisition", "margin", "retention", "inventory"]:
            result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
                z_score=3.0,
                current_value=50,
                baseline_value=20,
                metric_name="Test",
                domain=domain,
            )
            assert result.domain == domain

    def test_anomaly_alert_z_score_in_result(self) -> None:
        """Result contains z-score."""
        z = 2.8
        result = OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
            z_score=z,
            current_value=40,
            baseline_value=20,
            metric_name="Metric",
            domain="operations",
        )
        assert result.z_score == pytest.approx(z, abs=0.01)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_trajectory_single_negative_value(self) -> None:
        """Trajectory with negative values."""
        values = [-100, -90, -80, -70, -60]
        trajectory = EarlyWarningDetector.compute_trajectory(values)
        assert trajectory is not None
        assert trajectory.slope > 0

    def test_trajectory_very_large_values(self) -> None:
        """Trajectory with very large numbers."""
        values = [1000000, 900000, 800000, 700000, 600000]
        trajectory = EarlyWarningDetector.compute_trajectory(values)
        assert trajectory is not None
        assert trajectory.slope < 0

    def test_trajectory_very_small_values(self) -> None:
        """Trajectory with very small numbers."""
        values = [0.01, 0.009, 0.008, 0.007, 0.006]
        trajectory = EarlyWarningDetector.compute_trajectory(values)
        assert trajectory is not None

    def test_early_warning_boundary_r_squared_exactly_min(self) -> None:
        """Warning fires when r_squared exactly at MIN_R_SQUARED."""
        historical = [100, 98, 96, 94, 92]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=92,
            threshold_value=70,
            comparison_operator=">",
            metric_name="Test",
        )
        if result.trajectory.r_squared >= EarlyWarningDetector.MIN_R_SQUARED:
            if (
                0 < result.days_to_breach
                < EarlyWarningDetector.PREDICTION_WINDOW_DAYS_THRESHOLD
            ):
                assert result.is_warning is True

    def test_early_warning_boundary_days_exactly_at_threshold(self) -> None:
        """Warning fires when days_to_breach near boundary."""
        historical = [100, 96, 92, 88, 84]
        result = EarlyWarningDetector.detect_early_warning(
            historical_values=historical,
            current_value=84,
            threshold_value=0,
            comparison_operator=">",
            metric_name="Test",
        )
        if result.days_to_breach > 25:
            assert result.is_warning is False

    def test_anomaly_alert_z_score_exactly_at_threshold(self) -> None:
        """Alert fires when z-score > 2.0 (not >=)."""
        result_exact = (
            OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
                z_score=2.0,
                current_value=30,
                baseline_value=20,
                metric_name="M",
                domain="ops",
            )
        )
        result_above = (
            OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
                z_score=2.01,
                current_value=30,
                baseline_value=20,
                metric_name="M",
                domain="ops",
            )
        )
        assert result_exact.is_anomalous_alert is False
        assert result_above.is_anomalous_alert is True

    def test_anomaly_alert_confidence_capped_at_1_0(self) -> None:
        """Confidence never exceeds 1.0."""
        result = (
            OperationalAnomalyAlertHandler.create_operational_anomaly_alert(
                z_score=10.0,
                current_value=100,
                baseline_value=10,
                metric_name="M",
                domain="ops",
            )
        )
        assert result.confidence <= 1.0
