"""FR-071 / T-054: Rule pack v1 — major signal families.

Defines six core recommendation rules, one per data domain.  Thresholds are
read from RuleInput.thresholds (populated from TenantRuleThreshold at job
time), with sensible hardcoded fallback defaults so the engine is safe to run
even before a tenant has customised anything.

Priority scale (lower = surface first):
    10  EXC-001  contribution margin breach       — direct profitability signal
    15  INV-001  stockout risk count              — capital / revenue at risk
    18  OPS-001  operational revenue at risk      — lost revenue evidence
    20  ACQ-001  blended ROAS below floor         — spend efficiency
    22  RET-001  repeat purchase rate below floor — customer-lifetime signal
    25  MRG-001  margin drift threshold exceeded  — cost-driver warning
"""

from __future__ import annotations

from worker.app.rules.engine import Rule, RuleInput, RuleResult

# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

_INV_RISK_STATUSES = frozenset({"stockout_risk", "critical_low", "out_of_stock"})


def _freshness_ctx(ri: RuleInput) -> str:
    d = ri.data_freshness_days
    if d == 0:
        return "Data is current."
    return f"Data is {d} day(s) old — treat recommendations with care."


# ---------------------------------------------------------------------------
# EXC-001: Contribution margin below tenant-configured floor
# ---------------------------------------------------------------------------


def _exc_001_condition(ri: RuleInput) -> bool:
    if ri.contribution_margin_pct is None:
        return False
    return ri.contribution_margin_pct < ri.thresholds.get("EXC-001", 30.0)


def _exc_001_result(ri: RuleInput) -> RuleResult:
    floor = ri.thresholds.get("EXC-001", 30.0)
    cm = ri.contribution_margin_pct or 0.0
    gap = floor - cm
    return RuleResult(
        rule_id="EXC-001",
        domain="executive",
        affected_area="Business profitability — contribution margin",
        signal_summary=(
            f"Contribution margin is {cm:.1f}%, which is {gap:.1f}pp below "
            f"the configured floor of {floor:.1f}%."
        ),
        suggested_action=(
            "Review cost structure — shipping, returns, and COGS — "
            "to identify the primary margin drag and restore profitability."
        ),
        estimated_impact=None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=10,
    )


# ---------------------------------------------------------------------------
# INV-001: Stockout-risk SKU count at or above tenant threshold
# ---------------------------------------------------------------------------


def _inv_001_condition(ri: RuleInput) -> bool:
    threshold = int(ri.thresholds.get("INV-001", 1.0))
    at_risk = [
        r for r in ri.inventory_risk_rows if r.get("status") in _INV_RISK_STATUSES
    ]
    return len(at_risk) >= threshold


def _inv_001_result(ri: RuleInput) -> RuleResult:
    at_risk = [
        r for r in ri.inventory_risk_rows if r.get("status") in _INV_RISK_STATUSES
    ]
    skus = ", ".join(r.get("sku", "?") for r in at_risk[:5])
    if len(at_risk) > 5:
        skus += f" +{len(at_risk) - 5} more"
    capital = sum((r.get("capital_at_risk") or 0.0) for r in at_risk)
    return RuleResult(
        rule_id="INV-001",
        domain="inventory",
        affected_area=f"Inventory — {len(at_risk)} SKU(s) at stockout risk",
        signal_summary=(
            f"{len(at_risk)} SKU(s) flagged as stockout risk: {skus}. "
            f"Estimated capital at risk: {ri.base_currency} {capital:,.0f}."
        ),
        suggested_action=(
            "Review reorder schedule for flagged SKUs and place "
            "purchase orders before the stockout window closes."
        ),
        estimated_impact=capital if capital > 0 else None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=15,
    )


# ---------------------------------------------------------------------------
# OPS-001: Stockout revenue at risk exceeds tenant-configured floor
# ---------------------------------------------------------------------------


def _ops_001_condition(ri: RuleInput) -> bool:
    threshold = ri.thresholds.get("OPS-001", 500.0)
    return any(
        (r.get("stockout_lost_revenue_estimate") or 0.0) >= threshold
        for r in ri.operational_impact_rows
    )


def _ops_001_result(ri: RuleInput) -> RuleResult:
    threshold = ri.thresholds.get("OPS-001", 500.0)
    flagged = [
        r
        for r in ri.operational_impact_rows
        if (r.get("stockout_lost_revenue_estimate") or 0.0) >= threshold
    ]
    total = sum((r.get("stockout_lost_revenue_estimate") or 0.0) for r in flagged)
    skus = ", ".join(r.get("sku", "?") for r in flagged[:5])
    if len(flagged) > 5:
        skus += f" +{len(flagged) - 5} more"
    return RuleResult(
        rule_id="OPS-001",
        domain="operational",
        affected_area=f"Operations — {len(flagged)} SKU(s) with revenue at risk",
        signal_summary=(
            f"{len(flagged)} SKU(s) have stockout lost-revenue estimates "
            f"above {ri.base_currency} {threshold:,.0f}: {skus}. "
            f"Total estimated revenue at risk: "
            f"{ri.base_currency} {total:,.0f}."
        ),
        suggested_action=(
            "Prioritise replenishment for flagged SKUs to prevent "
            "further lost revenue from stockout periods."
        ),
        estimated_impact=total if total > 0 else None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=18,
    )


