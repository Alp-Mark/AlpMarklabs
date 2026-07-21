from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from time import sleep
from typing import Any

import sentry_sdk
from backend.app.db.models import (
    AcquisitionMetricsSnapshot,
    AuditEvent,
    CohortRetentionSnapshot,
    CohortReturnSignal,
    ConnectorIntegration,
    CostDriverSnapshot,
    CostInput,
    ExecutiveKpiSnapshot,
    GoogleAdSpend,
    InventoryRiskSnapshot,
    InventoryRiskThreshold,
    MarginDriftSnapshot,
    MarginDriftThreshold,
    MetaAdSpend,
    OperationalImpactSnapshot,
    OptimizationStrategy,
    Recommendation,
    RetentionDailySnapshot,
    SegmentMarginSnapshot,
    ShopifyInventoryItem,
    ShopifyOrder,
    ShopifyOrderLineItem,
    Tenant,
    TenantRuleThreshold,
)
from backend.app.db.session import SessionLocal
from backend.app.recommendations.gap import scan_implementation_gaps
from backend.app.recommendations.outcome import scan_outcome_observations
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker.app.celery_app import celery_app
from worker.app.daily_data_simulator import run_daily_simulation
from worker.app.optimization.strategies.acquisition import (
    BudgetAllocationOptimizer,
)
from worker.app.optimization.strategies.multi_channel import (
    MultiChannelAllocator,
)
from worker.app.optimization.utils.monitoring import (
    log_optimization_failure,
    log_optimization_start,
    log_optimization_success,
)
from worker.app.rules.engine import Rule, RuleEngine, RuleInput
from worker.app.rules.pack import get_rules

logger = logging.getLogger(__name__)

SYNC_RETRY_MAX_ATTEMPTS = 3
SYNC_RETRY_BASE_BACKOFF_SECONDS = 5.0
SYNC_RETRY_MAX_BACKOFF_SECONDS = 30.0
EXECUTIVE_KPI_LOOKBACK_DAYS = 30
ACQUISITION_METRICS_LOOKBACK_DAYS = 30
ACQUISITION_PAYBACK_SCENARIO_MARGIN_DELTA = 0.10
RETENTION_LOOKBACK_DAYS = 365
SEGMENT_MARGIN_PERIOD_DAYS = 30
SEGMENT_HIGH_VALUE_TOP_FRACTION = 0.20
COHORT_RETURN_SIGNAL_LOOKBACK_DAYS = 365
INVENTORY_RISK_VELOCITY_30D_DAYS = 30
INVENTORY_RISK_VELOCITY_90D_DAYS = 90
INVENTORY_RISK_DEFAULT_STOCKOUT_ALERT_DAYS = 7.0
INVENTORY_RISK_DEFAULT_OVERSTOCK_WEEKS = 12.0
INVENTORY_RISK_DEFAULT_SLOW_MIN_QTY = 5
INVENTORY_RISK_DEFAULT_SLOW_MIN_WEEKS_COVER = 4.0
INVENTORY_RISK_DEFAULT_SLOW_MIN_CAPITAL = 0.0
COST_DRIVER_PERIOD_DAYS = 30
CONFIDENCE_HIGH_THRESHOLD_HOURS = 24.0
CONFIDENCE_MEDIUM_THRESHOLD_HOURS = 72.0
MARGIN_DRIFT_PERIOD_DAYS = 30
OPERATIONAL_IMPACT_PERIOD_DAYS = 30
OPERATIONAL_IMPACT_DEFAULT_RESTOCK_DAYS = 7.0
OPERATIONAL_IMPACT_REPEAT_RISK_HIGH_RETURN_PCT = 20.0
OPERATIONAL_IMPACT_REPEAT_RISK_MEDIUM_RETURN_PCT = 10.0


@celery_app.task(name="worker.app.tasks.ping")
def ping() -> str:
    return "pong"


def run_connector_sync_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> int:
    synced_at = now or datetime.now(UTC)
    db = session_factory()
    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.status == "connected"
                )
            )
        )
        for connector in connectors:
            connector.last_synced_at = synced_at
        db.commit()
        return len(connectors)
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_connector_sync_schedule")
def run_connector_sync_schedule() -> int:
    return run_connector_sync_job()


