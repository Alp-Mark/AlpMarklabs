"""Tests for anomaly detection service (T-073).

Tests cover baseline/dispersion calculation, anomaly detection logic,
and domain-specific handlers with edge cases.
"""

from __future__ import annotations

import pytest
from worker.app.simulation.anomaly_detector import (
    AnomalyDetector,
    AnomalyResult,
    detect_acquisition_anomaly,
    detect_inventory_anomaly,
    detect_kpi_anomaly,
    detect_margin_anomaly,
    detect_operations_anomaly,
    detect_retention_anomaly,
)


class TestAnomalyDetectorBaseline:
    """Test baseline (mean) calculation."""

    def test_compute_baseline_simple(self) -> None:
        """Compute baseline from simple dataset."""
        data = [2.0, 3.0, 4.0, 5.0, 6.0]
        baseline = AnomalyDetector.compute_baseline(data)
        assert baseline == 4.0

    def test_compute_baseline_single_value(self) -> None:
        """Baseline of single value is that value."""
        data = [5.0]
        baseline = AnomalyDetector.compute_baseline(data)
        assert baseline == 5.0

    def test_compute_baseline_empty(self) -> None:
        """Baseline of empty list is 0.0."""
        data: list[float] = []
        baseline = AnomalyDetector.compute_baseline(data)
        assert baseline == 0.0

    def test_compute_baseline_negative_values(self) -> None:
        """Baseline handles negative values."""
        data = [-5.0, -3.0, -1.0, 1.0, 3.0]
        baseline = AnomalyDetector.compute_baseline(data)
        assert baseline == -1.0


class TestAnomalyDetectorDispersion:
    """Test dispersion (standard deviation) calculation."""

    def test_compute_dispersion_simple(self) -> None:
        """Compute dispersion from simple dataset."""
        data = [2.0, 4.0, 6.0]
        baseline = AnomalyDetector.compute_baseline(data)
        dispersion = AnomalyDetector.compute_dispersion(data, baseline)
        assert abs(dispersion - 2.0) < 0.01  # stdev of [2,4,6] ≈ 2.0

    def test_compute_dispersion_no_variation(self) -> None:
        """Dispersion of constant values is 0.0."""
        data = [5.0, 5.0, 5.0]
        baseline = AnomalyDetector.compute_baseline(data)
        dispersion = AnomalyDetector.compute_dispersion(data, baseline)
        assert dispersion == 0.0

    def test_compute_dispersion_single_value(self) -> None:
        """Dispersion of single value is 0.0."""
        data = [5.0]
        dispersion = AnomalyDetector.compute_dispersion(data)
        assert dispersion == 0.0

    def test_compute_dispersion_empty(self) -> None:
        """Dispersion of empty list is 0.0."""
        data: list[float] = []
        dispersion = AnomalyDetector.compute_dispersion(data)
        assert dispersion == 0.0

    def test_compute_dispersion_without_baseline(self) -> None:
        """Dispersion can be computed without pre-computed baseline."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        dispersion = AnomalyDetector.compute_dispersion(data)
        assert abs(dispersion - 1.58) < 0.1  # stdev ≈ 1.58


class TestAnomalyDetectorDataGate:
    """Test minimum data requirements validation."""

    def test_validate_data_gate_sufficient_samples_no_window(self) -> None:
        """Sufficient samples pass gate without window requirement."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        is_valid, reason = AnomalyDetector.validate_data_gate(
            data, calendar_window_days=0
        )
        assert is_valid is True
        assert reason == ""

    def test_validate_data_gate_insufficient_samples(self) -> None:
        """Insufficient samples fail gate."""
        data = [1.0, 2.0]
        is_valid, reason = AnomalyDetector.validate_data_gate(data)
        assert is_valid is False
        assert "Insufficient samples" in reason

    def test_validate_data_gate_sufficient_window(self) -> None:
        """Sufficient calendar window passes gate."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        is_valid, reason = AnomalyDetector.validate_data_gate(
            data, calendar_window_days=90
        )
        assert is_valid is True

    def test_validate_data_gate_insufficient_window(self) -> None:
        """Insufficient calendar window fails gate."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        is_valid, reason = AnomalyDetector.validate_data_gate(
            data, calendar_window_days=60
        )
        assert is_valid is False
        assert "Insufficient window" in reason


class TestAnomalyDetection:
    """Test anomaly detection logic."""

    def test_detect_anomaly_within_normal_range(self) -> None:
        """Value within normal range is not flagged as anomalous."""
        baseline = 2.5
        dispersion = 0.5
        value = 2.6  # Just above baseline, well within 2σ

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is False
        assert result.confidence < 0.5
        assert result.z_score == pytest.approx(0.2)

    def test_detect_anomaly_outside_normal_range(self) -> None:
        """Value outside 2σ range is flagged as anomalous."""
        baseline = 2.5
        dispersion = 0.5
        value = 0.8  # Significantly below baseline (3.4σ below)

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.confidence > 0.9
        assert result.z_score == pytest.approx(-3.4)

    def test_detect_anomaly_at_threshold(self) -> None:
        """Value exactly at 2σ boundary."""
        baseline = 2.5
        dispersion = 0.5
        value = 3.5  # Exactly 2σ above baseline

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        # At |z| = 2.0, is_anomalous = False (threshold is > 2.0, not >= 2.0)
        assert result.is_anomalous is False
        assert result.z_score == pytest.approx(2.0)

    def test_detect_anomaly_no_variation(self) -> None:
        """With no historical variation, any non-baseline value is anomalous."""
        baseline = 5.0
        dispersion = 0.0
        value = 5.0

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is False
        assert result.confidence == 0.0

    def test_detect_anomaly_no_variation_different_value(self) -> None:
        """With no historical variation, different value is anomalous."""
        baseline = 5.0
        dispersion = 0.0
        value = 6.0

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.confidence == 1.0

    def test_detect_anomaly_negative_z_score(self) -> None:
        """Anomaly detection works with negative z-scores."""
        baseline = 100.0
        dispersion = 10.0
        value = 75.0  # 2.5σ below baseline

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.z_score == pytest.approx(-2.5)
        assert result.confidence == pytest.approx(0.833, rel=0.01)


