"""FR-076 / T-062: Implementation gap detection scanning.

Scans all approved recommendations and sets gap flags based on how long
they've been in approved status.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Recommendation
from backend.app.recommendations.lifecycle import RecommendationStatus

# Thresholds for implementation gap detection
IMPLEMENTATION_GAP_WARNING_DAYS = 14
IMPLEMENTATION_GAP_ESCALATION_DAYS = 30


def scan_implementation_gaps(db: Session, *, today: date | None = None) -> int:
    """Scan all approved recommendations and update gap flags.

    Sets implementation_gap_flag to:
        - "warning" if approved for 14-30 days
        - "escalated" if approved for >30 days
        - null if approved for <14 days

    Returns the count of recommendations updated.
    """
    check_date = today or date.today()

    approved_recs = list(
        db.scalars(
            select(Recommendation).where(
                Recommendation.status == RecommendationStatus.APPROVED.value,
                Recommendation.approved_at.is_not(None),
            )
        )
    )

    updated_count = 0
    for rec in approved_recs:
        if rec.approved_at is None:
            continue

        # Calculate days since approved (truncate at midnight for date-based comparison)
        approved_date = rec.approved_at.date() if rec.approved_at else None
        if approved_date is None:
            continue

        days_since_approved = (check_date - approved_date).days

        # Determine new flag value based on days elapsed
        if days_since_approved < IMPLEMENTATION_GAP_WARNING_DAYS:
            new_flag = None
        elif days_since_approved < IMPLEMENTATION_GAP_ESCALATION_DAYS:
            new_flag = "warning"
        else:
            new_flag = "escalated"

        # Only update if flag changed
        if rec.implementation_gap_flag != new_flag:
            rec.implementation_gap_flag = new_flag
            updated_count += 1

    if updated_count > 0:
        db.commit()

    return updated_count