def run_token_expiry_monitoring_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    warning_threshold = current_time + timedelta(days=7)
    warning_count = 0
    expired_count = 0

    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    db = session_factory()
    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.auth_mode == "oauth",
                    ConnectorIntegration.oauth_expires_at.is_not(None),
                )
            )
        )
        for connector in connectors:
            expires_at = connector.oauth_expires_at
            if expires_at is None:
                continue
            expires_at = _as_utc(expires_at)

            if expires_at <= current_time:
                if connector.oauth_expired_alert_sent_at is None:
                    connector.oauth_expired_alert_sent_at = current_time
                    connector.error_message = (
                        "OAuth token expired. Reauthorize connector to resume sync."
                    )
                    db.add(
                        AuditEvent(
                            tenant_id=connector.tenant_id,
                            actor_user_id=None,
                            action="connector.oauth_token_expired",
                            entity_type="connector",
                            entity_id=str(connector.id),
                            details={
                                "source": connector.source,
                                "expires_at": expires_at.isoformat(),
                            },
                        )
                    )
                    expired_count += 1
                continue

            if (
                expires_at <= warning_threshold
                and connector.oauth_expiry_warning_sent_at is None
            ):
                connector.oauth_expiry_warning_sent_at = current_time
                db.add(
                    AuditEvent(
                        tenant_id=connector.tenant_id,
                        actor_user_id=None,
                        action="connector.oauth_token_expiry_warning",
                        entity_type="connector",
                        entity_id=str(connector.id),
                        details={
                            "source": connector.source,
                            "expires_at": expires_at.isoformat(),
                            "days_remaining": max((expires_at - current_time).days, 0),
                        },
                    )
                )
                warning_count += 1

        db.commit()
        return {"warning_count": warning_count, "expired_count": expired_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_token_expiry_monitoring_schedule")
def run_token_expiry_monitoring_schedule() -> dict[str, int]:
    return run_token_expiry_monitoring_job()


def _compute_median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return 0.0 if current == 0 else None
    return round(((current - previous) / previous) * 100, 2)


def run_executive_kpi_computation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    snapshot_date = current_time.date()
    period_end_date = snapshot_date
    period_start_date = snapshot_date - timedelta(days=EXECUTIVE_KPI_LOOKBACK_DAYS - 1)
    period_start_dt = datetime.combine(period_start_date, datetime.min.time(), UTC)
    period_end_dt = datetime.combine(
        period_end_date + timedelta(days=1),
        datetime.min.time(),
        UTC,
    )

    db = session_factory()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
        computed_count = 0

        for tenant in tenants:
            revenue_raw = db.scalar(
                select(func.sum(ShopifyOrder.total_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at < period_end_dt,
                )
            )
            revenue_amount = round(float(revenue_raw or 0.0), 2)

            meta_spend_raw = db.scalar(
                select(func.sum(MetaAdSpend.spend_amount)).where(
                    MetaAdSpend.tenant_id == tenant.id,
                    MetaAdSpend.spend_date >= period_start_date,
                    MetaAdSpend.spend_date <= period_end_date,
                )
            )
            google_spend_raw = db.scalar(
                select(func.sum(GoogleAdSpend.spend_amount)).where(
                    GoogleAdSpend.tenant_id == tenant.id,
                    GoogleAdSpend.spend_date >= period_start_date,
                    GoogleAdSpend.spend_date <= period_end_date,
                )
            )
            ad_spend_amount = round(
                float(meta_spend_raw or 0.0) + float(google_spend_raw or 0.0),
                2,
            )

            # Read COGS % from cost_inputs (Finance Controller configures this).
            # Falls back to 0 if not configured — CM will show as marketing margin only.
            cogs_input = db.scalar(
                select(CostInput).where(
                    CostInput.tenant_id == tenant.id,
                    CostInput.input_type == "cogs",
                    CostInput.is_active.is_(True),
                )
            )
            cogs_pct: float = (
                cogs_input.amount
                if cogs_input is not None and cogs_input.unit == "pct_of_revenue"
                else 0.0
            )
            cogs_amount = round(revenue_amount * cogs_pct / 100.0, 2)

            blended_roas = (
                round(revenue_amount / ad_spend_amount, 2)
                if ad_spend_amount > 0
                else 0.0
            )
            contribution_margin_pct = (
                round(
                    ((revenue_amount - cogs_amount - ad_spend_amount) / revenue_amount)
                    * 100,
                    2,
                )
                if revenue_amount > 0
                else 0.0
            )

            previous_snapshot = db.scalar(
                select(ExecutiveKpiSnapshot)
                .where(
                    ExecutiveKpiSnapshot.tenant_id == tenant.id,
                    ExecutiveKpiSnapshot.snapshot_date < snapshot_date,
                )
                .order_by(ExecutiveKpiSnapshot.snapshot_date.desc())
                .limit(1)
            )

            if previous_snapshot is None:
                drift: dict[str, float | None] = {
                    "revenue_amount_pct": 0.0,
                    "ad_spend_amount_pct": 0.0,
                    "blended_roas_pct": 0.0,
                    "contribution_margin_pct_change": 0.0,
                }
            else:
                drift = {
                    "revenue_amount_pct": _pct_change(
                        revenue_amount,
                        previous_snapshot.revenue_amount,
                    ),
                    "ad_spend_amount_pct": _pct_change(
                        ad_spend_amount,
                        previous_snapshot.ad_spend_amount,
                    ),
                    "blended_roas_pct": _pct_change(
                        blended_roas,
                        previous_snapshot.blended_roas,
                    ),
                    "contribution_margin_pct_change": round(
                        contribution_margin_pct
                        - previous_snapshot.contribution_margin_pct,
                        2,
                    ),
                }

            snapshot = db.scalar(
                select(ExecutiveKpiSnapshot).where(
                    ExecutiveKpiSnapshot.tenant_id == tenant.id,
                    ExecutiveKpiSnapshot.snapshot_date == snapshot_date,
                )
            )

            if snapshot is None:
                snapshot = ExecutiveKpiSnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=snapshot_date,
                    period_start_date=period_start_date,
                    period_end_date=period_end_date,
                    revenue_amount=revenue_amount,
                    ad_spend_amount=ad_spend_amount,
                    blended_roas=blended_roas,
                    contribution_margin_pct=contribution_margin_pct,
                    drift=drift,
                )
                db.add(snapshot)
            else:
                snapshot.period_start_date = period_start_date
                snapshot.period_end_date = period_end_date
                snapshot.revenue_amount = revenue_amount
                snapshot.ad_spend_amount = ad_spend_amount
                snapshot.blended_roas = blended_roas
                snapshot.contribution_margin_pct = contribution_margin_pct
                snapshot.drift = drift

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.executive_snapshot_computed",
                    entity_type="executive_kpi_snapshot",
                    entity_id=str(snapshot.id),
                    details={
                        "snapshot_date": snapshot_date.isoformat(),
                        "period_start_date": period_start_date.isoformat(),
                        "period_end_date": period_end_date.isoformat(),
                        "revenue_amount": revenue_amount,
                        "ad_spend_amount": ad_spend_amount,
                        "blended_roas": blended_roas,
                        "contribution_margin_pct": contribution_margin_pct,
                        "drift": drift,
                    },
                )
            )

            computed_count += 1

        db.commit()
        return {"tenant_count": len(tenants), "snapshot_count": computed_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_executive_kpi_computation_schedule")
def run_executive_kpi_computation_schedule() -> dict[str, int]:
    return run_executive_kpi_computation_job()


def _compute_payback(
    spend: float,
    revenue: float,
    order_count: int,
    margin_delta: float = 0.0,
) -> float:
    if order_count == 0 or spend == 0:
        return 0.0
    contribution = revenue - spend
    if contribution <= 0:
        return 0.0
    avg_contribution = (contribution / order_count) * (1 + margin_delta)
    if avg_contribution <= 0:
        return 0.0
    cac = spend / order_count
    return round(cac / avg_contribution * ACQUISITION_METRICS_LOOKBACK_DAYS, 2)


def run_acquisition_metrics_computation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    snapshot_date = current_time.date()
    period_end_date = snapshot_date
    period_start_date = (
        snapshot_date - timedelta(days=ACQUISITION_METRICS_LOOKBACK_DAYS - 1)
    )
    period_start_dt = datetime.combine(period_start_date, datetime.min.time(), UTC)
    period_end_dt = datetime.combine(
        period_end_date + timedelta(days=1), datetime.min.time(), UTC
    )

    db = session_factory()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
        snapshot_count = 0

        for tenant in tenants:
            total_revenue_raw = db.scalar(
                select(func.sum(ShopifyOrder.total_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at < period_end_dt,
                )
            )
            total_revenue = float(total_revenue_raw or 0.0)

            total_orders_raw = db.scalar(
                select(func.count(ShopifyOrder.id)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at < period_end_dt,
                )
            )
            total_orders = int(total_orders_raw or 0)

            meta_spend_raw = db.scalar(
                select(func.sum(MetaAdSpend.spend_amount)).where(
                    MetaAdSpend.tenant_id == tenant.id,
                    MetaAdSpend.spend_date >= period_start_date,
                    MetaAdSpend.spend_date <= period_end_date,
                )
            )
            meta_spend = float(meta_spend_raw or 0.0)

            google_spend_raw = db.scalar(
                select(func.sum(GoogleAdSpend.spend_amount)).where(
                    GoogleAdSpend.tenant_id == tenant.id,
                    GoogleAdSpend.spend_date >= period_start_date,
                    GoogleAdSpend.spend_date <= period_end_date,
                )
            )
            google_spend = float(google_spend_raw or 0.0)

            total_spend = meta_spend + google_spend

            channel_rows: list[tuple[str, float]] = [
                ("meta", meta_spend),
                ("google_ads", google_spend),
                ("blended", total_spend),
            ]

            for channel, spend in channel_rows:
                if channel == "blended":
                    revenue = round(total_revenue, 2)
                    orders = total_orders
                elif total_spend > 0:
                    share = spend / total_spend
                    revenue = round(total_revenue * share, 2)
                    orders = round(total_orders * share)
                else:
                    revenue = 0.0
                    orders = 0

                spend = round(spend, 2)
                roas = round(revenue / spend, 2) if spend > 0 else 0.0
                cac = round(spend / orders, 2) if orders > 0 else 0.0
                cm_pct = (
                    round((revenue - spend) / revenue * 100, 2)
                    if revenue > 0
                    else 0.0
                )
                payback = _compute_payback(spend, revenue, orders)
                payback_upside = _compute_payback(
                    spend,
                    revenue,
                    orders,
                    ACQUISITION_PAYBACK_SCENARIO_MARGIN_DELTA,
                )
                payback_downside = _compute_payback(
                    spend,
                    revenue,
                    orders,
                    -ACQUISITION_PAYBACK_SCENARIO_MARGIN_DELTA,
                )

                existing = db.scalar(
                    select(AcquisitionMetricsSnapshot).where(
                        AcquisitionMetricsSnapshot.tenant_id == tenant.id,
                        AcquisitionMetricsSnapshot.channel == channel,
                        AcquisitionMetricsSnapshot.snapshot_date == snapshot_date,
                    )
                )

                if existing is None:
                    row = AcquisitionMetricsSnapshot(
                        tenant_id=tenant.id,
                        channel=channel,
                        snapshot_date=snapshot_date,
                        period_start_date=period_start_date,
                        period_end_date=period_end_date,
                        ad_spend_amount=spend,
                        revenue_attributed=revenue,
                        order_count=orders,
                        roas=roas,
                        cac=cac,
                        contribution_margin_pct=cm_pct,
                        payback_period_days=payback,
                        payback_upside_days=payback_upside,
                        payback_downside_days=payback_downside,
                    )
                    db.add(row)
                else:
                    existing.period_start_date = period_start_date
                    existing.period_end_date = period_end_date
                    existing.ad_spend_amount = spend
                    existing.revenue_attributed = revenue
                    existing.order_count = orders
                    existing.roas = roas
                    existing.cac = cac
                    existing.contribution_margin_pct = cm_pct
                    existing.payback_period_days = payback
                    existing.payback_upside_days = payback_upside
                    existing.payback_downside_days = payback_downside
                    row = existing

                db.add(
                    AuditEvent(
                        tenant_id=tenant.id,
                        actor_user_id=None,
                        action="kpi.acquisition_metrics_computed",
                        entity_type="acquisition_metrics_snapshot",
                        entity_id=str(row.id),
                        details={
                            "channel": channel,
                            "snapshot_date": snapshot_date.isoformat(),
                            "roas": roas,
                            "cac": cac,
                            "contribution_margin_pct": cm_pct,
                            "payback_period_days": payback,
                        },
                    )
                )
                snapshot_count += 1

        db.commit()
        return {"tenant_count": len(tenants), "snapshot_count": snapshot_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_acquisition_metrics_computation_schedule")
def run_acquisition_metrics_computation_schedule() -> dict[str, int]:
    return run_acquisition_metrics_computation_job()


def run_retention_cohort_computation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    current_time = now or datetime.now(UTC)
    snapshot_date = current_time.date()
    lookback_cohort_start = (
        snapshot_date - timedelta(days=RETENTION_LOOKBACK_DAYS)
    ).strftime("%Y-%m")

    db = session_factory()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
        retention_computed = 0
        cohort_computed = 0

        for tenant in tenants:
            order_objects = list(
                db.scalars(
                    select(ShopifyOrder)
                    .where(
                        ShopifyOrder.tenant_id == tenant.id,
                        ShopifyOrder.customer_id.is_not(None),
                    )
                    .order_by(ShopifyOrder.order_created_at)
                ).all()
            )

            if not order_objects:
                continue

            # Build per-customer chronological order list
            customer_orders: dict[str, list[datetime]] = {}
            for order_obj in order_objects:
                cust_id = order_obj.customer_id
                if cust_id is None:
                    continue
                if cust_id not in customer_orders:
                    customer_orders[cust_id] = []
                customer_orders[cust_id].append(order_obj.order_created_at)

            total_customers = len(customer_orders)
            if total_customers == 0:
                continue

            repeat_customers = sum(
                1 for ol in customer_orders.values() if len(ol) >= 2
            )
            three_plus_customers = sum(
                1 for ol in customer_orders.values() if len(ol) >= 3
            )
            repeat_purchase_rate_pct = (
                round((repeat_customers / total_customers) * 100, 2)
                if total_customers > 0
                else 0.0
            )

            # Brand-specific repurchase cadence: median(order1→order2 gaps)
            days_to_second_order: list[float] = []
            for ol in customer_orders.values():
                if len(ol) >= 2:
                    delta = (ol[1] - ol[0]).total_seconds() / 86400.0
                    if delta >= 0:
                        days_to_second_order.append(delta)
            expected_repurchase_cadence_days = _compute_median(days_to_second_order)

            # Trend vs prior snapshots
            prior_30_snap = db.scalar(
                select(RetentionDailySnapshot).where(
                    RetentionDailySnapshot.tenant_id == tenant.id,
                    RetentionDailySnapshot.snapshot_date
                    == snapshot_date - timedelta(days=30),
                )
            )
            prior_60_snap = db.scalar(
                select(RetentionDailySnapshot).where(
                    RetentionDailySnapshot.tenant_id == tenant.id,
                    RetentionDailySnapshot.snapshot_date
                    == snapshot_date - timedelta(days=60),
                )
            )
            prior_90_snap = db.scalar(
                select(RetentionDailySnapshot).where(
                    RetentionDailySnapshot.tenant_id == tenant.id,
                    RetentionDailySnapshot.snapshot_date
                    == snapshot_date - timedelta(days=90),
                )
            )

            prior_30 = (
                prior_30_snap.repeat_purchase_rate_pct
                if prior_30_snap is not None
                else None
            )
            prior_60 = (
                prior_60_snap.repeat_purchase_rate_pct
                if prior_60_snap is not None
                else None
            )
            prior_90 = (
                prior_90_snap.repeat_purchase_rate_pct
                if prior_90_snap is not None
                else None
            )

            trend_30d = (
                round(repeat_purchase_rate_pct - prior_30, 2)
                if prior_30 is not None
                else None
            )
            trend_60d = (
                round(repeat_purchase_rate_pct - prior_60, 2)
                if prior_60 is not None
                else None
            )
            trend_90d = (
                round(repeat_purchase_rate_pct - prior_90, 2)
                if prior_90 is not None
                else None
            )

            # Lifecycle funnel
            first_to_second_pct = (
                round((repeat_customers / total_customers) * 100, 2)
                if total_customers > 0
                else 0.0
            )
            second_to_repeat_pct = (
                round((three_plus_customers / repeat_customers) * 100, 2)
                if repeat_customers > 0
                else 0.0
            )
            lifecycle_funnel: dict[str, object] = {
                "first_order_count": total_customers,
                "second_order_count": repeat_customers,
                "repeat_cadence_count": three_plus_customers,
                "first_to_second_pct": first_to_second_pct,
                "second_to_repeat_pct": second_to_repeat_pct,
            }

            # Churn risk buckets (brand-specific cadence)
            healthy_count = 0
            mild_risk_count = 0
            high_risk_count = 0
            churned_count = 0
            if expected_repurchase_cadence_days is not None:
                for ol in customer_orders.values():
                    last_order_dt = ol[-1]
                    if last_order_dt.tzinfo is None:
                        last_order_dt = last_order_dt.replace(tzinfo=UTC)
                    silence_days = (
                        current_time - last_order_dt
                    ).total_seconds() / 86400.0
                    ratio = silence_days / expected_repurchase_cadence_days
                    if ratio < 1.0:
                        healthy_count += 1
                    elif ratio < 1.5:
                        mild_risk_count += 1
                    elif ratio < 2.0:
                        high_risk_count += 1
                    else:
                        churned_count += 1

            churn_risk_summary: dict[str, object] = {
                "expected_cadence_days": expected_repurchase_cadence_days,
                "healthy_count": healthy_count,
                "mild_risk_count": mild_risk_count,
                "high_risk_count": high_risk_count,
                "churned_count": churned_count,
            }

            # Upsert RetentionDailySnapshot
            daily_snap = db.scalar(
                select(RetentionDailySnapshot).where(
                    RetentionDailySnapshot.tenant_id == tenant.id,
                    RetentionDailySnapshot.snapshot_date == snapshot_date,
                )
            )
            if daily_snap is None:
                daily_snap = RetentionDailySnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=snapshot_date,
                    total_customers=total_customers,
                    repeat_customers=repeat_customers,
                    repeat_purchase_rate_pct=repeat_purchase_rate_pct,
                    trend_30d=trend_30d,
                    trend_60d=trend_60d,
                    trend_90d=trend_90d,
                    expected_repurchase_cadence_days=expected_repurchase_cadence_days,
                    lifecycle_funnel=lifecycle_funnel,
                    churn_risk_summary=churn_risk_summary,
                )
                db.add(daily_snap)
            else:
                daily_snap.total_customers = total_customers
                daily_snap.repeat_customers = repeat_customers
                daily_snap.repeat_purchase_rate_pct = repeat_purchase_rate_pct
                daily_snap.trend_30d = trend_30d
                daily_snap.trend_60d = trend_60d
                daily_snap.trend_90d = trend_90d
                daily_snap.expected_repurchase_cadence_days = (
                    expected_repurchase_cadence_days
                )
                daily_snap.lifecycle_funnel = lifecycle_funnel
                daily_snap.churn_risk_summary = churn_risk_summary

            retention_computed += 1

            # Per monthly cohort snapshots (within lookback window)
            cohort_customer_map: dict[str, list[str]] = {}
            for cust_id, ol in customer_orders.items():
                cohort_month = ol[0].strftime("%Y-%m")
                if cohort_month < lookback_cohort_start:
                    continue
                if cohort_month not in cohort_customer_map:
                    cohort_customer_map[cohort_month] = []
                cohort_customer_map[cohort_month].append(cust_id)

            for cohort_month, cohort_customer_ids in cohort_customer_map.items():
                cohort_size = len(cohort_customer_ids)
                repeat_in_cohort = sum(
                    1
                    for cid in cohort_customer_ids
                    if len(customer_orders[cid]) >= 2
                )
                cohort_rate_pct = (
                    round((repeat_in_cohort / cohort_size) * 100, 2)
                    if cohort_size > 0
                    else 0.0
                )
                year, month = int(cohort_month[:4]), int(cohort_month[5:])
                cohort_start_date = date(year, month, 1)
                days_since_cohort_start = (snapshot_date - cohort_start_date).days

                cohort_cadence_values: list[float] = []
                for cid in cohort_customer_ids:
                    ol_for_cid = customer_orders[cid]
                    if len(ol_for_cid) >= 2:
                        delta = (
                            ol_for_cid[1] - ol_for_cid[0]
                        ).total_seconds() / 86400.0
                        if delta >= 0:
                            cohort_cadence_values.append(delta)
                avg_days_to_second_order = _compute_median(cohort_cadence_values)

                cohort_snap = db.scalar(
                    select(CohortRetentionSnapshot).where(
                        CohortRetentionSnapshot.tenant_id == tenant.id,
                        CohortRetentionSnapshot.cohort_month == cohort_month,
                        CohortRetentionSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if cohort_snap is None:
                    cohort_snap = CohortRetentionSnapshot(
                        tenant_id=tenant.id,
                        cohort_month=cohort_month,
                        snapshot_date=snapshot_date,
                        cohort_size=cohort_size,
                        repeat_customer_count=repeat_in_cohort,
                        repeat_purchase_rate_pct=cohort_rate_pct,
                        days_since_cohort_start=days_since_cohort_start,
                        avg_days_to_second_order=avg_days_to_second_order,
                    )
                    db.add(cohort_snap)
                else:
                    cohort_snap.cohort_size = cohort_size
                    cohort_snap.repeat_customer_count = repeat_in_cohort
                    cohort_snap.repeat_purchase_rate_pct = cohort_rate_pct
                    cohort_snap.days_since_cohort_start = days_since_cohort_start
                    cohort_snap.avg_days_to_second_order = avg_days_to_second_order

                cohort_computed += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.retention_snapshot_computed",
                    entity_type="retention_daily_snapshot",
                    entity_id=str(daily_snap.id),
                    details={
                        "snapshot_date": snapshot_date.isoformat(),
                        "total_customers": total_customers,
                        "repeat_customers": repeat_customers,
                        "repeat_purchase_rate_pct": repeat_purchase_rate_pct,
                        "cohort_snapshot_count": len(cohort_customer_map),
                    },
                )
            )

        db.commit()
        return {
            "retention_snapshot_count": retention_computed,
            "cohort_snapshot_count": cohort_computed,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_retention_cohort_computation_schedule")
def run_retention_cohort_computation_schedule() -> dict[str, int]:
    return run_retention_cohort_computation_job()


def _default_shopify_order_fetcher(
    connector: ConnectorIntegration,
    now: datetime,
) -> list[dict[str, object]]:
    # Return empty list - no test orders in production.
    # Real Shopify API integration should provide actual order fetcher.
    return []


def _record_connector_sync_failure(
    db: Session,
    *,
    connector: ConnectorIntegration,
    source: str,
    job_name: str,
    reason: str,
    failed_at: datetime,
) -> None:
    normalized_reason = reason.strip() or "unknown sync error"

    def _source_label(value: str) -> str:
        labels = {
            "shopify": "Shopify",
            "meta": "Meta Ads",
            "google_ads": "Google Ads",
        }
        return labels.get(value, value)

    def _map_sync_error(raw_reason: str) -> tuple[str, str, str]:
        lowered = raw_reason.lower()
        source_label = _source_label(source)

        if (
            "unauthorized" in lowered
            or "forbidden" in lowered
            or "invalid_grant" in lowered
            or "token" in lowered
        ):
            return (
                "AUTH_REAUTH_REQUIRED",
                (
                    f"{source_label} authorization is invalid or expired. "
                    "Reauthorize this connector to resume sync."
                ),
                "Open connector settings and reauthorize the integration.",
            )

        if (
            "quota" in lowered
            or "rate limit" in lowered
            or "too many requests" in lowered
        ):
            return (
                "RATE_LIMITED",
                (
                    f"{source_label} API rate limit was reached during sync. "
                    "Sync will need a retry after cooldown."
                ),
                "Retry later or reduce sync frequency and API load.",
            )

        if (
            "timeout" in lowered
            or "timed out" in lowered
            or "connection" in lowered
            or "network" in lowered
        ):
            return (
                "NETWORK_TIMEOUT",
                (
                    f"{source_label} sync timed out while fetching data. "
                    "Temporary network/provider disruption is likely."
                ),
                "Retry sync and verify provider availability/connectivity.",
            )

        return (
            "UNKNOWN_PROVIDER_ERROR",
            (
                f"{source_label} sync failed due to an unexpected provider error. "
                "Review logs and retry."
            ),
            "Inspect connector logs and retry. Escalate if the issue persists.",
        )

    error_code, actionable_message, suggested_action = _map_sync_error(
        normalized_reason
    )
    connector.error_message = actionable_message[:500]

    db.add(
        AuditEvent(
            tenant_id=connector.tenant_id,
            actor_user_id=None,
            action="alert.connector_sync_failure_created",
            entity_type="connector",
            entity_id=str(connector.id),
            details={
                "source": source,
                "job_name": job_name,
                "reason": normalized_reason,
                "error_code": error_code,
                "actionable_message": actionable_message,
                "suggested_action": suggested_action,
                "failed_at": failed_at.isoformat(),
            },
        )
    )


def _run_with_retry_and_capped_backoff(
    operation: Callable[[], list[dict[str, object]]],
    *,
    max_attempts: int,
    base_backoff_seconds: float,
    max_backoff_seconds: float,
    sleep_fn: Callable[[float], None],
) -> list[dict[str, object]]:
    attempt = 1
    while True:
        try:
            return operation()
        except Exception:
            if attempt >= max_attempts:
                raise
            backoff_seconds = min(
                base_backoff_seconds * (2 ** (attempt - 1)),
                max_backoff_seconds,
            )
            sleep_fn(backoff_seconds)
            attempt += 1


def run_shopify_order_sync_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
    order_fetcher: Callable[
        [ConnectorIntegration, datetime],
        list[dict[str, object]],
    ] = _default_shopify_order_fetcher,
    max_attempts: int = SYNC_RETRY_MAX_ATTEMPTS,
    base_backoff_seconds: float = SYNC_RETRY_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = SYNC_RETRY_MAX_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, int]:
    synced_at = now or datetime.now(UTC)
    db = session_factory()
    synced_connectors = 0
    upserted_orders = 0

    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.source == "shopify",
                    ConnectorIntegration.status == "connected",
                )
            )
        )
        for connector in connectors:
            try:
                def fetch_orders(
                    connector_for_retry: ConnectorIntegration = connector,
                    synced_at_for_retry: datetime = synced_at,
                ) -> list[dict[str, object]]:
                    return order_fetcher(connector_for_retry, synced_at_for_retry)

                orders = _run_with_retry_and_capped_backoff(
                    fetch_orders,
                    max_attempts=max_attempts,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    sleep_fn=sleep_fn,
                )
                for order in orders:
                    external_order_id = str(order["external_order_id"])
                    existing = db.scalar(
                        select(ShopifyOrder).where(
                            ShopifyOrder.tenant_id == connector.tenant_id,
                            ShopifyOrder.connector_id == connector.id,
                            ShopifyOrder.external_order_id == external_order_id,
                        )
                    )
                    order_created_at = order["order_created_at"]
                    if not isinstance(order_created_at, datetime):
                        raise ValueError("order_created_at must be a datetime value")
                    total_amount = order["total_amount"]
                    if not isinstance(total_amount, int | float):
                        raise ValueError("total_amount must be numeric")

                    discount_amount_raw = order.get("discount_amount")
                    shipping_amount_raw = order.get("shipping_amount")
                    refund_amount_raw = order.get("refund_amount")
                    is_refunded_raw = order.get("is_refunded", False)

                    discount_amount: float | None = (
                        float(discount_amount_raw)
                        if isinstance(discount_amount_raw, (int, float))
                        else None
                    )
                    shipping_amount: float | None = (
                        float(shipping_amount_raw)
                        if isinstance(shipping_amount_raw, (int, float))
                        else None
                    )
                    refund_amount: float | None = (
                        float(refund_amount_raw)
                        if isinstance(refund_amount_raw, (int, float))
                        else None
                    )
                    is_refunded: bool = bool(is_refunded_raw)

                    if existing is None:
                        customer_id_raw = order.get("customer_id")
                        db.add(
                            ShopifyOrder(
                                tenant_id=connector.tenant_id,
                                connector_id=connector.id,
                                external_order_id=external_order_id,
                                customer_id=(
                                    str(customer_id_raw)
                                    if customer_id_raw is not None
                                    else None
                                ),
                                order_number=str(order["order_number"]),
                                currency=str(order["currency"]),
                                total_amount=float(total_amount),
                                discount_amount=discount_amount,
                                shipping_amount=shipping_amount,
                                refund_amount=refund_amount,
                                is_refunded=is_refunded,
                                order_created_at=order_created_at,
                                synced_at=synced_at,
                            )
                        )
                    else:
                        customer_id_raw = order.get("customer_id")
                        existing.customer_id = (
                            str(customer_id_raw)
                            if customer_id_raw is not None
                            else None
                        )
                        existing.order_number = str(order["order_number"])
                        existing.currency = str(order["currency"])
                        existing.total_amount = float(total_amount)
                        existing.discount_amount = discount_amount
                        existing.shipping_amount = shipping_amount
                        existing.refund_amount = refund_amount
                        existing.is_refunded = is_refunded
                        existing.order_created_at = order_created_at
                        existing.synced_at = synced_at
                    upserted_orders += 1

                    # Upsert line items — flush first so order.id is available
                    db.flush()
                    order_row = existing or db.scalar(
                        select(ShopifyOrder).where(
                            ShopifyOrder.tenant_id == connector.tenant_id,
                            ShopifyOrder.connector_id == connector.id,
                            ShopifyOrder.external_order_id == external_order_id,
                        )
                    )
                    if order_row is not None:
                        raw_line_items = order.get("line_items")
                        if isinstance(raw_line_items, list):
                            for idx, li in enumerate(raw_line_items):
                                if not isinstance(li, dict):
                                    continue
                                raw_qty = li.get("quantity", 1)
                                li_qty: int = (
                                    int(raw_qty)
                                    if isinstance(raw_qty, (int, float))
                                    else 1
                                )
                                raw_price = li.get("unit_price", 0.0)
                                li_price: float = (
                                    float(raw_price)
                                    if isinstance(raw_price, (int, float))
                                    else 0.0
                                )
                                existing_li = db.scalar(
                                    select(ShopifyOrderLineItem).where(
                                        ShopifyOrderLineItem.tenant_id
                                        == connector.tenant_id,
                                        ShopifyOrderLineItem.order_id == order_row.id,
                                        ShopifyOrderLineItem.line_item_index == idx,
                                    )
                                )
                                if existing_li is None:
                                    db.add(
                                        ShopifyOrderLineItem(
                                            tenant_id=connector.tenant_id,
                                            order_id=order_row.id,
                                            line_item_index=idx,
                                            sku=(
                                                str(li["sku"])
                                                if li.get("sku")
                                                else None
                                            ),
                                            product_title=str(
                                                li.get("product_title", "")
                                            ),
                                            variant_title=(
                                                str(li["variant_title"])
                                                if li.get("variant_title")
                                                else None
                                            ),
                                            quantity=li_qty,
                                            unit_price=li_price,
                                            order_created_at=order_created_at,
                                        )
                                    )
                                else:
                                    existing_li.sku = (
                                        str(li["sku"])
                                        if li.get("sku")
                                        else None
                                    )
                                    existing_li.product_title = str(
                                        li.get("product_title", "")
                                    )
                                    existing_li.variant_title = (
                                        str(li["variant_title"])
                                        if li.get("variant_title")
                                        else None
                                    )
                                    existing_li.quantity = li_qty
                                    existing_li.unit_price = li_price
                                    existing_li.order_created_at = order_created_at

                connector.last_synced_at = synced_at
                connector.error_message = None
                synced_connectors += 1

                db.add(
                    AuditEvent(
                        tenant_id=connector.tenant_id,
                        actor_user_id=None,
                        action="connector.shopify_orders_synced",
                        entity_type="connector",
                        entity_id=str(connector.id),
                        details={
                            "source": "shopify",
                            "orders_synced": len(orders),
                        },
                        severity="debug",
                        category="data_sync",
                        is_system_generated=True,
                        visible_to_personas=["brand_admin", "super_admin"],
                    )
                )
            except Exception as exc:
                _record_connector_sync_failure(
                    db,
                    connector=connector,
                    source="shopify",
                    job_name="shopify_order_sync",
                    reason=str(exc),
                    failed_at=synced_at,
                )

        db.commit()
        return {
            "connector_count": synced_connectors,
            "order_upsert_count": upserted_orders,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_shopify_order_sync_schedule")
def run_shopify_order_sync_schedule() -> dict[str, int]:
    return run_shopify_order_sync_job()


def _default_shopify_inventory_fetcher(
    connector: ConnectorIntegration,
    now: datetime,
) -> list[dict[str, object]]:
    # Return empty list - no test inventory in production.
    # Real Shopify API integration should provide actual inventory fetcher.
    return []


def run_shopify_inventory_sync_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
    inventory_fetcher: Callable[
        [ConnectorIntegration, datetime],
        list[dict[str, object]],
    ] = _default_shopify_inventory_fetcher,
    max_attempts: int = SYNC_RETRY_MAX_ATTEMPTS,
    base_backoff_seconds: float = SYNC_RETRY_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = SYNC_RETRY_MAX_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, int]:
    synced_at = now or datetime.now(UTC)
    db = session_factory()
    synced_connectors = 0
    upserted_items = 0

    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.source == "shopify",
                    ConnectorIntegration.status == "connected",
                )
            )
        )
        for connector in connectors:
            try:
                def fetch_inventory(
                    connector_for_retry: ConnectorIntegration = connector,
                    synced_at_for_retry: datetime = synced_at,
                ) -> list[dict[str, object]]:
                    return inventory_fetcher(
                        connector_for_retry,
                        synced_at_for_retry,
                    )

                items = _run_with_retry_and_capped_backoff(
                    fetch_inventory,
                    max_attempts=max_attempts,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    sleep_fn=sleep_fn,
                )
                for item in items:
                    external_inventory_item_id = str(item["external_inventory_item_id"])
                    existing = db.scalar(
                        select(ShopifyInventoryItem).where(
                            ShopifyInventoryItem.tenant_id == connector.tenant_id,
                            ShopifyInventoryItem.connector_id == connector.id,
                            ShopifyInventoryItem.external_inventory_item_id
                            == external_inventory_item_id,
                        )
                    )
                    available_quantity = item["available_quantity"]
                    if not isinstance(available_quantity, int):
                        raise ValueError("available_quantity must be int")

                    reorder_point_raw = item.get("reorder_point")
                    cost_per_unit_raw = item.get("cost_per_unit")
                    location_id_raw = item.get("location_id")

                    reorder_point: int | None = (
                        int(reorder_point_raw)
                        if isinstance(reorder_point_raw, int)
                        else None
                    )
                    cost_per_unit: float | None = (
                        float(cost_per_unit_raw)
                        if isinstance(cost_per_unit_raw, (int, float))
                        else None
                    )

                    if existing is None:
                        db.add(
                            ShopifyInventoryItem(
                                tenant_id=connector.tenant_id,
                                connector_id=connector.id,
                                external_inventory_item_id=external_inventory_item_id,
                                sku=str(item["sku"]),
                                product_title=str(item["product_title"]),
                                variant_title=(
                                    str(item["variant_title"])
                                    if item["variant_title"] is not None
                                    else None
                                ),
                                available_quantity=available_quantity,
                                reorder_point=reorder_point,
                                cost_per_unit=cost_per_unit,
                                location_id=(
                                    str(location_id_raw)
                                    if location_id_raw is not None
                                    else None
                                ),
                                synced_at=synced_at,
                            )
                        )
                    else:
                        existing.sku = str(item["sku"])
                        existing.product_title = str(item["product_title"])
                        existing.variant_title = (
                            str(item["variant_title"])
                            if item["variant_title"] is not None
                            else None
                        )
                        existing.available_quantity = available_quantity
                        existing.reorder_point = reorder_point
                        existing.cost_per_unit = cost_per_unit
                        existing.location_id = (
                            str(location_id_raw)
                            if location_id_raw is not None
                            else None
                        )
                        existing.synced_at = synced_at
                    upserted_items += 1

                connector.last_synced_at = synced_at
                connector.error_message = None
                synced_connectors += 1
                db.add(
                    AuditEvent(
                        tenant_id=connector.tenant_id,
                        actor_user_id=None,
                        action="connector.shopify_inventory_synced",
                        entity_type="connector",
                        entity_id=str(connector.id),
                        details={
                            "source": "shopify",
                            "inventory_items_synced": len(items),
                        },
                        severity="debug",
                        category="data_sync",
                        is_system_generated=True,
                        visible_to_personas=["brand_admin", "super_admin"],
                    )
                )
            except Exception as exc:
                _record_connector_sync_failure(
                    db,
                    connector=connector,
                    source="shopify",
                    job_name="shopify_inventory_sync",
                    reason=str(exc),
                    failed_at=synced_at,
                )

        db.commit()
        return {
            "connector_count": synced_connectors,
            "inventory_upsert_count": upserted_items,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_shopify_inventory_sync_schedule")
def run_shopify_inventory_sync_schedule() -> dict[str, int]:
    return run_shopify_inventory_sync_job()


def _default_meta_spend_fetcher(
    connector: ConnectorIntegration,
    now: datetime,
) -> list[dict[str, object]]:
    base_id = str(connector.id).replace("-", "")[:8]
    spend_date = (now - timedelta(days=1)).date()
    return [
        {
            "external_campaign_id": f"{base_id}-meta-001",
            "campaign_name": "Meta Prospecting - Core",
            "spend_date": spend_date,
            "currency": "USD",
            "spend_amount": 312.40,
        },
        {
            "external_campaign_id": f"{base_id}-meta-002",
            "campaign_name": "Meta Retargeting - Cart 7D",
            "spend_date": spend_date,
            "currency": "USD",
            "spend_amount": 128.75,
        },
    ]


def run_meta_spend_sync_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
    spend_fetcher: Callable[
        [ConnectorIntegration, datetime],
        list[dict[str, object]],
    ] = _default_meta_spend_fetcher,
    max_attempts: int = SYNC_RETRY_MAX_ATTEMPTS,
    base_backoff_seconds: float = SYNC_RETRY_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = SYNC_RETRY_MAX_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, int]:
    synced_at = now or datetime.now(UTC)
    db = session_factory()
    synced_connectors = 0
    upserted_rows = 0

    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.source == "meta",
                    ConnectorIntegration.status == "connected",
                )
            )
        )
        for connector in connectors:
            try:
                def fetch_meta_spend(
                    connector_for_retry: ConnectorIntegration = connector,
                    synced_at_for_retry: datetime = synced_at,
                ) -> list[dict[str, object]]:
                    return spend_fetcher(connector_for_retry, synced_at_for_retry)

                rows = _run_with_retry_and_capped_backoff(
                    fetch_meta_spend,
                    max_attempts=max_attempts,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    sleep_fn=sleep_fn,
                )
                for row in rows:
                    external_campaign_id = str(row["external_campaign_id"])
                    spend_date = row["spend_date"]
                    if not isinstance(spend_date, date):
                        raise ValueError("spend_date must be a date")
                    spend_amount = row["spend_amount"]
                    if not isinstance(spend_amount, int | float):
                        raise ValueError("spend_amount must be numeric")

                    existing = db.scalar(
                        select(MetaAdSpend).where(
                            MetaAdSpend.tenant_id == connector.tenant_id,
                            MetaAdSpend.connector_id == connector.id,
                            MetaAdSpend.external_campaign_id == external_campaign_id,
                            MetaAdSpend.spend_date == spend_date,
                        )
                    )

                    if existing is None:
                        db.add(
                            MetaAdSpend(
                                tenant_id=connector.tenant_id,
                                connector_id=connector.id,
                                external_campaign_id=external_campaign_id,
                                campaign_name=str(row["campaign_name"]),
                                spend_date=spend_date,
                                currency=str(row["currency"]),
                                spend_amount=float(spend_amount),
                                synced_at=synced_at,
                            )
                        )
                    else:
                        existing.campaign_name = str(row["campaign_name"])
                        existing.currency = str(row["currency"])
                        existing.spend_amount = float(spend_amount)
                        existing.synced_at = synced_at

                    upserted_rows += 1

                connector.last_synced_at = synced_at
                connector.error_message = None
                synced_connectors += 1

                db.add(
                    AuditEvent(
                        tenant_id=connector.tenant_id,
                        actor_user_id=None,
                        action="connector.meta_spend_synced",
                        entity_type="connector",
                        entity_id=str(connector.id),
                        details={
                            "source": "meta",
                            "spend_rows_synced": len(rows),
                        },
                    )
                )
            except Exception as exc:
                _record_connector_sync_failure(
                    db,
                    connector=connector,
                    source="meta",
                    job_name="meta_spend_sync",
                    reason=str(exc),
                    failed_at=synced_at,
                )

        db.commit()
        return {
            "connector_count": synced_connectors,
            "spend_row_upsert_count": upserted_rows,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_meta_spend_sync_schedule")
def run_meta_spend_sync_schedule() -> dict[str, int]:
    return run_meta_spend_sync_job()


def _default_google_spend_fetcher(
    connector: ConnectorIntegration,
    now: datetime,
) -> list[dict[str, object]]:
    base_id = str(connector.id).replace("-", "")[:8]
    spend_date = (now - timedelta(days=1)).date()
    return [
        {
            "external_campaign_id": f"{base_id}-google-001",
            "campaign_name": "Google Search - Branded",
            "spend_date": spend_date,
            "currency": "USD",
            "spend_amount": 201.15,
        },
        {
            "external_campaign_id": f"{base_id}-google-002",
            "campaign_name": "Google Search - Non Brand",
            "spend_date": spend_date,
            "currency": "USD",
            "spend_amount": 389.60,
        },
    ]


def run_google_spend_sync_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
    spend_fetcher: Callable[
        [ConnectorIntegration, datetime],
        list[dict[str, object]],
    ] = _default_google_spend_fetcher,
    max_attempts: int = SYNC_RETRY_MAX_ATTEMPTS,
    base_backoff_seconds: float = SYNC_RETRY_BASE_BACKOFF_SECONDS,
    max_backoff_seconds: float = SYNC_RETRY_MAX_BACKOFF_SECONDS,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, int]:
    synced_at = now or datetime.now(UTC)
    db = session_factory()
    synced_connectors = 0
    upserted_rows = 0

    try:
        connectors = list(
            db.scalars(
                select(ConnectorIntegration).where(
                    ConnectorIntegration.source == "google_ads",
                    ConnectorIntegration.status == "connected",
                )
            )
        )
        for connector in connectors:
            try:
                def fetch_google_spend(
                    connector_for_retry: ConnectorIntegration = connector,
                    synced_at_for_retry: datetime = synced_at,
                ) -> list[dict[str, object]]:
                    return spend_fetcher(connector_for_retry, synced_at_for_retry)

                rows = _run_with_retry_and_capped_backoff(
                    fetch_google_spend,
                    max_attempts=max_attempts,
                    base_backoff_seconds=base_backoff_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                    sleep_fn=sleep_fn,
                )
                for row in rows:
                    external_campaign_id = str(row["external_campaign_id"])
                    spend_date = row["spend_date"]
                    if not isinstance(spend_date, date):
                        raise ValueError("spend_date must be a date")
                    spend_amount = row["spend_amount"]
                    if not isinstance(spend_amount, int | float):
                        raise ValueError("spend_amount must be numeric")

                    existing = db.scalar(
                        select(GoogleAdSpend).where(
                            GoogleAdSpend.tenant_id == connector.tenant_id,
                            GoogleAdSpend.connector_id == connector.id,
                            GoogleAdSpend.external_campaign_id == external_campaign_id,
                            GoogleAdSpend.spend_date == spend_date,
                        )
                    )

                    if existing is None:
                        db.add(
                            GoogleAdSpend(
                                tenant_id=connector.tenant_id,
                                connector_id=connector.id,
                                external_campaign_id=external_campaign_id,
                                campaign_name=str(row["campaign_name"]),
                                spend_date=spend_date,
                                currency=str(row["currency"]),
                                spend_amount=float(spend_amount),
                                synced_at=synced_at,
                            )
                        )
                    else:
                        existing.campaign_name = str(row["campaign_name"])
                        existing.currency = str(row["currency"])
                        existing.spend_amount = float(spend_amount)
                        existing.synced_at = synced_at

                    upserted_rows += 1

                connector.last_synced_at = synced_at
                connector.error_message = None
                synced_connectors += 1

                db.add(
                    AuditEvent(
                        tenant_id=connector.tenant_id,
                        actor_user_id=None,
                        action="connector.google_ads_spend_synced",
                        entity_type="connector",
                        entity_id=str(connector.id),
                        details={
                            "source": "google_ads",
                            "spend_rows_synced": len(rows),
                        },
                    )
                )
            except Exception as exc:
                _record_connector_sync_failure(
                    db,
                    connector=connector,
                    source="google_ads",
                    job_name="google_ads_spend_sync",
                    reason=str(exc),
                    failed_at=synced_at,
                )

        db.commit()
        return {
            "connector_count": synced_connectors,
            "spend_row_upsert_count": upserted_rows,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_google_spend_sync_schedule")
def run_google_spend_sync_schedule() -> dict[str, int]:
    return run_google_spend_sync_job()


# ---------------------------------------------------------------------------
# T-046  FR-041 — Segment margin computation
# ---------------------------------------------------------------------------


def run_segment_margin_computation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    """Compute contribution margin per customer segment for every active tenant.

    Segments computed:
      new        — exactly 1 order ever, first order within the analysis period.
      returning  — 2+ orders ever, at least 1 within the analysis period.
      high_value — top SEGMENT_HIGH_VALUE_TOP_FRACTION by lifetime revenue,
                   with at least 1 order in the analysis period.
      at_risk    — silence_days between 1× and 2× expected repurchase cadence.
                   Skipped if cadence data is unavailable.
      churned    — silence_days ≥ 2× expected repurchase cadence.
                   Skipped if cadence data is unavailable.

    COGS is 0.0 until cost inputs are provided (T-047/T-048).  The
    data_completeness field records this so the API layer can surface the
    right confidence signal to the front-end.
    """
    current_time = now or datetime.now(UTC)
    snapshot_date = current_time.date()
    period_start = (
        current_time - timedelta(days=SEGMENT_MARGIN_PERIOD_DAYS)
    ).date()
    period_end = snapshot_date

    db = session_factory()
    snapshot_count = 0

    try:
        tenants = list(
            db.scalars(select(Tenant).where(Tenant.is_active.is_(True)))
        )

        for tenant in tenants:
            # All orders with customer_id (needed for all-time classification)
            all_orders: list[ShopifyOrder] = list(
                db.scalars(
                    select(ShopifyOrder)
                    .where(
                        ShopifyOrder.tenant_id == tenant.id,
                        ShopifyOrder.customer_id.is_not(None),
                    )
                    .order_by(ShopifyOrder.order_created_at)
                )
            )
            if not all_orders:
                continue

            # ----------------------------------------------------------------
            # Build per-customer history (all time)
            # ----------------------------------------------------------------
            customer_order_history: dict[
                str, list[tuple[datetime, float]]
            ] = {}
            for order in all_orders:
                cid = order.customer_id
                assert cid is not None  # filtered above
                if cid not in customer_order_history:
                    customer_order_history[cid] = []
                order_dt = order.order_created_at
                if order_dt.tzinfo is None:
                    order_dt = order_dt.replace(tzinfo=UTC)
                customer_order_history[cid].append((order_dt, order.total_amount))

            # ----------------------------------------------------------------
            # Filter to analysis period
            # ----------------------------------------------------------------
            period_orders: list[ShopifyOrder] = [
                o for o in all_orders
                if period_start <= (
                    o.order_created_at.replace(tzinfo=UTC)
                    if o.order_created_at.tzinfo is None
                    else o.order_created_at
                ).date() <= period_end
            ]
            if not period_orders:
                continue

            period_customer_ids: set[str] = {
                o.customer_id
                for o in period_orders
                if o.customer_id is not None
            }

            # ----------------------------------------------------------------
            # Ad spend in period (acquisition cost for new segment)
            # ----------------------------------------------------------------
            meta_spend: float = db.scalar(
                select(func.sum(MetaAdSpend.spend_amount)).where(
                    MetaAdSpend.tenant_id == tenant.id,
                    MetaAdSpend.spend_date >= period_start,
                    MetaAdSpend.spend_date <= period_end,
                )
            ) or 0.0
            google_spend: float = db.scalar(
                select(func.sum(GoogleAdSpend.spend_amount)).where(
                    GoogleAdSpend.tenant_id == tenant.id,
                    GoogleAdSpend.spend_date >= period_start,
                    GoogleAdSpend.spend_date <= period_end,
                )
            ) or 0.0
            total_ad_spend = meta_spend + google_spend

            # ----------------------------------------------------------------
            # Expected repurchase cadence from latest retention snapshot
            # ----------------------------------------------------------------
            latest_retention: RetentionDailySnapshot | None = db.scalar(
                select(RetentionDailySnapshot)
                .where(RetentionDailySnapshot.tenant_id == tenant.id)
                .order_by(RetentionDailySnapshot.snapshot_date.desc())
            )
            expected_cadence: float | None = (
                latest_retention.expected_repurchase_cadence_days
                if latest_retention is not None
                else None
            )

            # ----------------------------------------------------------------
            # Classify customers into segments
            # ----------------------------------------------------------------

            # new: exactly 1 order ever, first (and only) order in period
            new_customers: set[str] = {
                cid
                for cid, history in customer_order_history.items()
                if len(history) == 1
                and period_start <= history[0][0].date() <= period_end
            }

            # returning: 2+ orders ever, at least one in period
            returning_customers: set[str] = {
                cid
                for cid in period_customer_ids
                if len(customer_order_history.get(cid, [])) >= 2
            }

            # high_value: top SEGMENT_HIGH_VALUE_TOP_FRACTION by cumulative LTV
            # among customers with at least one period order
            customer_ltv: dict[str, float] = {
                cid: sum(amt for _, amt in history)
                for cid, history in customer_order_history.items()
                if cid in period_customer_ids
            }
            sorted_by_ltv = sorted(
                customer_ltv.keys(),
                key=lambda c: customer_ltv[c],
                reverse=True,
            )
            hv_count = max(
                1, int(len(sorted_by_ltv) * SEGMENT_HIGH_VALUE_TOP_FRACTION)
            )
            high_value_customers: set[str] = set(sorted_by_ltv[:hv_count])

            # at_risk / churned — only when cadence data is available
            at_risk_customers: set[str] = set()
            churned_customers: set[str] = set()
            cadence_available = (
                expected_cadence is not None and expected_cadence > 0
            )
            if cadence_available:
                assert expected_cadence is not None
                for cid, history in customer_order_history.items():
                    last_dt = history[-1][0]
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=UTC)
                    silence_days = (
                        current_time - last_dt
                    ).total_seconds() / 86400.0
                    ratio = silence_days / expected_cadence
                    if 1.0 <= ratio < 2.0:
                        at_risk_customers.add(cid)
                    elif ratio >= 2.0:
                        churned_customers.add(cid)

            # ----------------------------------------------------------------
            # Compute margin per segment and upsert
            # ----------------------------------------------------------------
            segments_to_compute: dict[str, set[str]] = {
                "new": new_customers,
                "returning": returning_customers,
                "high_value": high_value_customers,
            }
            if cadence_available:
                segments_to_compute["at_risk"] = at_risk_customers
                segments_to_compute["churned"] = churned_customers

            computed_count = 0
            for segment_type, segment_cids in segments_to_compute.items():
                seg_orders = [
                    o for o in period_orders
                    if o.customer_id in segment_cids
                ]

                customer_count = len(segment_cids)
                order_count = len(seg_orders)
                revenue = sum(o.total_amount for o in seg_orders)
                shipping_cost = sum(
                    o.shipping_amount if o.shipping_amount is not None else 0.0
                    for o in seg_orders
                )
                returns_cost = sum(
                    o.refund_amount if o.refund_amount is not None else 0.0
                    for o in seg_orders
                )
                acquisition_cost = (
                    total_ad_spend if segment_type == "new" else 0.0
                )
                # Read COGS % from cost_inputs; falls back to 0 if not configured
                seg_cogs_input = db.scalar(
                    select(CostInput).where(
                        CostInput.tenant_id == tenant.id,
                        CostInput.input_type == "cogs",
                        CostInput.is_active.is_(True),
                    )
                )
                cogs = (
                    revenue * (seg_cogs_input.amount / 100.0)
                    if seg_cogs_input is not None
                    and seg_cogs_input.unit == "pct_of_revenue"
                    else 0.0
                )
                margin_amount = (
                    revenue - cogs - shipping_cost - returns_cost - acquisition_cost
                )
                margin_pct = (
                    (margin_amount / revenue * 100.0) if revenue > 0.0 else 0.0
                )

                existing: SegmentMarginSnapshot | None = db.scalar(
                    select(SegmentMarginSnapshot).where(
                        SegmentMarginSnapshot.tenant_id == tenant.id,
                        SegmentMarginSnapshot.segment_type == segment_type,
                        SegmentMarginSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if existing is None:
                    db.add(
                        SegmentMarginSnapshot(
                            tenant_id=tenant.id,
                            segment_type=segment_type,
                            snapshot_date=snapshot_date,
                            period_start_date=period_start,
                            period_end_date=period_end,
                            customer_count=customer_count,
                            order_count=order_count,
                            revenue=revenue,
                            cogs=cogs,
                            shipping_cost=shipping_cost,
                            returns_cost=returns_cost,
                            acquisition_cost=acquisition_cost,
                            contribution_margin_amount=margin_amount,
                            contribution_margin_pct=margin_pct,
                            data_completeness="partial_no_cogs",
                        )
                    )
                else:
                    existing.period_start_date = period_start
                    existing.period_end_date = period_end
                    existing.customer_count = customer_count
                    existing.order_count = order_count
                    existing.revenue = revenue
                    existing.cogs = cogs
                    existing.shipping_cost = shipping_cost
                    existing.returns_cost = returns_cost
                    existing.acquisition_cost = acquisition_cost
                    existing.contribution_margin_amount = margin_amount
                    existing.contribution_margin_pct = margin_pct
                    existing.data_completeness = "partial_no_cogs"

                snapshot_count += 1
                computed_count += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.segment_margin_snapshot_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"segment_snapshot_count": computed_count},
                )
            )

        db.commit()
        return {"segment_snapshot_count": snapshot_count}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T-046  FR-042 — Cohort return signal computation
