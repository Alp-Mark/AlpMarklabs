"""FR-074 / T-060: Recommendation suppression service.

Tracks rejection counts per (tenant_id, rule_id).  When the count reaches
the configurable threshold (default 3), a suppression window opens and new
recommendations for that rule are blocked for suppression_window_days
(default 30) days.

State transitions:
    counting  → suppressed   (rejection_count reaches threshold)
    suppressed → expired     (suppressed_until < today, natural expiry)
    suppressed → overridden  (Brand Admin lifts the suppression)
    expired / overridden → counting (next rejection resets count to 0, then 1)

No DB commits are performed here — callers are responsible.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import RecommendationSuppressionState


def is_suppressed(
    db: Session,
    tenant_id: uuid.UUID,
    rule_id: str,
    *,
    today: date | None = None,
) -> bool:
    """Return True if rule_id is currently under an active suppression window."""
    check_date = today or date.today()
    row = db.scalar(
        select(RecommendationSuppressionState).where(
            RecommendationSuppressionState.tenant_id == tenant_id,
            RecommendationSuppressionState.rule_id == rule_id,
        )
    )
    if row is None or row.suppressed_until is None:
        return False
    if row.is_overridden:
        return False
    return row.suppressed_until >= check_date


def record_rejection(
    db: Session,
    tenant_id: uuid.UUID,
    rule_id: str,
    *,
    today: date | None = None,
) -> RecommendationSuppressionState:
    """Record one rejection for (tenant_id, rule_id) and open a suppression
    window if the threshold is reached.

    Rules:
    - Creates the state row on first rejection.
    - If a previous suppression window expired naturally, resets count to 0.
    - If the previous suppression was overridden by an admin, resets count to 0.
    - While currently suppressed (not overridden), further rejections are
      ignored (the recommendation should not have been created, but we are
      defensive here).
    - When rejection_count reaches rejection_threshold, opens suppressed_until
      window and resets rejection_count to 0 so the next cycle starts fresh.
    """
    check_date = today or date.today()

    row = db.scalar(
        select(RecommendationSuppressionState).where(
            RecommendationSuppressionState.tenant_id == tenant_id,
            RecommendationSuppressionState.rule_id == rule_id,
        )
    )

    if row is None:
        row = RecommendationSuppressionState(
            tenant_id=tenant_id,
            rule_id=rule_id,
            rejection_count=0,
        )
        db.add(row)
        db.flush()

    # Natural expiry: window closed on its own — start a fresh count
    if (
        row.suppressed_until is not None
        and row.suppressed_until < check_date
        and not row.is_overridden
    ):
        row.rejection_count = 0
        row.suppressed_until = None

    # Currently suppressed (and not overridden) — nothing more to count
    if (
        row.suppressed_until is not None
        and row.suppressed_until >= check_date
        and not row.is_overridden
    ):
        return row

    # Admin previously lifted the suppression — start a fresh count
    if row.is_overridden:
        row.rejection_count = 0
        row.is_overridden = False
        row.suppressed_until = None

    row.rejection_count += 1

    if row.rejection_count >= row.rejection_threshold:
        row.suppressed_until = check_date + timedelta(days=row.suppression_window_days)
        row.rejection_count = 0  # reset so the next cycle after expiry starts fresh

    return row


def lift_suppression(
    db: Session,
    tenant_id: uuid.UUID,
    rule_id: str,
    *,
    today: date | None = None,
) -> RecommendationSuppressionState | None:
    """Override an active suppression window.

    Marks is_overridden=True and resets rejection_count to 0 so that
    subsequent rejections start a fresh count from zero.

    Returns the updated row if an active suppression was found, None if there
    was nothing to lift (no row, no active window, already expired, already
    overridden).
    """
    check_date = today or date.today()

    row = db.scalar(
        select(RecommendationSuppressionState).where(
            RecommendationSuppressionState.tenant_id == tenant_id,
            RecommendationSuppressionState.rule_id == rule_id,
        )
    )

    if (
        row is None
        or row.suppressed_until is None
        or row.suppressed_until < check_date
        or row.is_overridden
    ):
        return None

    row.is_overridden = True
    row.rejection_count = 0
    return row
