"""Tests for backend.app.recommendations.lifecycle (T-058)."""

from __future__ import annotations

import pytest
from backend.app.recommendations.lifecycle import (
    TERMINAL_STATUSES,
    TRANSITIONS,
    InvalidTransitionError,
    RecommendationStatus,
    transition,
)

# ---------------------------------------------------------------------------
# RecommendationStatus enum
# ---------------------------------------------------------------------------


def test_status_values_match_db_strings() -> None:
    """Status enum values must match the plain strings stored in the database."""
    assert RecommendationStatus.NEW.value == "new"
    assert RecommendationStatus.REVIEWED.value == "reviewed"
    assert RecommendationStatus.APPROVED.value == "approved"
    assert RecommendationStatus.REJECTED.value == "rejected"
    assert RecommendationStatus.IMPLEMENTED_EXTERNALLY.value == "implemented_externally"
    assert RecommendationStatus.OUTCOME_OBSERVED.value == "outcome_observed"


def test_all_eight_statuses_exist() -> None:
    """Exactly eight statuses are defined (6 original + 2 E1 additions)."""
    assert len(RecommendationStatus) == 8


# ---------------------------------------------------------------------------
# Terminal statuses
# ---------------------------------------------------------------------------


def test_rejected_is_terminal() -> None:
    assert RecommendationStatus.REJECTED in TERMINAL_STATUSES


def test_outcome_observed_is_terminal() -> None:
    assert RecommendationStatus.OUTCOME_OBSERVED in TERMINAL_STATUSES


def test_non_terminal_statuses_not_in_terminal_set() -> None:
    for status in RecommendationStatus:
        if status in (
            RecommendationStatus.REJECTED,
            RecommendationStatus.OUTCOME_OBSERVED,
            RecommendationStatus.EXPIRED,
            RecommendationStatus.ARCHIVED,
        ):
            continue
        assert status not in TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# Legal transitions — happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current, to",
    [
        ("new", "reviewed"),
        ("reviewed", "approved"),
        ("reviewed", "rejected"),
        ("approved", "implemented_externally"),
        ("approved", "rejected"),
        ("implemented_externally", "outcome_observed"),
    ],
)
def test_legal_transition_returns_new_status(current: str, to: str) -> None:
    """All legal transitions return the correct RecommendationStatus."""
    result = transition(current, to)
    assert result == RecommendationStatus(to)


def test_transition_accepts_enum_values() -> None:
    """transition() works when passed RecommendationStatus enum values directly."""
    result = transition(RecommendationStatus.NEW, RecommendationStatus.REVIEWED)
    assert result == RecommendationStatus.REVIEWED


# ---------------------------------------------------------------------------
# Illegal transitions — forward skips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current, to",
    [
        ("new", "approved"),
        ("new", "rejected"),
        ("new", "implemented_externally"),
        ("new", "outcome_observed"),
        ("reviewed", "implemented_externally"),
        ("reviewed", "outcome_observed"),
        ("approved", "outcome_observed"),
        ("approved", "new"),
        ("approved", "reviewed"),
        ("implemented_externally", "new"),
        ("implemented_externally", "reviewed"),
        ("implemented_externally", "approved"),
        ("implemented_externally", "rejected"),
    ],
)
def test_illegal_transition_raises(current: str, to: str) -> None:
    """All illegal transitions raise InvalidTransitionError."""
    with pytest.raises(InvalidTransitionError):
        transition(current, to)


# ---------------------------------------------------------------------------
# Reviewed is forward-only — cannot go back to new
# ---------------------------------------------------------------------------


def test_reviewed_cannot_go_back_to_new() -> None:
    with pytest.raises(InvalidTransitionError) as exc_info:
        transition("reviewed", "new")
    assert exc_info.value.current == RecommendationStatus.REVIEWED
    assert exc_info.value.requested == RecommendationStatus.NEW


# ---------------------------------------------------------------------------
# Terminal states — no transitions permitted from them
# ---------------------------------------------------------------------------


def test_rejected_is_terminal_no_transition_allowed() -> None:
    for status in RecommendationStatus:
        with pytest.raises(InvalidTransitionError):
            transition("rejected", status.value)


def test_outcome_observed_is_terminal_no_transition_allowed() -> None:
    for status in RecommendationStatus:
        with pytest.raises(InvalidTransitionError):
            transition("outcome_observed", status.value)


# ---------------------------------------------------------------------------
# InvalidTransitionError carries correct metadata
# ---------------------------------------------------------------------------


def test_invalid_transition_error_attributes() -> None:
    with pytest.raises(InvalidTransitionError) as exc_info:
        transition("new", "approved")
    err = exc_info.value
    assert err.current == RecommendationStatus.NEW
    assert err.requested == RecommendationStatus.APPROVED
    assert "new" in str(err)
    assert "approved" in str(err)


# ---------------------------------------------------------------------------
# Unknown status string raises ValueError
# ---------------------------------------------------------------------------


def test_unknown_current_status_raises_value_error() -> None:
    with pytest.raises(ValueError):
        transition("in_progress", "reviewed")


def test_unknown_to_status_raises_value_error() -> None:
    with pytest.raises(ValueError):
        transition("new", "completed")


# ---------------------------------------------------------------------------
# TRANSITIONS map structure
# ---------------------------------------------------------------------------


def test_terminal_statuses_absent_from_transitions_map() -> None:
    """Terminal states must not appear as keys in TRANSITIONS."""
    assert RecommendationStatus.REJECTED not in TRANSITIONS
    assert RecommendationStatus.OUTCOME_OBSERVED not in TRANSITIONS


def test_transitions_map_has_four_source_states() -> None:
    """Four non-terminal states appear as keys in TRANSITIONS."""
    assert len(TRANSITIONS) == 4
