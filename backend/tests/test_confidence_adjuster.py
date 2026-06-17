"""Tests for confidence adjuster and data freshness injection (T-077)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from worker.app.simulation.confidence_adjuster import ConfidenceAdjuster
from worker.app.simulation.early_warning_detector import (
    EarlyWarningResult,
    OperationalAnomalyAlertResult,
    TrajectoryMetrics,
)


class TestStalenessHoursComputation:
    """Test staleness_hours calculation."""

    def test_fresh_data_zero_staleness(self) -> None:
        """Data synced now should have zero staleness."""
        now = datetime.now(UTC)
        staleness = ConfidenceAdjuster.compute_staleness_hours(now, now)
        assert staleness == pytest.approx(0.0, abs=0.01)

    def test_one_hour_old(self) -> None:
        """Data synced 1 hour ago should show 1.0 hour staleness."""
        now = datetime.now(UTC)
        one_hour_ago = now - timedelta(hours=1)
        staleness = ConfidenceAdjuster.compute_staleness_hours(
            one_hour_ago, now
        )
        assert staleness == pytest.approx(1.0, abs=0.01)

    def test_one_day_old(self) -> None:
        """Data synced 24 hours ago should show 24.0 hour staleness."""
        now = datetime.now(UTC)
        one_day_ago = now - timedelta(days=1)
        staleness = ConfidenceAdjuster.compute_staleness_hours(
            one_day_ago, now
        )
        assert staleness == pytest.approx(24.0, abs=0.01)

    def test_seven_days_old(self) -> None:
        """Data synced 7 days ago should show 168.0 hour staleness."""
        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)
        staleness = ConfidenceAdjuster.compute_staleness_hours(
            seven_days_ago, now
        )
        assert staleness == pytest.approx(168.0, abs=0.1)

    def test_future_timestamp_clamped_to_zero(self) -> None:
        """Future timestamp should be clamped to zero staleness."""
        now = datetime.now(UTC)
        future = now + timedelta(hours=1)
        staleness = ConfidenceAdjuster.compute_staleness_hours(
            future, now
        )
        assert staleness == pytest.approx(0.0, abs=0.01)

    def test_naive_datetime_treated_as_utc(self) -> None:
        """Naive datetime should be treated as UTC."""
        last_synced = datetime(2026, 6, 12, 10, 0, 0)  # Naive
        reference = datetime(2026, 6, 12, 12, 0, 0)  # Naive
        staleness = ConfidenceAdjuster.compute_staleness_hours(
            last_synced, reference
        )
        assert staleness == pytest.approx(2.0, abs=0.01)


class TestConfidencePenaltyComputation:
    """Test confidence penalty based on staleness."""

    def test_zero_staleness_zero_penalty(self) -> None:
        """Fresh data (0 staleness) should have zero penalty."""
        penalty = ConfidenceAdjuster.compute_confidence_penalty(0.0)
        assert penalty == 0.0

    def test_linear_penalty_before_48_hours(self) -> None:
        """Penalty should be linear (0.1% per hour) before 48 hours."""
        # 24 hours = 24 * 0.001 = 0.024 penalty
        penalty = ConfidenceAdjuster.compute_confidence_penalty(24.0)
        assert penalty == pytest.approx(0.024, abs=0.001)

    def test_penalty_at_48_hour_threshold(self) -> None:
        """At 48-hour threshold, penalty = 0.048."""
        penalty = ConfidenceAdjuster.compute_confidence_penalty(48.0)
        assert penalty == pytest.approx(0.048, abs=0.001)

    def test_penalty_escalates_after_seven_days(self) -> None:
        """Penalty escalates (0.5% per hour) after 7 days."""
        # 168 hours (7 days):
        # First 48h: 48 * 0.001 = 0.048
        # Next 120h (168-48): 120 * 0.001 = 0.120
        # Total = 0.168
        penalty = ConfidenceAdjuster.compute_confidence_penalty(168.0)
        assert penalty == pytest.approx(0.168, abs=0.001)

    def test_penalty_much_older_data_capped_at_1_0(self) -> None:
        """Very old data should have penalty capped at 1.0."""
        # 30 days = 720 hours
        penalty = ConfidenceAdjuster.compute_confidence_penalty(720.0)
        assert penalty <= 1.0

    def test_penalty_linear_between_48_and_168_hours(self) -> None:
        """Penalty grows linearly between 48 and 168 hours."""
        penalty_at_96 = ConfidenceAdjuster.compute_confidence_penalty(96.0)
        penalty_at_120 = ConfidenceAdjuster.compute_confidence_penalty(120.0)

        # Difference should be (120-96) * 0.001 = 0.024
        expected_diff = (120 - 96) * 0.001
        actual_diff = penalty_at_120 - penalty_at_96
        assert actual_diff == pytest.approx(expected_diff, abs=0.001)


class TestFreshnessMetadataCreation:
    """Test freshness metadata object creation."""

    def test_fresh_data_not_stale(self) -> None:
        """Data synced < 48h ago should not be marked stale."""
        now = datetime.now(UTC)
        one_day_ago = now - timedelta(hours=24)
        metadata = ConfidenceAdjuster.create_freshness_metadata(
            one_day_ago, "shopify", now
        )
        assert metadata.is_stale is False
        assert metadata.domain == "shopify"
        assert metadata.staleness_hours == pytest.approx(24.0, abs=0.01)

    def test_stale_data_marked_stale(self) -> None:
        """Data synced > 48h ago should be marked stale."""
        now = datetime.now(UTC)
        three_days_ago = now - timedelta(days=3)
        metadata = ConfidenceAdjuster.create_freshness_metadata(
            three_days_ago, "meta_ads", now
        )
        assert metadata.is_stale is True
        assert metadata.domain == "meta_ads"

    def test_critical_staleness_for_old_data(self) -> None:
        """Data > 7 days old should have significant penalty."""
        now = datetime.now(UTC)
        ten_days_ago = now - timedelta(days=10)
        metadata = ConfidenceAdjuster.create_freshness_metadata(
            ten_days_ago, "google_ads", now
        )
        assert metadata.is_stale is True
        assert metadata.confidence_penalty > 0.1  # Critical penalty


class TestEarlyWarningConfidenceAdjustment:
    """Test confidence adjustment for early warning results."""

    @pytest.fixture
    def sample_early_warning(self) -> EarlyWarningResult:
        """Create a sample early warning result for testing."""
        trajectory = TrajectoryMetrics(
            slope=-5.0,
            r_squared=0.95,
            periods_analyzed=5,
            current_value=80.0,
            baseline_value=90.0,
            prediction_window_days=4.0,
        )
        return EarlyWarningResult(
            is_warning=True,
            confidence=0.8,
            trajectory=trajectory,
            reasoning="ROAS declining rapidly",
            days_to_breach=4.0,
        )

    def test_fresh_data_no_confidence_reduction(
        self, sample_early_warning: EarlyWarningResult
    ) -> None:
        """Fresh data should not reduce confidence."""
        now = datetime.now(UTC)
        freshness = ConfidenceAdjuster.create_freshness_metadata(
            now, "shopify", now
        )
        adjusted = ConfidenceAdjuster.adjust_early_warning_result(
            sample_early_warning, [freshness], now
        )

        assert adjusted.confidence == pytest.approx(0.8, abs=0.01)
        assert adjusted.original_confidence == pytest.approx(0.8, abs=0.01)

    def test_stale_data_reduces_confidence(
        self, sample_early_warning: EarlyWarningResult
    ) -> None:
        """Stale data should reduce confidence proportionally."""
        now = datetime.now(UTC)
        three_days_ago = now - timedelta(days=3)
        freshness = ConfidenceAdjuster.create_freshness_metadata(
            three_days_ago, "shopify", now
        )

        adjusted = ConfidenceAdjuster.adjust_early_warning_result(
            sample_early_warning, [freshness], now
        )

        # Original was 0.8, with significant staleness penalty
        assert adjusted.confidence < 0.8
        assert adjusted.original_confidence == pytest.approx(0.8, abs=0.01)
        assert len(adjusted.freshness_metadata) == 1

    def test_multiple_sources_uses_worst_staleness(
        self, sample_early_warning: EarlyWarningResult
    ) -> None:
        """Multiple sources should use worst-case staleness penalty."""
        now = datetime.now(UTC)
        fresh = ConfidenceAdjuster.create_freshness_metadata(
            now, "shopify", now
        )
        stale = ConfidenceAdjuster.create_freshness_metadata(
            now - timedelta(days=5), "meta_ads", now
        )

        adjusted = ConfidenceAdjuster.adjust_early_warning_result(
            sample_early_warning, [fresh, stale], now
        )

        # Should use stale penalty (5 days)
        assert adjusted.confidence < sample_early_warning.confidence
        assert len(adjusted.freshness_metadata) == 2

    def test_no_freshness_data_returns_unchanged(
        self, sample_early_warning: EarlyWarningResult
    ) -> None:
        """Empty freshness list should return unchanged result."""
        adjusted = ConfidenceAdjuster.adjust_early_warning_result(
            sample_early_warning, []
        )

        assert adjusted.confidence == sample_early_warning.confidence
        assert adjusted.freshness_metadata == []


class TestOperationalAnomalyConfidenceAdjustment:
    """Test confidence adjustment for operational anomaly results."""

    @pytest.fixture
    def sample_anomaly_alert(self) -> OperationalAnomalyAlertResult:
        """Create a sample operational anomaly alert for testing."""
        return OperationalAnomalyAlertResult(
            is_anomalous_alert=True,
            confidence=0.85,
            z_score=2.5,
            reasoning="Return rate spike detected",
            domain="operations",
        )

    def test_fresh_data_preserves_anomaly_confidence(
        self, sample_anomaly_alert: OperationalAnomalyAlertResult
    ) -> None:
        """Fresh data should preserve anomaly confidence."""
        now = datetime.now(UTC)
        freshness = ConfidenceAdjuster.create_freshness_metadata(
            now, "shopify", now
        )

        adjusted = ConfidenceAdjuster.adjust_operational_anomaly_result(
            sample_anomaly_alert, [freshness], now
        )

        assert adjusted.confidence == pytest.approx(0.85, abs=0.01)
        assert adjusted.original_confidence == pytest.approx(0.85, abs=0.01)

    def test_stale_data_penalizes_anomaly_confidence(
        self, sample_anomaly_alert: OperationalAnomalyAlertResult
    ) -> None:
        """Stale data should reduce anomaly confidence."""
        now = datetime.now(UTC)
        old_sync = now - timedelta(days=4)
        freshness = ConfidenceAdjuster.create_freshness_metadata(
            old_sync, "inventory_system", now
        )

        adjusted = ConfidenceAdjuster.adjust_operational_anomaly_result(
            sample_anomaly_alert, [freshness], now
        )

        assert adjusted.confidence < sample_anomaly_alert.confidence
        assert adjusted.z_score == sample_anomaly_alert.z_score
        assert adjusted.domain == sample_anomaly_alert.domain


class TestConfidencePenaltyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_penalty_exactly_at_48_hour_boundary(self) -> None:
        """Penalty at exact 48-hour boundary should be computed correctly."""
        penalty = ConfidenceAdjuster.compute_confidence_penalty(48.0)
        assert penalty == pytest.approx(0.048, abs=0.001)

    def test_penalty_exactly_at_168_hour_boundary(self) -> None:
        """Penalty at exact 168-hour (7-day) boundary should be 0.168."""
        penalty = ConfidenceAdjuster.compute_confidence_penalty(168.0)
        assert penalty == pytest.approx(0.168, abs=0.001)

    def test_penalty_one_hour_after_168(self) -> None:
        """One hour past 7 days should include critical penalty rate."""
        penalty_at_168 = ConfidenceAdjuster.compute_confidence_penalty(168.0)
        penalty_at_169 = ConfidenceAdjuster.compute_confidence_penalty(169.0)

        # Extra penalty should be 0.005 (critical rate)
        expected_increase = 0.005
        actual_increase = penalty_at_169 - penalty_at_168
        assert actual_increase == pytest.approx(expected_increase, abs=0.001)

    def test_very_small_staleness_minimal_penalty(self) -> None:
        """Minutes of staleness should have minimal penalty."""
        penalty_10_min = ConfidenceAdjuster.compute_confidence_penalty(
            10.0 / 60.0
        )
        assert penalty_10_min < 0.001


class TestConfidenceAdjustmentPreservesOtherFields:
    """Ensure adjustment preserves non-confidence fields."""

    def test_early_warning_preserves_trajectory(self) -> None:
        """Confidence adjustment should preserve trajectory data."""
        trajectory = TrajectoryMetrics(
            slope=-3.0,
            r_squared=0.92,
            periods_analyzed=10,
            current_value=75.0,
            baseline_value=85.0,
            prediction_window_days=5.0,
        )
        result = EarlyWarningResult(
            is_warning=True,
            confidence=0.9,
            trajectory=trajectory,
            reasoning="Test",
            days_to_breach=5.0,
        )

        now = datetime.now(UTC)
        stale = ConfidenceAdjuster.create_freshness_metadata(
            now - timedelta(days=2), "shopify", now
        )
        adjusted = ConfidenceAdjuster.adjust_early_warning_result(
            result, [stale], now
        )

        assert adjusted.trajectory.slope == trajectory.slope
        assert adjusted.trajectory.r_squared == trajectory.r_squared
        assert adjusted.trajectory.periods_analyzed == 10
        assert adjusted.reasoning == "Test"

    def test_anomaly_preserves_z_score_and_domain(self) -> None:
        """Confidence adjustment should preserve z-score and domain."""
        result = OperationalAnomalyAlertResult(
            is_anomalous_alert=True,
            confidence=0.8,
            z_score=3.2,
            reasoning="Inventory spike",
            domain="inventory",
        )

        now = datetime.now(UTC)
        stale = ConfidenceAdjuster.create_freshness_metadata(
            now - timedelta(days=3), "warehouse", now
        )
        adjusted = ConfidenceAdjuster.adjust_operational_anomaly_result(
            result, [stale], now
        )

        assert adjusted.z_score == 3.2
        assert adjusted.domain == "inventory"
        assert adjusted.is_anomalous_alert is True
