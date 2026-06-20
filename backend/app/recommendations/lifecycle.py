"""FR-071 / T-058: Recommendation lifecycle state machine.

Defines the valid statuses a recommendation can hold and enforces legal
transitions between them.  Any attempt to move a recommendation to a status
that is not reachable from its current status raises InvalidTransitionError.

Lifecycle (cross-cutting rule 2, D-12, E1 extensions):

    new
     └─► reviewed
          ├─► approved
          │    └─► implemented_externally
          │         └─► outcome_observed  (terminal)
          └─► rejected                    (terminal)
    
    E1 additions:
    - expired: reachable from new, reviewed, approved
    - archived: reachable from any non-terminal state

Rules:
- "reviewed" is forward-only: a recommendation cannot return to "new" once seen.
- "rejected" is terminal: no further transitions are permitted.
- "outcome_observed" is terminal: no further transitions are permitted.
- "expired" is terminal: recommendation is no longer relevant.
- "archived" is terminal: removed from active view for audit purposes.
- Every other transition not listed in TRANSITIONS is illegal.

No DB I/O occurs in this module.  The caller fetches the recommendation,
reads its current status, calls transition(), and writes the returned new
status back.
"""

from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class RecommendationStatus(StrEnum):
    """Valid statuses for a Recommendation row.

    Inherits from str so values compare equal to the plain strings stored in
    the database (e.g. status == "new" evaluates to True).
    
    E1 additions:
    - EXPIRED: recommendation no longer relevant (time-based or conditions changed)
    - ARCHIVED: removed from active view but preserved for audit
    """

    NEW = "new"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED_EXTERNALLY = "implemented_externally"
    OUTCOME_OBSERVED = "outcome_observed"
    EXPIRED = "expired"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Transition map
# ---------------------------------------------------------------------------

# Maps each status to the set of statuses it is allowed to move to.
# Terminal states (rejected, outcome_observed, expired, archived) are
# intentionally absent as keys — any attempt to transition from them is illegal.
TRANSITIONS: dict[RecommendationStatus, frozenset[RecommendationStatus]] = {
    RecommendationStatus.NEW: frozenset(
        {
            RecommendationStatus.REVIEWED,
            RecommendationStatus.EXPIRED,
            RecommendationStatus.ARCHIVED,
        }
    ),
    RecommendationStatus.REVIEWED: frozenset(
        {
            RecommendationStatus.APPROVED,
            RecommendationStatus.REJECTED,
            RecommendationStatus.EXPIRED,
            RecommendationStatus.ARCHIVED,
        }
    ),
    RecommendationStatus.APPROVED: frozenset(
        {
            RecommendationStatus.IMPLEMENTED_EXTERNALLY,
            RecommendationStatus.REJECTED,
            RecommendationStatus.EXPIRED,
            RecommendationStatus.ARCHIVED,
        }
    ),
    RecommendationStatus.IMPLEMENTED_EXTERNALLY: frozenset(
        {
            RecommendationStatus.OUTCOME_OBSERVED,
            RecommendationStatus.ARCHIVED,
        }
    ),
}

# Terminal states — present here for fast membership checks by callers.
TERMINAL_STATUSES: frozenset[RecommendationStatus] = frozenset(
    {
        RecommendationStatus.REJECTED,
        RecommendationStatus.OUTCOME_OBSERVED,
        RecommendationStatus.EXPIRED,
        RecommendationStatus.ARCHIVED,
    }
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class InvalidTransitionError(Exception):
    """Raised when a requested status transition is not permitted.

    Attributes
    ----------
    current:  The status the recommendation is currently in.
    requested: The status that was requested.
    """

    def __init__(
        self,
        current: RecommendationStatus,
        requested: RecommendationStatus,
    ) -> None:
        self.current = current
        self.requested = requested
        super().__init__(
            f"Cannot transition recommendation from '{current.value}' "
            f"to '{requested.value}'."
        )


# ---------------------------------------------------------------------------
# transition() — the single enforcement point
# ---------------------------------------------------------------------------


def transition(
    current: RecommendationStatus | str,
    to: RecommendationStatus | str,
) -> RecommendationStatus:
    """Validate and return the new status after a lifecycle transition.

    Parameters
    ----------
    current:
        The recommendation's current status.  Accepts a RecommendationStatus
        or a plain string (as stored in the database).
    to:
        The requested next status.  Accepts a RecommendationStatus or a plain
        string.

    Returns
    -------
    RecommendationStatus
        The validated new status.  Write this value back to the database.

    Raises
    ------
    ValueError
        If current or to is not a recognised status string.
    InvalidTransitionError
        If the move from current to to is not a legal transition.
    """
    current_status = RecommendationStatus(current)
    to_status = RecommendationStatus(to)

    allowed = TRANSITIONS.get(current_status)

    if allowed is None:
        # current is a terminal state — no transitions permitted
        raise InvalidTransitionError(current_status, to_status)

    if to_status not in allowed:
        raise InvalidTransitionError(current_status, to_status)

    return to_status