# ---------------------------------------------------------------------------


def run_cohort_return_signal_computation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    """Compute return/refund signal per cohort for every active tenant.

    This is the FR-042 retention signal view — completely separate from
    the operational returns view.  No unit cost or logistics data is
    stored here.  The repeat_purchase_rate_pct is copied from the most
    recent CohortRetentionSnapshot so callers can compare both metrics
    side-by-side without a join.
    """
    current_time = now or datetime.now(UTC)
    snapshot_date = current_time.date()
    lookback_start = current_time - timedelta(days=COHORT_RETURN_SIGNAL_LOOKBACK_DAYS)

    db = session_factory()
    signal_count = 0

    try:
        tenants = list(
            db.scalars(select(Tenant).where(Tenant.is_active.is_(True)))
        )

        for tenant in tenants:
            # Orders with customer_id within the lookback window
            all_orders: list[ShopifyOrder] = list(
                db.scalars(
                    select(ShopifyOrder)
                    .where(
                        ShopifyOrder.tenant_id == tenant.id,
                        ShopifyOrder.customer_id.is_not(None),
                        ShopifyOrder.order_created_at >= lookback_start,
                    )
                    .order_by(ShopifyOrder.order_created_at)
                )
            )
            if not all_orders:
                continue

            # ----------------------------------------------------------------
            # Determine each customer's cohort (month of first order)
            # ----------------------------------------------------------------
            customer_orders: dict[str, list[ShopifyOrder]] = {}
            for order in all_orders:
                cid = order.customer_id
                assert cid is not None
                if cid not in customer_orders:
                    customer_orders[cid] = []
                customer_orders[cid].append(order)

            customer_cohort_month: dict[str, str] = {}
            for cid, orders in customer_orders.items():
                first_dt = min(
                    o.order_created_at for o in orders
                )
                if first_dt.tzinfo is None:
                    first_dt = first_dt.replace(tzinfo=UTC)
                customer_cohort_month[cid] = first_dt.strftime("%Y-%m")

            # ----------------------------------------------------------------
            # Group all orders by cohort
            # ----------------------------------------------------------------
            cohort_orders: dict[str, list[ShopifyOrder]] = {}
            for order in all_orders:
                cid = order.customer_id
                assert cid is not None
                cm = customer_cohort_month.get(cid)
                if cm is None:
                    continue
                if cm not in cohort_orders:
                    cohort_orders[cm] = []
                cohort_orders[cm].append(order)

            cohort_customer_map: dict[str, set[str]] = {
                cm: {
                    o.customer_id
                    for o in orders
                    if o.customer_id is not None
                }
                for cm, orders in cohort_orders.items()
            }

            # ----------------------------------------------------------------
            # Compute return signal per cohort and upsert
            # ----------------------------------------------------------------
            for cohort_month, cohort_order_list in cohort_orders.items():
                cohort_size = len(cohort_customer_map[cohort_month])
                total_orders = len(cohort_order_list)
                refunded_orders = sum(
                    1 for o in cohort_order_list if o.is_refunded
                )
                return_rate_pct = (
                    refunded_orders / total_orders * 100.0
                    if total_orders > 0
                    else 0.0
                )

                # Read repeat purchase rate from most recent retention snapshot
                cohort_retention: CohortRetentionSnapshot | None = db.scalar(
                    select(CohortRetentionSnapshot)
                    .where(
                        CohortRetentionSnapshot.tenant_id == tenant.id,
                        CohortRetentionSnapshot.cohort_month == cohort_month,
                    )
                    .order_by(CohortRetentionSnapshot.snapshot_date.desc())
                )
                repeat_purchase_rate_pct = (
                    cohort_retention.repeat_purchase_rate_pct
                    if cohort_retention is not None
                    else 0.0
                )

                existing_signal: CohortReturnSignal | None = db.scalar(
                    select(CohortReturnSignal).where(
                        CohortReturnSignal.tenant_id == tenant.id,
                        CohortReturnSignal.cohort_month == cohort_month,
                        CohortReturnSignal.snapshot_date == snapshot_date,
                    )
                )
                if existing_signal is None:
                    db.add(
                        CohortReturnSignal(
                            tenant_id=tenant.id,
                            cohort_month=cohort_month,
                            snapshot_date=snapshot_date,
                            cohort_size=cohort_size,
                            total_orders=total_orders,
                            refunded_orders=refunded_orders,
                            return_rate_pct=return_rate_pct,
                            repeat_purchase_rate_pct=repeat_purchase_rate_pct,
                        )
                    )
                else:
                    existing_signal.cohort_size = cohort_size
                    existing_signal.total_orders = total_orders
                    existing_signal.refunded_orders = refunded_orders
                    existing_signal.return_rate_pct = return_rate_pct
                    existing_signal.repeat_purchase_rate_pct = (
                        repeat_purchase_rate_pct
                    )
                signal_count += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.cohort_return_signal_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"cohort_signal_count": len(cohort_orders)},
                )
            )

        db.commit()
        return {"cohort_return_signal_count": signal_count}
    finally:
        db.close()


