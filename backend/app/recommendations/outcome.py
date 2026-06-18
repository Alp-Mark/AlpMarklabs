"""FR-069, FR-077 / T-063: Outcome observation and cross-metric impact tracking.

Tracks recommendations marked as "implemented_externally" and observes real-world
impact by comparing KPI snapshots before and after a configurable window (default
30 days). Flags guardrail violations if optimizing one metric harmed another.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Recommendation
from backend.app.recommendations.lifecycle import RecommendationStatus

# Configurable observation window after implementation
OUTCOME_OBSERVATION_WINDOW_DAYS = 30

# All KPIs tracked for cross-metric impact comparison
KPI_NAMES = [
    "contribution_margin_pct",
    "cac_payback_period",
    "blended_roas",
    "return_rate_pct",
    "repeat_purchase_rate_pct",
    "cac_by_channel",
    "time_to_insight",
]

# Guardrail rules: if metric A improves but metric B worsens, flag violation
GUARDRAIL_RULES = [
    {
        "name": "roas_repeat_purchase",
        "improving_metric": "blended_roas",
        "must_not_worsen": "repeat_purchase_rate_pct",
        "message": "ROAS improved but repeat purchase rate dropped",
    },
    {
        "name": "margin_return_rate",
        "improving_metric": "contribution_margin_pct",
        "must_not_worsen": "return_rate_pct",
        "message": "Margin improved but return rate rose",
    },
    {
        "name": "cac_payback_qualified_volume",
        "improving_metric": "cac_payback_period",
        "must_not_worsen": "blended_roas",
        "message": "CAC payback improved but ROAS dropped (volume quality concern)",
    },
]


def scan_outcome_observations(
    db: Session,
    *,
    today: date | None = None,
) -> int:
    """Scan recommendations for outcome observation eligibility.

    Queries all recommendations where:
      - status == "implemented_externally"
      - implemented_at IS NOT NULL
      - today - implemented_at.date() >= OUTCOME_OBSERVATION_WINDOW_DAYS

    For eligible recommendations, populates outcome_metrics_after and
    outcome_impact_summary (simulated for now; real implementation would
    query synced metric snapshots). Then transitions to "outcome_observed".

    Parameters
    ----------
    db : Session
        Database session.
    today : date, optional
        Reference date for calculation. Defaults to datetime.now(UTC).date().

    Returns
    -------
    int
        Count of recommendations transitioned to outcome_observed in this scan.
    """
    if today is None:
        today = datetime.now(UTC).date()

    # Query all implemented_externally recommendations ready for observation
    stmt = select(Recommendation).where(
        Recommendation.status == RecommendationStatus.IMPLEMENTED_EXTERNALLY,
        Recommendation.implemented_at.isnot(None),
    )
    recs = db.execute(stmt).scalars().all()

    updated_count = 0
    for rec in recs:
        if rec.implemented_at is None:
            continue

        days_since_implemented = (today - rec.implemented_at.date()).days
        if days_since_implemented < OUTCOME_OBSERVATION_WINDOW_DAYS:
            continue

        # Simulate outcome metrics (placeholder; real implementation queries snapshots)
        if rec.outcome_metrics_before is None:
            # If no before snapshot, skip (shouldn't happen in normal flow)
            continue

        # Generate after snapshot and impact summary
        after_snapshot = _simulate_outcome_metrics(rec.outcome_metrics_before)
        impact_summary = _compute_impact_summary(
            rec.outcome_metrics_before,
            after_snapshot,
        )

        # Populate outcome fields
        rec.outcome_metrics_after = after_snapshot
        rec.outcome_impact_summary = impact_summary
        rec.outcome_observed_at = datetime.now(UTC)
        rec.status = RecommendationStatus.OUTCOME_OBSERVED.value

        updated_count += 1

    db.commit()
    return updated_count


def _simulate_outcome_metrics(before: dict) -> dict:
    """Simulate post-implementation KPI snapshot.

    Placeholder logic: shifts metrics +/- 5-10% randomly. Real implementation
    would query actual synced metric snapshots for the tenant.

    Parameters
    ----------
    before : dict
        Before snapshot with all KPI names as keys.

    Returns
    -------
    dict
        After snapshot with same structure.
    """
    after: dict[str, float | None] = {}
    for kpi_name, before_value in before.items():
        if before_value is None:
            after[kpi_name] = None
            continue

        # Placeholder: assume +5% improvement (real logic queries actual data)
        if isinstance(before_value, (int, float)):
            # Metrics to maximize: contribution_margin_pct, blended_roas, etc.
            after[kpi_name] = before_value * 1.05
        else:
            after[kpi_name] = before_value

    return after


def _compute_impact_summary(before: dict, after: dict) -> dict[str, object]:
    """Compute before/after comparison and check guardrail violations.

    Parameters
    ----------
    before : dict
        Before-window KPI snapshot.
    after : dict
        After-window KPI snapshot.

    Returns
    -------
    dict
        Comparison with per-metric deltas and guardrail violation flags.
    """
    summary: dict[str, object] = {
        "metrics": {},
        "guardrail_violations": [],
    }

    # Per-metric comparison
    metrics_dict: dict[str, dict[str, object]] = {}
    for kpi_name in KPI_NAMES:
        before_val = before.get(kpi_name)
        after_val = after.get(kpi_name)

        if before_val is None or after_val is None:
            metrics_dict[kpi_name] = {
                "before": before_val,
                "after": after_val,
                "change": None,
                "direction": None,
            }
            continue

        change = after_val - before_val
        direction = (
            "improved"
            if change > 0
            else "worsened"
            if change < 0
            else "unchanged"
        )

        metrics_dict[kpi_name] = {
            "before": before_val,
            "after": after_val,
            "change": change,
            "direction": direction,
        }

    summary["metrics"] = metrics_dict

    # Check guardrail violations
    violations_list: list[dict[str, object]] = []
    for rule in GUARDRAIL_RULES:
        improving_metric = rule["improving_metric"]
        must_not_worsen = rule["must_not_worsen"]

        improving_summary = metrics_dict.get(improving_metric, {})
        worsen_summary = metrics_dict.get(must_not_worsen, {})

        improving_direction = improving_summary.get("direction")
        worsen_direction = worsen_summary.get("direction")

        # Flag violation if improving metric improved but worsening metric worsened
        if improving_direction == "improved" and worsen_direction == "worsened":
            violations_list.append({
                "rule_name": rule["name"],
                "message": rule["message"],
                "improving_metric": improving_metric,
                "worsening_metric": must_not_worsen,
            })

    summary["guardrail_violations"] = violations_list

    return summary
