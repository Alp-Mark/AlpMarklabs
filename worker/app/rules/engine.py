"""FR-071 / T-053: Deterministic rule engine core.

Defines the data structures and evaluation loop used by every recommendation
rule in AlpMark.  Determinism guarantee: given the same RuleInput, calling
RuleEngine.evaluate() will always return the same set of RuleResults in the
same order.  No I/O, no randomness, and no ML occur inside this module.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class RuleInput:
    """Data container passed to every rule condition during evaluation.

    Carries the latest metric snapshots for one tenant on one snapshot date.
    Rules must only read from this object — never mutate it.
    """

    tenant_id: str
    snapshot_date: date
    base_currency: str = "USD"

    # --- Acquisition signals ---
    blended_roas: float | None = None
    channel_roas_rows: list[dict[str, Any]] = field(default_factory=list)
    # Each row: {"channel": str, "roas": float, "cac": float,
    #            "payback_period_days": float}

    # --- Finance / margin signals ---
    contribution_margin_pct: float | None = None
    margin_drift_rows: list[dict[str, Any]] = field(default_factory=list)
    # Each row: {"channel": str, "category": str, "drift_pct": float | None,
    #            "threshold_exceeded": bool, "actual_margin_pct": float}

    # --- Retention signals ---
    repeat_purchase_rate_pct: float | None = None
    churn_risk_high_count: int = 0

    # --- Inventory risk signals ---
    inventory_risk_rows: list[dict[str, Any]] = field(default_factory=list)
    # Each row: {"sku": str, "product_title": str, "status": str,
    #            "days_to_stockout": float | None, "current_quantity": int,
    #            "capital_at_risk": float | None, "confidence": str}

    # --- Operational impact signals ---
    operational_impact_rows: list[dict[str, Any]] = field(default_factory=list)
    # Each row: {"sku": str, "product_title": str, "inventory_status": str,
    #            "stockout_lost_revenue_estimate": float | None,
    #            "return_rate_30d_pct": float, "confidence": str}

    # --- Data freshness ---
    data_freshness_days: int = 0  # days since most recent successful sync

    # --- Tenant-configured rule thresholds ---
    # Keyed by rule_id (e.g. "ACQ-001") → threshold value.
    # Populated by _build_rule_input() from TenantRuleThreshold rows.
    # Rules fall back to built-in defaults when a key is absent.
    thresholds: dict[str, float] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Output produced when a rule's condition evaluates to True.

    All non-default fields are required.  The rule's build_result callable
    is responsible for populating them from the RuleInput it received.
    """

    rule_id: str
    domain: str  # "inventory"|"acquisition"|"retention"|"finance"|"operational"
    affected_area: str  # human-readable label, e.g. "SKU: BOOT-001"
    signal_summary: str  # what signal fired, e.g. "3 days to stockout"
    suggested_action: str
    estimated_impact: float | None  # monetary estimate in tenant base_currency
    confidence_level: str  # "high" | "medium" | "low"
    data_freshness_context: str  # human-readable freshness note
    priority: int = 50  # static domain ordering tiebreaker
    impact_score: float = 0.0  # T-055 dynamic score; higher = surface first
    evidence: dict[str, Any] = field(default_factory=dict)  # T-057 structured payload


@dataclass
class Rule:
    """A single deterministic recommendation rule.

    condition:    pure function — receives RuleInput, returns bool.
                  Must not mutate the input or produce side effects.
    build_result: called only when condition returns True.
                  Must return a fully populated RuleResult.
    """

    rule_id: str
    domain: str
    description: str
    condition: Callable[[RuleInput], bool]
    build_result: Callable[[RuleInput], RuleResult]
    priority: int = 50  # used for stable ordering in RuleEngine


class RuleEngine:
    """Evaluates a fixed list of Rules against a RuleInput.

    Determinism guarantee: rules are evaluated in stable priority order
    (ascending priority, then rule_id as tiebreaker).  A rule with the same
    condition and the same RuleInput always produces the same RuleResult.
    """

    def __init__(self, rules: list[Rule]) -> None:
        # Sort once at construction time so evaluate() is always stable.
        self._rules: list[Rule] = sorted(
            rules, key=lambda r: (r.priority, r.rule_id)
        )

    def evaluate(self, rule_input: RuleInput) -> list[RuleResult]:
        """Return one RuleResult for each rule whose condition fires.

        Results are returned in the same stable priority order the rules
        were sorted into during __init__.  Each result's ``impact_score``
        is populated via scorer.compute_impact_score (T-055).
        """
        # Import here to avoid module-level circular references.
        from worker.app.rules.confidence import (
            compute_confidence_level,  # noqa: PLC0415
        )
        from worker.app.rules.evidence import build_evidence  # noqa: PLC0415
        from worker.app.rules.scorer import compute_impact_score  # noqa: PLC0415

        results: list[RuleResult] = []
        for rule in self._rules:
            if rule.condition(rule_input):
                result = rule.build_result(rule_input)
                result.impact_score = compute_impact_score(rule.rule_id, rule_input)
                result.confidence_level = compute_confidence_level(
                    rule.rule_id, rule_input
                )
                result.evidence = build_evidence(rule.rule_id, rule_input)
                results.append(result)
        return results