@celery_app.task(
    name="worker.app.tasks.run_retention_segment_computation_schedule"
)
def run_retention_segment_computation_schedule() -> dict[str, int]:
    margin = run_segment_margin_computation_job()
    signal = run_cohort_return_signal_computation_job()
    return {
        "segment_snapshot_count": margin["segment_snapshot_count"],
        "cohort_return_signal_count": signal["cohort_return_signal_count"],
    }


# ---------------------------------------------------------------------------
# T-047: Finance cost drivers and margin drift
# ---------------------------------------------------------------------------


def _to_float(val: object) -> float:
    """Safely convert a SQLAlchemy aggregate result to float (0.0 on None)."""
    return float(val) if isinstance(val, (int, float)) else 0.0


def _compute_confidence(
    last_updated_at: datetime, now: datetime
) -> tuple[float, str]:
    """Derive a recency-based confidence score and label.

    score = 1 / (1 + elapsed_hours / 24)
    high  : elapsed < 24 h  (score ≥ 0.5)
    medium: 24 h ≤ elapsed < 72 h  (0.25 ≤ score < 0.5)
    low   : elapsed ≥ 72 h  (score < 0.25)
    """
    elapsed_hours = (now - last_updated_at).total_seconds() / 3600.0
    score = 1.0 / (1.0 + elapsed_hours / 24.0)
    if elapsed_hours < CONFIDENCE_HIGH_THRESHOLD_HOURS:
        label = "high"
    elif elapsed_hours < CONFIDENCE_MEDIUM_THRESHOLD_HOURS:
        label = "medium"
    else:
        label = "low"
    return score, label


