"""Tests for alert generation pipeline (T-074).

Tests cover:
- Threshold crossing logic for all operators (<, >, <=, >=, ==, !=)
- Alert generation decision matrix (threshold × anomaly combinations)
- Confidence scoring
- Reasoning generation for all scenarios
- Edge cases (invalid operators, boundary values, zero values)
"""

from __future__ import annotations

import pytest
from worker.app.simulation.alert_generator import (
    AlertDecision,
    AlertGenerator,
)
from worker.app.simulation.anomaly_detector import AnomalyResult


class TestThresholdCrossing:
    """Test threshold crossing detection with all operators."""

    def test_less_than_operator_true(self) -> None:
        """Value < threshold should return True."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=1.5, threshold_value=2.0, comparison_operator="<"
        )
        assert crossed is True

    def test_less_than_operator_false(self) -> None:
        """Value >= threshold should return False."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.5, threshold_value=2.0, comparison_operator="<"
        )
        assert crossed is False

    def test_greater_than_operator_true(self) -> None:
        """Value > threshold should return True."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.5, threshold_value=2.0, comparison_operator=">"
        )
        assert crossed is True

    def test_greater_than_operator_false(self) -> None:
        """Value <= threshold should return False."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=1.5, threshold_value=2.0, comparison_operator=">"
        )
        assert crossed is False

    def test_less_than_equal_operator_at_boundary(self) -> None:
        """Value == threshold should return True for <=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.0, threshold_value=2.0, comparison_operator="<="
        )
        assert crossed is True

    def test_less_than_equal_operator_below(self) -> None:
        """Value < threshold should return True for <=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=1.5, threshold_value=2.0, comparison_operator="<="
        )
        assert crossed is True

    def test_less_than_equal_operator_above(self) -> None:
        """Value > threshold should return False for <=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.5, threshold_value=2.0, comparison_operator="<="
        )
        assert crossed is False

    def test_greater_than_equal_operator_at_boundary(self) -> None:
        """Value == threshold should return True for >=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.0, threshold_value=2.0, comparison_operator=">="
        )
        assert crossed is True

    def test_greater_than_equal_operator_above(self) -> None:
        """Value > threshold should return True for >=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.5, threshold_value=2.0, comparison_operator=">="
        )
        assert crossed is True

    def test_greater_than_equal_operator_below(self) -> None:
        """Value < threshold should return False for >=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=1.5, threshold_value=2.0, comparison_operator=">="
        )
        assert crossed is False

    def test_equals_operator_true(self) -> None:
        """Value == threshold should return True for ==."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.0, threshold_value=2.0, comparison_operator="=="
        )
        assert crossed is True

    def test_equals_operator_false(self) -> None:
        """Value != threshold should return False for ==."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.1, threshold_value=2.0, comparison_operator="=="
        )
        assert crossed is False

    def test_not_equals_operator_true(self) -> None:
        """Value != threshold should return True for !=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.1, threshold_value=2.0, comparison_operator="!="
        )
        assert crossed is True

    def test_not_equals_operator_false(self) -> None:
        """Value == threshold should return False for !=."""
        crossed = AlertGenerator.check_threshold_crossed(
            value=2.0, threshold_value=2.0, comparison_operator="!="
        )
        assert crossed is False

    def test_invalid_operator_raises_error(self) -> None:
        """Invalid operator should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid operator"):
            AlertGenerator.check_threshold_crossed(
                value=2.0, threshold_value=2.0, comparison_operator="???"
            )


