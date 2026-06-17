import os
from datetime import timedelta

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

SYSTEM_SYNC_CADENCE = {
    "connector-sync-scheduler": timedelta(minutes=15),
    "connector-token-expiry-monitor": timedelta(hours=1),
    "executive-kpi-computation-schedule": timedelta(hours=24),
    "acquisition-metrics-computation-schedule": timedelta(hours=24),
    "retention-cohort-computation-schedule": timedelta(hours=24),
    "retention-segment-computation-schedule": timedelta(hours=24),
    "finance-cost-drift-schedule": timedelta(hours=24),
    "inventory-risk-schedule": timedelta(hours=24),
    "operational-impact-schedule": timedelta(hours=24),
    "rule-engine-schedule": timedelta(hours=24),
    "threshold-suggestion-schedule": timedelta(days=7),
}

SOURCE_SYNC_CADENCE = {
    "shopify-order-sync-schedule": timedelta(minutes=30),
    "shopify-inventory-sync-schedule": timedelta(minutes=30),
    "meta-spend-sync-schedule": timedelta(hours=24),
    "google-spend-sync-schedule": timedelta(hours=24),
}

celery_app = Celery(
    "alpmark_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.app.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "connector-sync-scheduler": {
            "task": "worker.app.tasks.run_connector_sync_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["connector-sync-scheduler"],
        },
        "connector-token-expiry-monitor": {
            "task": "worker.app.tasks.run_token_expiry_monitoring_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["connector-token-expiry-monitor"],
        },
        "executive-kpi-computation-schedule": {
            "task": "worker.app.tasks.run_executive_kpi_computation_schedule",
            "schedule": SYSTEM_SYNC_CADENCE[
                "executive-kpi-computation-schedule"
            ],
        },
        "acquisition-metrics-computation-schedule": {
            "task": "worker.app.tasks.run_acquisition_metrics_computation_schedule",
            "schedule": SYSTEM_SYNC_CADENCE[
                "acquisition-metrics-computation-schedule"
            ],
        },
        "retention-cohort-computation-schedule": {
            "task": "worker.app.tasks.run_retention_cohort_computation_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["retention-cohort-computation-schedule"],
        },
        "retention-segment-computation-schedule": {
            "task": "worker.app.tasks.run_retention_segment_computation_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["retention-segment-computation-schedule"],
        },
        "finance-cost-drift-schedule": {
            "task": "worker.app.tasks.run_finance_cost_drift_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["finance-cost-drift-schedule"],
        },
        "inventory-risk-schedule": {
            "task": "worker.app.tasks.run_inventory_risk_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["inventory-risk-schedule"],
        },
        "operational-impact-schedule": {
            "task": "worker.app.tasks.run_operational_impact_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["operational-impact-schedule"],
        },
        "rule-engine-schedule": {
            "task": "worker.app.tasks.run_rule_engine_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["rule-engine-schedule"],
        },
        "threshold-suggestion-schedule": {
            "task": "worker.app.tasks.run_threshold_suggestion_schedule",
            "schedule": SYSTEM_SYNC_CADENCE["threshold-suggestion-schedule"],
        },
        "shopify-order-sync-schedule": {
            "task": "worker.app.tasks.run_shopify_order_sync_schedule",
            "schedule": SOURCE_SYNC_CADENCE["shopify-order-sync-schedule"],
        },
        "shopify-inventory-sync-schedule": {
            "task": "worker.app.tasks.run_shopify_inventory_sync_schedule",
            "schedule": SOURCE_SYNC_CADENCE["shopify-inventory-sync-schedule"],
        },
        "meta-spend-sync-schedule": {
            "task": "worker.app.tasks.run_meta_spend_sync_schedule",
            "schedule": SOURCE_SYNC_CADENCE["meta-spend-sync-schedule"],
        },
        "google-spend-sync-schedule": {
            "task": "worker.app.tasks.run_google_spend_sync_schedule",
            "schedule": SOURCE_SYNC_CADENCE["google-spend-sync-schedule"],
        },
    },
)
