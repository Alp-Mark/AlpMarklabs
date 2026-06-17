"""FR-071 / T-057: Evidence payload assembler for recommendation rules.

Produces a structured, machine-readable dict for each fired rule containing
the exact values, thresholds, and affected entities that triggered the signal.

The evidence payload is stored as JSON on ``Recommendation.evidence`` and
serves two purposes:
- Audit trail: what values were observed vs what threshold was active at the
  moment the recommendation was created, independent of later threshold edits.
- API consumers: structured data for downstream display, export, or simulation
  without having to re-parse the ``signal_summary`` text string.

All payloads share a common envelope:
    {
        "rule_id":             str,
        "threshold_value":     float,    # value active at fire time
        "data_freshness_days": int,
        "base_currency":       str,
        ...rule-specific fields...
    }

Rule-specific fields
--------------------
EXC-001 / ACQ-001 / RET-001 (percentage-deviation rules):
    actual_value, floor_value, gap

INV-001 (inventory stockout-risk):
    at_risk_count, at_risk_skus (full list), total_capital_at_risk

OPS-001 (operational revenue at risk):
    flagged_count, flagged_skus (full list), total_revenue_at_risk

MRG-001 (margin drift):
    breach_count, affected_entries (full list with channel/category/drift_pct)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from worker.app.rules.engine import RuleInput

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_INV_RISK_STATUSES: frozenset[str] = frozenset(
    {"stockout_risk", "critical_low", "out_of_stock"}
)


def _envelope(rule_id: str, threshold_value: float, ri: RuleInput) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "threshold_value": threshold_value,
        "data_freshness_days": ri.data_freshness_days,
        "base_currency": ri.base_currency,
    }


# ---------------------------------------------------------------------------
# Per-rule evidence builders
# ---------------------------------------------------------------------------


def _evidence_exc_001(ri: RuleInput) -> dict[str, Any]:
    floor = ri.thresholds.get("EXC-001", 30.0)
    actual = ri.contribution_margin_pct or 0.0
    payload = _envelope("EXC-001", floor, ri)
    payload.update(
        {
            "actual_cm_pct": actual,
            "floor_pct": floor,
            "gap_pp": round(floor - actual, 4),
        }
    )
    return payload


def _evidence_inv_001(ri: RuleInput) -> dict[str, Any]:
    threshold = ri.thresholds.get("INV-001", 1.0)
    at_risk = [r for r in ri.inventory_risk_rows if r.get("status") in _INV_RISK_STATUSES]
    total_capital = sum((r.get("capital_at_risk") or 0.0) for r in at_risk)
    skus = [
        {
            "sku": r.get("sku", ""),
            "status": r.get("status", ""),
            "days_to_stockout": r.get("days_to_stockout"),
            "capital_at_risk": r.get("capital_at_risk"),
            "confidence": r.get("confidence", ""),
        }
        for r in at_risk
    ]
    payload = _envelope("INV-001", threshold, ri)
    payload.update(
        {
            "at_risk_count": len(at_risk),
            "at_risk_skus": skus,
            "total_capital_at_risk": round(total_capital, 4),
        }
    )
    return payload


def _evidence_ops_001(ri: RuleInput) -> dict[str, Any]:
    threshold = ri.thresholds.get("OPS-001", 500.0)
    flagged = [
        r
        for r in ri.operational_impact_rows
        if (r.get("stockout_lost_revenue_estimate") or 0.0) >= threshold
    ]
    total = sum((r.get("stockout_lost_revenue_estimate") or 0.0) for r in flagged)
    skus = [
        {
            "sku": r.get("sku", ""),
            "revenue_at_risk": r.get("stockout_lost_revenue_estimate"),
            "confidence": r.get("confidence", ""),
        }
        for r in flagged
    ]
    payload = _envelope("OPS-001", threshold, ri)
    payload.update(
        {
            "flagged_count": len(flagged),
            "flagged_skus": skus,
            "total_revenue_at_risk": round(total, 4),
        }
    )
    return payload


def _evidence_acq_001(ri: RuleInput) -> dict[str, Any]:
    floor = ri.thresholds.get("ACQ-001", 1.5)
    actual = ri.blended_roas or 0.0
    payload = _envelope("ACQ-001", floor, ri)
    payload.update(
        {
            "actual_roas": actual,
            "floor_roas": floor,
            "gap": round(floor - actual, 4),
        }
    )
    return payload


def _evidence_ret_001(ri: RuleInput) -> dict[str, Any]:
    floor = ri.thresholds.get("RET-001", 20.0)
    actual = ri.repeat_purchase_rate_pct or 0.0
    payload = _envelope("RET-001", floor, ri)
    payload.update(
        {
            "actual_rpr_pct": actual,
            "floor_pct": floor,
            "gap_pp": round(floor - actual, 4),
        }
    )
    return payload


def _evidence_mrg_001(ri: RuleInput) -> dict[str, Any]:
    threshold = ri.thresholds.get("MRG-001", 1.0)
    exceeded = [r for r in ri.margin_drift_rows if r.get("threshold_exceeded")]
    entries = [
        {
            "channel": r.get("channel", ""),
            "category": r.get("category", ""),
            "drift_pct": r.get("drift_pct"),
            "actual_margin_pct": r.get("actual_margin_pct"),
        }
        for r in exceeded
    ]
    payload = _envelope("MRG-001", threshold, ri)
    payload.update(
        {
            "breach_count": len(exceeded),
            "affected_entries": entries,
        }
    )
    return payload


_EVIDENCE_DISPATCH: dict[str, Callable[[RuleInput], dict[str, Any]]] = {
    "EXC-001": _evidence_exc_001,
    "INV-001": _evidence_inv_001,
    "OPS-001": _evidence_ops_001,
    "ACQ-001": _evidence_acq_001,
    "RET-001": _evidence_ret_001,
    "MRG-001": _evidence_mrg_001,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_evidence(rule_id: str, ri: RuleInput) -> dict[str, Any]:
    """Return a structured evidence dict for a rule that has fired.

    Returns a minimal envelope for unknown rule IDs so new rules never
    cause a hard failure before their evidence builder is registered.
    """
    builder = _EVIDENCE_DISPATCH.get(rule_id)
    if builder is None:
        return _envelope(rule_id, 0.0, ri)
    return builder(ri)