class TestAlertGenerationMatrix:
    """Test alert generation decision matrix: threshold × anomaly
    combinations.
    """

    def _create_anomaly_result(
        self, is_anomalous: bool, confidence: float = 0.8
    ) -> AnomalyResult:
        """Helper to create AnomalyResult."""
        return AnomalyResult(
            is_anomalous=is_anomalous,
            confidence=confidence,
            z_score=3.5 if is_anomalous else 0.5,
            baseline=2.0,
            dispersion=0.5,
            reasoning="Test anomaly" if is_anomalous else "Normal",
        )

    def test_both_false_no_alert(self) -> None:
        """Neither threshold crossed nor anomalous → no alert."""
        anomaly = self._create_anomaly_result(is_anomalous=False)
        decision = AlertGenerator.generate_alert(
            value=2.1,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.confidence == 0.0
        assert decision.threshold_crossed is False
        assert decision.is_anomalous is False

    def test_threshold_true_anomaly_false_no_alert(self) -> None:
        """Threshold crossed but not anomalous → no alert."""
        anomaly = self._create_anomaly_result(is_anomalous=False)
        decision = AlertGenerator.generate_alert(
            value=0.5,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.confidence == 0.0
        assert decision.threshold_crossed is True
        assert decision.is_anomalous is False

    def test_threshold_false_anomaly_true_no_alert(self) -> None:
        """Anomalous but threshold not crossed → no alert."""
        anomaly = self._create_anomaly_result(is_anomalous=True, confidence=0.95)
        decision = AlertGenerator.generate_alert(
            value=1.8,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.confidence == 0.0
        assert decision.threshold_crossed is False
        assert decision.is_anomalous is True

    def test_both_true_alert_fires(self) -> None:
        """Both threshold crossed and anomalous → alert fires."""
        anomaly = self._create_anomaly_result(is_anomalous=True, confidence=0.92)
        decision = AlertGenerator.generate_alert(
            value=0.3,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.confidence == 0.92
        assert decision.threshold_crossed is True
        assert decision.is_anomalous is True

    def test_high_confidence_anomaly_with_both_true(self) -> None:
        """High-confidence anomaly + threshold → high-confidence alert."""
        anomaly = self._create_anomaly_result(is_anomalous=True, confidence=0.99)
        decision = AlertGenerator.generate_alert(
            value=0.1,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.confidence == 0.99

    def test_low_confidence_anomaly_with_both_true(self) -> None:
        """Low-confidence anomaly + threshold → low-confidence alert."""
        anomaly = self._create_anomaly_result(is_anomalous=True, confidence=0.45)
        decision = AlertGenerator.generate_alert(
            value=0.5,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.confidence == 0.45


class TestAlertDecisionStructure:
    """Test AlertDecision dataclass structure and fields."""

    def test_alert_decision_creation(self) -> None:
        """AlertDecision should populate all required fields."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.88,
            z_score=-3.2,
            baseline=2.5,
            dispersion=0.3,
            reasoning="High deviation",
        )
        decision = AlertGenerator.generate_alert(
            value=1.5,
            threshold_value=2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.confidence == 0.88
        assert decision.z_score == -3.2
        assert decision.value == 1.5
        assert decision.threshold_value == 2.0
        assert decision.comparison_operator == "<"
        assert isinstance(decision, AlertDecision)


class TestAlertReasoningGeneration:
    """Test reasoning messages for all decision scenarios."""

    def test_reasoning_both_false(self) -> None:
        """Reasoning when both threshold and anomaly are false."""
        anomaly = AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.3,
            baseline=2.5,
            dispersion=0.3,
            reasoning="Normal",
        )
        decision = AlertGenerator.generate_alert(
            value=2.6,
            threshold_value=2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert "healthy" in decision.reasoning.lower()
        assert "did not cross" in decision.reasoning.lower()
        assert "not anomalous" in decision.reasoning.lower()

    def test_reasoning_threshold_true_anomaly_false(self) -> None:
        """Reasoning when threshold crossed but not anomalous."""
        anomaly = AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.1,
            baseline=2.5,
            dispersion=0.3,
            reasoning="Normal",
        )
        decision = AlertGenerator.generate_alert(
            value=1.8,
            threshold_value=2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert "crossed threshold" in decision.reasoning.lower()
        assert "not anomalous" in decision.reasoning.lower()
        assert "fluctuation" in decision.reasoning.lower()

    def test_reasoning_threshold_false_anomaly_true(self) -> None:
        """Reasoning when anomalous but threshold not crossed."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.85,
            z_score=3.1,
            baseline=2.5,
            dispersion=0.3,
            reasoning="Anomalous",
        )
        decision = AlertGenerator.generate_alert(
            value=3.5,
            threshold_value=1.5,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert "anomalous" in decision.reasoning.lower()
        assert "did not cross threshold" in decision.reasoning.lower()

    def test_reasoning_both_true_alert_fires(self) -> None:
        """Reasoning when both conditions true → alert fires."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.91,
            z_score=-4.2,
            baseline=2.5,
            dispersion=0.3,
            reasoning="Anomalous",
        )
        decision = AlertGenerator.generate_alert(
            value=0.8,
            threshold_value=2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert "ALERT" in decision.reasoning
        assert "crossed threshold" in decision.reasoning.lower()
        assert "anomalous" in decision.reasoning.lower()
        assert "actionable" in decision.reasoning.lower()


class TestAlertWithGreaterThanOperator:
    """Test alert generation with > operator (anomaly above baseline)."""

    def test_greater_than_both_conditions_true(self) -> None:
        """Value > threshold AND anomalous → alert fires."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.87,
            z_score=3.5,
            baseline=2.0,
            dispersion=0.5,
            reasoning="Spike detected",
        )
        decision = AlertGenerator.generate_alert(
            value=3.8,
            threshold_value=3.5,
            comparison_operator=">",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.threshold_crossed is True
        assert decision.is_anomalous is True

    def test_greater_than_threshold_false_no_alert(self) -> None:
        """Value <= threshold with > operator → no alert."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.87,
            z_score=3.5,
            baseline=2.0,
            dispersion=0.5,
            reasoning="Spike",
        )
        decision = AlertGenerator.generate_alert(
            value=2.8,
            threshold_value=3.5,
            comparison_operator=">",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False


class TestAlertWithEqualsOperator:
    """Test alert generation with == operator (exact match scenarios)."""

    def test_equals_operator_both_true(self) -> None:
        """Value == threshold AND anomalous → alert fires."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.8,
            z_score=2.1,
            baseline=5.0,
            dispersion=1.5,
            reasoning="Exact anomaly",
        )
        decision = AlertGenerator.generate_alert(
            value=5.0,
            threshold_value=5.0,
            comparison_operator="==",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.threshold_crossed is True
        assert decision.is_anomalous is True

    def test_equals_operator_threshold_false(self) -> None:
        """Value != threshold with == operator → no alert."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.8,
            z_score=2.1,
            baseline=5.0,
            dispersion=1.5,
            reasoning="Anomaly",
        )
        decision = AlertGenerator.generate_alert(
            value=5.1,
            threshold_value=5.0,
            comparison_operator="==",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.threshold_crossed is False
        assert decision.is_anomalous is True


class TestEdgeCasesAlertGeneration:
    """Test edge cases: zero values, negative values, boundary conditions."""

    def test_zero_value_normal(self) -> None:
        """Value of 0 should be handled correctly."""
        anomaly = AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.5,
            reasoning="Zero is normal",
        )
        decision = AlertGenerator.generate_alert(
            value=0.0,
            threshold_value=1.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.value == 0.0

    def test_negative_values(self) -> None:
        """Negative values should be handled correctly."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.89,
            z_score=-2.8,
            baseline=-1.0,
            dispersion=0.3,
            reasoning="Negative anomaly",
        )
        decision = AlertGenerator.generate_alert(
            value=-2.5,
            threshold_value=-2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.value == -2.5

    def test_very_large_values(self) -> None:
        """Very large values should be handled correctly."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.94,
            z_score=3.9,
            baseline=1000000.0,
            dispersion=50000.0,
            reasoning="Large spike",
        )
        decision = AlertGenerator.generate_alert(
            value=2000000.0,
            threshold_value=1500000.0,
            comparison_operator=">",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True

    def test_very_small_values(self) -> None:
        """Very small values should be handled correctly."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.85,
            z_score=2.5,
            baseline=0.0001,
            dispersion=0.00005,
            reasoning="Small spike",
        )
        decision = AlertGenerator.generate_alert(
            value=0.00005,
            threshold_value=0.0002,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.threshold_crossed is True
        assert decision.is_anomalous is True

    def test_floating_point_precision(self) -> None:
        """Floating point values should be compared correctly."""
        anomaly = AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.1,
            baseline=1.4142135,
            dispersion=0.01,
            reasoning="Normal",
        )
        decision = AlertGenerator.generate_alert(
            value=1.41421,
            threshold_value=1.42,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.threshold_crossed is True  # 1.41421 < 1.42


class TestAlertDecisionConsistency:
    """Test internal consistency of AlertDecision across scenarios."""

    def test_confidence_zero_when_no_alert(self) -> None:
        """Confidence should always be 0 when should_fire is False."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.95,
            z_score=3.5,
            baseline=2.0,
            dispersion=0.3,
            reasoning="Very anomalous",
        )
        decision = AlertGenerator.generate_alert(
            value=3.5,
            threshold_value=1.0,
            comparison_operator="<",  # threshold not crossed
            anomaly_result=anomaly,
        )
        assert decision.should_fire is False
        assert decision.confidence == 0.0

    def test_confidence_nonzero_only_when_alert_fires(self) -> None:
        """Confidence > 0 only when should_fire is True."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.88,
            z_score=3.0,
            baseline=2.0,
            dispersion=0.3,
            reasoning="Anomalous",
        )
        decision = AlertGenerator.generate_alert(
            value=0.8,
            threshold_value=1.5,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is True
        assert decision.confidence > 0.0
        assert decision.confidence == 0.88

    def test_z_score_preserved_from_anomaly(self) -> None:
        """Z-score should be preserved from AnomalyResult."""
        z_score_value = 2.7
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.82,
            z_score=z_score_value,
            baseline=2.0,
            dispersion=0.3,
            reasoning="Test",
        )
        decision = AlertGenerator.generate_alert(
            value=0.9,
            threshold_value=1.5,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.z_score == z_score_value

    def test_all_fields_populated_when_alert_fires(self) -> None:
        """All AlertDecision fields should be populated."""
        anomaly = AnomalyResult(
            is_anomalous=True,
            confidence=0.91,
            z_score=-3.1,
            baseline=2.5,
            dispersion=0.4,
            reasoning="Test anomaly",
        )
        decision = AlertGenerator.generate_alert(
            value=1.3,
            threshold_value=2.0,
            comparison_operator="<",
            anomaly_result=anomaly,
        )
        assert decision.should_fire is not None
        assert decision.confidence is not None
        assert decision.threshold_crossed is not None
        assert decision.is_anomalous is not None
        assert decision.reasoning is not None
        assert decision.z_score is not None
        assert decision.value is not None
        assert decision.threshold_value is not None
        assert decision.comparison_operator is not None
