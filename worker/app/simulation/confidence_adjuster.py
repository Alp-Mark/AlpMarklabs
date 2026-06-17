"""FR-119 / T-077: Stale Data and Confidence Injection.

Injects data freshness context into alerts and adjusts confidence scores
based on how recent the source data is.

Staleness reduces confidence: older data = less certain conclusions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from worker.app.simulation.early_warning_detector import (
    DataFreshnessMetadata,
    EarlyWarningResult,
    OperationalAnomalyAlertResult,
)


class ConfidenceAdjuster:
    """Adjusts alert confidence based on data freshness."""

    # Staleness thresholds
    STALE_THRESHOLD_HOURS = 48  # Data > 48h old is marked stale
    CRITICAL_STALE_HOURS = 168  # Data > 7 days is critical (highly penalized)

    # Confidence penalty per hour of staleness
    PENALTY_PER_HOUR = 0.001  # 0.1% penalty per hour
    CRITICAL_PENALTY_PER_HOUR = 0.005  # 0.5% penalty per hour after 7 days

    @staticmethod
    def compute_staleness_hours(
        last_synced_at: datetime,
        reference_time: datetime | None = None,
    ) -> float:
        """Compute hours since last sync.

        Args:
            last_synced_at: Timestamp of last successful data sync.
            reference_time: Current time (default: UTC now). For testing.

        Returns:
            Hours since last_synced_at. Always non-negative.
        """
        if reference_time is None:
            reference_time = datetime.now(UTC)

        # Ensure both are timezone-aware
        if last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=UTC)
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=UTC)

        delta = reference_time - last_synced_at
        return max(0.0, delta.total_seconds() / 3600.0)

    @staticmethod
    def compute_confidence_penalty(
        staleness_hours: float,
    ) -> float:
        """Compute confidence penalty based on staleness.

        Linear penalty up to 48h, then exponential after 7 days.

        Args:
            staleness_hours: Hours since data was synced.

        Returns:
            Penalty factor (0.0-1.0). 1.0 = zero penalty, 0.0 = total loss.
        """
        if staleness_hours <= 0:
            return 0.0  # No penalty for fresh data

        if staleness_hours <= ConfidenceAdjuster.CRITICAL_STALE_HOURS:
            # Linear penalty for 0-168h (0.1% per hour)
            penalty = (
                staleness_hours * ConfidenceAdjuster.PENALTY_PER_HOUR
            )
        else:
            # Up to 168h: linear 0.1% per hour = 0.168
            penalty = (
                ConfidenceAdjuster.CRITICAL_STALE_HOURS
                * ConfidenceAdjuster.PENALTY_PER_HOUR
            )
            # Beyond 168h: critical rate 0.5% per hour
            excess_hours = (
                staleness_hours
                - ConfidenceAdjuster.CRITICAL_STALE_HOURS
            )
            penalty += (
                excess_hours
                * ConfidenceAdjuster.CRITICAL_PENALTY_PER_HOUR
            )

        return min(1.0, penalty)

    @staticmethod
    def adjust_early_warning_result(
        result: EarlyWarningResult,
        freshness_list: list[DataFreshnessMetadata],
        reference_time: datetime | None = None,
    ) -> EarlyWarningResult:
        """Adjust early warning confidence based on freshness.

        Stores original confidence, applies staleness penalty, and adds
        freshness metadata to result.

        Args:
            result: EarlyWarningResult to adjust.
            freshness_list: List of DataFreshnessMetadata for source data.
            reference_time: Current time for staleness calc (default: UTC now).

        Returns:
            Updated EarlyWarningResult with adjusted confidence.
        """
        if not freshness_list:
            return result

        # Store original confidence
        original_confidence = result.confidence

        # Compute worst-case staleness penalty from all sources
        max_penalty = 0.0
        for freshness in freshness_list:
            max_penalty = max(max_penalty, freshness.confidence_penalty)

        # Apply penalty: new_confidence = original * (1 - penalty)
        adjusted_confidence = max(
            0.0, original_confidence * (1.0 - max_penalty)
        )

        # Create new result with adjusted values
        return EarlyWarningResult(
            is_warning=result.is_warning,
            confidence=adjusted_confidence,
            trajectory=result.trajectory,
            reasoning=result.reasoning,
            days_to_breach=result.days_to_breach,
            freshness_metadata=freshness_list,
            original_confidence=original_confidence,
        )

    @staticmethod
    def adjust_operational_anomaly_result(
        result: OperationalAnomalyAlertResult,
        freshness_list: list[DataFreshnessMetadata],
        reference_time: datetime | None = None,
    ) -> OperationalAnomalyAlertResult:
        """Adjust operational anomaly confidence based on freshness.

        Stores original confidence, applies staleness penalty, and adds
        freshness metadata to result.

        Args:
            result: OperationalAnomalyAlertResult to adjust.
            freshness_list: List of DataFreshnessMetadata for source data.
            reference_time: Current time for staleness calc (default: UTC now).

        Returns:
            Updated OperationalAnomalyAlertResult with adjusted confidence.
        """
        if not freshness_list:
            return result

        # Store original confidence
        original_confidence = result.confidence

        # Compute worst-case staleness penalty from all sources
        max_penalty = 0.0
        for freshness in freshness_list:
            max_penalty = max(max_penalty, freshness.confidence_penalty)

        # Apply penalty: new_confidence = original * (1 - penalty)
        adjusted_confidence = max(
            0.0, original_confidence * (1.0 - max_penalty)
        )

        # Create new result with adjusted values
        return OperationalAnomalyAlertResult(
            is_anomalous_alert=result.is_anomalous_alert,
            confidence=adjusted_confidence,
            z_score=result.z_score,
            reasoning=result.reasoning,
            domain=result.domain,
            freshness_metadata=freshness_list,
            original_confidence=original_confidence,
        )

    @staticmethod
    def create_freshness_metadata(
        last_synced_at: datetime,
        domain: str,
        reference_time: datetime | None = None,
    ) -> DataFreshnessMetadata:
        """Create freshness metadata for a single data source.

        Args:
            last_synced_at: Timestamp of last successful sync.
            domain: Source domain (e.g., "shopify", "meta_ads").
            reference_time: Current time (default: UTC now). For testing.

        Returns:
            DataFreshnessMetadata with staleness and penalty computed.
        """
        staleness_hours = ConfidenceAdjuster.compute_staleness_hours(
            last_synced_at, reference_time
        )
        is_stale = (
            staleness_hours
            > ConfidenceAdjuster.STALE_THRESHOLD_HOURS
        )
        penalty = ConfidenceAdjuster.compute_confidence_penalty(
            staleness_hours
        )

        return DataFreshnessMetadata(
            last_synced_at=last_synced_at,
            domain=domain,
            is_stale=is_stale,
            staleness_hours=staleness_hours,
            confidence_penalty=penalty,
        )
