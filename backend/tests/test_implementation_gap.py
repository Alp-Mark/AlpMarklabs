"""Test implementation gap detection (FR-076 / T-062)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from backend.app.db.base import Base
from backend.app.db.models import (
    Recommendation,
    Tenant,
)
from backend.app.recommendations.gap import scan_implementation_gaps
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Get a direct database session for test setup."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    session = local_session()
    yield session
    session.close()
    engine.dispose()


def _seed_recommendation(
    db: Session,
    tenant_id: uuid.UUID,
    rule_id: str = "rule_001",
    status: str = "approved",
    approved_at: datetime | None = None,
    snapshot_date: date = date(2026, 6, 2),
) -> Recommendation:
    """Create a test recommendation."""
    rec = Recommendation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        rule_id=rule_id,
        domain="acquisition",
        snapshot_date=snapshot_date,
        affected_area="channel_spend",
        signal_summary="Test signal",
        suggested_action="Test action",
        estimated_impact=0.15,
        confidence_level="high",
        data_freshness_context="Fresh data",
        status=status,
        priority=1,
        impact_score=0.8,
        evidence={},
        approved_at=approved_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _create_test_tenant(db: Session) -> Tenant:
    """Create a test tenant in the given session."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-{uuid.uuid4().hex[:8]}",
        base_currency="USD",
    )
    db.add(tenant)
    db.commit()
    return tenant


class TestImplementationGapScan:
    """Test the gap detection logic."""

    def test_scan_no_approved_recs(self, db: Session) -> None:
        """Scan returns 0 when no approved recommendations exist."""
        tenant = _create_test_tenant(db)

        # Create a rejected recommendation
        _seed_recommendation(
            db, tenant.id, status="rejected", snapshot_date=date(2026, 6, 1)
        )

        result = scan_implementation_gaps(db)
        assert result == 0

    def test_scan_approved_without_timestamp(self, db: Session) -> None:
        """Scan handles approved recs without approved_at timestamp."""
        tenant = _create_test_tenant(db)

        # Create approved rec without approved_at
        _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=None,
            snapshot_date=date(2026, 6, 1),
        )

        result = scan_implementation_gaps(db)
        assert result == 0

    def test_scan_new_approved_no_flag(self, db: Session) -> None:
        """Approved <14 days ago: flag should be None."""
        tenant = _create_test_tenant(db)
        today = date(2026, 6, 15)
        approved_at = datetime.combine(date(2026, 6, 10), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 10),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag is None

    def test_scan_13_days_no_flag(self, db: Session) -> None:
        """Approved 13 days ago: flag should be None."""
        tenant = _create_test_tenant(db)
        today = date(2026, 6, 15)
        approved_at = datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 2),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag is None

    def test_scan_14_days_warning(self, db: Session) -> None:
        """Approved exactly 14 days ago: flag should be 'warning'."""
        tenant = _create_test_tenant(db)
        today = date(2026, 6, 16)
        approved_at = datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 2),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "warning"

    def test_scan_29_days_warning(self, db: Session) -> None:
        """Approved 29 days ago: flag should be 'warning'."""
        tenant = _create_test_tenant(db)
        today = date(2026, 7, 1)
        approved_at = datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 2),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "warning"

    def test_scan_30_days_escalated(self, db: Session) -> None:
        """Approved exactly 30 days ago: flag should be 'escalated'."""
        tenant = _create_test_tenant(db)
        today = date(2026, 7, 2)
        approved_at = datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 2),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "escalated"

    def test_scan_31_days_escalated(self, db: Session) -> None:
        """Approved 31 days ago: flag should be 'escalated'."""
        tenant = _create_test_tenant(db)
        today = date(2026, 7, 3)
        approved_at = datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
            tzinfo=UTC
        )

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=approved_at,
            snapshot_date=date(2026, 6, 2),
        )

        scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "escalated"

    def test_scan_multiple_recs_various_windows(self, db: Session) -> None:
        """Scan correctly handles multiple recs in different windows."""
        tenant = _create_test_tenant(db)
        today = date(2026, 6, 30)

        # Approved 2 days ago: no flag
        rec1 = _seed_recommendation(
            db,
            tenant.id,
            rule_id="rule_001",
            status="approved",
            approved_at=datetime.combine(
                date(2026, 6, 28), datetime.min.time()
            ).replace(tzinfo=UTC),
            snapshot_date=date(2026, 6, 28),
        )

        # Approved 20 days ago: warning
        rec2 = _seed_recommendation(
            db,
            tenant.id,
            rule_id="rule_002",
            status="approved",
            approved_at=datetime.combine(
                date(2026, 6, 10), datetime.min.time()
            ).replace(tzinfo=UTC),
            snapshot_date=date(2026, 6, 10),
        )

        # Approved 31 days ago: escalated
        rec3 = _seed_recommendation(
            db,
            tenant.id,
            rule_id="rule_003",
            status="approved",
            approved_at=datetime.combine(
                date(2026, 5, 30), datetime.min.time()
            ).replace(tzinfo=UTC),
            snapshot_date=date(2026, 5, 30),
        )

        updated = scan_implementation_gaps(db, today=today)

        db.refresh(rec1)
        db.refresh(rec2)
        db.refresh(rec3)

        assert rec1.implementation_gap_flag is None
        assert rec2.implementation_gap_flag == "warning"
        assert rec3.implementation_gap_flag == "escalated"
        assert updated == 2  # rec2 and rec3 changed; rec1 stays None

    def test_scan_updates_existing_flag(self, db: Session) -> None:
        """Scan updates flag when it changes (e.g. warning -> escalated)."""
        tenant = _create_test_tenant(db)
        today = date(2026, 7, 2)

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
                tzinfo=UTC
            ),
            snapshot_date=date(2026, 6, 2),
        )

        # Pre-set flag to warning (simulating previous run)
        rec.implementation_gap_flag = "warning"
        db.commit()

        # Run scan at day 30 (should escalate)
        updated = scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "escalated"
        assert updated == 1  # Flag changed, so counted as updated

    def test_scan_no_updates_if_flag_unchanged(self, db: Session) -> None:
        """Scan returns 0 if flag doesn't change."""
        tenant = _create_test_tenant(db)
        today = date(2026, 6, 16)

        rec = _seed_recommendation(
            db,
            tenant.id,
            status="approved",
            approved_at=datetime.combine(date(2026, 6, 2), datetime.min.time()).replace(
                tzinfo=UTC
            ),
            snapshot_date=date(2026, 6, 2),
        )

        # Pre-set flag to what it should be
        rec.implementation_gap_flag = "warning"
        db.commit()

        # Run scan (flag should stay warning)
        updated = scan_implementation_gaps(db, today=today)

        db.refresh(rec)
        assert rec.implementation_gap_flag == "warning"
        assert updated == 0  # Flag didn't change, so 0 updated
