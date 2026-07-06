"""Tests for E1 - Recommendation confidence, data sources, expired/archived states."""

from __future__ import annotations

from datetime import date
from typing import Any

import jwt
from backend.app.db.models import Recommendation
from backend.app.recommendations.lifecycle import (
    InvalidTransitionError,
    RecommendationStatus,
    transition,
)
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET


def _make_token(email: str) -> str:
    """Create JWT token."""
    return jwt.encode(
        {"sub": email, "email": email, "platform_role": "member"},
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )


def test_recommendation_has_confidence_score_field(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Recommendation model includes confidence_score (0-1)."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="test_rule",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="Meta Ads",
        signal_summary="CAC increased 20%",
        suggested_action="Reduce Meta spend 15%",
        confidence_level="high",
        confidence_score=0.82,
        data_freshness_context="Last synced 2 hours ago",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.confidence_score == 0.82


def test_recommendation_has_data_sources_field(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Recommendation model includes data_sources JSON list."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="test_rule",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="Email campaigns",
        signal_summary="Repeat rate declining",
        suggested_action="Launch winback sequence",
        confidence_level="medium",
        confidence_score=0.65,
        data_sources=["shopify", "meta"],
        data_freshness_context="Last synced 1 day ago",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.data_sources == ["shopify", "meta"]


def test_recommendation_api_returns_confidence_score(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /recommendations returns confidence_score in response."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="api_test_rule",
        domain="finance",
        snapshot_date=date.today(),
        affected_area="Margin",
        signal_summary="Margin down 5%",
        suggested_action="Review supplier contracts",
        confidence_level="very_high",
        confidence_score=0.93,
        data_freshness_context="Last synced 30 minutes ago",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    matching = [r for r in items if r["id"] == str(rec.id)]
    assert len(matching) == 1
    assert matching[0]["confidence_score"] == 0.93


def test_recommendation_api_returns_data_sources(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """GET /recommendations returns data_sources in response."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="data_source_test",
        domain="operations",
        snapshot_date=date.today(),
        affected_area="Inventory",
        signal_summary="Stockout risk for SKU-123",
        suggested_action="Reorder 500 units",
        confidence_level="high",
        confidence_score=0.85,
        data_sources=["shopify", "google_ads"],
        data_freshness_context="Last synced 4 hours ago",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    token = _make_token(user.email)
    response = client.get(
        f"/tenants/{tenant.id}/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    matching = [r for r in items if r["id"] == str(rec.id)]
    assert len(matching) == 1
    assert matching[0]["data_sources"] == ["shopify", "google_ads"]


def test_recommendation_confidence_score_default(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Recommendation confidence_score defaults to 0.5 if not provided."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="default_test",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="Channel",
        signal_summary="CAC spike",
        suggested_action="Pause campaign",
        confidence_level="medium",
        data_freshness_context="Stale data",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.confidence_score == 0.5


def test_recommendation_data_sources_default_empty(
    client: Any, db_session: Any, tenant: Any
) -> None:
    """Recommendation data_sources defaults to empty list."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="default_sources_test",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="Churn",
        signal_summary="Churn increasing",
        suggested_action="Launch retention campaign",
        confidence_level="low",
        confidence_score=0.4,
        data_freshness_context="No recent data",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.data_sources == []


def test_transition_new_to_expired() -> None:
    """Can transition NEW -> EXPIRED."""
    result = transition(RecommendationStatus.NEW, RecommendationStatus.EXPIRED)
    assert result == RecommendationStatus.EXPIRED


def test_transition_reviewed_to_expired() -> None:
    """Can transition REVIEWED -> EXPIRED."""
    result = transition(RecommendationStatus.REVIEWED, RecommendationStatus.EXPIRED)
    assert result == RecommendationStatus.EXPIRED


def test_transition_approved_to_expired() -> None:
    """Can transition APPROVED -> EXPIRED."""
    result = transition(RecommendationStatus.APPROVED, RecommendationStatus.EXPIRED)
    assert result == RecommendationStatus.EXPIRED


def test_transition_implemented_to_expired_disallowed() -> None:
    """Cannot transition IMPLEMENTED_EXTERNALLY -> EXPIRED."""
    try:
        transition(
            RecommendationStatus.IMPLEMENTED_EXTERNALLY, RecommendationStatus.EXPIRED
        )
        raise AssertionError("Should have raised InvalidTransitionError")
    except InvalidTransitionError as exc:
        assert exc.current == RecommendationStatus.IMPLEMENTED_EXTERNALLY
        assert exc.requested == RecommendationStatus.EXPIRED


def test_transition_new_to_archived() -> None:
    """Can transition NEW -> ARCHIVED."""
    result = transition(RecommendationStatus.NEW, RecommendationStatus.ARCHIVED)
    assert result == RecommendationStatus.ARCHIVED


def test_transition_reviewed_to_archived() -> None:
    """Can transition REVIEWED -> ARCHIVED."""
    result = transition(RecommendationStatus.REVIEWED, RecommendationStatus.ARCHIVED)
    assert result == RecommendationStatus.ARCHIVED


def test_transition_approved_to_archived() -> None:
    """Can transition APPROVED -> ARCHIVED."""
    result = transition(RecommendationStatus.APPROVED, RecommendationStatus.ARCHIVED)
    assert result == RecommendationStatus.ARCHIVED


def test_transition_implemented_to_archived() -> None:
    """Can transition IMPLEMENTED_EXTERNALLY -> ARCHIVED."""
    result = transition(
        RecommendationStatus.IMPLEMENTED_EXTERNALLY, RecommendationStatus.ARCHIVED
    )
    assert result == RecommendationStatus.ARCHIVED


def test_transition_expired_is_terminal() -> None:
    """EXPIRED is terminal - cannot transition further."""
    try:
        transition(RecommendationStatus.EXPIRED, RecommendationStatus.ARCHIVED)
        raise AssertionError("Should have raised InvalidTransitionError")
    except InvalidTransitionError as exc:
        assert exc.current == RecommendationStatus.EXPIRED
        assert exc.requested == RecommendationStatus.ARCHIVED


def test_transition_archived_is_terminal() -> None:
    """ARCHIVED is terminal - cannot transition further."""
    try:
        transition(RecommendationStatus.ARCHIVED, RecommendationStatus.REVIEWED)
        raise AssertionError("Should have raised InvalidTransitionError")
    except InvalidTransitionError as exc:
        assert exc.current == RecommendationStatus.ARCHIVED
        assert exc.requested == RecommendationStatus.REVIEWED


def test_update_recommendation_status_to_expired_via_api(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /recommendations/{id}/status supports EXPIRED transition."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="expire_test",
        domain="growth",
        snapshot_date=date.today(),
        affected_area="Campaign",
        signal_summary="Old signal",
        suggested_action="Old action",
        confidence_level="low",
        confidence_score=0.3,
        data_freshness_context="Stale",
        status="new",
        source="optimization",
    )
    db_session.add(rec)
    db_session.commit()

    token = _make_token(user.email)
    response = client.patch(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/status",
        json={"to_status": "expired", "note": "Conditions changed"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "expired"

    # Verify in DB
    db_session.expire_all()
    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.status == "expired"
    assert fetched.review_note == "Conditions changed"


def test_update_recommendation_status_to_archived_via_api(
    client: Any, db_session: Any, tenant: Any, user: Any
) -> None:
    """PATCH /recommendations/{id}/status supports ARCHIVED transition."""
    rec = Recommendation(
        tenant_id=tenant.id,
        rule_id="archive_test",
        domain="retention",
        snapshot_date=date.today(),
        affected_area="Segment",
        signal_summary="Low priority",
        suggested_action="Deprioritized",
        confidence_level="medium",
        confidence_score=0.55,
        data_freshness_context="Recent",
        status="reviewed",
    )
    db_session.add(rec)
    db_session.commit()

    token = _make_token(user.email)
    response = client.patch(
        f"/tenants/{tenant.id}/recommendations/{rec.id}/status",
        json={"to_status": "archived", "note": "Cleanup for Q2"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"

    # Verify in DB
    db_session.expire_all()
    fetched = db_session.get(Recommendation, rec.id)
    assert fetched is not None
    assert fetched.status == "archived"
    assert fetched.review_note == "Cleanup for Q2"


def test_confidence_level_enum_values() -> None:
    """Confidence level supports 5 structured levels."""
    # This is enforced by validation in the service layer, not DB schema
    # Test that all 5 levels are valid strings
    levels = ["very_low", "low", "medium", "high", "very_high"]
    for level in levels:
        rec = Recommendation(
            tenant_id="00000000-0000-0000-0000-000000000001",
            rule_id=f"test_{level}",
            domain="test",
            snapshot_date=date.today(),
            affected_area="test",
            signal_summary="test",
            suggested_action="test",
            confidence_level=level,
            confidence_score=0.5,
            data_freshness_context="test",
            status="new",
        source="optimization",
        )
        assert rec.confidence_level == level


def test_recommendation_response_schema_includes_e1_fields() -> None:
    """RecommendationResponse schema includes E1 fields."""
    from backend.app.schemas.recommendation import RecommendationResponse

    # Check field annotations exist
    annotations = RecommendationResponse.__annotations__
    assert "confidence_score" in annotations
    assert "data_sources" in annotations
    assert "confidence_level" in annotations
    assert "status" in annotations
