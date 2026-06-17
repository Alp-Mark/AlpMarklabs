"""Anomaly detection service for KPI metrics (T-073).

Detects when metric values deviate significantly from their historical baseline
and dispersion patterns. Returns anomaly confidence scores for use in alert
generation and recommendation filtering.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal


@dataclass
class AnomalyResult:
    """Result of anomaly detection for a single metric value."""

    is_anomalous: bool
    confidence: float  # 0.0–1.0, higher = more confident it's anomalous
    z_score: float  # standardized score: (value - baseline) / dispersion
    baseline: float
    dispersion: float
    reasoning: str


class AnomalyDetector:
    """Core anomaly detection engine."""

    # Minimum data requirements for reliable baseline calculation
    MIN_SAMPLES = 5
    MIN_DAYS = 90

    @staticmethod
    def validate_data_gate(
        data_points: list[float],
        calendar_window_days: int = 0,
    ) -> tuple[bool, str]:
        """Check if data meets minimum requirements for anomaly detection.

        Args:
            data_points: Historical data points (e.g., daily ROAS values).
            calendar_window_days: Number of days represented by the data.

        Returns:
            (is_valid, reason_if_invalid)
        """
        if len(data_points) < AnomalyDetector.MIN_SAMPLES:
            return (
                False,
                (
                    f"Insufficient samples: {len(data_points)} < "
                    f"{AnomalyDetector.MIN_SAMPLES}"
                ),
            )

        if calendar_window_days > 0 and calendar_window_days < AnomalyDetector.MIN_DAYS:
            return (
                False,
                (
                    f"Insufficient window: {calendar_window_days}d < "
                    f"{AnomalyDetector.MIN_DAYS}d"
                ),
            )

        return True, ""

    @staticmethod
    def compute_baseline(data_points: list[float]) -> float:
        """Compute baseline (mean) of historical data.

        Args:
            data_points: Historical values.

        Returns:
            Mean value.
        """
        if not data_points:
            return 0.0
        return statistics.mean(data_points)

    @staticmethod
    def compute_dispersion(
        data_points: list[float], baseline: float | None = None
    ) -> float:
        """Compute dispersion (standard deviation) of historical data.

        Args:
            data_points: Historical values.
            baseline: Optional pre-computed baseline. If not provided, computed.

        Returns:
            Standard deviation.
        """
        if len(data_points) < 2:
            return 0.0

        if baseline is None:
            baseline = AnomalyDetector.compute_baseline(data_points)

        try:
            return statistics.stdev(data_points)
        except statistics.StatisticsError:
            return 0.0

    @staticmethod
    def detect_anomaly(
        value: float,
        baseline: float,
        dispersion: float,
        domain: Literal[
            "kpi", "acquisition", "margin", "retention", "inventory", "operations"
        ] = "kpi",
    ) -> AnomalyResult:
        """Detect if a value is anomalous given baseline and dispersion.

        Uses z-score method: z = (value - baseline) / dispersion.
        Confidence threshold: |z| > 2.0 is considered anomalous (95% confidence).

        Args:
            value: The data point to evaluate.
            baseline: Mean of historical data.
            dispersion: Standard deviation of historical data.
            domain: Metric domain for domain-specific handler lookup.

        Returns:
            AnomalyResult with confidence, z-score, and reasoning.
        """
        # Handle edge case: no variation in historical data
        if dispersion <= 0:
            is_anomalous = value != baseline
            confidence = 1.0 if is_anomalous else 0.0
            reasoning = (
                "No historical variation; flagging non-baseline value"
                if is_anomalous
                else "Constant historical baseline; value matches"
            )
            return AnomalyResult(
                is_anomalous=is_anomalous,
                confidence=confidence,
                z_score=0.0,
                baseline=baseline,
                dispersion=dispersion,
                reasoning=reasoning,
            )

        # Compute z-score
        z_score = (value - baseline) / dispersion

        # Anomaly threshold: |z_score| > 2.0 (approximately 95% confidence interval)
        is_anomalous = abs(z_score) > 2.0

        # Confidence scales with z-score magnitude
        # At |z| = 2.0, confidence = 0.67
        # At |z| = 3.0, confidence = 1.0 (fully confident)
        confidence = min(abs(z_score) / 3.0, 1.0)

        # Domain-specific reasoning
        reasoning = _get_domain_reasoning(
            domain, z_score, baseline, value, is_anomalous
        )

        return AnomalyResult(
            is_anomalous=is_anomalous,
            confidence=confidence,
            z_score=z_score,
            baseline=baseline,
            dispersion=dispersion,
            reasoning=reasoning,
        )


def _get_domain_reasoning(
    domain: str,
    z_score: float,
    baseline: float,
    value: float,
    is_anomalous: bool,
) -> str:
    """Generate domain-specific reasoning for anomaly detection."""
    direction = "below" if z_score < 0 else "above"
    magnitude = f"{abs(z_score):.2f}σ"

    if domain == "kpi":
        metric = "KPI"
    elif domain == "acquisition":
        metric = "acquisition metric"
    elif domain == "margin":
        metric = "margin"
    elif domain == "retention":
        metric = "retention metric"
    elif domain == "inventory":
        metric = "inventory metric"
    elif domain == "operations":
        metric = "operational metric"
    else:
        metric = "metric"

    if not is_anomalous:
        return (
            f"{metric.title()} within normal range: {value:.2f} "
            f"(baseline: {baseline:.2f})"
        )

    return (
        f"{metric.title()} anomaly detected: {value:.2f} is {direction} "
        f"baseline ({baseline:.2f}) by {magnitude}"
    )


def detect_kpi_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in executive KPI metrics (margin %, ROAS, CAC payback).

    Args:
        value: Current KPI value to evaluate.
        data_points: Historical KPI values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=f"Insufficient data for KPI anomaly detection: {reason}",
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(value, baseline, dispersion, domain="kpi")


def detect_acquisition_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in acquisition metrics (CAC, ROAS by channel).

    Args:
        value: Current acquisition metric value to evaluate.
        data_points: Historical acquisition metric values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=(
                f"Insufficient data for acquisition anomaly detection: {reason}"
            ),
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(
        value, baseline, dispersion, domain="acquisition"
    )


def detect_margin_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in contribution margin metrics.

    Args:
        value: Current margin value to evaluate.
        data_points: Historical margin values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=f"Insufficient data for margin anomaly detection: {reason}",
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(value, baseline, dispersion, domain="margin")


def detect_retention_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in retention metrics (repeat purchase rate, churn rate).

    Args:
        value: Current retention metric value to evaluate.
        data_points: Historical retention metric values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=(
                f"Insufficient data for retention anomaly detection: {reason}"
            ),
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(
        value, baseline, dispersion, domain="retention"
    )


def detect_inventory_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in inventory metrics (stockout risk, inventory velocity).

    Args:
        value: Current inventory metric value to evaluate.
        data_points: Historical inventory metric values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=(
                f"Insufficient data for inventory anomaly detection: {reason}"
            ),
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(
        value, baseline, dispersion, domain="inventory"
    )


def detect_operations_anomaly(
    value: float,
    data_points: list[float],
    calendar_window_days: int = 0,
) -> AnomalyResult:
    """Detect anomalies in operational metrics (return rate, shipping cost).

    Args:
        value: Current operational metric value to evaluate.
        data_points: Historical operational metric values.
        calendar_window_days: Time window covered by data.

    Returns:
        AnomalyResult with anomaly detection outcome.
    """
    is_valid, reason = AnomalyDetector.validate_data_gate(
        data_points, calendar_window_days
    )
    if not is_valid:
        return AnomalyResult(
            is_anomalous=False,
            confidence=0.0,
            z_score=0.0,
            baseline=0.0,
            dispersion=0.0,
            reasoning=(
                f"Insufficient data for operations anomaly detection: {reason}"
            ),
        )

    baseline = AnomalyDetector.compute_baseline(data_points)
    dispersion = AnomalyDetector.compute_dispersion(data_points, baseline)

    return AnomalyDetector.detect_anomaly(
        value, baseline, dispersion, domain="operations"
    )
