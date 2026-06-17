"""FR-109 / T-074: Alert Generation Pipeline.

Combines threshold checks (T-072) with anomaly detection (T-073) to generate
alerts only when BOTH conditions are true:
1. Metric crosses configured threshold.
2. Metric behaves anomalously.

This reduces false positives and ensures alerts are actionable, real signals.
"""

from __future__ import annotations

from dataclasses import dataclass

from worker.app.simulation.anomaly_detector import AnomalyResult


@dataclass
class AlertDecision:
    """Structured decision on whether an alert should fire.

    Attributes:
        should_fire: True if both threshold crossed AND anomalous.
        confidence: 0.0–1.0, confidence in the alert decision.
        threshold_crossed: True if metric crossed the threshold boundary.
        is_anomalous: True if metric is anomalous.
        reasoning: Human-readable explanation for the decision.
        z_score: Standard deviations from baseline (from AnomalyResult).
        value: The current metric value.
        threshold_value: The configured threshold.
        comparison_operator: The operator ("<", ">", "<=", etc).
    """

    should_fire: bool
    confidence: float
    threshold_crossed: bool
    is_anomalous: bool
    reasoning: str
    z_score: float
    value: float
    threshold_value: float
    comparison_operator: str


class AlertGenerator:
    """Pipeline that combines threshold + anomaly checks for alert generation."""

    @staticmethod
    def check_threshold_crossed(
        value: float,
        threshold_value: float,
        comparison_operator: str,
    ) -> bool:
        """Check if value crosses the threshold boundary.

        Args:
            value: Current metric value.
            threshold_value: Configured threshold boundary.
            comparison_operator: One of "<", ">", "<=", ">=", "==", "!=".

        Returns:
            True if value satisfies the comparison with threshold.

        Raises:
            ValueError: If operator is invalid.
        """
        operators = {
            "<": lambda v, t: v < t,
            ">": lambda v, t: v > t,
            "<=": lambda v, t: v <= t,
            ">=": lambda v, t: v >= t,
            "==": lambda v, t: v == t,
            "!=": lambda v, t: v != t,
        }
        if comparison_operator not in operators:
            raise ValueError(
                f"Invalid operator: {comparison_operator}. "
                f"Must be one of: {', '.join(operators.keys())}"
            )
        return operators[comparison_operator](value, threshold_value)

    @staticmethod
    def generate_alert(
        value: float,
        threshold_value: float,
        comparison_operator: str,
        anomaly_result: AnomalyResult,
    ) -> AlertDecision:
        """Generate alert decision by combining threshold + anomaly checks.

        Alert fires (should_fire=True) only when BOTH conditions are true:
        1. Value crosses threshold (threshold_crossed=True)
        2. Value is anomalous (is_anomalous=True)

        Args:
            value: Current metric value.
            threshold_value: Configured threshold boundary.
            comparison_operator: Operator ("<", ">", "<=", ">=", "==", "!=").
            anomaly_result: AnomalyResult from anomaly detection (T-073).

        Returns:
            AlertDecision with should_fire, confidence, and reasoning.
        """
        threshold_crossed = AlertGenerator.check_threshold_crossed(
            value, threshold_value, comparison_operator
        )
        is_anomalous = anomaly_result.is_anomalous

        # Alert fires only when BOTH conditions are true
        should_fire = threshold_crossed and is_anomalous

        # Confidence is the product of both signals
        # If one is false, confidence reflects certainty that we should NOT alert
        if should_fire:
            # Both conditions true: confidence is anomaly confidence
            # (threshold is binary, so we use anomaly confidence)
            confidence = anomaly_result.confidence
        else:
            # At least one condition false: low confidence in firing
            # Reason: missing either threshold or anomaly signal
            confidence = 0.0

        reasoning = _get_alert_reasoning(
            value,
            threshold_value,
            comparison_operator,
            threshold_crossed,
            is_anomalous,
            anomaly_result.z_score,
            anomaly_result.baseline,
            anomaly_result.dispersion,
        )

        return AlertDecision(
            should_fire=should_fire,
            confidence=confidence,
            threshold_crossed=threshold_crossed,
            is_anomalous=is_anomalous,
            reasoning=reasoning,
            z_score=anomaly_result.z_score,
            value=value,
            threshold_value=threshold_value,
            comparison_operator=comparison_operator,
        )


def _get_alert_reasoning(
    value: float,
    threshold_value: float,
    comparison_operator: str,
    threshold_crossed: bool,
    is_anomalous: bool,
    z_score: float,
    baseline: float,
    dispersion: float,
) -> str:
    """Generate human-readable reasoning for alert decision."""
    if not threshold_crossed and not is_anomalous:
        return (
            f"Metric is healthy: value {value:.2f} did not cross "
            f"threshold ({comparison_operator} {threshold_value:.2f}) "
            f"and is not anomalous (z={z_score:.2f}, normal range "
            f"{baseline - 2 * dispersion:.2f}–{baseline + 2 * dispersion:.2f})."
        )
    if threshold_crossed and not is_anomalous:
        return (
            f"Value {value:.2f} crossed threshold "
            f"({comparison_operator} {threshold_value:.2f}), "
            f"but is not anomalous (z={z_score:.2f}, within normal range). "
            f"Likely temporary fluctuation; no alert triggered."
        )
    if not threshold_crossed and is_anomalous:
        return (
            f"Value {value:.2f} is anomalous (z={z_score:.2f}, "
            f"baseline {baseline:.2f} ± {dispersion:.2f}), "
            f"but did not cross threshold ({comparison_operator} "
            f"{threshold_value:.2f}). Anomaly within acceptable threshold range; "
            f"no alert triggered."
        )
    # both threshold_crossed and is_anomalous
    return (
        f"ALERT: Value {value:.2f} crossed threshold "
        f"({comparison_operator} {threshold_value:.2f}) "
        f"AND is anomalous (z={z_score:.2f}, baseline {baseline:.2f} ± "
        f"{dispersion:.2f}). Significant actionable signal detected."
    )
