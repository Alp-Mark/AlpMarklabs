"""Seed realistic DEMO data for the 'one8' shoe brand (a single demo tenant).

This populates every analytics dashboard (executive, growth/acquisition,
retention/cohorts, finance, operations) plus recommendations, alert history,
and saved simulations so the connected frontend shows meaningful content.

IMPORTANT
---------
* ALL figures below are fictional, hand-crafted demo data for 'one8'.
  They are NOT real and must never be treated as a real business baseline.
* Currency is configured via ``CURRENCY`` / ``LOCALE`` below (INR / en-IN).
* The tenant id and owner email are fixed constants so they are stable to
  paste into the frontend configuration.
* Re-running is safe: per-tenant demo rows are deleted and re-inserted, while
  the tenant / owner user / membership are created once and reused.

How to run
----------
Point ``DATABASE_URL`` at the target database (e.g. the Railway Postgres
public connection string) and run from the repository root::

    DATABASE_URL="postgresql://user:pass@host:port/db" python scripts/seed_one8.py

Or, with the Railway CLI linked to the project::

    railway run python scripts/seed_one8.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

# Ensure the repository root is importable when run as a plain script
# (``python scripts/seed_one8.py``) so ``import backend...`` resolves.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# When run via ``railway run -s Postgres`` the private ``DATABASE_URL`` points at
# ``postgres.railway.internal``, which only resolves inside Railway's network.
# Prefer the public proxy URL so the seed can connect from a developer laptop.
_public_db_url = os.getenv("DATABASE_PUBLIC_URL")
if _public_db_url:
    os.environ["DATABASE_URL"] = _public_db_url

from backend.app.db.models import (  # noqa: E402
    AcquisitionCohort,
    AlertEventLog,
    CohortSnapshot,
    CostDriverSnapshot,
    InventoryRiskSnapshot,
    MarginDriftSnapshot,
    OperationalImpactSnapshot,
    Recommendation,
    Scenario,
    Simulation,
    Tenant,
    TenantMembership,
    User,
)
from backend.app.db.session import SessionLocal  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# --------------------------------------------------------------------------- #
# Fixed demo identity (stable across re-runs)
# --------------------------------------------------------------------------- #
TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
TENANT_NAME = "one8"
TENANT_SLUG = "one8"
OWNER_EMAIL = "owner@one8.com"
OWNER_NAME = "one8 Owner"

# brand_admin satisfies every dashboard endpoint's role requirement.
OWNER_ROLE = "brand_admin"

# Demo currency. one8 is an Indian brand, so the demo uses Indian Rupees with
# the en-IN locale. ``_USD_TO_INR`` scales the hand-authored USD figures into
# believable INR amounts; adjust it (or the per-item numbers) to taste.
CURRENCY = "INR"
LOCALE = "en-IN"

# Demo display FX used to scale the hand-authored USD figures into INR.
_USD_TO_INR = 83.0


def _inr(usd: float) -> float:
    """Scale a USD demo figure into a clean whole-rupee INR amount."""
    return float(round(usd * _USD_TO_INR))


# Approximate monthly net revenue (INR) used to scale the demo cost drivers.
MONTHLY_REVENUE = _inr(850_000.0)

# Channels used across acquisition demo data.
ACQ_CHANNELS = ("shopify_organic", "meta_ads", "google_ads")

# Cohort observation windows seeded so the comparison view has data regardless
# of which window the frontend requests.
COHORT_WINDOWS = (30, 60, 90)


# --------------------------------------------------------------------------- #
# Small date helpers
# --------------------------------------------------------------------------- #
def _add_months(d: date, months: int) -> date:
    """Return the first day of the month ``months`` away from ``d``."""
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _month_end(first_of_month: date) -> date:
    """Return the last day of the month that starts on ``first_of_month``."""
    return _add_months(first_of_month, 1) - timedelta(days=1)


def _complete_months(today: date, count: int) -> list[date]:
    """Return the first-of-month dates for the last ``count`` complete months.

    The current (partial) month is excluded so cohort end dates are always in
    the past and fall inside typical dashboard date ranges.
    """
    last_complete = _add_months(today.replace(day=1), -1)
    return [_add_months(last_complete, -i) for i in range(count - 1, -1, -1)]


# --------------------------------------------------------------------------- #
# Shared product catalogue (used by inventory + operational views)
# --------------------------------------------------------------------------- #
# Each entry mixes inventory-risk and operational-impact attributes so the two
# operations dashboards stay consistent on the same SKUs.
PRODUCTS: list[dict[str, Any]] = [
    {
        "sku": "ONE8-RUN-001",
        "title": "Velocity Runner",
        "variant": "Black / UK 8",
        "unit_price": 89.99,
        "on_hand": 18,
        "reorder": 60,
        "daily_velocity": 4.2,
        "days_to_stockout": 4.3,
        "weeks_of_cover": 0.6,
        "days_since_sale": 0,
        "capital_at_risk": 1_620.0,
        "inv_status": "stockout_risk",
        "op_status": "high",
        "repeat_risk": "medium",
        "return_rate": 6.1,
        "logistics_cpu": 6.5,
        "confidence": "high",
    },
    {
        "sku": "ONE8-RUN-002",
        "title": "Velocity Runner Pro",
        "variant": "White / UK 9",
        "unit_price": 119.99,
        "on_hand": 45,
        "reorder": 50,
        "daily_velocity": 3.1,
        "days_to_stockout": 14.5,
        "weeks_of_cover": 2.1,
        "days_since_sale": 1,
        "capital_at_risk": 4_950.0,
        "inv_status": "low_stock",
        "op_status": "medium",
        "repeat_risk": "low",
        "return_rate": 5.4,
        "logistics_cpu": 6.5,
        "confidence": "high",
    },
    {
        "sku": "ONE8-CAS-001",
        "title": "Street Classic",
        "variant": "Grey / UK 8",
        "unit_price": 74.99,
        "on_hand": 320,
        "reorder": 80,
        "daily_velocity": 5.0,
        "days_to_stockout": 64.0,
        "weeks_of_cover": 9.1,
        "days_since_sale": 0,
        "capital_at_risk": None,
        "inv_status": "in_stock",
        "op_status": "none",
        "repeat_risk": "none",
        "return_rate": 4.8,
        "logistics_cpu": 5.0,
        "confidence": "high",
    },
    {
        "sku": "ONE8-CAS-002",
        "title": "Court Casual",
        "variant": "Navy / UK 10",
        "unit_price": 79.99,
        "on_hand": 540,
        "reorder": 90,
        "daily_velocity": 1.2,
        "days_to_stockout": 450.0,
        "weeks_of_cover": 38.0,
        "days_since_sale": 2,
        "capital_at_risk": 21_600.0,
        "inv_status": "overstock",
        "op_status": "low",
        "repeat_risk": "high",
        "return_rate": 14.8,
        "logistics_cpu": 5.5,
        "confidence": "medium",
    },
    {
        "sku": "ONE8-TRN-001",
        "title": "Train Flex",
        "variant": "Black / UK 9",
        "unit_price": 99.99,
        "on_hand": 210,
        "reorder": 70,
        "daily_velocity": 3.8,
        "days_to_stockout": 55.0,
        "weeks_of_cover": 7.9,
        "days_since_sale": 0,
        "capital_at_risk": None,
        "inv_status": "in_stock",
        "op_status": "none",
        "repeat_risk": "none",
        "return_rate": 6.7,
        "logistics_cpu": 5.5,
        "confidence": "high",
    },
    {
        "sku": "ONE8-SAN-001",
        "title": "Coast Slide",
        "variant": "Olive / UK 8",
        "unit_price": 39.99,
        "on_hand": 260,
        "reorder": 40,
        "daily_velocity": 0.4,
        "days_to_stockout": 650.0,
        "weeks_of_cover": 52.0,
        "days_since_sale": 21,
        "capital_at_risk": 5_720.0,
        "inv_status": "slow_moving",
        "op_status": "low",
        "repeat_risk": "low",
        "return_rate": 9.2,
        "logistics_cpu": 4.0,
        "confidence": "medium",
    },
    {
        "sku": "ONE8-FORM-001",
        "title": "Boardroom Derby",
        "variant": "Tan / UK 9",
        "unit_price": 109.99,
        "on_hand": 30,
        "reorder": 45,
        "daily_velocity": 1.1,
        "days_to_stockout": 27.0,
        "weeks_of_cover": 3.9,
        "days_since_sale": 1,
        "capital_at_risk": 3_300.0,
        "inv_status": "low_stock",
        "op_status": "medium",
        "repeat_risk": "low",
        "return_rate": 5.9,
        "logistics_cpu": 6.0,
        "confidence": "high",
    },
]


# Scale the hand-authored USD product economics into INR so the inventory and
# operational dashboards stay internally consistent on the same SKUs.
for _p in PRODUCTS:
    _p["unit_price"] = _inr(_p["unit_price"])
    _p["logistics_cpu"] = _inr(_p["logistics_cpu"])
    if _p["capital_at_risk"] is not None:
        _p["capital_at_risk"] = _inr(_p["capital_at_risk"])


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def build_cost_drivers(today: date, now: datetime) -> list[CostDriverSnapshot]:
    """Five Phase-1 cost drivers for the latest snapshot date."""
    period_start = today - timedelta(days=29)
    updated = now - timedelta(hours=2)
    # (driver_type, pct_of_revenue, source, source_platform)
    rows = [
        ("cogs", 42.0, "estimated", "shopify"),
        ("shipping", 6.0, "synced", "shopify"),
        ("returns", 8.0, "synced", "shopify"),
        ("discounts", 5.0, "synced", "shopify"),
        ("ad_spend", 18.0, "synced", "meta_google"),
    ]
    drivers: list[CostDriverSnapshot] = []
    for driver_type, pct, source, platform in rows:
        amount = round(MONTHLY_REVENUE * pct / 100.0, 2)
        drivers.append(
            CostDriverSnapshot(
                tenant_id=TENANT_ID,
                driver_type=driver_type,
                snapshot_date=today,
                period_start_date=period_start,
                period_end_date=today,
                absolute_amount=amount,
                revenue=MONTHLY_REVENUE,
                pct_of_revenue=pct,
                margin_impact_amount=-amount,
                source=source,
                source_platform=platform,
                last_updated_at=updated,
                confidence_score=0.9,
                confidence_label="high",
            )
        )
    return drivers


def build_margin_drift(today: date) -> list[MarginDriftSnapshot]:
    """Channel x category margin drift for the latest snapshot date."""
    # (channel, category, actual, expected, exceeded, reason)
    rows = [
        ("shopify", "Running", 38.5, 44.0, True, "Discount depth increased"),
        ("meta_ads", "Casual", 41.2, 42.0, False, "Within normal range"),
        ("google_ads", "Training", 36.0, 40.0, True, "Shipping cost spike"),
        ("shopify", "Formal", 47.0, 46.0, False, "Within normal range"),
    ]
    snapshots: list[MarginDriftSnapshot] = []
    for channel, category, actual, expected, exceeded, reason in rows:
        snapshots.append(
            MarginDriftSnapshot(
                tenant_id=TENANT_ID,
                snapshot_date=today,
                channel=channel,
                category=category,
                actual_margin_pct=actual,
                expected_margin_pct=expected,
                drift_pct=round(actual - expected, 2),
                threshold_exceeded=exceeded,
                variance_reason=reason,
                data_completeness="complete",
            )
        )
    return snapshots


def build_inventory_risk(today: date) -> list[InventoryRiskSnapshot]:
    """One inventory-risk row per catalogue SKU for the latest snapshot date."""
    snapshots: list[InventoryRiskSnapshot] = []
    for p in PRODUCTS:
        snapshots.append(
            InventoryRiskSnapshot(
                tenant_id=TENANT_ID,
                snapshot_date=today,
                sku=p["sku"],
                product_title=p["title"],
                variant_title=p["variant"],
                current_quantity=p["on_hand"],
                reorder_point=p["reorder"],
                status=p["inv_status"],
                daily_velocity_30d=p["daily_velocity"],
                days_to_stockout=p["days_to_stockout"],
                weekly_velocity_90d=round(p["daily_velocity"] * 7, 2),
                weeks_of_cover=p["weeks_of_cover"],
                days_since_last_sale=p["days_since_sale"],
                capital_at_risk=p["capital_at_risk"],
                seasonal_adjustment_applied=False,
                confidence=p["confidence"],
                data_completeness="complete",
            )
        )
    return snapshots


def build_operational_impact(today: date) -> list[OperationalImpactSnapshot]:
    """One operational-impact row per catalogue SKU for the latest date."""
    snapshots: list[OperationalImpactSnapshot] = []
    for p in PRODUCTS:
        velocity = p["daily_velocity"]
        unit_price = p["unit_price"]
        op_status = p["op_status"]
        units_sold = round(velocity * 30)
        return_qty = round(units_sold * p["return_rate"] / 100.0)
        return_cpu = round(unit_price * 0.12, 2)
        days_to_restock = 10.0 if op_status in ("high", "medium") else 7.0
        lost_revenue = (
            round(velocity * days_to_restock * unit_price, 2)
            if op_status in ("high", "medium")
            else None
        )
        snapshots.append(
            OperationalImpactSnapshot(
                tenant_id=TENANT_ID,
                snapshot_date=today,
                sku=p["sku"],
                product_title=p["title"],
                variant_title=p["variant"],
                inventory_status=op_status,
                daily_velocity_30d=velocity,
                avg_unit_price=unit_price,
                days_to_restock_estimate=days_to_restock,
                stockout_lost_revenue_estimate=lost_revenue,
                repeat_purchase_risk=p["repeat_risk"],
                logistics_cost_per_unit=p["logistics_cpu"],
                logistics_cost_total_30d=round(p["logistics_cpu"] * units_sold, 2),
                logistics_margin_impact_pct=round(
                    p["logistics_cpu"] / unit_price * 100, 1
                ),
                units_sold_30d=units_sold,
                return_quantity_30d=return_qty,
                return_rate_30d_pct=p["return_rate"],
                return_cost_per_unit=return_cpu,
                return_cost_total_30d=round(return_cpu * return_qty, 2),
                confidence=p["confidence"],
                data_completeness="complete",
            )
        )
    return snapshots


def build_acquisition_cohorts(
    months: list[date], now: datetime
) -> list[AcquisitionCohort]:
    """Acquisition context per month x channel (read-only retention view)."""
    # channel -> (base_count, count_step, base_cac, cac_step, base_aov,
    #             aov_step, base_repeat90, repeat_step)
    config = {
        "shopify_organic": (900, 60, 12.2, -0.1, 96.0, 1.0, 0.330, 0.005),
        "meta_ads": (1500, 40, 31.0, 0.6, 88.0, 0.5, 0.210, 0.004),
        "google_ads": (1100, 50, 27.0, 0.2, 90.0, 0.6, 0.250, 0.004),
    }
    last_idx = len(months) - 1
    cohorts: list[AcquisitionCohort] = []
    for idx, first in enumerate(months):
        end = _month_end(first)
        for channel in ACQ_CHANNELS:
            base_c, c_step, base_cac, cac_step, base_aov, aov_step, rep, rep_s = (
                config[channel]
            )
            count = int(base_c + c_step * idx)
            cac = _inr(base_cac + cac_step * idx)
            aov = _inr(base_aov + aov_step * idx)
            # Newest complete month: 90-day signal has not fully matured yet.
            repeat90 = None if idx == last_idx else round(rep + rep_s * idx, 4)
            cohorts.append(
                AcquisitionCohort(
                    tenant_id=TENANT_ID,
                    cohort_start_date=first,
                    cohort_end_date=end,
                    cohort_grain="month",
                    channel=channel,
                    new_customer_count=count,
                    blended_cac=cac,
                    first_order_aov=aov,
                    total_acquisition_spend=round(count * cac, 2),
                    repeat_purchase_rate_90d=repeat90,
                    synced_at=now - timedelta(hours=6),
                )
            )
    return cohorts


def build_cohort_snapshots(months: list[date]) -> list[CohortSnapshot]:
    """Cohort metrics per month x observation window for side-by-side compare."""
    window_factor = {30: 0.55, 60: 0.80, 90: 1.0}
    snapshots: list[CohortSnapshot] = []
    for idx, first in enumerate(months):
        end = _month_end(first)
        customer_count = 1800 + idx * 220
        base_repeat = 0.27 + idx * 0.012
        base_churn = 0.55 - idx * 0.015
        aov = _inr(86.0 + idx * 1.5)
        repeat_freq = round(1.6 + idx * 0.03, 2)
        for window in COHORT_WINDOWS:
            factor = window_factor[window]
            repeat_rate = round(min(base_repeat * factor, 0.95), 4)
            churn_rate = round(min(base_churn + (1 - factor) * 0.1, 0.95), 4)
            revenue = round(customer_count * aov * (1.0 + repeat_rate), 2)
            snapshots.append(
                CohortSnapshot(
                    tenant_id=TENANT_ID,
                    cohort_start_date=first,
                    cohort_end_date=end,
                    cohort_grain="month",
                    observation_window_days=window,
                    customer_count=customer_count,
                    repeat_rate=repeat_rate,
                    churn_rate=churn_rate,
                    avg_order_value=aov,
                    total_revenue=revenue,
                    repeat_purchase_frequency=repeat_freq,
                )
            )
    return snapshots


def build_recommendations(today: date, now: datetime) -> list[Recommendation]:
    """Recommendations across all domains, spanning the status lifecycle."""
    recs: list[Recommendation] = []

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="ACQ-001",
            domain="acquisition",
            snapshot_date=today,
            affected_area="Meta Ads - Prospecting",
            signal_summary=(
                "Meta prospecting CAC rose 28% over 14 days while "
                "contribution stayed flat, signalling efficiency loss in "
                "cold audiences."
            ),
            suggested_action=(
                "Shift 15% of Meta prospecting budget to Shopify organic and "
                "Google branded search, where blended CAC is ~60% lower."
            ),
            estimated_impact=42_000.0,
            confidence_level="high",
            data_freshness_context="Meta synced 2h ago; Shopify synced 1h ago.",
            status="new",
            priority=90,
            impact_score=0.88,
            evidence={
                "meta_cac_change_pct": 28.4,
                "blended_cac_meta": _inr(34.10),
                "blended_cac_shopify": _inr(12.20),
                "window_days": 14,
            },
        )
    )

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="MRG-001",
            domain="finance",
            snapshot_date=today,
            affected_area="Running - Shopify",
            signal_summary=(
                "Contribution margin on Running shoes drifted -5.5pts below "
                "the 44% baseline, driven by deeper sitewide discounts."
            ),
            suggested_action=(
                "Cap Running-category discounts at 15% and re-test the "
                "free-shipping threshold at ₹6,225 to recover ~4pts of margin."
            ),
            estimated_impact=31_500.0,
            confidence_level="high",
            data_freshness_context="Cost inputs updated 1d ago; orders synced 1h ago.",
            status="reviewed",
            priority=80,
            impact_score=0.81,
            evidence={
                "actual_margin_pct": 38.5,
                "baseline_margin_pct": 44.0,
                "drift_pts": -5.5,
                "discount_depth_pct": 22.0,
            },
            review_note="Validated against finance cost inputs; matches Q3 target.",
        )
    )

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="INV-001",
            domain="inventory",
            snapshot_date=today,
            affected_area="ONE8-RUN-001 - Velocity Runner",
            signal_summary=(
                "Velocity Runner (Black/UK8) will stock out in ~4 days at "
                "current sell-through; it is a top-5 revenue SKU."
            ),
            suggested_action=(
                "Expedite a 300-unit replenishment PO and temporarily pause "
                "paid traffic to the variant to avoid overselling."
            ),
            estimated_impact=26_800.0,
            confidence_level="high",
            data_freshness_context="Inventory synced 1h ago.",
            status="approved",
            priority=85,
            impact_score=0.84,
            evidence={
                "sku": "ONE8-RUN-001",
                "days_to_stockout": 4.3,
                "daily_velocity": 4.2,
                "on_hand": 18,
            },
            approved_at=now - timedelta(days=3),
        )
    )

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="OPS-001",
            domain="operational",
            snapshot_date=today,
            affected_area="ONE8-CAS-002 - Court Casual",
            signal_summary=(
                "Court Casual 30-day return rate is 14.8%, ~2x the catalogue "
                "average, concentrated in the UK 10 size."
            ),
            suggested_action=(
                "Review the size chart and add fit guidance for UK 10; flag "
                "the batch for QA on heel fit."
            ),
            estimated_impact=9_400.0,
            confidence_level="medium",
            data_freshness_context="Orders synced 1h ago; returns synced 3h ago.",
            status="new",
            priority=70,
            impact_score=0.66,
            evidence={
                "sku": "ONE8-CAS-002",
                "return_rate_pct": 14.8,
                "catalogue_avg_pct": 7.4,
            },
        )
    )

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="RET-001",
            domain="retention",
            snapshot_date=today,
            affected_area="One-time buyers - 30-60 days",
            signal_summary=(
                "Repeat rate for the recent cohort is tracking 6pts below "
                "trend; ~1.8k one-time buyers sit in the 30-60 day window."
            ),
            suggested_action=(
                "Launch a 12% winback offer to 30-60 day one-time buyers via "
                "email/SMS, capped to protect margin."
            ),
            estimated_impact=18_200.0,
            confidence_level="high",
            data_freshness_context="Cohorts recomputed 6h ago.",
            status="implemented_externally",
            priority=75,
            impact_score=0.72,
            evidence={
                "segment_size": 1800,
                "offer_pct": 12,
                "expected_response_pct": 9.5,
            },
            approved_at=now - timedelta(days=9),
            implemented_at=now - timedelta(days=6),
        )
    )

    recs.append(
        Recommendation(
            tenant_id=TENANT_ID,
            rule_id="EXC-001",
            domain="executive",
            snapshot_date=today,
            affected_area="Blended contribution margin",
            signal_summary=(
                "Margin-recovery actions across Running and paid media were "
                "implemented last month; the outcome window has now closed."
            ),
            suggested_action=(
                "Lock in discount guardrails and reallocate the recovered "
                "budget into Shopify organic and retention."
            ),
            estimated_impact=58_000.0,
            confidence_level="high",
            data_freshness_context="Outcome window 30d; KPIs synced 1h ago.",
            status="outcome_observed",
            priority=95,
            impact_score=0.91,
            evidence={"actions": ["MRG-001", "ACQ-001"], "window_days": 30},
            approved_at=now - timedelta(days=38),
            implemented_at=now - timedelta(days=35),
            outcome_observed_at=now - timedelta(days=5),
            outcome_metrics_before={
                "contribution_margin_pct": 40.1,
                "cac_payback_period": 5.8,
                "blended_roas": 2.6,
                "return_rate_pct": 8.1,
                "repeat_purchase_rate_pct": 24.0,
                "cac_by_channel": {
                    "meta_ads": _inr(34.1),
                    "google_ads": _inr(28.0),
                    "shopify_organic": _inr(12.2),
                },
                "time_to_insight": 1.0,
            },
            outcome_metrics_after={
                "contribution_margin_pct": 43.4,
                "cac_payback_period": 4.9,
                "blended_roas": 2.9,
                "return_rate_pct": 7.4,
                "repeat_purchase_rate_pct": 26.5,
                "cac_by_channel": {
                    "meta_ads": _inr(29.8),
                    "google_ads": _inr(27.2),
                    "shopify_organic": _inr(12.0),
                },
                "time_to_insight": 0.5,
            },
            outcome_impact_summary={
                "contribution_margin_pct": {
                    "before": 40.1,
                    "after": 43.4,
                    "change": 3.3,
                    "direction": "improved",
                },
                "return_rate_pct": {
                    "before": 8.1,
                    "after": 7.4,
                    "change": -0.7,
                    "direction": "improved",
                },
                "repeat_purchase_rate_pct": {
                    "before": 24.0,
                    "after": 26.5,
                    "change": 2.5,
                    "direction": "improved",
                },
                "guardrail_violation": False,
            },
        )
    )

    # Scale all hand-authored USD impact figures into INR.
    for _r in recs:
        if _r.estimated_impact is not None:
            _r.estimated_impact = _inr(_r.estimated_impact)

    return recs


def build_alert_events(now: datetime, actor_user_id: uuid.UUID) -> list[AlertEventLog]:
    """A short alert history mixing system-created and user-actioned events."""
    # (alert_id, alert_type, event_type, actor, age_days, age_hours, data)
    rows: list[tuple[str, str, str, uuid.UUID | None, int, int, dict]] = [
        (
            "INV-ONE8-RUN-001",
            "inventory_stockout",
            "created",
            None,
            4,
            0,
            {"days_to_stockout": 4.3, "sku": "ONE8-RUN-001"},
        ),
        (
            "INV-ONE8-RUN-001",
            "inventory_stockout",
            "acknowledged",
            actor_user_id,
            3,
            22,
            {"note": "Replenishment PO raised"},
        ),
        (
            "MRG-RUNNING-SHOPIFY",
            "margin_drift",
            "created",
            None,
            3,
            0,
            {"drift_pts": -5.5, "category": "Running"},
        ),
        (
            "CAC-META-PROSPECTING",
            "cac_spike",
            "created",
            None,
            2,
            0,
            {"cac_change_pct": 28.4, "channel": "meta_ads"},
        ),
        (
            "CAC-META-PROSPECTING",
            "cac_spike",
            "acknowledged",
            actor_user_id,
            1,
            21,
            {"note": "Budget shift under review"},
        ),
        (
            "RET-RATE-CAS-002",
            "return_rate",
            "created",
            None,
            1,
            0,
            {"return_rate_pct": 14.8, "sku": "ONE8-CAS-002"},
        ),
    ]
    events: list[AlertEventLog] = []
    for alert_id, alert_type, event_type, actor, days, hours, data in rows:
        events.append(
            AlertEventLog(
                tenant_id=TENANT_ID,
                alert_id=alert_id,
                alert_type=alert_type,
                event_type=event_type,
                actor_user_id=actor,
                event_data=data,
                created_at=now - timedelta(days=days, hours=hours),
            )
        )
    return events


def build_simulations(now: datetime) -> list[Simulation]:
    """Three saved manual simulations with baseline/upside/downside scenarios."""

    def scenario(input_val: float, output_val: float, label: str) -> dict:
        base = {"input": input_val, "output": output_val, "label": label}
        if label == "current_state":
            return base
        base["assumptions"] = (
            {"execution_quality": "perfect", "market_conditions": "favorable"}
            if label == "optimized_best_case"
            else {"execution_quality": "imperfect", "market_conditions": "neutral"}
        )
        return base

    sims: list[Simulation] = []

    # 1) Acquisition: reallocate spend toward efficient channels.
    sims.append(
        Simulation(
            tenant_id=TENANT_ID,
            recommendation_id=None,
            domain="acquisition",
            simulation_type="manual",
            x_star={"value": _inr(127_500.0), "domain": "acquisition"},
            confidence_level="high",
            data_freshness_signal="high",
            metric_completeness_signal="high",
            baseline_scenario=scenario(
                12_450_000.0, 32_370_000.0, "current_state"
            ),
            upside_scenario=scenario(
                10_582_500.0, 36_271_000.0, "optimized_best_case"
            ),
            downside_scenario=scenario(
                10_582_500.0, 25_389_700.0, "optimized_worst_case"
            ),
            simulation_metadata={
                "scenario_label": "Reallocate Meta -> Organic/Google",
                "optimizer": "scipy.optimize.minimize",
                "method": "BFGS",
            },
            created_at=now - timedelta(days=2),
        )
    )

    # 2) Retention: 12% winback offer to one-time buyers.
    sims.append(
        Simulation(
            tenant_id=TENANT_ID,
            recommendation_id=None,
            domain="retention",
            simulation_type="manual",
            x_star={"value": 12.0, "domain": "retention"},
            confidence_level="medium",
            data_freshness_signal="high",
            metric_completeness_signal="medium",
            baseline_scenario=scenario(0.0, 0.0, "current_state"),
            upside_scenario=scenario(12.0, _inr(24_500.0), "optimized_best_case"),
            downside_scenario=scenario(12.0, _inr(11_700.0), "optimized_worst_case"),
            simulation_metadata={
                "scenario_label": "12% winback offer (30-60 day buyers)",
                "segment_size": 1800,
            },
            created_at=now - timedelta(days=1, hours=4),
        )
    )

    # 3) Margin: cap Running discounts to recover contribution margin.
    sims.append(
        Simulation(
            tenant_id=TENANT_ID,
            recommendation_id=None,
            domain="margin",
            simulation_type="manual",
            x_star={"value": 15.0, "domain": "margin"},
            confidence_level="high",
            data_freshness_signal="high",
            metric_completeness_signal="high",
            baseline_scenario=scenario(22.0, 38.5, "current_state"),
            upside_scenario=scenario(15.0, 43.0, "optimized_best_case"),
            downside_scenario=scenario(15.0, 41.0, "optimized_worst_case"),
            simulation_metadata={
                "scenario_label": "Cap Running discount at 15%",
                "metric": "contribution_margin_pct",
            },
            created_at=now - timedelta(hours=20),
        )
    )

    return sims


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _delete_existing_demo_data(db: Session) -> None:
    """Remove this tenant's demo rows so the seed is idempotent.

    Order matters for foreign keys: scenarios -> simulations -> recommendations,
    then the independent snapshot/alert tables.
    """
    sim_ids = list(
        db.scalars(select(Simulation.id).where(Simulation.tenant_id == TENANT_ID))
    )
    if sim_ids:
        db.execute(delete(Scenario).where(Scenario.simulation_id.in_(sim_ids)))
    db.execute(delete(Simulation).where(Simulation.tenant_id == TENANT_ID))
    db.execute(delete(Recommendation).where(Recommendation.tenant_id == TENANT_ID))
    db.execute(delete(AlertEventLog).where(AlertEventLog.tenant_id == TENANT_ID))
    db.execute(
        delete(CostDriverSnapshot).where(CostDriverSnapshot.tenant_id == TENANT_ID)
    )
    db.execute(
        delete(MarginDriftSnapshot).where(MarginDriftSnapshot.tenant_id == TENANT_ID)
    )
    db.execute(
        delete(InventoryRiskSnapshot).where(
            InventoryRiskSnapshot.tenant_id == TENANT_ID
        )
    )
    db.execute(
        delete(OperationalImpactSnapshot).where(
            OperationalImpactSnapshot.tenant_id == TENANT_ID
        )
    )
    db.execute(
        delete(AcquisitionCohort).where(AcquisitionCohort.tenant_id == TENANT_ID)
    )
    db.execute(delete(CohortSnapshot).where(CohortSnapshot.tenant_id == TENANT_ID))


def seed() -> None:
    today = datetime.now(UTC).date()
    now = datetime.now(UTC)
    months = _complete_months(today, 6)

    db = SessionLocal()
    try:
        # 1) Tenant (create once, refresh demo attributes on re-run).
        tenant = db.get(Tenant, TENANT_ID)
        if tenant is None:
            tenant = Tenant(
                id=TENANT_ID,
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                base_currency=CURRENCY,
                locale=LOCALE,
            )
            db.add(tenant)
        else:
            tenant.name = TENANT_NAME
            tenant.base_currency = CURRENCY
            tenant.locale = LOCALE

        # 2) Owner user (matched by email at login).
        user = db.scalar(select(User).where(User.email == OWNER_EMAIL))
        if user is None:
            user = User(
                email=OWNER_EMAIL,
                full_name=OWNER_NAME,
                is_active=True,
            )
            db.add(user)
        else:
            user.is_active = True
        db.flush()  # ensure user.id is available

        # 3) Membership granting brand_admin on this tenant.
        membership = db.scalar(
            select(TenantMembership).where(
                TenantMembership.tenant_id == TENANT_ID,
                TenantMembership.user_id == user.id,
            )
        )
        if membership is None:
            db.add(
                TenantMembership(
                    tenant_id=TENANT_ID,
                    user_id=user.id,
                    role=OWNER_ROLE,
                )
            )
        else:
            membership.role = OWNER_ROLE

        # 4) Replace per-tenant demo data.
        _delete_existing_demo_data(db)

        rows: list[object] = []
        rows += build_cost_drivers(today, now)
        rows += build_margin_drift(today)
        rows += build_inventory_risk(today)
        rows += build_operational_impact(today)
        rows += build_acquisition_cohorts(months, now)
        rows += build_cohort_snapshots(months)
        rows += build_recommendations(today, now)
        rows += build_alert_events(now, user.id)
        rows += build_simulations(now)
        db.add_all(rows)

        db.commit()

        print("Seed complete for tenant 'one8'.")
        print(f"  Tenant id (VITE_PYTHON_API_TENANT): {TENANT_ID}")
        print(f"  Owner email (VITE_PYTHON_API_EMAIL): {OWNER_EMAIL}")
        print("  Password (VITE_PYTHON_API_PASSWORD): any non-empty value")
        print(f"  Base currency: {CURRENCY} ({LOCALE})")
        print(f"  Rows inserted: {len(rows)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