# ---------------------------------------------------------------------------
# ACQ-001: Blended ROAS below tenant-configured floor
# ---------------------------------------------------------------------------


def _acq_001_condition(ri: RuleInput) -> bool:
    if ri.blended_roas is None:
        return False
    return ri.blended_roas < ri.thresholds.get("ACQ-001", 1.5)


def _acq_001_result(ri: RuleInput) -> RuleResult:
    floor = ri.thresholds.get("ACQ-001", 1.5)
    roas = ri.blended_roas or 0.0
    gap = floor - roas
    return RuleResult(
        rule_id="ACQ-001",
        domain="acquisition",
        affected_area="Paid acquisition — blended ROAS",
        signal_summary=(
            f"Blended ROAS is {roas:.2f}, which is {gap:.2f} below the "
            f"configured floor of {floor:.2f}."
        ),
        suggested_action=(
            "Review channel mix and reallocate budget away from the "
            "lowest-ROAS channels to recover blended efficiency."
        ),
        estimated_impact=None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=20,
    )


# ---------------------------------------------------------------------------
# RET-001: Repeat purchase rate below tenant-configured floor
# ---------------------------------------------------------------------------


def _ret_001_condition(ri: RuleInput) -> bool:
    if ri.repeat_purchase_rate_pct is None:
        return False
    return ri.repeat_purchase_rate_pct < ri.thresholds.get("RET-001", 20.0)


def _ret_001_result(ri: RuleInput) -> RuleResult:
    floor = ri.thresholds.get("RET-001", 20.0)
    rpr = ri.repeat_purchase_rate_pct or 0.0
    gap = floor - rpr
    return RuleResult(
        rule_id="RET-001",
        domain="retention",
        affected_area="Customer retention — repeat purchase rate",
        signal_summary=(
            f"Repeat purchase rate is {rpr:.1f}%, which is {gap:.1f}pp below "
            f"the configured floor of {floor:.1f}%."
        ),
        suggested_action=(
            "Activate a win-back sequence for lapsed customers and review "
            "post-purchase flows (email cadence, loyalty offers) to improve "
            "second-purchase conversion."
        ),
        estimated_impact=None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=22,
    )


# ---------------------------------------------------------------------------
# MRG-001: Margin drift threshold exceeded for one or more channel/categories
# ---------------------------------------------------------------------------


def _mrg_001_condition(ri: RuleInput) -> bool:
    threshold = int(ri.thresholds.get("MRG-001", 1.0))
    exceeded = [r for r in ri.margin_drift_rows if r.get("threshold_exceeded")]
    return len(exceeded) >= threshold


def _mrg_001_result(ri: RuleInput) -> RuleResult:
    exceeded = [r for r in ri.margin_drift_rows if r.get("threshold_exceeded")]
    channels = sorted({r.get("channel", "?") for r in exceeded})
    label = ", ".join(channels[:3])
    if len(channels) > 3:
        label += f" +{len(channels) - 3} more"
    return RuleResult(
        rule_id="MRG-001",
        domain="finance",
        affected_area=(
            f"Margin drift — {len(exceeded)} channel/category combination(s)"
        ),
        signal_summary=(
            f"{len(exceeded)} channel/category combination(s) have exceeded "
            f"margin drift thresholds. Affected channels: {label}."
        ),
        suggested_action=(
            "Investigate cost driver changes (COGS, shipping, returns) for "
            "flagged channels and adjust pricing or spend allocation."
        ),
        estimated_impact=None,
        confidence_level="medium",
        data_freshness_context=_freshness_ctx(ri),
        priority=25,
    )


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------


def get_rules() -> list[Rule]:
    """Return the active rule pack (v1 — six signal-family rules)."""
    return [
        Rule(
            rule_id="EXC-001",
            domain="executive",
            description="Contribution margin below tenant-configured floor.",
            condition=_exc_001_condition,
            build_result=_exc_001_result,
            priority=10,
        ),
        Rule(
            rule_id="INV-001",
            domain="inventory",
            description="Stockout-risk SKU count at or above tenant threshold.",
            condition=_inv_001_condition,
            build_result=_inv_001_result,
            priority=15,
        ),
        Rule(
            rule_id="OPS-001",
            domain="operational",
            description="Stockout revenue at risk exceeds tenant-configured floor.",
            condition=_ops_001_condition,
            build_result=_ops_001_result,
            priority=18,
        ),
        Rule(
            rule_id="ACQ-001",
            domain="acquisition",
            description="Blended ROAS below tenant-configured floor.",
            condition=_acq_001_condition,
            build_result=_acq_001_result,
            priority=20,
        ),
        Rule(
            rule_id="RET-001",
            domain="retention",
            description="Repeat purchase rate below tenant-configured floor.",
            condition=_ret_001_condition,
            build_result=_ret_001_result,
            priority=22,
        ),
        Rule(
            rule_id="MRG-001",
            domain="finance",
            description="Margin drift threshold exceeded for one or more channels.",
            condition=_mrg_001_condition,
            build_result=_mrg_001_result,
            priority=25,
        ),
    ]