def _compute_variance_reason(
    db: Session,
    tenant_id: object,
    snapshot_date: date,
    current_drivers: list[CostDriverSnapshot],
) -> str:
    """Identify the cost driver with the largest absolute change vs prior snapshot."""
    prior_date: date | None = db.scalar(
        select(CostDriverSnapshot.snapshot_date)
        .where(
            CostDriverSnapshot.tenant_id == tenant_id,
            CostDriverSnapshot.snapshot_date < snapshot_date,
        )
        .order_by(CostDriverSnapshot.snapshot_date.desc())
    )
    if prior_date is None:
        return "data_insufficient"

    prior_drivers = list(
        db.scalars(
            select(CostDriverSnapshot).where(
                CostDriverSnapshot.tenant_id == tenant_id,
                CostDriverSnapshot.snapshot_date == prior_date,
            )
        )
    )

    current_by_type = {s.driver_type: s.absolute_amount for s in current_drivers}
    prior_by_type = {s.driver_type: s.absolute_amount for s in prior_drivers}

    max_change_driver: str | None = None
    max_change = 0.0
    for driver_type, current_amount in current_by_type.items():
        prior_amount = prior_by_type.get(driver_type, 0.0)
        change = abs(current_amount - prior_amount)
        if change > max_change:
            max_change = change
            max_change_driver = driver_type

    if max_change_driver is None or max_change < 0.01:
        return "no_significant_change"

    reason_map: dict[str, str] = {
        "ad_spend": "increased_ad_spend",
        "returns": "higher_returns",
        "discounts": "higher_discounts",
        "shipping": "increased_shipping",
        "cogs": "higher_cogs",
    }
    return reason_map.get(max_change_driver, "cost_driver_change")