class TestDomainHandlers:
    """Test domain-specific anomaly detection handlers."""

    @staticmethod
    def create_normal_data(
        baseline: float, dispersion: float, count: int = 90
    ) -> list[float]:
        """Create synthetic normal data around baseline with given dispersion."""
        import random

        random.seed(42)
        return [baseline + random.gauss(0, dispersion) for _ in range(count)]

    def test_detect_kpi_anomaly_normal(self) -> None:
        """KPI anomaly handler detects normal values."""
        baseline = 2.5
        dispersion = 0.3
        data = self.create_normal_data(baseline, dispersion)

        result = detect_kpi_anomaly(2.6, data, calendar_window_days=90)

        assert result.is_anomalous is False
        assert result.confidence < 0.5

    def test_detect_kpi_anomaly_anomalous(self) -> None:
        """KPI anomaly handler detects anomalous values."""
        baseline = 2.5
        dispersion = 0.3
        data = self.create_normal_data(baseline, dispersion)

        result = detect_kpi_anomaly(0.5, data, calendar_window_days=90)

        assert result.is_anomalous is True
        assert result.confidence > 0.8

    def test_detect_kpi_anomaly_insufficient_data(self) -> None:
        """KPI handler returns zero confidence when data insufficient."""
        data = [1.0, 2.0]  # Only 2 samples

        result = detect_kpi_anomaly(1.5, data, calendar_window_days=30)

        assert result.is_anomalous is False
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasoning

    def test_detect_acquisition_anomaly_normal(self) -> None:
        """Acquisition anomaly handler detects normal values."""
        baseline = 15.0
        dispersion = 2.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_acquisition_anomaly(15.5, data, calendar_window_days=90)

        assert result.is_anomalous is False

    def test_detect_margin_anomaly_normal(self) -> None:
        """Margin anomaly handler detects normal values."""
        baseline = 40.0
        dispersion = 3.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_margin_anomaly(40.5, data, calendar_window_days=90)

        assert result.is_anomalous is False

    def test_detect_retention_anomaly_normal(self) -> None:
        """Retention anomaly handler detects normal values."""
        baseline = 25.0
        dispersion = 2.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_retention_anomaly(25.3, data, calendar_window_days=90)

        assert result.is_anomalous is False

    def test_detect_inventory_anomaly_normal(self) -> None:
        """Inventory anomaly handler detects normal values."""
        baseline = 500.0
        dispersion = 50.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_inventory_anomaly(510.0, data, calendar_window_days=90)

        assert result.is_anomalous is False

    def test_detect_operations_anomaly_normal(self) -> None:
        """Operations anomaly handler detects normal values."""
        baseline = 8.5
        dispersion = 1.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_operations_anomaly(8.8, data, calendar_window_days=90)

        assert result.is_anomalous is False

    def test_detect_operations_anomaly_anomalous(self) -> None:
        """Operations anomaly handler detects anomalous values."""
        baseline = 8.5
        dispersion = 1.0
        data = self.create_normal_data(baseline, dispersion)

        result = detect_operations_anomaly(2.0, data, calendar_window_days=90)

        assert result.is_anomalous is True
        assert result.confidence > 0.8


class TestAnomalyResultDataclass:
    """Test AnomalyResult dataclass."""

    def test_anomaly_result_creation(self) -> None:
        """AnomalyResult can be created and accessed."""
        result = AnomalyResult(
            is_anomalous=True,
            confidence=0.95,
            z_score=2.5,
            baseline=10.0,
            dispersion=1.0,
            reasoning="Test anomaly",
        )

        assert result.is_anomalous is True
        assert result.confidence == 0.95
        assert result.z_score == 2.5
        assert result.baseline == 10.0
        assert result.dispersion == 1.0
        assert result.reasoning == "Test anomaly"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_dispersion(self) -> None:
        """Anomaly detection with very small but non-zero dispersion."""
        baseline = 100.0
        dispersion = 0.001
        value = 100.003  # 3σ above

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.z_score == pytest.approx(3.0)

    def test_very_large_values(self) -> None:
        """Anomaly detection with large magnitude values."""
        baseline = 1_000_000.0
        dispersion = 100_000.0
        value = 900_000.0  # 1σ below

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is False
        assert result.z_score == pytest.approx(-1.0)

    def test_negative_values(self) -> None:
        """Anomaly detection with negative values."""
        baseline = -50.0
        dispersion = 5.0
        value = -30.0  # 4σ above (more positive)

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.z_score == pytest.approx(4.0)

    def test_zero_value(self) -> None:
        """Anomaly detection with zero value."""
        baseline = 10.0
        dispersion = 2.0
        value = 0.0

        result = AnomalyDetector.detect_anomaly(value, baseline, dispersion)

        assert result.is_anomalous is True
        assert result.z_score == pytest.approx(-5.0)
