"""FR-071 / T-055: Impact scoring for recommendation ranking.

Computes a dynamic ``impact_score`` (float ≥ 0.0) for each fired rule.
Higher score = more important = surfaces first in the recommendations API.

Formula
-------
    impact_score = domain_weight × min(severity_factor, _MAX_SEVERITY) × 100

Domain weights are derived from each rule's base priority (100 / priority),
so a margin breach (priority 10, weight 10.0) always outranks a ROAS gap
(priority 20, weight 5.0) at equal percentage deviation.

Severity factors
----------------
Percentage-deviation rules (EXC-001, ACQ-001, RET-001):
    severity = (floor_threshold − actual) / floor_threshold
    Produces a 0.0–1.0 ratio capped at 10.0 (i.e. floor can't go negative).

Count-multiple rules (INV-001, MRG-001):
    severity = observed_count / count_threshold
    3 at-risk SKUs against a threshold of 1 → severity = 3.0.

Currency-multiple rule (OPS-001):
    severity = total_revenue_at_risk / currency_threshold
    ₹500 000 at risk against a threshold of ₹50 000 → severity = 10.0.

Cap
---
_MAX_SEVERITY = 10.0 prevents extreme outliers from inflating scores so
high that all other signals become invisible in ranked lists.

Known limitation
----------------
Percentage and monetary severity factors are on different scales and are
only made comparable via the domain-weight multiplier.  A future iteration
that adds ``revenue_amount_last_30d`` to RuleInput could normalise monetary
rules against revenue and produce a fully comparable dimensionless score.
"""

from __future__ import annotations

from collections.abc import Callable

from worker.app.rules.engine import RuleInput

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_SEVERITY: float = 10.0

# 100 / base_priority for each rule — mirrors the priority scale in pack.py
_DOMAIN_WEIGHT: dict[str, float] = {
    "EXC-001": 10.00,  # 100 / 10
    "INV-001": 6.67,   # 100 / 15
    "OPS-001": 5.56,   # 100 / 18
    "ACQ-001": 5.00,   # 100 / 20
    "RET-001": 4.55,   # 100 / 22
    "MRG-001": 4.00,   # 100 / 25
}

_INV_RISK_STATUSES: frozenset[str] = frozenset(
    {"stockout_risk", "critical_low", "out_of_stock"}
)

# ---------------------------------------------------------------------------
# Per-rule severity functions
# ---------------------------------------------------------------------------


def _severity_exc_001(ri: RuleInput) -> float:
    floor = ri.thresholds.get("EXC-001", 30.0)
    if floor <= 0.0:
        return 0.0
    cm = ri.contribution_margin_pct or 0.0
    return max(0.0, (floor - cm) / floor)


def _severity_inv_001(ri: RuleInput) -> float:
    threshold = max(1.0, ri.thresholds.get("INV-001", 1.0))
    at_risk = sum(
        1 for r in ri.inventory_risk_rows if r.get("status") in _INV_RISK_STATUSES
    )
    return at_risk / threshold


def _severity_ops_001(ri: RuleInput) -> float:
    threshold = ri.thresholds.get("OPS-001", 500.0)
    if threshold <= 0.0:
        return 0.0
    total = sum(
        (r.get("stockout_lost_revenue_estimate") or 0.0)
        for r in ri.operational_impact_rows
    )
    return total / threshold


def _severity_acq_001(ri: RuleInput) -> float:
    floor = ri.thresholds.get("ACQ-001", 1.5)
    if floor <= 0.0:
        return 0.0
    roas = ri.blended_roas or 0.0
    return max(0.0, (floor - roas) / floor)


def _severity_ret_001(ri: RuleInput) -> float:
    floor = ri.thresholds.get("RET-001", 20.0)
    if floor <= 0.0:
        return 0.0
    rpr = ri.repeat_purchase_rate_pct or 0.0
    return max(0.0, (floor - rpr) / floor)


def _severity_mrg_001(ri: RuleInput) -> float:
    threshold = max(1.0, ri.thresholds.get("MRG-001", 1.0))
    breach_count = sum(1 for r in ri.margin_drift_rows if r.get("threshold_exceeded"))
    return breach_count / threshold


_SEVERITY_DISPATCH: dict[str, Callable[[RuleInput], float]] = {
    "EXC-001": _severity_exc_001,
    "INV-001": _severity_inv_001,
    "OPS-001": _severity_ops_001,
    "ACQ-001": _severity_acq_001,
    "RET-001": _severity_ret_001,
    "MRG-001": _severity_mrg_001,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_impact_score(rule_id: str, ri: RuleInput) -> float:
    """Return a non-negative impact score for a rule that has fired.

    Returns 0.0 for unknown rule IDs so callers never receive None.
    """
    severity_fn = _SEVERITY_DISPATCH.get(rule_id)
    if severity_fn is None:
        return 0.0
    weight = _DOMAIN_WEIGHT.get(rule_id, 1.0)
    severity = min(severity_fn(ri), _MAX_SEVERITY)
    return round(weight * severity * 100.0, 4)