def run_cost_driver_computation_job(
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    """FR-048/FR-049: Compute daily cost-driver breakdown for every active tenant.

    Five driver types: cogs, shipping, returns, discounts, ad_spend.
    Each row stores absolute cost, % of revenue, margin impact, data source
    metadata, and a recency-based confidence label.  COGS is 0.0 until
    cost inputs are provided (T-048).
    """
    current_time: datetime = now if now is not None else datetime.now(UTC)
    snapshot_date = current_time.date()
    period_start_dt = current_time - timedelta(days=COST_DRIVER_PERIOD_DAYS)
    period_start = period_start_dt.date()
    period_end = snapshot_date

    db: Session = session_factory()
    driver_count = 0
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))

        for tenant in tenants:
            revenue_val = db.scalar(
                select(func.sum(ShopifyOrder.total_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            revenue = _to_float(revenue_val)
            if revenue == 0.0:
                continue

            # --- Shopify connector recency ---
            shopify_connector = db.scalar(
                select(ConnectorIntegration)
                .where(
                    ConnectorIntegration.tenant_id == tenant.id,
                    ConnectorIntegration.source == "shopify",
                )
                .order_by(ConnectorIntegration.last_synced_at.desc())
            )
            shopify_last_synced: datetime
            if shopify_connector and shopify_connector.last_synced_at is not None:
                dt = shopify_connector.last_synced_at
                shopify_last_synced = (
                    dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
                )
            else:
                shopify_last_synced = current_time

            # --- Ad platform connector recency ---
            meta_connector = db.scalar(
                select(ConnectorIntegration)
                .where(
                    ConnectorIntegration.tenant_id == tenant.id,
                    ConnectorIntegration.source == "meta",
                )
                .order_by(ConnectorIntegration.last_synced_at.desc())
            )
            google_connector = db.scalar(
                select(ConnectorIntegration)
                .where(
                    ConnectorIntegration.tenant_id == tenant.id,
                    ConnectorIntegration.source == "google_ads",
                )
                .order_by(ConnectorIntegration.last_synced_at.desc())
            )
            ad_candidates: list[datetime] = []
            if meta_connector and meta_connector.last_synced_at is not None:
                dt2 = meta_connector.last_synced_at
                ad_candidates.append(
                    dt2 if dt2.tzinfo is not None else dt2.replace(tzinfo=UTC)
                )
            if google_connector and google_connector.last_synced_at is not None:
                dt3 = google_connector.last_synced_at
                ad_candidates.append(
                    dt3 if dt3.tzinfo is not None else dt3.replace(tzinfo=UTC)
                )
            ad_last_synced: datetime = (
                max(ad_candidates) if ad_candidates else current_time
            )

            # --- Driver amounts ---
            shipping_val = db.scalar(
                select(func.sum(ShopifyOrder.shipping_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.shipping_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            shipping = _to_float(shipping_val)

            returns_val = db.scalar(
                select(func.sum(ShopifyOrder.refund_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.is_refunded.is_(True),
                    ShopifyOrder.refund_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            returns_cost = _to_float(returns_val)

            discounts_val = db.scalar(
                select(func.sum(ShopifyOrder.discount_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.discount_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            discounts = _to_float(discounts_val)

            meta_spend_val = db.scalar(
                select(func.sum(MetaAdSpend.spend_amount)).where(
                    MetaAdSpend.tenant_id == tenant.id,
                    MetaAdSpend.spend_date >= period_start,
                    MetaAdSpend.spend_date <= period_end,
                )
            )
            meta_spend = _to_float(meta_spend_val)

            google_spend_val = db.scalar(
                select(func.sum(GoogleAdSpend.spend_amount)).where(
                    GoogleAdSpend.tenant_id == tenant.id,
                    GoogleAdSpend.spend_date >= period_start,
                    GoogleAdSpend.spend_date <= period_end,
                )
            )
            google_spend = _to_float(google_spend_val)

            ad_spend = meta_spend + google_spend

            # Read COGS % from cost_inputs (Finance Controller configures this)
            driver_cogs_input = db.scalar(
                select(CostInput).where(
                    CostInput.tenant_id == tenant.id,
                    CostInput.input_type == "cogs",
                    CostInput.is_active.is_(True),
                )
            )
            cogs_amount_driver = (
                revenue * (driver_cogs_input.amount / 100.0)
                if driver_cogs_input is not None
                and driver_cogs_input.unit == "pct_of_revenue"
                else 0.0
            )

            # (driver_type, amount, source_platform, last_updated_at)
            driver_defs: list[tuple[str, float, str, datetime]] = [
                ("cogs", cogs_amount_driver, "cost_inputs", current_time),
                ("shipping", shipping, "shopify", shopify_last_synced),
                ("returns", returns_cost, "shopify", shopify_last_synced),
                ("discounts", discounts, "shopify", shopify_last_synced),
                ("ad_spend", ad_spend, "meta_google", ad_last_synced),
            ]

            new_drivers: list[CostDriverSnapshot] = []
            for driver_type, amount, source_platform, last_updated_at in driver_defs:
                source = "manual" if source_platform == "manual_entry" else "synced"
                confidence_score, confidence_label = _compute_confidence(
                    last_updated_at, current_time
                )
                pct = (amount / revenue * 100.0) if revenue > 0.0 else 0.0

                existing = db.scalar(
                    select(CostDriverSnapshot).where(
                        CostDriverSnapshot.tenant_id == tenant.id,
                        CostDriverSnapshot.driver_type == driver_type,
                        CostDriverSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if existing is None:
                    new_snap = CostDriverSnapshot(
                        tenant_id=tenant.id,
                        driver_type=driver_type,
                        snapshot_date=snapshot_date,
                        period_start_date=period_start,
                        period_end_date=period_end,
                        absolute_amount=amount,
                        revenue=revenue,
                        pct_of_revenue=pct,
                        margin_impact_amount=-amount,
                        source=source,
                        source_platform=source_platform,
                        last_updated_at=last_updated_at,
                        confidence_score=confidence_score,
                        confidence_label=confidence_label,
                    )
                    db.add(new_snap)
                    new_drivers.append(new_snap)
                else:
                    existing.absolute_amount = amount
                    existing.revenue = revenue
                    existing.pct_of_revenue = pct
                    existing.margin_impact_amount = -amount
                    existing.last_updated_at = last_updated_at
                    existing.confidence_score = confidence_score
                    existing.confidence_label = confidence_label
                    new_drivers.append(existing)
                driver_count += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.cost_driver_snapshot_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"driver_count": len(driver_defs)},
                )
            )

        db.commit()
        return {"cost_driver_snapshot_count": driver_count}
    finally:
        db.close()


def run_margin_drift_computation_job(
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    now: datetime | None = None,
) -> dict[str, int]:
    """FR-053/FR-054: Compute daily margin drift and check alert thresholds.

    For each active tenant with revenue in the period:
    - Computes actual blended margin % directly from order and ad-spend data.
    - Always produces a 'blended/all' drift snapshot.
    - Checks each active MarginDriftThreshold; fires an alert AuditEvent
      when |drift_pct| >= threshold_pct.
    - expected_margin_pct is taken from the most recent prior drift snapshot
      for the same channel/category combination.
    """
    current_time: datetime = now if now is not None else datetime.now(UTC)
    snapshot_date = current_time.date()
    period_start_dt = current_time - timedelta(days=MARGIN_DRIFT_PERIOD_DAYS)
    period_start = period_start_dt.date()
    period_end = snapshot_date

    db: Session = session_factory()
    drift_count = 0
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))

        for tenant in tenants:
            revenue_val = db.scalar(
                select(func.sum(ShopifyOrder.total_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            revenue = _to_float(revenue_val)
            if revenue == 0.0:
                continue

            # Inline cost computation (same window as cost driver job)
            shipping_val = db.scalar(
                select(func.sum(ShopifyOrder.shipping_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.shipping_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            shipping = _to_float(shipping_val)

            returns_val = db.scalar(
                select(func.sum(ShopifyOrder.refund_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.is_refunded.is_(True),
                    ShopifyOrder.refund_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            returns_cost = _to_float(returns_val)

            discounts_val = db.scalar(
                select(func.sum(ShopifyOrder.discount_amount)).where(
                    ShopifyOrder.tenant_id == tenant.id,
                    ShopifyOrder.discount_amount.is_not(None),
                    ShopifyOrder.order_created_at >= period_start_dt,
                    ShopifyOrder.order_created_at <= current_time,
                )
            )
            discounts = _to_float(discounts_val)

            meta_spend_val = db.scalar(
                select(func.sum(MetaAdSpend.spend_amount)).where(
                    MetaAdSpend.tenant_id == tenant.id,
                    MetaAdSpend.spend_date >= period_start,
                    MetaAdSpend.spend_date <= period_end,
                )
            )
            meta_spend = _to_float(meta_spend_val)

            google_spend_val = db.scalar(
                select(func.sum(GoogleAdSpend.spend_amount)).where(
                    GoogleAdSpend.tenant_id == tenant.id,
                    GoogleAdSpend.spend_date >= period_start,
                    GoogleAdSpend.spend_date <= period_end,
                )
            )
            google_spend = _to_float(google_spend_val)

            total_costs = (
                shipping + returns_cost + discounts + meta_spend + google_spend
            )
            actual_margin_pct = (revenue - total_costs) / revenue * 100.0

            # Variance reason from prior cost driver snapshots
            current_drivers = list(
                db.scalars(
                    select(CostDriverSnapshot).where(
                        CostDriverSnapshot.tenant_id == tenant.id,
                        CostDriverSnapshot.snapshot_date == snapshot_date,
                    )
                )
            )
            variance_reason = _compute_variance_reason(
                db, tenant.id, snapshot_date, current_drivers
            )

            # Build profiles: active thresholds + always include blended/all
            thresholds = list(
                db.scalars(
                    select(MarginDriftThreshold).where(
                        MarginDriftThreshold.tenant_id == tenant.id,
                        MarginDriftThreshold.is_active.is_(True),
                    )
                )
            )
            profiles: list[tuple[str, str, float | None]] = [
                (t.channel, t.category, t.threshold_pct) for t in thresholds
            ]
            has_blended = any(
                ch == "blended" and cat == "all" for ch, cat, _ in profiles
            )
            if not has_blended:
                profiles.append(("blended", "all", None))

            for channel, category, threshold_pct in profiles:
                prior_snap = db.scalar(
                    select(MarginDriftSnapshot)
                    .where(
                        MarginDriftSnapshot.tenant_id == tenant.id,
                        MarginDriftSnapshot.channel == channel,
                        MarginDriftSnapshot.category == category,
                        MarginDriftSnapshot.snapshot_date < snapshot_date,
                    )
                    .order_by(MarginDriftSnapshot.snapshot_date.desc())
                )
                expected_margin_pct: float | None = (
                    prior_snap.actual_margin_pct if prior_snap is not None else None
                )

                drift_pct: float | None = None
                if (
                    expected_margin_pct is not None
                    and expected_margin_pct != 0.0
                ):
                    drift_pct = (
                        (actual_margin_pct - expected_margin_pct)
                        / abs(expected_margin_pct)
                        * 100.0
                    )

                threshold_exceeded = bool(
                    drift_pct is not None
                    and threshold_pct is not None
                    and abs(drift_pct) >= threshold_pct
                )

                snap_variance_reason = (
                    variance_reason
                    if expected_margin_pct is not None
                    else "data_insufficient"
                )
                data_completeness = (
                    "partial_no_cogs"
                    if channel == "blended"
                    else "partial_no_channel_attribution"
                )

                existing = db.scalar(
                    select(MarginDriftSnapshot).where(
                        MarginDriftSnapshot.tenant_id == tenant.id,
                        MarginDriftSnapshot.channel == channel,
                        MarginDriftSnapshot.category == category,
                        MarginDriftSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if existing is None:
                    db.add(
                        MarginDriftSnapshot(
                            tenant_id=tenant.id,
                            snapshot_date=snapshot_date,
                            channel=channel,
                            category=category,
                            actual_margin_pct=actual_margin_pct,
                            expected_margin_pct=expected_margin_pct,
                            drift_pct=drift_pct,
                            threshold_exceeded=threshold_exceeded,
                            variance_reason=snap_variance_reason,
                            data_completeness=data_completeness,
                        )
                    )
                else:
                    existing.actual_margin_pct = actual_margin_pct
                    existing.expected_margin_pct = expected_margin_pct
                    existing.drift_pct = drift_pct
                    existing.threshold_exceeded = threshold_exceeded
                    existing.variance_reason = snap_variance_reason
                    existing.data_completeness = data_completeness

                if threshold_exceeded:
                    db.add(
                        AuditEvent(
                            tenant_id=tenant.id,
                            actor_user_id=None,
                            action="alert.margin_drift_threshold_exceeded",
                            entity_type="tenant",
                            entity_id=str(tenant.id),
                            details={
                                "channel": channel,
                                "category": category,
                                "actual_margin_pct": actual_margin_pct,
                                "expected_margin_pct": expected_margin_pct,
                                "drift_pct": drift_pct,
                                "threshold_pct": threshold_pct,
                                "variance_reason": snap_variance_reason,
                            },
                        )
                    )
                drift_count += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.margin_drift_snapshot_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"drift_snapshot_count": len(profiles)},
                )
            )

        db.commit()
        return {"margin_drift_snapshot_count": drift_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_finance_cost_drift_schedule")
def run_finance_cost_drift_schedule() -> dict[str, int]:
    cost = run_cost_driver_computation_job()
    drift = run_margin_drift_computation_job()
    return {
        "cost_driver_snapshot_count": cost["cost_driver_snapshot_count"],
        "margin_drift_snapshot_count": drift["margin_drift_snapshot_count"],
    }


# ---------------------------------------------------------------------------
# T-050: Inventory risk computations (FR-058 to FR-062)
# ---------------------------------------------------------------------------


def run_inventory_risk_computation_job(
    *,
    session_factory: Callable[[], Session] | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Compute daily inventory risk status for every active SKU per tenant.

    Velocity is computed from real per-SKU line item data in
    shopify_order_line_items.  data_completeness is set to "computed"
    when line item records exist, "estimated" otherwise (no line items
    synced yet for this tenant).

    Status priority (only one status per SKU):
        stockout_risk → low_stock → slow_moving → overstock → in_stock
    """
    if now is None:
        now = datetime.now(tz=UTC)
    snapshot_date = now.date()

    factory = session_factory if session_factory is not None else SessionLocal
    db: Session = factory()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
        snapshot_count = 0

        for tenant in tenants:
            items = list(
                db.scalars(
                    select(ShopifyInventoryItem).where(
                        ShopifyInventoryItem.tenant_id == tenant.id
                    )
                )
            )
            if not items:
                continue

            window_30d = now - timedelta(days=INVENTORY_RISK_VELOCITY_30D_DAYS)
            window_90d = now - timedelta(days=INVENTORY_RISK_VELOCITY_90D_DAYS)

            # Load threshold for "all" category (tenant-wide fallback)
            threshold = db.scalar(
                select(InventoryRiskThreshold).where(
                    InventoryRiskThreshold.tenant_id == tenant.id,
                    InventoryRiskThreshold.category == "all",
                    InventoryRiskThreshold.is_active.is_(True),
                )
            )
            stockout_days = (
                threshold.stockout_alert_days
                if threshold is not None
                else INVENTORY_RISK_DEFAULT_STOCKOUT_ALERT_DAYS
            )
            overstock_weeks = (
                threshold.overstock_weeks_threshold
                if threshold is not None
                else INVENTORY_RISK_DEFAULT_OVERSTOCK_WEEKS
            )
            slow_min_qty = (
                threshold.slow_moving_min_qty
                if threshold is not None
                else INVENTORY_RISK_DEFAULT_SLOW_MIN_QTY
            )
            slow_min_wc = (
                threshold.slow_moving_min_weeks_cover
                if threshold is not None
                else INVENTORY_RISK_DEFAULT_SLOW_MIN_WEEKS_COVER
            )
            slow_min_cap = (
                threshold.slow_moving_min_capital
                if threshold is not None
                else INVENTORY_RISK_DEFAULT_SLOW_MIN_CAPITAL
            )

            for item in items:
                # Per-SKU velocity from real line item data
                units_sold_30d: int = db.scalar(
                    select(func.sum(ShopifyOrderLineItem.quantity)).where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                        ShopifyOrderLineItem.order_created_at >= window_30d,
                        ShopifyOrderLineItem.order_created_at < now,
                    )
                ) or 0

                units_sold_90d: int = db.scalar(
                    select(func.sum(ShopifyOrderLineItem.quantity)).where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                        ShopifyOrderLineItem.order_created_at >= window_90d,
                        ShopifyOrderLineItem.order_created_at < now,
                    )
                ) or 0

                daily_v: float = units_sold_30d / INVENTORY_RISK_VELOCITY_30D_DAYS
                weekly_v: float = (
                    units_sold_90d / INVENTORY_RISK_VELOCITY_90D_DAYS * 7.0
                )

                # Last sale date for this specific SKU
                last_sale_at: datetime | None = db.scalar(
                    select(func.max(ShopifyOrderLineItem.order_created_at)).where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                    )
                )
                days_since_last_sale: int | None = None
                if last_sale_at is not None:
                    if last_sale_at.tzinfo is None:
                        last_sale_at = last_sale_at.replace(tzinfo=UTC)
                    days_since_last_sale = (snapshot_date - last_sale_at.date()).days
                elif units_sold_30d == 0:
                    days_since_last_sale = 9999

                # Confidence based on 30d unit volume
                if units_sold_30d >= 10:
                    confidence = "high"
                elif units_sold_30d >= 3:
                    confidence = "medium"
                else:
                    confidence = "low"

                data_completeness = "computed"

                qty = item.available_quantity
                days_to_stockout = qty / daily_v if daily_v > 0 else None
                weeks_of_cover = qty / weekly_v if weekly_v > 0 else None
                capital_at_risk = (
                    qty * item.cost_per_unit if item.cost_per_unit is not None else None
                )

                # Determine status — priority order
                if days_to_stockout is not None and days_to_stockout <= stockout_days:
                    item_status = "stockout_risk"
                elif item.reorder_point is not None and qty < item.reorder_point:
                    item_status = "low_stock"
                elif (
                    days_since_last_sale is not None
                    and days_since_last_sale > 30
                    and qty > slow_min_qty
                    and (weeks_of_cover is None or weeks_of_cover > slow_min_wc)
                    and (capital_at_risk is None or capital_at_risk > slow_min_cap)
                ):
                    item_status = "slow_moving"
                elif weeks_of_cover is not None and weeks_of_cover > overstock_weeks:
                    item_status = "overstock"
                else:
                    item_status = "in_stock"

                # Upsert
                existing = db.scalar(
                    select(InventoryRiskSnapshot).where(
                        InventoryRiskSnapshot.tenant_id == tenant.id,
                        InventoryRiskSnapshot.sku == item.sku,
                        InventoryRiskSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if existing is not None:
                    existing.current_quantity = qty
                    existing.reorder_point = item.reorder_point
                    existing.status = item_status
                    existing.daily_velocity_30d = daily_v
                    existing.days_to_stockout = days_to_stockout
                    existing.weekly_velocity_90d = weekly_v
                    existing.weeks_of_cover = weeks_of_cover
                    existing.days_since_last_sale = days_since_last_sale
                    existing.capital_at_risk = capital_at_risk
                    existing.confidence = confidence
                    existing.data_completeness = data_completeness
                else:
                    db.add(
                        InventoryRiskSnapshot(
                            tenant_id=tenant.id,
                            snapshot_date=snapshot_date,
                            sku=item.sku,
                            product_title=item.product_title,
                            variant_title=item.variant_title,
                            current_quantity=qty,
                            reorder_point=item.reorder_point,
                            status=item_status,
                            daily_velocity_30d=daily_v,
                            days_to_stockout=days_to_stockout,
                            weekly_velocity_90d=weekly_v,
                            weeks_of_cover=weeks_of_cover,
                            days_since_last_sale=days_since_last_sale,
                            capital_at_risk=capital_at_risk,
                            seasonal_adjustment_applied=False,
                            confidence=confidence,
                            data_completeness=data_completeness,
                        )
                    )
                    snapshot_count += 1

                # Alerts for stockout_risk and low_stock
                if item_status in ("stockout_risk", "low_stock"):
                    db.add(
                        AuditEvent(
                            tenant_id=tenant.id,
                            actor_user_id=None,
                            action=f"alert.inventory_{item_status}",
                            entity_type="inventory_risk_snapshot",
                            entity_id=str(item.id),
                            details={
                                "sku": item.sku,
                                "status": item_status,
                                "current_quantity": qty,
                                "days_to_stockout": days_to_stockout,
                            },
                        )
                    )

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.inventory_risk_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"sku_count": len(items)},
                )
            )

        db.commit()
        return {"inventory_risk_snapshot_count": snapshot_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_inventory_risk_schedule")
def run_inventory_risk_schedule() -> dict[str, int]:
    return run_inventory_risk_computation_job()


def run_operational_impact_computation_job(
    *,
    session_factory: Callable[[], Session] | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Compute daily operational impact per SKU per tenant.

    FR-064: Stockout lost-revenue estimate = daily_velocity × days_to_restock
            × avg_unit_price.  Computed only for stockout_risk / low_stock SKUs.
            Repeat-purchase risk derived from tenant-level avg return rate.
    FR-065: Logistics cost burden per SKU from active CostInput records
            (shipping + return_processing types).
    FR-066: Operational return analytics from ShopifyOrderLineItem join to
            ShopifyOrder — completely separate from retention cohort signal.
    """
    if now is None:
        now = datetime.now(tz=UTC)
    snapshot_date = now.date()
    window_30d = now - timedelta(days=OPERATIONAL_IMPACT_PERIOD_DAYS)

    factory = session_factory if session_factory is not None else SessionLocal
    db: Session = factory()
    try:
        tenants = list(db.scalars(select(Tenant).where(Tenant.is_active.is_(True))))
        snapshot_count = 0

        for tenant in tenants:
            items = list(
                db.scalars(
                    select(ShopifyInventoryItem).where(
                        ShopifyInventoryItem.tenant_id == tenant.id
                    )
                )
            )
            if not items:
                continue

            # Tenant-level avg return rate for repeat-purchase risk (FR-064)
            latest_return_signals = list(
                db.scalars(
                    select(CohortReturnSignal).where(
                        CohortReturnSignal.tenant_id == tenant.id,
                        CohortReturnSignal.snapshot_date == select(
                            func.max(CohortReturnSignal.snapshot_date)
                        ).where(
                            CohortReturnSignal.tenant_id == tenant.id
                        ).scalar_subquery(),
                    )
                )
            )
            avg_cohort_return_rate: float = 0.0
            if latest_return_signals:
                avg_cohort_return_rate = sum(
                    s.return_rate_pct for s in latest_return_signals
                ) / len(latest_return_signals)

            # Tenant shipping cost (flat per_order, first active record) — FR-065
            shipping_input = db.scalar(
                select(CostInput).where(
                    CostInput.tenant_id == tenant.id,
                    CostInput.input_type == "shipping",
                    CostInput.is_active.is_(True),
                )
            )
            shipping_per_order: float = (
                shipping_input.amount
                if shipping_input is not None and shipping_input.unit == "per_order"
                else 0.0
            )

            # Return processing cost — FR-065 / FR-066
            return_processing_input = db.scalar(
                select(CostInput).where(
                    CostInput.tenant_id == tenant.id,
                    CostInput.input_type == "return_processing",
                    CostInput.is_active.is_(True),
                )
            )
            return_cost_per_unit_tenant: float | None = (
                return_processing_input.amount
                if return_processing_input is not None
                else None
            )

            for item in items:
                # Pull today's inventory risk snapshot for status + velocity
                risk_snap = db.scalar(
                    select(InventoryRiskSnapshot).where(
                        InventoryRiskSnapshot.tenant_id == tenant.id,
                        InventoryRiskSnapshot.sku == item.sku,
                        InventoryRiskSnapshot.snapshot_date == snapshot_date,
                    )
                )
                daily_v: float = (
                    risk_snap.daily_velocity_30d if risk_snap is not None else 0.0
                )
                inv_status: str = (
                    risk_snap.status if risk_snap is not None else "in_stock"
                )

                # FR-064 — avg unit price from line items
                avg_price_raw: float | None = db.scalar(
                    select(func.avg(ShopifyOrderLineItem.unit_price)).where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                        ShopifyOrderLineItem.order_created_at >= window_30d,
                    )
                )
                avg_unit_price: float = (
                    avg_price_raw if avg_price_raw is not None else 0.0
                )

                # FR-064 — stockout lost revenue (only for at-risk SKUs)
                stockout_lost_revenue: float | None = None
                if inv_status in ("stockout_risk", "low_stock") and daily_v > 0:
                    stockout_lost_revenue = (
                        daily_v
                        * OPERATIONAL_IMPACT_DEFAULT_RESTOCK_DAYS
                        * avg_unit_price
                    )

                # FR-064 — repeat purchase risk from cohort return rate
                high_pct = OPERATIONAL_IMPACT_REPEAT_RISK_HIGH_RETURN_PCT
                mid_pct = OPERATIONAL_IMPACT_REPEAT_RISK_MEDIUM_RETURN_PCT
                if avg_cohort_return_rate >= high_pct:
                    repeat_risk = "high"
                elif avg_cohort_return_rate >= mid_pct:
                    repeat_risk = "medium"
                elif inv_status in ("stockout_risk", "low_stock"):
                    repeat_risk = "low"
                else:
                    repeat_risk = "none"

                # FR-066 — per-SKU return analytics from line items
                units_sold_30d: int = db.scalar(
                    select(func.sum(ShopifyOrderLineItem.quantity)).where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                        ShopifyOrderLineItem.order_created_at >= window_30d,
                        ShopifyOrderLineItem.order_created_at < now,
                    )
                ) or 0

                # Return qty: line items for this SKU where parent order refunded
                return_qty_30d: int = db.scalar(
                    select(func.sum(ShopifyOrderLineItem.quantity))
                    .join(
                        ShopifyOrder,
                        ShopifyOrderLineItem.order_id == ShopifyOrder.id,
                    )
                    .where(
                        ShopifyOrderLineItem.tenant_id == tenant.id,
                        ShopifyOrderLineItem.sku == item.sku,
                        ShopifyOrderLineItem.order_created_at >= window_30d,
                        ShopifyOrderLineItem.order_created_at < now,
                        ShopifyOrder.is_refunded.is_(True),
                    )
                ) or 0

                return_rate_pct: float = (
                    (return_qty_30d / units_sold_30d) * 100.0
                    if units_sold_30d > 0
                    else 0.0
                )
                return_cost_total: float | None = (
                    return_qty_30d * return_cost_per_unit_tenant
                    if return_cost_per_unit_tenant is not None
                    else None
                )

                # FR-065 — logistics cost burden
                # Estimate: shipping_per_order × units_sold (proxy; Phase 1)
                logistics_cost_per_unit: float | None = None
                logistics_cost_total: float | None = None
                logistics_margin_impact: float | None = None
                if shipping_per_order > 0 and units_sold_30d > 0:
                    logistics_cost_per_unit = shipping_per_order
                    logistics_cost_total = shipping_per_order * units_sold_30d
                    revenue_30d = avg_unit_price * units_sold_30d
                    if revenue_30d > 0:
                        logistics_margin_impact = (
                            logistics_cost_total / revenue_30d
                        ) * 100.0

                # Confidence based on units sold
                if units_sold_30d >= 10:
                    confidence = "high"
                elif units_sold_30d >= 3:
                    confidence = "medium"
                else:
                    confidence = "low"
                data_completeness = (
                    "computed" if units_sold_30d > 0 else "no_sales_data"
                )

                # Upsert
                existing = db.scalar(
                    select(OperationalImpactSnapshot).where(
                        OperationalImpactSnapshot.tenant_id == tenant.id,
                        OperationalImpactSnapshot.sku == item.sku,
                        OperationalImpactSnapshot.snapshot_date == snapshot_date,
                    )
                )
                if existing is not None:
                    existing.inventory_status = inv_status
                    existing.daily_velocity_30d = daily_v
                    existing.avg_unit_price = avg_unit_price
                    existing.stockout_lost_revenue_estimate = stockout_lost_revenue
                    existing.repeat_purchase_risk = repeat_risk
                    existing.logistics_cost_per_unit = logistics_cost_per_unit
                    existing.logistics_cost_total_30d = logistics_cost_total
                    existing.logistics_margin_impact_pct = logistics_margin_impact
                    existing.units_sold_30d = units_sold_30d
                    existing.return_quantity_30d = return_qty_30d
                    existing.return_rate_30d_pct = return_rate_pct
                    existing.return_cost_per_unit = return_cost_per_unit_tenant
                    existing.return_cost_total_30d = return_cost_total
                    existing.confidence = confidence
                    existing.data_completeness = data_completeness
                else:
                    db.add(
                        OperationalImpactSnapshot(
                            tenant_id=tenant.id,
                            snapshot_date=snapshot_date,
                            sku=item.sku,
                            product_title=item.product_title,
                            variant_title=item.variant_title,
                            inventory_status=inv_status,
                            daily_velocity_30d=daily_v,
                            avg_unit_price=avg_unit_price,
                            days_to_restock_estimate=OPERATIONAL_IMPACT_DEFAULT_RESTOCK_DAYS,
                            stockout_lost_revenue_estimate=stockout_lost_revenue,
                            repeat_purchase_risk=repeat_risk,
                            logistics_cost_per_unit=logistics_cost_per_unit,
                            logistics_cost_total_30d=logistics_cost_total,
                            logistics_margin_impact_pct=logistics_margin_impact,
                            units_sold_30d=units_sold_30d,
                            return_quantity_30d=return_qty_30d,
                            return_rate_30d_pct=return_rate_pct,
                            return_cost_per_unit=return_cost_per_unit_tenant,
                            return_cost_total_30d=return_cost_total,
                            confidence=confidence,
                            data_completeness=data_completeness,
                        )
                    )
                    snapshot_count += 1

            db.add(
                AuditEvent(
                    tenant_id=tenant.id,
                    actor_user_id=None,
                    action="kpi.operational_impact_computed",
                    entity_type="tenant",
                    entity_id=str(tenant.id),
                    details={"sku_count": len(items)},
                )
            )

        db.commit()
        return {"operational_impact_snapshot_count": snapshot_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_operational_impact_schedule")
def run_operational_impact_schedule() -> dict[str, int]:
    return run_operational_impact_computation_job()


# ---------------------------------------------------------------------------
# T-053: Deterministic rule engine job
# ---------------------------------------------------------------------------


def _build_rule_input(
    db: Session, tenant: Tenant, today: date
) -> RuleInput:
    """Build a RuleInput for one tenant from its latest metric snapshots.

    Queries the most-recent snapshot_date available for each domain and
    assembles the signals that rule conditions will evaluate.
    """
    # --- Executive KPI (blended ROAS, contribution margin) ---
    exec_snap = db.scalar(
        select(ExecutiveKpiSnapshot)
        .where(ExecutiveKpiSnapshot.tenant_id == tenant.id)
        .order_by(ExecutiveKpiSnapshot.snapshot_date.desc())
        .limit(1)
    )
    blended_roas: float | None = exec_snap.blended_roas if exec_snap else None
    contribution_margin_pct: float | None = (
        exec_snap.contribution_margin_pct if exec_snap else None
    )

    # --- Acquisition metrics (per-channel ROAS / CAC / payback) ---
    latest_acq_date = db.scalar(
        select(func.max(AcquisitionMetricsSnapshot.snapshot_date)).where(
            AcquisitionMetricsSnapshot.tenant_id == tenant.id
        )
    )
    channel_roas_rows: list[dict[str, Any]] = []
    if latest_acq_date is not None:
        acq_rows = db.scalars(
            select(AcquisitionMetricsSnapshot).where(
                AcquisitionMetricsSnapshot.tenant_id == tenant.id,
                AcquisitionMetricsSnapshot.snapshot_date == latest_acq_date,
            )
        ).all()
        channel_roas_rows = [
            {
                "channel": r.channel,
                "roas": r.roas,
                "cac": r.cac,
                "payback_period_days": r.payback_period_days,
            }
            for r in acq_rows
        ]

    # --- Retention (repeat purchase rate, churn risk count) ---
    retention_snap = db.scalar(
        select(RetentionDailySnapshot)
        .where(RetentionDailySnapshot.tenant_id == tenant.id)
        .order_by(RetentionDailySnapshot.snapshot_date.desc())
        .limit(1)
    )
    repeat_purchase_rate_pct: float | None = (
        retention_snap.repeat_purchase_rate_pct if retention_snap else None
    )
    churn_risk_high_count = 0
    if retention_snap:
        _raw = retention_snap.churn_risk_summary.get("high_risk_count", 0)
        churn_risk_high_count = _raw if isinstance(_raw, int) else 0

    # --- Margin drift (per channel/category) ---
    latest_drift_date = db.scalar(
        select(func.max(MarginDriftSnapshot.snapshot_date)).where(
            MarginDriftSnapshot.tenant_id == tenant.id
        )
    )
    margin_drift_rows: list[dict[str, Any]] = []
    if latest_drift_date is not None:
        drift_rows = db.scalars(
            select(MarginDriftSnapshot).where(
                MarginDriftSnapshot.tenant_id == tenant.id,
                MarginDriftSnapshot.snapshot_date == latest_drift_date,
            )
        ).all()
        margin_drift_rows = [
            {
                "channel": r.channel,
                "category": r.category,
                "drift_pct": r.drift_pct,
                "threshold_exceeded": r.threshold_exceeded,
                "actual_margin_pct": r.actual_margin_pct,
            }
            for r in drift_rows
        ]

    # --- Inventory risk (per SKU) ---
    latest_inv_date = db.scalar(
        select(func.max(InventoryRiskSnapshot.snapshot_date)).where(
            InventoryRiskSnapshot.tenant_id == tenant.id
        )
    )
    inventory_risk_rows: list[dict[str, Any]] = []
    if latest_inv_date is not None:
        inv_rows = db.scalars(
            select(InventoryRiskSnapshot).where(
                InventoryRiskSnapshot.tenant_id == tenant.id,
                InventoryRiskSnapshot.snapshot_date == latest_inv_date,
            )
        ).all()
        inventory_risk_rows = [
            {
                "sku": r.sku,
                "product_title": r.product_title,
                "status": r.status,
                "days_to_stockout": r.days_to_stockout,
                "current_quantity": r.current_quantity,
                "capital_at_risk": r.capital_at_risk,
                "confidence": r.confidence,
            }
            for r in inv_rows
        ]

    # --- Operational impact (per SKU) ---
    latest_op_date = db.scalar(
        select(func.max(OperationalImpactSnapshot.snapshot_date)).where(
            OperationalImpactSnapshot.tenant_id == tenant.id
        )
    )
    operational_impact_rows: list[dict[str, Any]] = []
    if latest_op_date is not None:
        op_rows = db.scalars(
            select(OperationalImpactSnapshot).where(
                OperationalImpactSnapshot.tenant_id == tenant.id,
                OperationalImpactSnapshot.snapshot_date == latest_op_date,
            )
        ).all()
        operational_impact_rows = [
            {
                "sku": r.sku,
                "product_title": r.product_title,
                "inventory_status": r.inventory_status,
                "stockout_lost_revenue_estimate": r.stockout_lost_revenue_estimate,
                "return_rate_30d_pct": r.return_rate_30d_pct,
                "confidence": r.confidence,
            }
            for r in op_rows
        ]

    # --- Data freshness: days since most recent snapshot across all domains ---
    available_dates = [
        d
        for d in [
            exec_snap.snapshot_date if exec_snap else None,
            latest_acq_date,
            retention_snap.snapshot_date if retention_snap else None,
            latest_drift_date,
            latest_inv_date,
            latest_op_date,
        ]
        if d is not None
    ]
    if available_dates:
        data_freshness_days = (today - max(available_dates)).days
    else:
        data_freshness_days = 0

    # --- Rule thresholds ---
    threshold_rows = db.scalars(
        select(TenantRuleThreshold).where(
            TenantRuleThreshold.tenant_id == tenant.id
        )
    ).all()
    thresholds = {r.rule_id: r.threshold_value for r in threshold_rows}

    return RuleInput(
        tenant_id=str(tenant.id),
        snapshot_date=today,
        base_currency=tenant.base_currency,
        blended_roas=blended_roas,
        channel_roas_rows=channel_roas_rows,
        contribution_margin_pct=contribution_margin_pct,
        margin_drift_rows=margin_drift_rows,
        repeat_purchase_rate_pct=repeat_purchase_rate_pct,
        churn_risk_high_count=churn_risk_high_count,
        inventory_risk_rows=inventory_risk_rows,
        operational_impact_rows=operational_impact_rows,
        data_freshness_days=data_freshness_days,
        thresholds=thresholds,
    )


def run_rule_engine_job(
    session_factory: sessionmaker | None = None,
    rules: list[Rule] | None = None,
) -> dict[str, int]:
    """FR-071 / T-053: Evaluate the rule engine against all active tenants.

    Loads the latest metric snapshots for every active tenant, builds a
    RuleInput, runs the deterministic RuleEngine, and persists any new
    Recommendation rows.  Duplicate suppression is enforced by the unique
    constraint on (tenant_id, rule_id, snapshot_date).

    Args:
        session_factory: Override the database session factory (used in tests).
        rules: Override the rule pack (used in tests).

    Returns:
        {"tenants_processed": int, "recommendations_created": int}
    """
    active_rules = rules if rules is not None else get_rules()
    engine = RuleEngine(active_rules)
    today = date.today()
    sf = session_factory or SessionLocal
    db: Session = sf()
    tenants_processed = 0
    recommendations_created = 0
    try:
        tenants = db.scalars(select(Tenant).where(Tenant.is_active.is_(True))).all()
        for tenant in tenants:
            tenants_processed += 1
            rule_input = _build_rule_input(db, tenant, today)
            results = engine.evaluate(rule_input)
            for result in results:
                # Always replace: delete any previous copy of this rule for this
                # tenant (any date) and insert a fresh one. This prevents the
                # recommendations page from filling up with near-identical cards
                # generated on consecutive days.
                db.execute(
                    delete(Recommendation).where(
                        Recommendation.tenant_id == tenant.id,
                        Recommendation.rule_id == result.rule_id,
                        Recommendation.status == "new",
                    )
                )
                rec = Recommendation(
                    tenant_id=tenant.id,
                    rule_id=result.rule_id,
                    domain=result.domain,
                    snapshot_date=today,
                    affected_area=result.affected_area,
                    signal_summary=result.signal_summary,
                    suggested_action=result.suggested_action,
                    estimated_impact=result.estimated_impact,
                    confidence_level=result.confidence_level,
                    data_freshness_context=result.data_freshness_context,
                    priority=result.priority,
                    impact_score=result.impact_score,
                    evidence=result.evidence,
                    status="new",
                )
                db.add(rec)
                recommendations_created += 1
        db.commit()
    finally:
        db.close()
    return {
        "tenants_processed": tenants_processed,
        "recommendations_created": recommendations_created,
    }


@celery_app.task(name="worker.app.tasks.run_rule_engine_schedule")
def run_rule_engine_schedule() -> dict[str, int]:
    return run_rule_engine_job()


# ===========================================================================
# T-054b: Suggested threshold engine
# ===========================================================================

import math  # noqa: E402
import statistics  # noqa: E402

from backend.app.schemas.locale import (  # noqa: E402
    OPS_CURRENCY_SCALE_VS_USD,
    OPS_USD_FLOOR,
)

THRESHOLD_SUGGESTION_LOOKBACK_DAYS = 90
THRESHOLD_SUGGESTION_MIN_SNAPSHOTS = 7


def _compute_suggested_thresholds(
    db: Session,
    tenant: Tenant,
    today: date,
) -> dict[str, float | None]:
    """Compute data-driven suggested threshold values from historical snapshots.

    Uses up to THRESHOLD_SUGGESTION_LOOKBACK_DAYS of metric history per signal.
    Returns None for any rule where fewer than THRESHOLD_SUGGESTION_MIN_SNAPSHOTS
    data points are available — not enough signal to be trustworthy.
    """
    cutoff = today - timedelta(days=THRESHOLD_SUGGESTION_LOOKBACK_DAYS)
    suggestions: dict[str, float | None] = {
        "ACQ-001": None,
        "EXC-001": None,
        "INV-001": None,
        "MRG-001": None,
        "OPS-001": None,
        "RET-001": None,
    }

    # --- ACQ-001 & EXC-001: ExecutiveKpiSnapshot 90-day history ---
    # One snapshot per tenant×date; filter out zero/default rows (no data).
    exec_snaps = db.scalars(
        select(ExecutiveKpiSnapshot)
        .where(
            ExecutiveKpiSnapshot.tenant_id == tenant.id,
            ExecutiveKpiSnapshot.snapshot_date >= cutoff,
        )
        .order_by(ExecutiveKpiSnapshot.snapshot_date)
    ).all()

    roas_values: list[float] = [
        s.blended_roas for s in exec_snaps if s.blended_roas > 0
    ]
    if len(roas_values) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        avg = statistics.mean(roas_values)
        suggestions["ACQ-001"] = round(avg * 0.75, 2)

    cm_values: list[float] = [
        s.contribution_margin_pct
        for s in exec_snaps
        if s.contribution_margin_pct > 0
    ]
    if len(cm_values) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        avg = statistics.mean(cm_values)
        suggestions["EXC-001"] = round(avg * 0.90, 1)

    # --- RET-001: RetentionDailySnapshot 90-day average × 0.85 ---
    ret_values: list[float] = [
        s.repeat_purchase_rate_pct
        for s in db.scalars(
            select(RetentionDailySnapshot).where(
                RetentionDailySnapshot.tenant_id == tenant.id,
                RetentionDailySnapshot.snapshot_date >= cutoff,
                RetentionDailySnapshot.repeat_purchase_rate_pct > 0,
            )
        ).all()
    ]
    if len(ret_values) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        avg = statistics.mean(ret_values)
        suggestions["RET-001"] = round(avg * 0.85, 1)

    # --- INV-001: 75th percentile of daily at-risk SKU counts ---
    _at_risk_statuses = ["stockout_risk", "critical_low", "out_of_stock"]
    inv_dates = db.scalars(
        select(InventoryRiskSnapshot.snapshot_date)
        .where(
            InventoryRiskSnapshot.tenant_id == tenant.id,
            InventoryRiskSnapshot.snapshot_date >= cutoff,
        )
        .distinct()
    ).all()
    if len(inv_dates) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        daily_at_risk: list[int] = []
        for snap_date in inv_dates:
            count = db.scalar(
                select(func.count(InventoryRiskSnapshot.id)).where(
                    InventoryRiskSnapshot.tenant_id == tenant.id,
                    InventoryRiskSnapshot.snapshot_date == snap_date,
                    InventoryRiskSnapshot.status.in_(_at_risk_statuses),
                )
            ) or 0
            daily_at_risk.append(count)
        p75 = statistics.quantiles(daily_at_risk, n=4)[2]
        suggestions["INV-001"] = float(max(1, math.ceil(p75)))

    # --- MRG-001: 75th percentile of daily margin breach counts ---
    mrg_dates = db.scalars(
        select(MarginDriftSnapshot.snapshot_date)
        .where(
            MarginDriftSnapshot.tenant_id == tenant.id,
            MarginDriftSnapshot.snapshot_date >= cutoff,
        )
        .distinct()
    ).all()
    if len(mrg_dates) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        daily_breaches: list[int] = []
        for snap_date in mrg_dates:
            count = db.scalar(
                select(func.count(MarginDriftSnapshot.id)).where(
                    MarginDriftSnapshot.tenant_id == tenant.id,
                    MarginDriftSnapshot.snapshot_date == snap_date,
                    MarginDriftSnapshot.threshold_exceeded.is_(True),
                )
            ) or 0
            daily_breaches.append(count)
        p75 = statistics.quantiles(daily_breaches, n=4)[2]
        suggestions["MRG-001"] = float(max(1, math.ceil(p75)))

    # --- OPS-001: 75th percentile of per-SKU revenue-at-risk values ---
    revenue_values: list[float] = [
        v
        for v in db.scalars(
            select(OperationalImpactSnapshot.stockout_lost_revenue_estimate).where(
                OperationalImpactSnapshot.tenant_id == tenant.id,
                OperationalImpactSnapshot.snapshot_date >= cutoff,
                OperationalImpactSnapshot.stockout_lost_revenue_estimate.is_not(
                    None
                ),
            )
        ).all()
        if v is not None and v > 0
    ]
    if len(revenue_values) >= THRESHOLD_SUGGESTION_MIN_SNAPSHOTS:
        p75 = statistics.quantiles(revenue_values, n=4)[2]
        floor = OPS_USD_FLOOR * OPS_CURRENCY_SCALE_VS_USD.get(
            tenant.base_currency, 1.0
        )
        suggestions["OPS-001"] = round(max(p75, floor), 2)

    return suggestions


def run_threshold_suggestion_job(
    session_factory: sessionmaker | None = None,
) -> dict[str, int]:
    """FR-071 / T-054b: Compute and persist suggested thresholds for all active tenants.

    Reads historical metric snapshots, derives data-driven threshold suggestions
    per rule, and updates TenantRuleThreshold.suggested_value.  When
    is_customised=False, also updates threshold_value so tenants receive smarter
    defaults automatically without any manual configuration.

    Args:
        session_factory: Override the database session factory (used in tests).

    Returns:
        {"tenants_processed": int, "thresholds_updated": int}
    """
    factory = session_factory or SessionLocal
    db: Session = factory()
    tenants_processed = 0
    thresholds_updated = 0
    today = datetime.now(UTC).date()

    try:
        tenants = db.scalars(
            select(Tenant).where(Tenant.is_active.is_(True))
        ).all()
        for tenant in tenants:
            tenants_processed += 1
            suggestions = _compute_suggested_thresholds(db, tenant, today)
            for rule_id, suggested in suggestions.items():
                if suggested is None:
                    continue
                row = db.scalar(
                    select(TenantRuleThreshold).where(
                        TenantRuleThreshold.tenant_id == tenant.id,
                        TenantRuleThreshold.rule_id == rule_id,
                    )
                )
                if row is None:
                    continue
                row.suggested_value = suggested
                if not row.is_customised:
                    row.threshold_value = suggested
                thresholds_updated += 1
        db.commit()
    finally:
        db.close()

    return {
        "tenants_processed": tenants_processed,
        "thresholds_updated": thresholds_updated,
    }


@celery_app.task(name="worker.app.tasks.run_threshold_suggestion_schedule")
def run_threshold_suggestion_schedule() -> dict[str, int]:
    return run_threshold_suggestion_job()


def run_implementation_gap_scan_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, int]:
    """FR-076 / T-062: Scan all approved recommendations for implementation gaps.

    Sets gap flags based on how long recommendations have been in approved status.
    """
    db = session_factory()
    try:
        updated_count = scan_implementation_gaps(db)
        return {
            "recommendations_updated": updated_count,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_implementation_gap_scan_schedule")
def run_implementation_gap_scan_schedule() -> dict[str, int]:
    """Daily task to scan for implementation gaps (FR-076 / T-062)."""
    return run_implementation_gap_scan_job()


def run_outcome_observation_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, int]:
    """FR-069, FR-077 / T-063: Scan for outcome-eligible recommendations.

    Identifies recommendations where:
      - status == "implemented_externally"
      - implemented_at > OUTCOME_OBSERVATION_WINDOW_DAYS ago
    Populates outcome metrics snapshots and impact summaries, then transitions
    to "outcome_observed" status.
    """
    db = session_factory()
    try:
        updated_count = scan_outcome_observations(db)
        return {
            "recommendations_observed": updated_count,
        }
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_outcome_observation_schedule")
def run_outcome_observation_schedule() -> dict[str, int]:
    """Daily task to scan for outcome observations (FR-069, FR-077 / T-063)."""
    return run_outcome_observation_job()


# ============================================================================
# T-064: Saved Analysis Views and Share Metadata (Scheduled Exports)
# ============================================================================


@celery_app.task(name="worker.app.tasks.run_analysis_view_exports_job")
def run_analysis_view_exports_job(
    session_factory: sessionmaker = SessionLocal,
) -> dict[str, Any]:
    """
    FR-034 / T-064: Scan for shared analysis views and send scheduled exports.

    This is a placeholder task for future implementation of scheduled view exports
    with email delivery. Currently just returns success.
    """
    db = session_factory()
    try:
        # Placeholder: Future implementation would:
        # 1. Query AnalysisViewShare records with scheduled_export=True
        # 2. Call export_analysis_view() for each
        # 3. Email exports to recipients
        export_count = 0
        return {"analysis_views_exported": export_count}
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_analysis_view_exports_schedule")
def run_analysis_view_exports_schedule() -> dict[str, Any]:
    """
    Optional daily task to export and email saved analysis views
    (FR-034 / T-064).
    """
    return run_optimization_engine_job()


def run_optimization_engine_job(
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, Any]:
    """
    Run optimization engine for all active tenants (Phase 2 Beta Launch).
    
    Executes the optimizer workflow (fetch data, train models, optimize) and
    creates user-facing Recommendation records with ML-generated insights.
    Each recommendation is linked to its fitted model and optimization run
    for full provenance.
    
    Environment:
        ENABLE_OPTIMIZATION_ENGINE: Set to "true" to enable (default: "false")
    
    Returns:
        Dict with run statistics: tenants_processed, successful_runs, 
        failed_runs, recommendations_created
    """
    # Check if optimization engine is enabled
    if os.getenv("ENABLE_OPTIMIZATION_ENGINE", "false").lower() != "true":
        logger.info("Optimization engine disabled - skipping optimization run")
        return {
            "engine_enabled": False,
            "tenants_processed": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "recommendations_created": 0,
        }
    
    db = session_factory()
    tenants_processed = 0
    successful_runs = 0
    failed_runs = 0
    recommendations_created = 0
    
    try:
        # Query all active tenants
        tenants = list(
            db.scalars(
                select(Tenant).where(Tenant.is_active == True)  # noqa: E712
            )
        )
        
        logger.info(f"Optimization engine: Processing {len(tenants)} active tenants")
        
        for tenant in tenants:
            tenants_processed += 1
            
            # Find enabled optimization strategies for this tenant
            strategies = list(
                db.scalars(
                    select(OptimizationStrategy)
                    .where(OptimizationStrategy.tenant_id == tenant.id)
                    .where(OptimizationStrategy.is_enabled == True)  # noqa: E712
                )
            )
            
            if not strategies:
                logger.debug(
                    f"Optimization engine: No enabled strategies for "
                    f"tenant {tenant.slug}"
                )
                continue
            
            for strategy in strategies:
                try:
                    # Log start of optimization
                    log_optimization_start(
                        tenant_id=tenant.id,
                        strategy_name=strategy.strategy_name,
                        domain=strategy.domain,
                        config=strategy.config,
                    )
                    
                    # Create optimizer based on strategy type
                    if strategy.strategy_type == "budget_allocation":
                        optimizer = BudgetAllocationOptimizer(
                            strategy_id=strategy.id,
                            db=db,
                        )
                        
                        # Run optimization workflow (fetch, train, optimize)
                        # This creates OptimizationRun and FittedModel records
                        result = optimizer.run(
                            tenant_id=tenant.id,
                            days=strategy.config.get("lookback_days", 90),
                        )
                        
                        # Create user-facing recommendation from optimization result
                        recommendation = optimizer.create_recommendation_record()
                        db.commit()
                        recommendations_created += 1
                        
                        # Log success (run_id will be set after train_models)
                        if optimizer.optimization_run_id:
                            log_optimization_success(
                                run_id=optimizer.optimization_run_id,
                                tenant_id=tenant.id,
                                strategy_name=strategy.strategy_name,
                                metrics={
                                    "expected_conversions": result.get(
                                        "expected_impact", {}
                                    ).get("expected_daily_conversions"),
                                    "lift_pct": result.get("expected_impact", {}).get(
                                        "conversions_lift_pct"
                                    ),
                                    "confidence": result.get("confidence_level"),
                                    "recommendation_id": str(recommendation.id),
                                },
                            )
                        
                        lift_pct = result.get("expected_impact", {}).get(
                            "conversions_lift_pct", 0
                        )
                        logger.info(
                            f"Optimization success: {tenant.slug} / "
                            f"{strategy.strategy_name} - lift={lift_pct:.1f}% - "
                            f"recommendation={recommendation.id}"
                        )
                        successful_runs += 1
                    
                    elif strategy.strategy_type == "multi_channel_allocation":
                        optimizer = MultiChannelAllocator(
                            strategy_id=strategy.id,
                            db=db,
                        )
                        
                        result = optimizer.run(
                            tenant_id=tenant.id,
                            days=strategy.config.get("lookback_days", 90),
                        )
                        
                        recommendation = optimizer.create_recommendation_record()
                        db.commit()
                        recommendations_created += 1
                        
                        if optimizer.optimization_run_id:
                            log_optimization_success(
                                run_id=optimizer.optimization_run_id,
                                tenant_id=tenant.id,
                                strategy_name=strategy.strategy_name,
                                metrics={
                                    "lift_pct": result.get("lift_pct", 0),
                                    "num_channels": result.get("num_channels"),
                                    "confidence": getattr(
                                        recommendation,
                                        "confidence_score",
                                        None,
                                    ),
                                    "recommendation_id": str(recommendation.id),
                                },
                            )
                        
                        logger.info(
                            f"Multi-channel optimization success: "
                            f"{tenant.slug} / {strategy.strategy_name} "
                            f"- lift={result.get('lift_pct', 0):.1f}% "
                            f"- channels={result.get('num_channels')} "
                            f"- recommendation={recommendation.id}"
                        )
                        successful_runs += 1

                    else:
                        logger.warning(
                            f"Optimization engine: Unknown strategy type "
                            f"'{strategy.strategy_type}' for tenant {tenant.slug}"
                        )
                
                except Exception as e:
                    failed_runs += 1
                    
                    # Log failure (check if optimizer exists and has run_id)
                    run_id = None
                    if "optimizer" in locals() and hasattr(
                        optimizer, "optimization_run_id"
                    ):
                        run_id = optimizer.optimization_run_id
                    
                    if run_id:
                        log_optimization_failure(
                            run_id=run_id,
                            error=e,
                            tenant_id=tenant.id,
                            strategy_name=strategy.strategy_name,
                            context={
                                "tenant_slug": tenant.slug,
                                "strategy_id": str(strategy.id),
                                "domain": strategy.domain,
                            },
                        )
                    
                    logger.error(
                        f"Optimization engine failed: {tenant.slug} / "
                        f"{strategy.strategy_name} - {e}"
                    )
                    
                    # Capture exception in Sentry
                    sentry_sdk.capture_exception(e)
        
        logger.info(
            f"Optimization engine complete: {tenants_processed} tenants, "
            f"{successful_runs} successful, {failed_runs} failed, "
            f"{recommendations_created} recommendations created"
        )
        
        return {
            "engine_enabled": True,
            "tenants_processed": tenants_processed,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "recommendations_created": recommendations_created,
        }
    
    finally:
        db.close()


@celery_app.task(name="worker.app.tasks.run_optimization_engine_schedule")
def run_optimization_engine_schedule() -> dict[str, Any]:
    """
    Scheduled task to run ML optimization engine (Phase 2 Beta Launch).
    
    Runs the full optimization workflow (fetch data, train saturation curves,
    optimize budget allocations) and creates user-facing Recommendation records
    with ML-generated insights. Each recommendation includes source='optimization',
    optimization_metadata with model accuracy, and fitted_model_id for provenance.
    
    Returns:
        Dict with execution statistics including recommendations_created
    """
    return run_optimization_engine_job()


@celery_app.task(name="worker.app.tasks.run_daily_data_simulation_schedule")
def run_daily_data_simulation_schedule() -> dict[str, Any]:
    """
    Scheduled task to generate daily simulated data for One8 tenant.
    
    Simulates continuous Shopify and ad platform data ingestion by generating
    realistic daily orders, refunds, and ad spend. This keeps the test dataset
    growing organically like a real production environment.
    
    Environment:
        ENABLE_DAILY_DATA_SIMULATION: Set to "true" to enable (default: disabled)
    
    Returns:
        Dict with generation statistics
    """
    # Check if simulation is enabled
    enabled = os.getenv("ENABLE_DAILY_DATA_SIMULATION", "false").lower() == "true"
    
    if not enabled:
        return {
            "simulation_enabled": False,
            "message": (
                "Daily data simulation is disabled. "
                "Set ENABLE_DAILY_DATA_SIMULATION=true to enable."
            ),
        }
    
    # Run simulation for today
    result = run_daily_simulation()
    result["simulation_enabled"] = True
    
    return result

