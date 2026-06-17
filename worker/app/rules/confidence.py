"""FR-071 / T-056: Confidence model for recommendation signals.

Computes a dynamic ``confidence_level`` ("high" | "medium" | "low") for each
fired rule by combining three factors applied in order:

1. **Rule base confidence** — inherent certainty of the signal type.

   =========  ======  =================================================
   Rule       Base    Reasoning
   =========  ======  =================================================
   EXC-001    high    Direct metric observation (contribution margin %)
   ACQ-001    high    Direct metric observation (blended ROAS)
   RET-001    high    Direct metric observation (repeat purchase rate %)
   INV-001    medium  Inferred from stock-level counts and velocity
   OPS-001    medium  Estimated revenue loss (projection, not observed)
   MRG-001    low     Drift pattern inference across channel/category
   =========  ======  =================================================

2. **Row-level source confidence** — for INV-001 and OPS-001, each flagged
   source row carries a ``confidence`` field ("high"/"medium"/"low") set by
   the upstream computation job.  If a strict majority of the flagged rows
   report ``"low"`` confidence, the rule-level confidence is downgraded one
   step (high → medium, medium → low, low → low).

3. **Data staleness cap** — applied last; stale data can only reduce
   confidence, never raise it:

   - 0–2 days  → no cap (keep base confidence)
   - 3–6 days  → cap at ``"medium"``
   - 7+  days  → cap at ``"low"``
"""

from __future__ import annotations

from worker.app.rules.engine import RuleInput

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HIGH: str = "high"
_MEDIUM: str = "medium"
_LOW: str = "low"

# Numeric rank used to compare levels (higher = more confident).
_RANK: dict[str, int] = {_HIGH: 2, _MEDIUM: 1, _LOW: 0}

# Rule base confidence — one entry per rule in the pack.
_BASE_CONFIDENCE: dict[str, str] = {
    "EXC-001": _HIGH,    # direct metric observation
    "ACQ-001": _HIGH,    # direct metric observation
    "RET-001": _HIGH,    # direct metric observation
    "INV-001": _MEDIUM,  # inferred from stock levels / velocity
    "OPS-001": _MEDIUM,  # estimated revenue loss (projection)
    "MRG-001": _LOW,     # drift pattern inference
}

# Statuses that mark an inventory row as at-risk (mirrors pack.py).
_INV_RISK_STATUSES: frozenset[str] = frozenset(
    {"stockout_risk", "critical_low", "out_of_stock"}
)

# Staleness thresholds (inclusive lower bound, in days).
_STALE_MEDIUM_DAYS: int = 3   # 3–6 days → cap at "medium"
_STALE_LOW_DAYS: int = 7      # 7+  days → cap at "low"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lower_of(a: str, b: str) -> str:
    """Return whichever confidence level has the lower rank."""
    return a if _RANK[a] <= _RANK[b] else b


def _downgrade(level: str) -> str:
    """Drop one confidence level: high → medium, medium/low → low."""
    if level == _HIGH:
        return _MEDIUM
    return _LOW


def _staleness_cap(days: int) -> str:
    """Maximum confidence level permitted given data age in days."""
    if days >= _STALE_LOW_DAYS:
        return _LOW
    if days >= _STALE_MEDIUM_DAYS:
        return _MEDIUM
    return _HIGH


def _majority_are_low(rows: list[dict]) -> bool:
    """True when strictly more than half of ``rows`` report 'low' confidence."""
    if not rows:
        return False
    low_count = sum(1 for r in rows if r.get("confidence", "").lower() == _LOW)
    return low_count > len(rows) / 2


def _inv_001_flagged(ri: RuleInput) -> list[dict]:
    return [r for r in ri.inventory_risk_rows if r.get("status") in _INV_RISK_STATUSES]


def _ops_001_flagged(ri: RuleInput) -> list[dict]:
    threshold = ri.thresholds.get("OPS-001", 500.0)
    return [
        r
        for r in ri.operational_impact_rows
        if (r.get("stockout_lost_revenue_estimate") or 0.0) >= threshold
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_confidence_level(rule_id: str, ri: RuleInput) -> str:
    """Return "high", "medium", or "low" for a rule that has fired.

    Unknown rule IDs fall back to "medium" so new rules are never silently
    miscategorised as high-confidence.
    """
    # Step 1: rule base confidence.
    level = _BASE_CONFIDENCE.get(rule_id, _MEDIUM)

    # Step 2: row-level source confidence (INV-001 and OPS-001 only).
    if rule_id == "INV-001" and _majority_are_low(_inv_001_flagged(ri)):
        level = _downgrade(level)
    elif rule_id == "OPS-001" and _majority_are_low(_ops_001_flagged(ri)):
        level = _downgrade(level)

    # Step 3: staleness cap — can only reduce, never raise.
    level = _lower_of(level, _staleness_cap(ri.data_freshness_days))

    return level
