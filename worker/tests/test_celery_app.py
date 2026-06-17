import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from backend.app.db.base import Base
from backend.app.db.models import (
    AcquisitionMetricsSnapshot,
    AuditEvent,
    CohortRetentionSnapshot,
    CohortReturnSignal,
    ConnectorIntegration,
    CostDriverSnapshot,
    ExecutiveKpiSnapshot,
    GoogleAdSpend,
    InventoryRiskSnapshot,
    MarginDriftSnapshot,
    MarginDriftThreshold,
    MetaAdSpend,
    OperationalImpactSnapshot,
    RetentionDailySnapshot,
    SegmentMarginSnapshot,
    ShopifyInventoryItem,
    ShopifyOrder,
    ShopifyOrderLineItem,
    Tenant,
    TenantRuleThreshold,
)
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from worker.app.celery_app import celery_app
from worker.app.rules.engine import Rule, RuleEngine, RuleInput, RuleResult
from worker.app.tasks import (
    ping,
    run_acquisition_metrics_computation_job,
    run_cohort_return_signal_computation_job,
    run_connector_sync_job,
    run_cost_driver_computation_job,
    run_executive_kpi_computation_job,
    run_google_spend_sync_job,
    run_inventory_risk_computation_job,
    run_margin_drift_computation_job,
    run_meta_spend_sync_job,
    run_operational_impact_computation_job,
    run_retention_cohort_computation_job,
    run_rule_engine_job,
    run_segment_margin_computation_job,
    run_shopify_inventory_sync_job,
    run_shopify_order_sync_job,
    run_threshold_suggestion_job,
    run_token_expiry_monitoring_job,
)


def test_celery_app_is_named() -> None:
    assert celery_app.main == "alpmark_worker"


def test_ping_task_is_registered() -> None:
    assert ping.name == "worker.app.tasks.ping"
    assert ping.name in celery_app.tasks


def test_connector_sync_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "connector-sync-scheduler" in beat_schedule
    assert (
        beat_schedule["connector-sync-scheduler"]["task"]
        == "worker.app.tasks.run_connector_sync_schedule"
    )


def test_token_expiry_monitoring_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "connector-token-expiry-monitor" in beat_schedule
    assert (
        beat_schedule["connector-token-expiry-monitor"]["task"]
        == "worker.app.tasks.run_token_expiry_monitoring_schedule"
    )


def test_executive_kpi_computation_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "executive-kpi-computation-schedule" in beat_schedule
    assert (
        beat_schedule["executive-kpi-computation-schedule"]["task"]
        == "worker.app.tasks.run_executive_kpi_computation_schedule"
    )


def test_shopify_order_sync_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "shopify-order-sync-schedule" in beat_schedule
    assert (
        beat_schedule["shopify-order-sync-schedule"]["task"]
        == "worker.app.tasks.run_shopify_order_sync_schedule"
    )


def test_shopify_inventory_sync_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "shopify-inventory-sync-schedule" in beat_schedule
    assert (
        beat_schedule["shopify-inventory-sync-schedule"]["task"]
        == "worker.app.tasks.run_shopify_inventory_sync_schedule"
    )


def test_meta_spend_sync_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "meta-spend-sync-schedule" in beat_schedule
    assert (
        beat_schedule["meta-spend-sync-schedule"]["task"]
        == "worker.app.tasks.run_meta_spend_sync_schedule"
    )


def test_google_spend_sync_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "google-spend-sync-schedule" in beat_schedule
    assert (
        beat_schedule["google-spend-sync-schedule"]["task"]
        == "worker.app.tasks.run_google_spend_sync_schedule"
    )


def test_source_sync_cadence_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert beat_schedule["shopify-order-sync-schedule"]["schedule"] == timedelta(
        minutes=30
    )
    assert beat_schedule["shopify-inventory-sync-schedule"]["schedule"] == timedelta(
        minutes=30
    )
    assert beat_schedule["meta-spend-sync-schedule"]["schedule"] == timedelta(
        hours=24
    )
    assert beat_schedule["google-spend-sync-schedule"]["schedule"] == timedelta(
        hours=24
    )


def test_executive_kpi_cadence_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert beat_schedule["executive-kpi-computation-schedule"]["schedule"] == timedelta(
        hours=24
    )


def test_run_connector_sync_job_updates_last_synced_at() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    fixed_now = datetime(2026, 5, 22, 23, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="SchedulerCo", slug="schedulerco", is_active=True)
    db.add(tenant)
    db.flush()
    db.add_all(
        [
            ConnectorIntegration(
                tenant_id=tenant.id,
                source="shopify",
                auth_mode="oauth",
                status="connected",
            ),
            ConnectorIntegration(
                tenant_id=tenant.id,
                source="klaviyo",
                auth_mode="api_key",
                status="disconnected",
            ),
        ]
    )
    db.commit()
    db.close()

    updated_count = run_connector_sync_job(session_factory=session_local, now=fixed_now)
    assert updated_count == 1

    verify_db: Session = session_local()
    connectors = list(verify_db.query(ConnectorIntegration).all())
    connected = [item for item in connectors if item.status == "connected"][0]
    disconnected = [item for item in connectors if item.status == "disconnected"][0]
    assert connected.last_synced_at is not None
    assert connected.last_synced_at.replace(tzinfo=UTC) == fixed_now
    assert disconnected.last_synced_at is None
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_token_expiry_monitoring_job_emits_warning_and_expired_alerts() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="ExpiryCo", slug="expiryco", is_active=True)
    db.add(tenant)
    db.flush()
    db.add_all(
        [
            ConnectorIntegration(
                tenant_id=tenant.id,
                source="shopify",
                auth_mode="oauth",
                status="connected",
                oauth_expires_at=now.replace(day=25),
            ),
            ConnectorIntegration(
                tenant_id=tenant.id,
                source="meta",
                auth_mode="oauth",
                status="connected",
                oauth_expires_at=now.replace(day=21),
            ),
            ConnectorIntegration(
                tenant_id=tenant.id,
                source="klaviyo",
                auth_mode="api_key",
                status="connected",
            ),
        ]
    )
    db.commit()
    db.close()

    result = run_token_expiry_monitoring_job(session_factory=session_local, now=now)
    assert result == {"warning_count": 1, "expired_count": 1}

    verify_db: Session = session_local()
    connectors = list(verify_db.query(ConnectorIntegration).all())
    warning_connector = [item for item in connectors if item.source == "shopify"][0]
    expired_connector = [item for item in connectors if item.source == "meta"][0]
    assert warning_connector.oauth_expiry_warning_sent_at is not None
    assert expired_connector.oauth_expired_alert_sent_at is not None
    assert expired_connector.error_message is not None

    events = list(verify_db.query(AuditEvent).all())
    actions = [event.action for event in events]
    assert "connector.oauth_token_expiry_warning" in actions
    assert "connector.oauth_token_expired" in actions

    second_result = run_token_expiry_monitoring_job(
        session_factory=session_local,
        now=now,
    )
    assert second_result == {"warning_count": 0, "expired_count": 0}
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_shopify_order_sync_job_upserts_orders() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 1, 30, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="OrderSyncCo", slug="ordersyncco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        current_now: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_order_id": "shop-order-1",
                "order_number": "#1001",
                "currency": "USD",
                "total_amount": 100.0,
                "order_created_at": current_now,
            },
            {
                "external_order_id": "shop-order-2",
                "order_number": "#1002",
                "currency": "USD",
                "total_amount": 150.0,
                "order_created_at": current_now,
            },
        ]

    first = run_shopify_order_sync_job(
        session_factory=session_local,
        now=now,
        order_fetcher=fetcher,
    )
    assert first == {"connector_count": 1, "order_upsert_count": 2}

    second = run_shopify_order_sync_job(
        session_factory=session_local,
        now=now,
        order_fetcher=fetcher,
    )
    assert second == {"connector_count": 1, "order_upsert_count": 2}

    verify_db: Session = session_local()
    orders = list(verify_db.query(ShopifyOrder).all())
    assert len(orders) == 2
    connector_after = verify_db.query(ConnectorIntegration).first()
    assert connector_after is not None
    assert connector_after.last_synced_at is not None
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "connector.shopify_orders_synced")
        .all()
    )
    assert len(events) == 2
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_executive_kpi_computation_job_computes_daily_snapshot_and_drift() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 9, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="ExecutiveKpiCo", slug="executivekpico", is_active=True)
    db.add(tenant)
    db.flush()

    previous_snapshot = ExecutiveKpiSnapshot(
        tenant_id=tenant.id,
        snapshot_date=(now - timedelta(days=1)).date(),
        period_start_date=(now - timedelta(days=30)).date(),
        period_end_date=(now - timedelta(days=1)).date(),
        revenue_amount=800.0,
        ad_spend_amount=200.0,
        blended_roas=4.0,
        contribution_margin_pct=75.0,
        drift={
            "revenue_amount_pct": 0.0,
            "ad_spend_amount_pct": 0.0,
            "blended_roas_pct": 0.0,
            "contribution_margin_pct_change": 0.0,
        },
    )
    db.add(previous_snapshot)

    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_order_id="exec-order-1",
            order_number="#EXEC-1001",
            currency="USD",
            total_amount=1000.0,
            order_created_at=now - timedelta(days=2),
            synced_at=now,
        )
    )
    db.add(
        MetaAdSpend(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_campaign_id="meta-camp-1",
            campaign_name="Meta Prospecting",
            spend_date=(now - timedelta(days=1)).date(),
            currency="USD",
            spend_amount=100.0,
            synced_at=now,
        )
    )
    db.add(
        GoogleAdSpend(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_campaign_id="google-camp-1",
            campaign_name="Google Search",
            spend_date=(now - timedelta(days=1)).date(),
            currency="USD",
            spend_amount=150.0,
            synced_at=now,
        )
    )
    db.commit()
    db.close()

    result = run_executive_kpi_computation_job(session_factory=session_local, now=now)
    assert result == {"tenant_count": 1, "snapshot_count": 1}

    verify_db: Session = session_local()
    snapshot = verify_db.scalar(
        verify_db.query(ExecutiveKpiSnapshot)
        .filter(ExecutiveKpiSnapshot.snapshot_date == now.date())
        .statement
    )
    assert snapshot is not None
    assert snapshot.revenue_amount == 1000.0
    assert snapshot.ad_spend_amount == 250.0
    assert snapshot.blended_roas == 4.0
    assert snapshot.contribution_margin_pct == 75.0
    assert snapshot.drift["revenue_amount_pct"] == 25.0
    assert snapshot.drift["ad_spend_amount_pct"] == 25.0
    assert snapshot.drift["blended_roas_pct"] == 0.0
    assert snapshot.drift["contribution_margin_pct_change"] == 0.0

    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "kpi.executive_snapshot_computed")
        .all()
    )
    assert len(events) == 1
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_shopify_inventory_sync_job_upserts_inventory_items() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 2, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="InventorySyncCo", slug="inventorysyncco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        current_now: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_inventory_item_id": "inv-item-1",
                "sku": "SKU-1001",
                "product_title": "Core Tee",
                "variant_title": "Black / M",
                "available_quantity": 42,
                "synced_at": current_now,
            },
            {
                "external_inventory_item_id": "inv-item-2",
                "sku": "SKU-1002",
                "product_title": "Core Hoodie",
                "variant_title": "Grey / L",
                "available_quantity": 17,
                "synced_at": current_now,
            },
        ]

    first = run_shopify_inventory_sync_job(
        session_factory=session_local,
        now=now,
        inventory_fetcher=fetcher,
    )
    assert first == {"connector_count": 1, "inventory_upsert_count": 2}

    second = run_shopify_inventory_sync_job(
        session_factory=session_local,
        now=now,
        inventory_fetcher=fetcher,
    )
    assert second == {"connector_count": 1, "inventory_upsert_count": 2}

    verify_db: Session = session_local()
    items = list(verify_db.query(ShopifyInventoryItem).all())
    assert len(items) == 2
    connector_after = verify_db.query(ConnectorIntegration).first()
    assert connector_after is not None
    assert connector_after.last_synced_at is not None
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "connector.shopify_inventory_synced")
        .all()
    )
    assert len(events) == 2
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_meta_spend_sync_job_upserts_spend_rows() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 3, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="MetaSpendCo", slug="metaspendco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_campaign_id": "meta-camp-1",
                "campaign_name": "Meta Prospecting",
                "spend_date": date(2026, 5, 22),
                "currency": "USD",
                "spend_amount": 240.5,
            },
            {
                "external_campaign_id": "meta-camp-2",
                "campaign_name": "Meta Retargeting",
                "spend_date": date(2026, 5, 22),
                "currency": "USD",
                "spend_amount": 95.25,
            },
        ]

    first = run_meta_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=fetcher,
    )
    assert first == {"connector_count": 1, "spend_row_upsert_count": 2}

    second = run_meta_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=fetcher,
    )
    assert second == {"connector_count": 1, "spend_row_upsert_count": 2}

    verify_db: Session = session_local()
    rows = list(verify_db.query(MetaAdSpend).all())
    assert len(rows) == 2
    connector_after = verify_db.query(ConnectorIntegration).first()
    assert connector_after is not None
    assert connector_after.last_synced_at is not None
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "connector.meta_spend_synced")
        .all()
    )
    assert len(events) == 2
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_google_spend_sync_job_upserts_spend_rows() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 4, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="GoogleSpendCo", slug="googlespendco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_campaign_id": "google-camp-1",
                "campaign_name": "Google Search Branded",
                "spend_date": date(2026, 5, 22),
                "currency": "USD",
                "spend_amount": 180.45,
            },
            {
                "external_campaign_id": "google-camp-2",
                "campaign_name": "Google Search Generic",
                "spend_date": date(2026, 5, 22),
                "currency": "USD",
                "spend_amount": 402.9,
            },
        ]

    first = run_google_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=fetcher,
    )
    assert first == {"connector_count": 1, "spend_row_upsert_count": 2}

    second = run_google_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=fetcher,
    )
    assert second == {"connector_count": 1, "spend_row_upsert_count": 2}

    verify_db: Session = session_local()
    rows = list(verify_db.query(GoogleAdSpend).all())
    assert len(rows) == 2
    connector_after = verify_db.query(ConnectorIntegration).first()
    assert connector_after is not None
    assert connector_after.last_synced_at is not None
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "connector.google_ads_spend_synced")
        .all()
    )
    assert len(events) == 2
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_meta_spend_sync_job_creates_failure_alert_on_fetch_error() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 5, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="MetaFailureCo", slug="metafailureco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def failing_fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        raise RuntimeError("meta api timeout")

    result = run_meta_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=failing_fetcher,
    )
    assert result == {"connector_count": 0, "spend_row_upsert_count": 0}

    verify_db: Session = session_local()
    failed_connector = verify_db.query(ConnectorIntegration).first()
    assert failed_connector is not None
    assert failed_connector.error_message is not None
    assert "timed out" in failed_connector.error_message.lower()
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "alert.connector_sync_failure_created")
        .all()
    )
    assert len(events) == 1
    assert events[0].details["source"] == "meta"
    assert events[0].details["reason"] == "meta api timeout"
    assert events[0].details["error_code"] == "NETWORK_TIMEOUT"
    assert "Retry sync" in str(events[0].details["suggested_action"])
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_google_spend_sync_job_creates_failure_alert_on_fetch_error() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 5, 30, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="GoogleFailureCo", slug="googlefailureco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def failing_fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        raise RuntimeError("google ads quota exceeded")

    result = run_google_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=failing_fetcher,
    )
    assert result == {"connector_count": 0, "spend_row_upsert_count": 0}

    verify_db: Session = session_local()
    failed_connector = verify_db.query(ConnectorIntegration).first()
    assert failed_connector is not None
    assert failed_connector.error_message is not None
    assert "rate limit" in failed_connector.error_message.lower()
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "alert.connector_sync_failure_created")
        .all()
    )
    assert len(events) == 1
    assert events[0].details["source"] == "google_ads"
    assert events[0].details["reason"] == "google ads quota exceeded"
    assert events[0].details["error_code"] == "RATE_LIMITED"
    assert "Retry later" in str(events[0].details["suggested_action"])
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_meta_spend_sync_job_retries_then_succeeds() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 6, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="MetaRetryCo", slug="metaretryco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    call_count = {"value": 0}
    backoffs: list[float] = []

    def flaky_fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise RuntimeError("temporary timeout")
        return [
            {
                "external_campaign_id": "meta-retry-1",
                "campaign_name": "Meta Retry Campaign",
                "spend_date": date(2026, 5, 22),
                "currency": "USD",
                "spend_amount": 123.45,
            }
        ]

    result = run_meta_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=flaky_fetcher,
        max_attempts=3,
        base_backoff_seconds=1.0,
        max_backoff_seconds=5.0,
        sleep_fn=lambda seconds: backoffs.append(seconds),
    )
    assert result == {"connector_count": 1, "spend_row_upsert_count": 1}
    assert call_count["value"] == 3
    assert backoffs == [1.0, 2.0]

    verify_db: Session = session_local()
    failure_alerts = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "alert.connector_sync_failure_created")
        .all()
    )
    assert len(failure_alerts) == 0
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_google_spend_sync_job_retries_with_capped_backoff() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 23, 6, 30, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="GoogleRetryCo", slug="googleretryco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="google_ads",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    call_count = {"value": 0}
    backoffs: list[float] = []

    def failing_fetcher(
        _: ConnectorIntegration,
        __: datetime,
    ) -> list[dict[str, object]]:
        call_count["value"] += 1
        raise RuntimeError("google rate limit")

    result = run_google_spend_sync_job(
        session_factory=session_local,
        now=now,
        spend_fetcher=failing_fetcher,
        max_attempts=4,
        base_backoff_seconds=2.0,
        max_backoff_seconds=3.0,
        sleep_fn=lambda seconds: backoffs.append(seconds),
    )
    assert result == {"connector_count": 0, "spend_row_upsert_count": 0}
    assert call_count["value"] == 4
    assert backoffs == [2.0, 3.0, 3.0]

    verify_db: Session = session_local()
    failure_alerts = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "alert.connector_sync_failure_created")
        .all()
    )
    assert len(failure_alerts) == 1
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_acquisition_metrics_computation_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "acquisition-metrics-computation-schedule" in beat_schedule
    assert (
        beat_schedule["acquisition-metrics-computation-schedule"]["task"]
        == "worker.app.tasks.run_acquisition_metrics_computation_schedule"
    )


def test_acquisition_metrics_cadence_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert beat_schedule["acquisition-metrics-computation-schedule"][
        "schedule"
    ] == timedelta(hours=24)


def test_run_acquisition_metrics_computation_job_computes_per_channel_snapshots() -> (
    None
):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 9, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="AcqMetricsCo", slug="acqmetricsco", is_active=True)
    db.add(tenant)
    db.flush()

    # Two orders totalling 1000 revenue
    for i, amount in enumerate([600.0, 400.0]):
        db.add(
            ShopifyOrder(
                tenant_id=tenant.id,
                connector_id=uuid.uuid4(),
                external_order_id=f"acq-order-{i}",
                order_number=f"#ACQ-{1000 + i}",
                currency="USD",
                total_amount=amount,
                order_created_at=now - timedelta(days=2),
                synced_at=now,
            )
        )

    # Meta spend: 200, Google spend: 300 → total 500
    db.add(
        MetaAdSpend(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_campaign_id="acq-meta-1",
            campaign_name="Meta Prospecting",
            spend_date=(now - timedelta(days=1)).date(),
            currency="USD",
            spend_amount=200.0,
            synced_at=now,
        )
    )
    db.add(
        GoogleAdSpend(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_campaign_id="acq-google-1",
            campaign_name="Google Search",
            spend_date=(now - timedelta(days=1)).date(),
            currency="USD",
            spend_amount=300.0,
            synced_at=now,
        )
    )
    db.commit()
    db.close()

    result = run_acquisition_metrics_computation_job(
        session_factory=session_local, now=now
    )
    # 3 channels: meta, google_ads, blended
    assert result == {"tenant_count": 1, "snapshot_count": 3}

    verify_db: Session = session_local()
    snapshots = list(
        verify_db.query(AcquisitionMetricsSnapshot)
        .filter(AcquisitionMetricsSnapshot.snapshot_date == now.date())
        .order_by(AcquisitionMetricsSnapshot.channel)
        .all()
    )
    assert len(snapshots) == 3

    channels = {s.channel: s for s in snapshots}
    assert set(channels.keys()) == {"meta", "google_ads", "blended"}

    # Blended: spend=500, revenue=1000, orders=2
    blended = channels["blended"]
    assert blended.ad_spend_amount == 500.0
    assert blended.revenue_attributed == 1000.0
    assert blended.order_count == 2
    assert blended.roas == 2.0
    assert blended.cac == 250.0
    # contribution_margin_pct = (1000 - 500) / 1000 * 100 = 50.0
    assert blended.contribution_margin_pct == 50.0
    # payback: cac / avg_contribution * period_days
    # avg_contribution = (1000 - 500) / 2 = 250; 250 / 250 * 30 = 30 days
    assert blended.payback_period_days == 30.0
    # upside (10% better margin): avg_contribution = 250*1.10=275; 250/275*30 ≈ 27.27
    assert blended.payback_upside_days == round(250 / 275 * 30, 2)
    # downside (10% worse margin): avg_contribution = 250*0.90=225; 250/225*30 ≈ 33.33
    assert blended.payback_downside_days == round(250 / 225 * 30, 2)

    # Meta: share = 200/500 = 0.4 → revenue = 400, orders = round(2*0.4) = 1
    meta = channels["meta"]
    assert meta.ad_spend_amount == 200.0
    assert meta.revenue_attributed == 400.0
    assert meta.order_count == 1
    assert meta.roas == 2.0
    # cac = 200/1 = 200
    assert meta.cac == 200.0

    # Google: share = 300/500 = 0.6 → revenue = 600, orders = round(2*0.6) = 1
    google = channels["google_ads"]
    assert google.ad_spend_amount == 300.0
    assert google.revenue_attributed == 600.0
    assert google.order_count == 1
    assert google.roas == 2.0
    assert google.cac == 300.0

    # One audit event per snapshot row
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "kpi.acquisition_metrics_computed")
        .all()
    )
    assert len(events) == 3
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_retention_cohort_computation_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "retention-cohort-computation-schedule" in beat_schedule
    assert (
        beat_schedule["retention-cohort-computation-schedule"]["task"]
        == "worker.app.tasks.run_retention_cohort_computation_schedule"
    )


def test_retention_cadence_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert beat_schedule["retention-cohort-computation-schedule"][
        "schedule"
    ] == timedelta(hours=24)


def test_run_retention_cohort_computation_job_no_orders_skips_tenant() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)
    db: Session = session_local()
    tenant = Tenant(name="EmptyRetCo", slug="emptyretco", is_active=True)
    db.add(tenant)
    db.commit()
    db.close()

    result = run_retention_cohort_computation_job(
        session_factory=session_local, now=now
    )
    assert result == {"retention_snapshot_count": 0, "cohort_snapshot_count": 0}

    verify_db: Session = session_local()
    assert verify_db.query(RetentionDailySnapshot).count() == 0
    assert verify_db.query(CohortRetentionSnapshot).count() == 0
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_retention_cohort_computation_job_computes_snapshots() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    # now = 2026-05-25T12:00 UTC → snapshot_date = 2026-05-25
    now = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="RetCohortCo", slug="retcohortco", is_active=True)
    db.add(tenant)
    db.flush()
    connector_id = uuid.uuid4()

    # CUST-A: cohort 2026-01, two orders 31 days apart
    # first order: 2026-01-01, second order: 2026-02-01
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="ret-a-1",
            order_number="#RET-A-1",
            currency="USD",
            total_amount=100.0,
            customer_id="CUST-A",
            order_created_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            synced_at=now,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="ret-a-2",
            order_number="#RET-A-2",
            currency="USD",
            total_amount=120.0,
            customer_id="CUST-A",
            order_created_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            synced_at=now,
        )
    )

    # CUST-B: cohort 2026-01, one order only (no repeat)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="ret-b-1",
            order_number="#RET-B-1",
            currency="USD",
            total_amount=80.0,
            customer_id="CUST-B",
            order_created_at=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
            synced_at=now,
        )
    )

    # CUST-C: cohort 2026-02, two orders 15 days apart
    # first order: 2026-02-01, second order: 2026-02-16
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="ret-c-1",
            order_number="#RET-C-1",
            currency="USD",
            total_amount=90.0,
            customer_id="CUST-C",
            order_created_at=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            synced_at=now,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="ret-c-2",
            order_number="#RET-C-2",
            currency="USD",
            total_amount=110.0,
            customer_id="CUST-C",
            order_created_at=datetime(2026, 2, 16, 10, 0, tzinfo=UTC),
            synced_at=now,
        )
    )
    db.commit()
    db.close()

    result = run_retention_cohort_computation_job(
        session_factory=session_local, now=now
    )
    # 1 tenant with orders → 1 daily snapshot, 2 cohort snapshots
    assert result == {"retention_snapshot_count": 1, "cohort_snapshot_count": 2}

    verify_db: Session = session_local()

    # Verify daily snapshot
    daily_snaps = list(verify_db.query(RetentionDailySnapshot).all())
    assert len(daily_snaps) == 1
    ds = daily_snaps[0]
    assert ds.snapshot_date == date(2026, 5, 25)
    assert ds.total_customers == 3
    assert ds.repeat_customers == 2
    assert ds.repeat_purchase_rate_pct == round(2 / 3 * 100, 2)
    assert ds.trend_30d is None  # no prior snapshots exist
    assert ds.trend_60d is None
    assert ds.trend_90d is None

    # expected cadence = median([31.0, 15.0]) = (15.0 + 31.0) / 2 = 23.0
    assert ds.expected_repurchase_cadence_days == 23.0

    # Lifecycle funnel
    assert ds.lifecycle_funnel["first_order_count"] == 3
    assert ds.lifecycle_funnel["second_order_count"] == 2
    assert ds.lifecycle_funnel["repeat_cadence_count"] == 0
    assert ds.lifecycle_funnel["first_to_second_pct"] == round(2 / 3 * 100, 2)
    assert ds.lifecycle_funnel["second_to_repeat_pct"] == 0.0

    # All customers are well past cadence of 23 days → all churned
    assert ds.churn_risk_summary["churned_count"] == 3
    assert ds.churn_risk_summary["healthy_count"] == 0

    # Verify cohort snapshots
    cohort_snaps = (
        verify_db.query(CohortRetentionSnapshot)
        .filter(CohortRetentionSnapshot.snapshot_date == date(2026, 5, 25))
        .order_by(CohortRetentionSnapshot.cohort_month)
        .all()
    )
    assert len(cohort_snaps) == 2

    cohorts = {c.cohort_month: c for c in cohort_snaps}
    assert set(cohorts.keys()) == {"2026-01", "2026-02"}

    # Cohort 2026-01: CUST-A (repeat) + CUST-B (not repeat)
    jan = cohorts["2026-01"]
    assert jan.cohort_size == 2
    assert jan.repeat_customer_count == 1
    assert jan.repeat_purchase_rate_pct == 50.0
    assert jan.days_since_cohort_start == (date(2026, 5, 25) - date(2026, 1, 1)).days
    # Only CUST-A has second order in this cohort: 31 days
    assert jan.avg_days_to_second_order == 31.0

    # Cohort 2026-02: CUST-C only (repeat)
    feb = cohorts["2026-02"]
    assert feb.cohort_size == 1
    assert feb.repeat_customer_count == 1
    assert feb.repeat_purchase_rate_pct == 100.0
    assert feb.days_since_cohort_start == (date(2026, 5, 25) - date(2026, 2, 1)).days
    # CUST-C: 15 days to second order
    assert feb.avg_days_to_second_order == 15.0

    # One audit event per tenant
    events = list(
        verify_db.query(AuditEvent)
        .filter(AuditEvent.action == "kpi.retention_snapshot_computed")
        .all()
    )
    assert len(events) == 1
    assert events[0].details["total_customers"] == 3
    assert events[0].details["cohort_snapshot_count"] == 2

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_shopify_order_sync_job_stores_financial_fields() -> None:
    """Order sync correctly stores discount_amount, shipping_amount,
    refund_amount, and is_refunded from the fetcher payload."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(
        name="OrderFinancialCo", slug="orderfinancialco", is_active=True
    )
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        current_now: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_order_id": "fin-order-1",
                "order_number": "#FIN-1001",
                "currency": "USD",
                "total_amount": 200.0,
                "discount_amount": 15.0,
                "shipping_amount": 8.99,
                "refund_amount": None,
                "is_refunded": False,
                "order_created_at": current_now,
            },
            {
                "external_order_id": "fin-order-2",
                "order_number": "#FIN-1002",
                "currency": "USD",
                "total_amount": 75.0,
                "discount_amount": None,
                "shipping_amount": 4.99,
                "refund_amount": 75.0,
                "is_refunded": True,
                "order_created_at": current_now,
            },
        ]

    result = run_shopify_order_sync_job(
        session_factory=session_local,
        now=now,
        order_fetcher=fetcher,
    )
    assert result == {"connector_count": 1, "order_upsert_count": 2}

    verify_db: Session = session_local()
    orders = {
        o.external_order_id: o
        for o in verify_db.query(ShopifyOrder).all()
    }
    assert len(orders) == 2

    order_1 = orders["fin-order-1"]
    assert order_1.discount_amount == 15.0
    assert order_1.shipping_amount == 8.99
    assert order_1.refund_amount is None
    assert order_1.is_refunded is False

    order_2 = orders["fin-order-2"]
    assert order_2.discount_amount is None
    assert order_2.shipping_amount == 4.99
    assert order_2.refund_amount == 75.0
    assert order_2.is_refunded is True

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_shopify_order_sync_job_stores_line_items() -> None:
    """Order sync upserts line items into shopify_order_line_items."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 11, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="LineItemCo", slug="lineitemco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        current_now: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_order_id": "li-order-1",
                "order_number": "#LI-1001",
                "currency": "USD",
                "total_amount": 120.0,
                "order_created_at": current_now,
                "line_items": [
                    {
                        "sku": "SKU-A",
                        "product_title": "Widget A",
                        "quantity": 2,
                        "unit_price": 30.0,
                    },
                    {
                        "sku": "SKU-B",
                        "product_title": "Widget B",
                        "quantity": 1,
                        "unit_price": 60.0,
                    },
                ],
            }
        ]

    # First sync — creates order + 2 line items
    result = run_shopify_order_sync_job(
        session_factory=session_local,
        now=now,
        order_fetcher=fetcher,
    )
    assert result == {"connector_count": 1, "order_upsert_count": 1}

    verify_db: Session = session_local()
    line_items = list(verify_db.query(ShopifyOrderLineItem).all())
    assert len(line_items) == 2
    skus = {li.sku for li in line_items}
    assert skus == {"SKU-A", "SKU-B"}
    qty_a = next(li.quantity for li in line_items if li.sku == "SKU-A")
    assert qty_a == 2
    verify_db.close()

    # Second sync — idempotent, still 2 line items
    run_shopify_order_sync_job(
        session_factory=session_local,
        now=now,
        order_fetcher=fetcher,
    )
    verify_db2: Session = session_local()
    assert verify_db2.query(ShopifyOrderLineItem).count() == 2
    verify_db2.close()

    Base.metadata.drop_all(bind=engine)


def test_run_shopify_inventory_sync_job_stores_financial_fields() -> None:
    """Inventory sync correctly stores reorder_point, cost_per_unit, and
    location_id from the fetcher payload (including nullable variants)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 10, 30, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(
        name="InvFinancialCo", slug="invfinancialco", is_active=True
    )
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.commit()
    db.close()

    def fetcher(
        _: ConnectorIntegration,
        current_now: datetime,
    ) -> list[dict[str, object]]:
        return [
            {
                "external_inventory_item_id": "inv-fin-001",
                "sku": "SKU-FIN-001",
                "product_title": "Cargo Pant",
                "variant_title": "Olive / 32",
                "available_quantity": 55,
                "reorder_point": 25,
                "cost_per_unit": 22.50,
                "location_id": "LOC-SYDNEY",
                "synced_at": current_now,
            },
            {
                "external_inventory_item_id": "inv-fin-002",
                "sku": "SKU-FIN-002",
                "product_title": "Cargo Pant",
                "variant_title": "Black / 34",
                "available_quantity": 8,
                "reorder_point": None,
                "cost_per_unit": None,
                "location_id": None,
                "synced_at": current_now,
            },
        ]

    result = run_shopify_inventory_sync_job(
        session_factory=session_local,
        now=now,
        inventory_fetcher=fetcher,
    )
    assert result == {"connector_count": 1, "inventory_upsert_count": 2}

    verify_db: Session = session_local()
    items = {
        i.external_inventory_item_id: i
        for i in verify_db.query(ShopifyInventoryItem).all()
    }
    assert len(items) == 2

    item_1 = items["inv-fin-001"]
    assert item_1.reorder_point == 25
    assert item_1.cost_per_unit == 22.50
    assert item_1.location_id == "LOC-SYDNEY"

    item_2 = items["inv-fin-002"]
    assert item_2.reorder_point is None
    assert item_2.cost_per_unit is None
    assert item_2.location_id is None

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# T-046  FR-041 — Segment margin and FR-042 — cohort return signal
# ---------------------------------------------------------------------------


def test_retention_segment_computation_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "retention-segment-computation-schedule" in beat_schedule
    assert (
        beat_schedule["retention-segment-computation-schedule"]["task"]
        == "worker.app.tasks.run_retention_segment_computation_schedule"
    )
    assert beat_schedule["retention-segment-computation-schedule"][
        "schedule"
    ] == timedelta(hours=24)


def test_run_segment_margin_computation_job_no_orders_skips_tenant() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    db: Session = session_local()
    tenant = Tenant(name="EmptySegCo", slug="emptysegco", is_active=True)
    db.add(tenant)
    db.commit()
    db.close()

    result = run_segment_margin_computation_job(
        session_factory=session_local, now=now
    )
    assert result == {"segment_snapshot_count": 0}

    verify_db: Session = session_local()
    assert verify_db.query(SegmentMarginSnapshot).count() == 0
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_segment_margin_computation_job_classifies_segments_and_computes_margins(  # noqa: E501
) -> None:
    """FR-041 behavioural test.

    now = 2026-05-25T10:00UTC → analysis period: 2026-04-25 to 2026-05-25

    Customers seeded:
      CUST-A  1 order (2026-05-10, in period)  → NEW
      CUST-B  2 orders (2026-03-01 outside + 2026-05-12 in period) → RETURNING
      CUST-C  3 orders (2026-02-01, 2026-03-15 outside + 2026-05-15 in period)
              with highest LTV (200+180+150=530) → HIGH_VALUE

    No RetentionDailySnapshot seeded → at_risk and churned segments are skipped.

    MetaAdSpend: $50 on 2026-05-10 (in period)
      → acquisition_cost for NEW = $50, for all others = $0

    Expected segment margins:
      new:       revenue=100, shipping=5,  returns=0, acq=50  → margin=45,  pct=45.0
      returning: revenue=60,  shipping=3,  returns=0, acq=0   → margin=57,  pct=95.0
      high_value:revenue=150, shipping=7.5,returns=0, acq=0   → margin=142.5,pct=95.0
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    connector_id = uuid.uuid4()

    db: Session = session_local()
    tenant = Tenant(name="SegMarginCo", slug="segmargco", is_active=True)
    db.add(tenant)
    db.flush()

    # CUST-A: 1 order in period (new customer)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-a-1",
            order_number="#SEG-A-1",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 5, 10, 9, 0, tzinfo=UTC),
            total_amount=100.0,
            currency="USD",
            shipping_amount=5.0,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )

    # CUST-B: order 1 outside period, order 2 inside period (returning)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-b-1",
            order_number="#SEG-B-1",
            customer_id="CUST-B",
            order_created_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
            total_amount=80.0,
            currency="USD",
            shipping_amount=4.0,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-b-2",
            order_number="#SEG-B-2",
            customer_id="CUST-B",
            order_created_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
            total_amount=60.0,
            currency="USD",
            shipping_amount=3.0,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )

    # CUST-C: 3 orders, highest LTV (530), period order on 2026-05-15 (high_value)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-c-1",
            order_number="#SEG-C-1",
            customer_id="CUST-C",
            order_created_at=datetime(2026, 2, 1, 9, 0, tzinfo=UTC),
            total_amount=200.0,
            currency="USD",
            shipping_amount=10.0,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-c-2",
            order_number="#SEG-C-2",
            customer_id="CUST-C",
            order_created_at=datetime(2026, 3, 15, 9, 0, tzinfo=UTC),
            total_amount=180.0,
            currency="USD",
            shipping_amount=9.0,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="seg-c-3",
            order_number="#SEG-C-3",
            customer_id="CUST-C",
            order_created_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
            total_amount=150.0,
            currency="USD",
            shipping_amount=7.5,
            discount_amount=None,
            refund_amount=None,
            is_refunded=False,
        )
    )

    # MetaAdSpend: $50 in period
    db.add(
        MetaAdSpend(
            tenant_id=tenant.id,
            connector_id=connector_id,
            spend_date=date(2026, 5, 10),
            external_campaign_id="camp-001",
            campaign_name="Campaign 001",
            spend_amount=50.0,
            currency="USD",
        )
    )

    db.commit()
    db.close()

    result = run_segment_margin_computation_job(
        session_factory=session_local, now=now
    )
    # new + returning + high_value = 3 snapshots (no cadence → no at_risk/churned)
    assert result == {"segment_snapshot_count": 3}

    verify_db: Session = session_local()
    snapshots = {
        s.segment_type: s
        for s in verify_db.query(SegmentMarginSnapshot).all()
    }
    assert set(snapshots.keys()) == {"new", "returning", "high_value"}

    new_snap = snapshots["new"]
    assert new_snap.customer_count == 1
    assert new_snap.order_count == 1
    assert new_snap.revenue == 100.0
    assert new_snap.shipping_cost == 5.0
    assert new_snap.returns_cost == 0.0
    assert new_snap.acquisition_cost == 50.0
    assert new_snap.cogs == 0.0
    assert abs(new_snap.contribution_margin_amount - 45.0) < 0.01
    assert abs(new_snap.contribution_margin_pct - 45.0) < 0.01
    assert new_snap.data_completeness == "partial_no_cogs"

    ret_snap = snapshots["returning"]
    # CUST-B (60 in period) + CUST-C (150 in period) are both returning
    assert ret_snap.customer_count == 2
    assert ret_snap.order_count == 2
    assert ret_snap.revenue == 210.0
    assert ret_snap.shipping_cost == 10.5
    assert ret_snap.returns_cost == 0.0
    assert ret_snap.acquisition_cost == 0.0
    assert abs(ret_snap.contribution_margin_amount - 199.5) < 0.01
    assert abs(ret_snap.contribution_margin_pct - 95.0) < 0.01

    hv_snap = snapshots["high_value"]
    # CUST-C has the highest LTV (530 vs 140 vs 100) → top 1 of 3 with period orders
    assert hv_snap.customer_count == 1
    assert hv_snap.order_count == 1
    assert hv_snap.revenue == 150.0
    assert hv_snap.shipping_cost == 7.5
    assert hv_snap.acquisition_cost == 0.0
    assert abs(hv_snap.contribution_margin_amount - 142.5) < 0.01

    audit_events = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "kpi.segment_margin_snapshot_computed"
    ).all()
    assert len(audit_events) == 1

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_cohort_return_signal_computation_job_computes_return_rate() -> None:
    """FR-042 behavioural test.

    Cohort 2026-01:
      CUST-A: 2 orders (Jan-05 not refunded, Jan-20 refunded)
      CUST-B: 1 order  (Jan-10 not refunded)
      → total_orders=3, refunded=1, return_rate_pct≈33.33
      CohortRetentionSnapshot seeded: repeat_purchase_rate_pct=50.0

    Cohort 2026-03:
      CUST-C: 2 orders (Mar-01 refunded, Mar-20 not refunded)
      → total_orders=2, refunded=1, return_rate_pct=50.0
      CohortRetentionSnapshot seeded: repeat_purchase_rate_pct=100.0

    Expected: 2 CohortReturnSignal rows, 1 AuditEvent per tenant.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    connector_id = uuid.uuid4()

    db: Session = session_local()
    tenant = Tenant(name="CohortRetSig", slug="cohortretsigtco", is_active=True)
    db.add(tenant)
    db.flush()

    # CUST-A, cohort 2026-01, two orders
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="crs-a-1",
            order_number="#CRS-A-1",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
            total_amount=80.0,
            currency="USD",
            is_refunded=False,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="crs-a-2",
            order_number="#CRS-A-2",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 1, 20, 9, 0, tzinfo=UTC),
            total_amount=60.0,
            currency="USD",
            refund_amount=60.0,
            is_refunded=True,
        )
    )

    # CUST-B, cohort 2026-01, one order (not refunded)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="crs-b-1",
            order_number="#CRS-B-1",
            customer_id="CUST-B",
            order_created_at=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
            total_amount=50.0,
            currency="USD",
            is_refunded=False,
        )
    )

    # CUST-C, cohort 2026-03, two orders (first refunded, second not)
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="crs-c-1",
            order_number="#CRS-C-1",
            customer_id="CUST-C",
            order_created_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
            total_amount=90.0,
            currency="USD",
            refund_amount=90.0,
            is_refunded=True,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="crs-c-2",
            order_number="#CRS-C-2",
            customer_id="CUST-C",
            order_created_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
            total_amount=110.0,
            currency="USD",
            is_refunded=False,
        )
    )

    # Seed CohortRetentionSnapshots so repeat_purchase_rate_pct is available
    db.add(
        CohortRetentionSnapshot(
            tenant_id=tenant.id,
            cohort_month="2026-01",
            snapshot_date=date(2026, 5, 24),
            cohort_size=2,
            repeat_customer_count=1,
            repeat_purchase_rate_pct=50.0,
            days_since_cohort_start=144,
        )
    )
    db.add(
        CohortRetentionSnapshot(
            tenant_id=tenant.id,
            cohort_month="2026-03",
            snapshot_date=date(2026, 5, 24),
            cohort_size=1,
            repeat_customer_count=1,
            repeat_purchase_rate_pct=100.0,
            days_since_cohort_start=85,
        )
    )

    db.commit()
    db.close()

    result = run_cohort_return_signal_computation_job(
        session_factory=session_local, now=now
    )
    assert result == {"cohort_return_signal_count": 2}

    verify_db: Session = session_local()
    signals = {
        s.cohort_month: s
        for s in verify_db.query(CohortReturnSignal).all()
    }
    assert set(signals.keys()) == {"2026-01", "2026-03"}

    jan = signals["2026-01"]
    assert jan.cohort_size == 2
    assert jan.total_orders == 3
    assert jan.refunded_orders == 1
    assert abs(jan.return_rate_pct - (1 / 3 * 100.0)) < 0.01
    assert jan.repeat_purchase_rate_pct == 50.0

    mar = signals["2026-03"]
    assert mar.cohort_size == 1
    assert mar.total_orders == 2
    assert mar.refunded_orders == 1
    assert abs(mar.return_rate_pct - 50.0) < 0.01
    assert mar.repeat_purchase_rate_pct == 100.0

    audit_events = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "kpi.cohort_return_signal_computed"
    ).all()
    assert len(audit_events) == 1

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# T-047: Finance cost drivers and margin drift
# ---------------------------------------------------------------------------


def test_finance_cost_drift_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "finance-cost-drift-schedule" in beat_schedule
    entry = beat_schedule["finance-cost-drift-schedule"]
    assert entry["task"] == "worker.app.tasks.run_finance_cost_drift_schedule"
    assert entry["schedule"] == timedelta(hours=24)


def test_run_cost_driver_computation_job_no_revenue_skips_tenant() -> None:
    """Tenants with no orders in the period should produce 0 driver snapshots."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    tenant = Tenant(slug="t-cdr-no-rev", name="No Revenue Tenant", is_active=True)
    db.add(tenant)
    db.commit()
    db.close()

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    result = run_cost_driver_computation_job(session_factory=session_local, now=now)
    assert result == {"cost_driver_snapshot_count": 0}

    Base.metadata.drop_all(bind=engine)


def test_run_cost_driver_computation_job_computes_all_five_drivers() -> None:
    """Tenants with revenue produce 5 driver snapshots with correct amounts."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    connector_id = uuid.uuid4()

    tenant = Tenant(slug="t-cdr-ok", name="CDR Tenant", is_active=True)
    db.add(tenant)
    db.flush()

    # Shopify connector synced 1 hour ago → high confidence
    shopify_connector = ConnectorIntegration(
        id=connector_id,
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="active",
        last_synced_at=datetime(2026, 5, 25, 9, 0, tzinfo=UTC),
    )
    db.add(shopify_connector)

    # Meta connector synced 4 hours ago → still high confidence (< 24h)
    meta_connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="meta",
        auth_mode="api_key",
        status="active",
        last_synced_at=datetime(2026, 5, 25, 6, 0, tzinfo=UTC),
    )
    db.add(meta_connector)

    # Two orders in period: revenue=1000, shipping=50, discount=20, refund=30
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="cdr-ord-1",
            order_number="#CDR-1",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            total_amount=600.0,
            currency="USD",
            shipping_amount=30.0,
            discount_amount=20.0,
            refund_amount=0.0,
            is_refunded=False,
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="cdr-ord-2",
            order_number="#CDR-2",
            customer_id="CUST-B",
            order_created_at=datetime(2026, 5, 21, 10, 0, tzinfo=UTC),
            total_amount=400.0,
            currency="USD",
            shipping_amount=20.0,
            discount_amount=0.0,
            refund_amount=30.0,
            is_refunded=True,
        )
    )

    # Meta ad spend in period: $100
    db.add(
        MetaAdSpend(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_campaign_id="camp-1",
            campaign_name="Test Campaign",
            spend_date=date(2026, 5, 20),
            spend_amount=100.0,
            currency="USD",
        )
    )
    db.commit()
    db.close()

    result = run_cost_driver_computation_job(session_factory=session_local, now=now)
    assert result["cost_driver_snapshot_count"] == 5

    verify_db: Session = session_local()
    drivers = {
        d.driver_type: d
        for d in verify_db.query(CostDriverSnapshot).all()
    }
    expected_drivers = {"cogs", "shipping", "returns", "discounts", "ad_spend"}
    assert set(drivers.keys()) == expected_drivers

    # Revenue = 600 + 400 = 1000
    assert drivers["shipping"].revenue == 1000.0
    assert drivers["shipping"].absolute_amount == 50.0  # 30 + 20
    assert abs(drivers["shipping"].pct_of_revenue - 5.0) < 0.01
    assert drivers["shipping"].margin_impact_amount == -50.0
    assert drivers["shipping"].confidence_label == "high"

    assert drivers["returns"].absolute_amount == 30.0
    assert drivers["returns"].confidence_label == "high"

    assert drivers["discounts"].absolute_amount == 20.0

    assert drivers["ad_spend"].absolute_amount == 100.0
    assert drivers["ad_spend"].source_platform == "meta_google"
    assert drivers["ad_spend"].confidence_label == "high"

    assert drivers["cogs"].absolute_amount == 0.0
    assert drivers["cogs"].source == "manual"
    assert drivers["cogs"].source_platform == "manual_entry"

    audit_events = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "kpi.cost_driver_snapshot_computed"
    ).all()
    assert len(audit_events) == 1

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_margin_drift_no_prior_snapshot_sets_data_insufficient() -> None:
    """First-run drift snapshot: expected=None, drift=None, reason=data_insufficient."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    connector_id = uuid.uuid4()

    tenant = Tenant(slug="t-drift-first", name="Drift First", is_active=True)
    db.add(tenant)
    db.flush()

    db.add(
        ConnectorIntegration(
            id=connector_id,
            tenant_id=tenant.id,
            source="shopify",
            auth_mode="oauth",
            status="active",
            last_synced_at=datetime(2026, 5, 25, 9, 0, tzinfo=UTC),
        )
    )
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="drift-ord-1",
            order_number="#DRIFT-1",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            total_amount=1000.0,
            currency="USD",
            shipping_amount=20.0,
            discount_amount=10.0,
            refund_amount=0.0,
            is_refunded=False,
        )
    )
    db.commit()
    db.close()

    result = run_margin_drift_computation_job(session_factory=session_local, now=now)
    assert result["margin_drift_snapshot_count"] == 1

    verify_db: Session = session_local()
    snaps = verify_db.query(MarginDriftSnapshot).all()
    assert len(snaps) == 1
    s = snaps[0]
    assert s.channel == "blended"
    assert s.category == "all"
    assert s.expected_margin_pct is None
    assert s.drift_pct is None
    assert s.threshold_exceeded is False
    assert s.variance_reason == "data_insufficient"
    assert s.data_completeness == "partial_no_cogs"

    alerts = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "alert.margin_drift_threshold_exceeded"
    ).all()
    assert len(alerts) == 0

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_margin_drift_fires_alert_when_threshold_exceeded() -> None:
    """Fires alert AuditEvent when |drift_pct| >= threshold_pct."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    now = datetime(2026, 5, 25, 10, 0, tzinfo=UTC)
    connector_id = uuid.uuid4()

    tenant = Tenant(slug="t-drift-alert", name="Drift Alert", is_active=True)
    db.add(tenant)
    db.flush()

    db.add(
        ConnectorIntegration(
            id=connector_id,
            tenant_id=tenant.id,
            source="shopify",
            auth_mode="oauth",
            status="active",
            last_synced_at=datetime(2026, 5, 25, 9, 0, tzinfo=UTC),
        )
    )

    # Revenue=1000, costs: shipping=100, discount=100 → actual_margin=80%
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector_id,
            external_order_id="alert-ord-1",
            order_number="#ALERT-1",
            customer_id="CUST-A",
            order_created_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
            total_amount=1000.0,
            currency="USD",
            shipping_amount=100.0,
            discount_amount=100.0,
            refund_amount=0.0,
            is_refunded=False,
        )
    )

    # Prior drift snapshot: expected_margin=96% → drift=(80-96)/96*100≈-16.7% > 10%
    db.add(
        MarginDriftSnapshot(
            tenant_id=tenant.id,
            snapshot_date=date(2026, 5, 24),
            channel="blended",
            category="all",
            actual_margin_pct=96.0,
            expected_margin_pct=None,
            drift_pct=None,
            threshold_exceeded=False,
            variance_reason="data_insufficient",
            data_completeness="partial_no_cogs",
        )
    )

    # Threshold: alert when |drift| >= 10%
    db.add(
        MarginDriftThreshold(
            tenant_id=tenant.id,
            channel="blended",
            category="all",
            threshold_pct=10.0,
            is_active=True,
            effective_date=date(2026, 1, 1),
        )
    )
    db.commit()
    db.close()

    result = run_margin_drift_computation_job(session_factory=session_local, now=now)
    assert result["margin_drift_snapshot_count"] == 1

    verify_db: Session = session_local()
    snap = verify_db.query(MarginDriftSnapshot).filter(
        MarginDriftSnapshot.snapshot_date == date(2026, 5, 25)
    ).one()
    assert snap.threshold_exceeded is True
    assert abs(snap.actual_margin_pct - 80.0) < 0.01
    assert snap.expected_margin_pct == 96.0
    # drift = (80 - 96) / |96| * 100 = -16.666...%
    assert snap.drift_pct is not None
    assert abs(snap.drift_pct - (-16.666666)) < 0.01

    alerts = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "alert.margin_drift_threshold_exceeded"
    ).all()
    assert len(alerts) == 1

    verify_db.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# T-050: Inventory risk computations (FR-058 to FR-062)
# ---------------------------------------------------------------------------


def _make_inventory_engine() -> tuple[Engine, sessionmaker[Session]]:
    """Return (engine, session_local) with all tables created."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local: sessionmaker[Session] = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    Base.metadata.create_all(bind=engine)
    return engine, session_local


def test_inventory_risk_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "inventory-risk-schedule" in beat_schedule
    entry = beat_schedule["inventory-risk-schedule"]
    assert entry["task"] == "worker.app.tasks.run_inventory_risk_schedule"
    assert entry["schedule"] == timedelta(hours=24)


def test_run_inventory_risk_no_items_skips_tenant() -> None:
    """Tenant with no inventory items produces 0 snapshots."""
    engine, session_local = _make_inventory_engine()
    now = datetime(2026, 5, 25, 6, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="EmptyShop", slug="emptyshop", is_active=True)
    db.add(tenant)
    db.commit()
    db.close()

    result = run_inventory_risk_computation_job(session_factory=session_local, now=now)
    assert result["inventory_risk_snapshot_count"] == 0

    verify_db: Session = session_local()
    assert verify_db.query(InventoryRiskSnapshot).count() == 0
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_inventory_risk_low_stock_status() -> None:
    """SKU below reorder_point → low_stock."""
    engine, session_local = _make_inventory_engine()
    now = datetime(2026, 5, 25, 6, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="LowStockCo", slug="lowstockco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.flush()
    item = ShopifyInventoryItem(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_inventory_item_id="inv-lt-1",
        sku="SKU-LT-001",
        product_title="Low Stock Widget",
        available_quantity=3,
        reorder_point=10,
        cost_per_unit=5.0,
        synced_at=now,
    )
    db.add(item)
    # One recent order to avoid slow_moving path
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id="ord-lt-1",
            order_number="1001",
            total_amount=50.0,
            currency="USD",
            is_refunded=False,
            order_created_at=now - timedelta(days=1),
        )
    )
    db.commit()
    db.close()

    result = run_inventory_risk_computation_job(session_factory=session_local, now=now)
    assert result["inventory_risk_snapshot_count"] == 1

    verify_db: Session = session_local()
    snap = verify_db.query(InventoryRiskSnapshot).filter(
        InventoryRiskSnapshot.sku == "SKU-LT-001"
    ).one()
    assert snap.status == "low_stock"
    assert snap.current_quantity == 3
    assert snap.capital_at_risk == 15.0
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_inventory_risk_stockout_risk_status() -> None:
    """SKU where days_to_stockout <= stockout_alert_days → stockout_risk."""
    engine, session_local = _make_inventory_engine()
    now = datetime(2026, 5, 25, 6, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="StockoutCo", slug="stockoutco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.flush()
    # available_quantity=0 → days_to_stockout=0 regardless of velocity (0/v==0)
    # But we need velocity > 0 so days_to_stockout is computed (not None).
    # Seed one order + 15 line items selling SKU-SO-001 within last 30 days.
    item = ShopifyInventoryItem(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_inventory_item_id="inv-so-1",
        sku="SKU-SO-001",
        product_title="Stockout Widget",
        available_quantity=0,
        synced_at=now,
    )
    db.add(item)
    order = ShopifyOrder(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_order_id="ord-so-0",
        order_number="2000",
        total_amount=50.0,
        currency="USD",
        is_refunded=False,
        order_created_at=now - timedelta(days=1),
    )
    db.add(order)
    db.flush()
    # 15 line items → units_sold_30d=15 → confidence="high"
    for i in range(15):
        db.add(
            ShopifyOrderLineItem(
                tenant_id=tenant.id,
                order_id=order.id,
                line_item_index=i,
                sku="SKU-SO-001",
                product_title="Stockout Widget",
                quantity=1,
                unit_price=50.0,
                order_created_at=now - timedelta(days=1),
            )
        )
    db.commit()
    db.close()

    result = run_inventory_risk_computation_job(session_factory=session_local, now=now)
    assert result["inventory_risk_snapshot_count"] == 1

    verify_db: Session = session_local()
    snap = verify_db.query(InventoryRiskSnapshot).filter(
        InventoryRiskSnapshot.sku == "SKU-SO-001"
    ).one()
    assert snap.status == "stockout_risk"
    assert snap.days_to_stockout == 0.0
    assert snap.confidence == "high"
    assert snap.data_completeness == "computed"
    alerts = verify_db.query(AuditEvent).filter(
        AuditEvent.action == "alert.inventory_stockout_risk"
    ).all()
    assert len(alerts) == 1
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_inventory_risk_slow_moving_requires_all_four_conditions() -> None:
    """slow_moving only when all 4 conditions hold; qty=1 fails min_qty → in_stock."""
    engine, session_local = _make_inventory_engine()
    now = datetime(2026, 5, 25, 6, 0, tzinfo=UTC)

    db: Session = session_local()
    tenant = Tenant(name="SlowMoveCo", slug="slowmoveco", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.flush()
    # qty=1 fails slow_moving_min_qty (default=5) → expected in_stock
    item = ShopifyInventoryItem(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_inventory_item_id="inv-sm-1",
        sku="SKU-SM-001",
        product_title="Slow Widget",
        available_quantity=1,
        synced_at=now,
    )
    db.add(item)
    # Last order > 30 days ago — satisfies days_since_last_sale condition
    db.add(
        ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=connector.id,
            external_order_id="ord-sm-old",
            order_number="9001",
            total_amount=50.0,
            currency="USD",
            is_refunded=False,
            order_created_at=now - timedelta(days=40),
        )
    )
    db.commit()
    db.close()

    result = run_inventory_risk_computation_job(session_factory=session_local, now=now)
    assert result["inventory_risk_snapshot_count"] == 1

    verify_db: Session = session_local()
    snap = verify_db.query(InventoryRiskSnapshot).filter(
        InventoryRiskSnapshot.sku == "SKU-SM-001"
    ).one()
    # qty=1 fails slow_moving_min_qty=5 → must NOT be slow_moving
    assert snap.status != "slow_moving"
    verify_db.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# T-051 Operational Impact Computation Tests
# ---------------------------------------------------------------------------


def _make_operational_impact_engine() -> tuple[Engine, sessionmaker[Session]]:
    """Return (engine, session_local) with all tables created."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local: sessionmaker[Session] = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    Base.metadata.create_all(bind=engine)
    return engine, session_local


def test_operational_impact_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "operational-impact-schedule" in beat_schedule
    entry = beat_schedule["operational-impact-schedule"]
    assert entry["task"] == "worker.app.tasks.run_operational_impact_schedule"


def test_run_operational_impact_no_items_returns_zero() -> None:
    engine, session_local = _make_operational_impact_engine()
    db: Session = session_local()

    tenant = Tenant(name="OpImpact NoItems", slug="opimpact-noitems", is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    result = run_operational_impact_computation_job(
        session_factory=session_local
    )
    assert result["operational_impact_snapshot_count"] == 0
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_operational_impact_stockout_lost_revenue(
    monkeypatch: pytest.MonkeyPatch,  # noqa: ARG001
) -> None:
    now = datetime.now(tz=UTC)
    engine, session_local = _make_operational_impact_engine()
    db: Session = session_local()

    tenant = Tenant(name="OpImpact Stockout", slug="opimpact-stockout", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.flush()

    inv_item = ShopifyInventoryItem(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_inventory_item_id="inv-ops-001",
        sku="SKU-OPS-001",
        product_title="Ops Prod",
        available_quantity=0,
        synced_at=now,
    )
    db.add(inv_item)
    db.commit()

    risk_snap = InventoryRiskSnapshot(
        tenant_id=tenant.id,
        snapshot_date=now.date(),
        sku="SKU-OPS-001",
        product_title="Ops Prod",
        current_quantity=0,
        status="stockout_risk",
        daily_velocity_30d=2.0,
        days_to_stockout=0.0,
        weekly_velocity_90d=14.0,
        confidence="high",
        data_completeness="computed",
    )
    db.add(risk_snap)
    db.commit()

    order_time = now - timedelta(days=5)
    order = ShopifyOrder(
        tenant_id=tenant.id,
        connector_id=uuid.uuid4(),
        external_order_id="order-ops-001",
        order_number="#OPS-1001",
        currency="USD",
        total_amount=200.0,
        is_refunded=False,
        order_created_at=order_time,
        synced_at=order_time,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for i in range(2):
        li = ShopifyOrderLineItem(
            tenant_id=tenant.id,
            order_id=order.id,
            line_item_index=i,
            sku="SKU-OPS-001",
            product_title="Ops Prod",
            quantity=1,
            unit_price=100.0,
            order_created_at=order_time,
        )
        db.add(li)
    db.commit()

    monkeypatch.setattr("worker.app.tasks.SessionLocal", session_local)
    result = run_operational_impact_computation_job(
        session_factory=session_local, now=now
    )
    assert result["operational_impact_snapshot_count"] == 1

    snap = db.query(OperationalImpactSnapshot).filter(
        OperationalImpactSnapshot.sku == "SKU-OPS-001"
    ).one()
    # daily_velocity=2.0 × 7 days × avg_price=100.0 = 1400.0
    assert snap.stockout_lost_revenue_estimate == pytest.approx(1400.0, rel=0.01)
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_operational_impact_return_rate(
    monkeypatch: pytest.MonkeyPatch,  # noqa: ARG001
) -> None:
    now = datetime.now(tz=UTC)
    engine, session_local = _make_operational_impact_engine()
    db: Session = session_local()

    tenant = Tenant(name="OpImpact Returns", slug="opimpact-returns", is_active=True)
    db.add(tenant)
    db.flush()
    connector = ConnectorIntegration(
        tenant_id=tenant.id,
        source="shopify",
        auth_mode="oauth",
        status="connected",
    )
    db.add(connector)
    db.flush()

    inv_item = ShopifyInventoryItem(
        tenant_id=tenant.id,
        connector_id=connector.id,
        external_inventory_item_id="inv-ret-001",
        sku="SKU-RET-001",
        product_title="Ret Prod",
        available_quantity=50,
        synced_at=now,
    )
    db.add(inv_item)
    db.commit()

    risk_snap = InventoryRiskSnapshot(
        tenant_id=tenant.id,
        snapshot_date=now.date(),
        sku="SKU-RET-001",
        product_title="Ret Prod",
        current_quantity=50,
        status="healthy",
        daily_velocity_30d=1.0,
        days_to_stockout=50.0,
        weekly_velocity_90d=7.0,
        confidence="high",
        data_completeness="computed",
    )
    db.add(risk_snap)
    db.commit()

    base_time = datetime.now(tz=UTC) - timedelta(days=10)

    # 4 normal orders (1 unit each)
    for i in range(4):
        order = ShopifyOrder(
            tenant_id=tenant.id,
            connector_id=uuid.uuid4(),
            external_order_id=f"order-norm-{i}",
            order_number=f"#RET-{i:04d}",
            currency="USD",
            total_amount=50.0,
            is_refunded=False,
            order_created_at=base_time,
            synced_at=base_time,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        db.add(ShopifyOrderLineItem(
            tenant_id=tenant.id,
            order_id=order.id,
            line_item_index=0,
            sku="SKU-RET-001",
            product_title="Ret Prod",
            quantity=1,
            unit_price=50.0,
            order_created_at=base_time,
        ))
    db.commit()

    # 1 refunded order (1 unit)
    refund_order = ShopifyOrder(
        tenant_id=tenant.id,
        connector_id=uuid.uuid4(),
        external_order_id="order-refund-0",
        order_number="#RET-9999",
        currency="USD",
        total_amount=50.0,
        is_refunded=True,
        order_created_at=base_time,
        synced_at=base_time,
    )
    db.add(refund_order)
    db.commit()
    db.refresh(refund_order)
    db.add(ShopifyOrderLineItem(
        tenant_id=tenant.id,
        order_id=refund_order.id,
        line_item_index=0,
        sku="SKU-RET-001",
        product_title="Ret Prod",
        quantity=1,
        unit_price=50.0,
        order_created_at=base_time,
    ))
    db.commit()

    monkeypatch.setattr("worker.app.tasks.SessionLocal", session_local)
    result = run_operational_impact_computation_job(
        session_factory=session_local, now=now
    )
    assert result["operational_impact_snapshot_count"] == 1

    snap = db.query(OperationalImpactSnapshot).filter(
        OperationalImpactSnapshot.sku == "SKU-RET-001"
    ).one()
    # 1 returned out of 5 total = 20%
    assert snap.return_rate_30d_pct == pytest.approx(20.0, rel=0.01)
    db.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# T-053 Rule Engine core tests
# ---------------------------------------------------------------------------


def _make_rule_engine_engine() -> tuple[Engine, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return engine, session_local


def _always_true(ri: RuleInput) -> bool:
    return True


def _always_false(ri: RuleInput) -> bool:
    return False


def _make_dummy_rule(
    rule_id: str = "TEST-001",
    condition: object = _always_true,
    priority: int = 10,
) -> Rule:
    def build_result(ri: RuleInput) -> RuleResult:
        return RuleResult(
            rule_id=rule_id,
            domain="inventory",
            affected_area="All SKUs",
            signal_summary="test signal",
            suggested_action="test action",
            estimated_impact=100.0,
            confidence_level="high",
            data_freshness_context="fresh",
            priority=priority,
        )

    return Rule(
        rule_id=rule_id,
        domain="inventory",
        description="test rule",
        condition=condition,  # type: ignore[arg-type]
        build_result=build_result,
        priority=priority,
    )


def _make_rule_input() -> RuleInput:
    from datetime import date

    return RuleInput(tenant_id="test-tenant", snapshot_date=date.today())


def test_rule_engine_no_rules_returns_empty() -> None:
    engine = RuleEngine([])
    assert engine.evaluate(_make_rule_input()) == []


def test_rule_engine_condition_false_returns_empty() -> None:
    rule = _make_dummy_rule(condition=_always_false)
    engine = RuleEngine([rule])
    assert engine.evaluate(_make_rule_input()) == []


def test_rule_engine_condition_true_returns_result() -> None:
    rule = _make_dummy_rule()
    engine = RuleEngine([rule])
    results = engine.evaluate(_make_rule_input())
    assert len(results) == 1
    assert results[0].rule_id == "TEST-001"
    assert results[0].domain == "inventory"
    assert results[0].estimated_impact == 100.0


def test_rule_engine_deterministic() -> None:
    """Same input evaluated twice must produce identical results."""
    rule = _make_dummy_rule()
    engine = RuleEngine([rule])
    ri = _make_rule_input()
    assert engine.evaluate(ri) == engine.evaluate(ri)


def test_rule_engine_priority_order() -> None:
    """Lower priority number must appear first in results."""
    rule_hi = _make_dummy_rule(rule_id="RULE-HIGH", priority=5)
    rule_lo = _make_dummy_rule(rule_id="RULE-LOW", priority=20)
    engine = RuleEngine([rule_lo, rule_hi])  # intentionally reversed input
    results = engine.evaluate(_make_rule_input())
    assert results[0].rule_id == "RULE-HIGH"
    assert results[1].rule_id == "RULE-LOW"


def test_rule_engine_schedule_is_configured() -> None:
    beat_schedule = celery_app.conf.beat_schedule
    assert "rule-engine-schedule" in beat_schedule
    entry = beat_schedule["rule-engine-schedule"]
    assert entry["task"] == "worker.app.tasks.run_rule_engine_schedule"


def test_run_rule_engine_job_no_tenants_returns_zero() -> None:
    engine, session_local = _make_rule_engine_engine()
    result = run_rule_engine_job(session_factory=session_local, rules=[])
    assert result["tenants_processed"] == 0
    assert result["recommendations_created"] == 0
    Base.metadata.drop_all(bind=engine)


def test_run_rule_engine_job_no_rules_produces_no_recommendations() -> None:
    engine, session_local = _make_rule_engine_engine()
    db: Session = session_local()
    tenant = Tenant(name="Rule Engine Co", slug="rule-engine-co", is_active=True)
    db.add(tenant)
    db.commit()
    result = run_rule_engine_job(session_factory=session_local, rules=[])
    assert result["tenants_processed"] == 1
    assert result["recommendations_created"] == 0
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_run_rule_engine_job_creates_recommendation() -> None:
    engine, session_local = _make_rule_engine_engine()
    db: Session = session_local()
    tenant = Tenant(name="Rule Fires Co", slug="rule-fires-co", is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    result = run_rule_engine_job(
        session_factory=session_local, rules=[_make_dummy_rule()]
    )
    assert result["tenants_processed"] == 1
    assert result["recommendations_created"] == 1

    from backend.app.db.models import Recommendation as RecModel

    db2: Session = session_local()
    recs = db2.scalars(
        select(RecModel).where(RecModel.tenant_id == tenant.id)
    ).all()
    assert len(recs) == 1
    assert recs[0].rule_id == "TEST-001"
    assert recs[0].status == "new"
    db.close()
    db2.close()
    Base.metadata.drop_all(bind=engine)


def test_run_rule_engine_job_no_duplicate_recommendations() -> None:
    """Running the job twice on the same day must not create duplicates."""
    engine, session_local = _make_rule_engine_engine()
    db: Session = session_local()
    tenant = Tenant(name="No Dup Co", slug="no-dup-co", is_active=True)
    db.add(tenant)
    db.commit()

    run_rule_engine_job(session_factory=session_local, rules=[_make_dummy_rule()])
    run_rule_engine_job(session_factory=session_local, rules=[_make_dummy_rule()])

    from backend.app.db.models import Recommendation as RecModel

    db2: Session = session_local()
    count = len(
        db2.scalars(select(RecModel).where(RecModel.tenant_id == tenant.id)).all()
    )
    assert count == 1
    db.close()
    db2.close()
    Base.metadata.drop_all(bind=engine)


# ===========================================================================
# T-054: Rule pack v1 tests
# ===========================================================================

from worker.app.rules.pack import get_rules  # noqa: E402


def _ri(**kwargs: object) -> RuleInput:
    """Build a minimal RuleInput; caller overrides only what the test needs."""
    return RuleInput(
        tenant_id="test-tenant",
        snapshot_date=date.today(),
        **kwargs,  # type: ignore[arg-type]
    )


# --- get_rules() contract ---

def test_get_rules_returns_six_rules() -> None:
    rules = get_rules()
    assert len(rules) == 6
    ids = {r.rule_id for r in rules}
    assert ids == {"ACQ-001", "EXC-001", "INV-001", "MRG-001", "OPS-001", "RET-001"}


def test_get_rules_sorted_by_priority() -> None:
    rules = get_rules()
    priorities = [r.priority for r in rules]
    assert priorities == sorted(priorities)


# --- EXC-001 ---

def test_exc_001_fires_when_margin_below_floor() -> None:
    ri = _ri(contribution_margin_pct=25.0, thresholds={"EXC-001": 30.0})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["EXC-001"].condition(ri) is True


def test_exc_001_silent_when_margin_above_floor() -> None:
    ri = _ri(contribution_margin_pct=35.0, thresholds={"EXC-001": 30.0})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["EXC-001"].condition(ri) is False


def test_exc_001_silent_when_margin_none() -> None:
    ri = _ri(contribution_margin_pct=None)
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["EXC-001"].condition(ri) is False


def test_exc_001_result_contains_gap() -> None:
    ri = _ri(contribution_margin_pct=25.0, thresholds={"EXC-001": 30.0})
    rules = {r.rule_id: r for r in get_rules()}
    result = rules["EXC-001"].build_result(ri)
    assert result.rule_id == "EXC-001"
    assert result.domain == "executive"
    assert "5.0pp" in result.signal_summary


# --- INV-001 ---

def test_inv_001_fires_when_sku_at_risk() -> None:
    ri = _ri(
        inventory_risk_rows=[
            {"sku": "SKU-A", "status": "stockout_risk", "capital_at_risk": 1000.0}
        ],
        thresholds={"INV-001": 1.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["INV-001"].condition(ri) is True


def test_inv_001_silent_when_no_risk() -> None:
    ri = _ri(
        inventory_risk_rows=[
            {"sku": "SKU-A", "status": "healthy", "capital_at_risk": None}
        ],
        thresholds={"INV-001": 1.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["INV-001"].condition(ri) is False


def test_inv_001_respects_count_threshold() -> None:
    """Only fires when at-risk count meets the threshold (2), not at 1."""
    rows = [
        {"sku": "SKU-A", "status": "stockout_risk", "capital_at_risk": 100.0},
    ]
    ri_under = _ri(inventory_risk_rows=rows, thresholds={"INV-001": 2.0})
    ri_at = _ri(
        inventory_risk_rows=rows
        + [{"sku": "SKU-B", "status": "critical_low", "capital_at_risk": 200.0}],
        thresholds={"INV-001": 2.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["INV-001"].condition(ri_under) is False
    assert rules["INV-001"].condition(ri_at) is True


def test_inv_001_result_includes_capital() -> None:
    ri = _ri(
        inventory_risk_rows=[
            {"sku": "SKU-A", "status": "stockout_risk", "capital_at_risk": 1500.0}
        ],
        thresholds={"INV-001": 1.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    result = rules["INV-001"].build_result(ri)
    assert result.estimated_impact == 1500.0


# --- OPS-001 ---

def test_ops_001_fires_when_revenue_at_risk() -> None:
    ri = _ri(
        operational_impact_rows=[
            {"sku": "SKU-B", "stockout_lost_revenue_estimate": 1000.0}
        ],
        thresholds={"OPS-001": 500.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["OPS-001"].condition(ri) is True


def test_ops_001_silent_when_below_threshold() -> None:
    ri = _ri(
        operational_impact_rows=[
            {"sku": "SKU-B", "stockout_lost_revenue_estimate": 100.0}
        ],
        thresholds={"OPS-001": 500.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["OPS-001"].condition(ri) is False


def test_ops_001_silent_when_estimate_none() -> None:
    ri = _ri(
        operational_impact_rows=[
            {"sku": "SKU-B", "stockout_lost_revenue_estimate": None}
        ],
        thresholds={"OPS-001": 500.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["OPS-001"].condition(ri) is False


# --- ACQ-001 ---

def test_acq_001_fires_when_roas_below_floor() -> None:
    ri = _ri(blended_roas=1.2, thresholds={"ACQ-001": 1.5})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["ACQ-001"].condition(ri) is True


def test_acq_001_silent_when_roas_above_floor() -> None:
    ri = _ri(blended_roas=2.0, thresholds={"ACQ-001": 1.5})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["ACQ-001"].condition(ri) is False


def test_acq_001_silent_when_roas_none() -> None:
    ri = _ri(blended_roas=None)
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["ACQ-001"].condition(ri) is False


def test_acq_001_result_contains_gap() -> None:
    ri = _ri(blended_roas=1.0, thresholds={"ACQ-001": 1.5})
    rules = {r.rule_id: r for r in get_rules()}
    result = rules["ACQ-001"].build_result(ri)
    assert result.rule_id == "ACQ-001"
    assert "0.50" in result.signal_summary


# --- RET-001 ---

def test_ret_001_fires_when_rate_below_floor() -> None:
    ri = _ri(repeat_purchase_rate_pct=15.0, thresholds={"RET-001": 20.0})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["RET-001"].condition(ri) is True


def test_ret_001_silent_when_rate_above_floor() -> None:
    ri = _ri(repeat_purchase_rate_pct=25.0, thresholds={"RET-001": 20.0})
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["RET-001"].condition(ri) is False


def test_ret_001_silent_when_rate_none() -> None:
    ri = _ri(repeat_purchase_rate_pct=None)
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["RET-001"].condition(ri) is False


# --- MRG-001 ---

def test_mrg_001_fires_when_threshold_exceeded() -> None:
    ri = _ri(
        margin_drift_rows=[
            {"channel": "meta", "category": "footwear", "threshold_exceeded": True}
        ],
        thresholds={"MRG-001": 1.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["MRG-001"].condition(ri) is True


def test_mrg_001_silent_when_no_breach() -> None:
    ri = _ri(
        margin_drift_rows=[
            {"channel": "meta", "category": "footwear", "threshold_exceeded": False}
        ],
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["MRG-001"].condition(ri) is False


def test_mrg_001_respects_count_threshold() -> None:
    rows = [{"channel": "meta", "category": "footwear", "threshold_exceeded": True}]
    ri_under = _ri(margin_drift_rows=rows, thresholds={"MRG-001": 2.0})
    ri_at = _ri(
        margin_drift_rows=rows
        + [{"channel": "google", "category": "boots", "threshold_exceeded": True}],
        thresholds={"MRG-001": 2.0},
    )
    rules = {r.rule_id: r for r in get_rules()}
    assert rules["MRG-001"].condition(ri_under) is False
    assert rules["MRG-001"].condition(ri_at) is True


# --- Fallback defaults (no thresholds dict set) ---

def test_rules_use_fallback_defaults_when_thresholds_empty() -> None:
    """Rules must not crash and must use built-in defaults when thresholds={}."""
    rules = {r.rule_id: r for r in get_rules()}
    # ACQ-001 default floor = 1.5; ROAS 1.0 should fire
    assert rules["ACQ-001"].condition(_ri(blended_roas=1.0)) is True
    # EXC-001 default floor = 30.0; margin 25 should fire
    assert rules["EXC-001"].condition(_ri(contribution_margin_pct=25.0)) is True
    # RET-001 default floor = 20.0; rate 10 should fire
    assert rules["RET-001"].condition(_ri(repeat_purchase_rate_pct=10.0)) is True


# ===========================================================================
# T-054b: Suggested threshold engine tests
# ===========================================================================


def _make_suggestion_test_db() -> tuple[Engine, sessionmaker]:
    """Create an isolated in-memory SQLite DB for threshold suggestion tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine)


def _seed_tenant_for_suggestion(session: Session) -> Tenant:
    """Create a tenant with the 6 default TenantRuleThreshold rows."""
    tenant = Tenant(name="Sug Co", slug="sugco", is_active=True)
    session.add(tenant)
    session.flush()
    for rule_id, value, unit in [
        ("ACQ-001", 1.5, "ratio"),
        ("EXC-001", 30.0, "pct"),
        ("INV-001", 1.0, "count"),
        ("MRG-001", 1.0, "count"),
        ("OPS-001", 500.0, "USD"),
        ("RET-001", 20.0, "pct"),
    ]:
        session.add(
            TenantRuleThreshold(
                tenant_id=tenant.id,
                rule_id=rule_id,
                threshold_value=value,
                threshold_unit=unit,
                description=f"Default {rule_id}",
            )
        )
    session.commit()
    return tenant


def test_threshold_suggestion_job_no_tenants_returns_zero() -> None:
    """Empty DB — job must return 0 for both counters."""
    engine, factory = _make_suggestion_test_db()
    try:
        result = run_threshold_suggestion_job(session_factory=factory)
        assert result["tenants_processed"] == 0
        assert result["thresholds_updated"] == 0
    finally:
        Base.metadata.drop_all(bind=engine)


def test_threshold_suggestion_job_skips_with_insufficient_data() -> None:
    """Fewer than 7 exec snapshots — no suggestion should be written."""
    engine, factory = _make_suggestion_test_db()
    try:
        db = factory()
        tenant = _seed_tenant_for_suggestion(db)
        today = date.today()
        for i in range(3):
            db.add(
                ExecutiveKpiSnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=today - timedelta(days=i),
                    period_start_date=today - timedelta(days=30 + i),
                    period_end_date=today - timedelta(days=i),
                    blended_roas=2.0,
                    contribution_margin_pct=35.0,
                )
            )
        db.commit()
        tenant_id = tenant.id  # capture before session closes
        db.close()

        result = run_threshold_suggestion_job(session_factory=factory)
        assert result["thresholds_updated"] == 0

        db2 = factory()
        row = db2.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant_id,
                TenantRuleThreshold.rule_id == "ACQ-001",
            )
        )
        assert row is not None
        assert row.suggested_value is None
        db2.close()
    finally:
        Base.metadata.drop_all(bind=engine)


def test_threshold_suggestion_job_updates_acq001() -> None:
    """10 exec snapshots with non-zero ROAS — ACQ-001 suggestion = mean × 0.75."""
    import statistics as _stats

    engine, factory = _make_suggestion_test_db()
    try:
        db = factory()
        tenant = _seed_tenant_for_suggestion(db)
        today = date.today()
        roas_list = [2.0, 2.2, 1.8, 2.4, 2.1, 1.9, 2.3, 2.0, 2.5, 1.7]
        for i, roas in enumerate(roas_list):
            db.add(
                ExecutiveKpiSnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=today - timedelta(days=i),
                    period_start_date=today - timedelta(days=30 + i),
                    period_end_date=today - timedelta(days=i),
                    blended_roas=roas,
                    contribution_margin_pct=0.0,
                )
            )
        db.commit()
        tenant_id = tenant.id  # capture before session closes
        db.close()

        run_threshold_suggestion_job(session_factory=factory)

        expected = round(_stats.mean(roas_list) * 0.75, 2)
        db2 = factory()
        row = db2.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant_id,
                TenantRuleThreshold.rule_id == "ACQ-001",
            )
        )
        assert row is not None
        assert row.suggested_value == pytest.approx(expected, rel=1e-5)
        # is_customised=False by default so threshold_value must also be updated
        assert row.threshold_value == pytest.approx(expected, rel=1e-5)
        db2.close()
    finally:
        Base.metadata.drop_all(bind=engine)


def test_threshold_suggestion_job_respects_is_customised() -> None:
    """When is_customised=True, threshold_value must NOT be overwritten."""
    engine, factory = _make_suggestion_test_db()
    try:
        db = factory()
        tenant = _seed_tenant_for_suggestion(db)
        # Manually override ACQ-001 threshold and mark as customised
        row = db.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant.id,
                TenantRuleThreshold.rule_id == "ACQ-001",
            )
        )
        assert row is not None
        row.threshold_value = 3.0
        row.is_customised = True
        today = date.today()
        for i in range(10):
            db.add(
                ExecutiveKpiSnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=today - timedelta(days=i),
                    period_start_date=today - timedelta(days=30 + i),
                    period_end_date=today - timedelta(days=i),
                    blended_roas=2.0,
                    contribution_margin_pct=0.0,
                )
            )
        db.commit()
        tenant_id = tenant.id  # capture before session closes
        db.close()

        run_threshold_suggestion_job(session_factory=factory)

        db2 = factory()
        row2 = db2.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant_id,
                TenantRuleThreshold.rule_id == "ACQ-001",
            )
        )
        assert row2 is not None
        assert row2.threshold_value == pytest.approx(3.0)  # manual value preserved
        assert row2.suggested_value is not None  # but suggestion is still written
        db2.close()
    finally:
        Base.metadata.drop_all(bind=engine)


def test_threshold_suggestion_job_updates_ret001() -> None:
    """10 RetentionDailySnapshot rows — RET-001 suggestion = mean × 0.85."""
    import statistics as _stats

    engine, factory = _make_suggestion_test_db()
    try:
        db = factory()
        tenant = _seed_tenant_for_suggestion(db)
        today = date.today()
        rate_list = [22.0, 24.0, 21.0, 23.5, 25.0, 20.5, 26.0, 22.5, 24.5, 21.5]
        for i, rate in enumerate(rate_list):
            db.add(
                RetentionDailySnapshot(
                    tenant_id=tenant.id,
                    snapshot_date=today - timedelta(days=i),
                    repeat_purchase_rate_pct=rate,
                )
            )
        db.commit()
        tenant_id = tenant.id  # capture before session closes
        db.close()

        run_threshold_suggestion_job(session_factory=factory)

        expected = round(_stats.mean(rate_list) * 0.85, 1)
        db2 = factory()
        row = db2.scalar(
            select(TenantRuleThreshold).where(
                TenantRuleThreshold.tenant_id == tenant_id,
                TenantRuleThreshold.rule_id == "RET-001",
            )
        )
        assert row is not None
        assert row.suggested_value == pytest.approx(expected, rel=1e-5)
        db2.close()
    finally:
        Base.metadata.drop_all(bind=engine)


def test_threshold_suggestion_schedule_is_configured() -> None:
    """threshold-suggestion-schedule must be present in the Celery beat schedule."""
    assert "threshold-suggestion-schedule" in celery_app.conf.beat_schedule
    entry = celery_app.conf.beat_schedule["threshold-suggestion-schedule"]
    assert entry["task"] == "worker.app.tasks.run_threshold_suggestion_schedule"


# ===========================================================================
# T-055: Impact scoring for recommendation ranking
# ===========================================================================

from worker.app.rules.scorer import compute_impact_score  # noqa: E402


def _ri_for_scorer(**kwargs: object) -> RuleInput:
    """Minimal RuleInput for scorer unit tests."""
    return RuleInput(
        tenant_id="scorer-tenant",
        snapshot_date=date.today(),
        **kwargs,  # type: ignore[arg-type]
    )


def test_impact_scorer_exc001_severity() -> None:
    """EXC-001: cm=24, floor=30 → severity=0.2, weight=10.0, score=200.0."""
    ri = _ri_for_scorer(
        contribution_margin_pct=24.0,
        thresholds={"EXC-001": 30.0},
    )
    score = compute_impact_score("EXC-001", ri)
    assert score == pytest.approx(200.0, rel=1e-3)


def test_impact_scorer_acq001_severity() -> None:
    """ACQ-001: roas=1.0, floor=1.5 → severity=0.3333, weight=5.0, score=166.67."""
    ri = _ri_for_scorer(
        blended_roas=1.0,
        thresholds={"ACQ-001": 1.5},
    )
    score = compute_impact_score("ACQ-001", ri)
    assert score == pytest.approx(5.0 * (0.5 / 1.5) * 100.0, rel=1e-3)


def test_impact_scorer_ret001_severity() -> None:
    """RET-001: rpr=15, floor=20 → severity=0.25, weight=4.55, score=113.75."""
    ri = _ri_for_scorer(
        repeat_purchase_rate_pct=15.0,
        thresholds={"RET-001": 20.0},
    )
    score = compute_impact_score("RET-001", ri)
    assert score == pytest.approx(4.55 * 0.25 * 100.0, rel=1e-3)


def test_impact_scorer_inv001_count_multiple() -> None:
    """INV-001: 3 at-risk SKUs, threshold=1 → severity=3.0, weight=6.67, score=2001.0."""
    ri = _ri_for_scorer(
        inventory_risk_rows=[
            {"sku": "A", "status": "stockout_risk"},
            {"sku": "B", "status": "critical_low"},
            {"sku": "C", "status": "out_of_stock"},
        ],
        thresholds={"INV-001": 1.0},
    )
    score = compute_impact_score("INV-001", ri)
    assert score == pytest.approx(6.67 * 3.0 * 100.0, rel=1e-3)


def test_impact_scorer_ops001_monetary_multiple() -> None:
    """OPS-001: total=2500, threshold=500 → severity=5.0, weight=5.56, score=2780.0."""
    ri = _ri_for_scorer(
        operational_impact_rows=[
            {"sku": "X", "stockout_lost_revenue_estimate": 2500.0},
        ],
        thresholds={"OPS-001": 500.0},
    )
    score = compute_impact_score("OPS-001", ri)
    assert score == pytest.approx(5.56 * 5.0 * 100.0, rel=1e-3)


def test_impact_scorer_mrg001_breach_multiple() -> None:
    """MRG-001: 2 breaches, threshold=1 → severity=2.0, weight=4.0, score=800.0."""
    ri = _ri_for_scorer(
        margin_drift_rows=[
            {"channel": "google", "threshold_exceeded": True},
            {"channel": "meta", "threshold_exceeded": True},
        ],
        thresholds={"MRG-001": 1.0},
    )
    score = compute_impact_score("MRG-001", ri)
    assert score == pytest.approx(4.0 * 2.0 * 100.0, rel=1e-3)


def test_impact_scorer_severity_capped_at_max() -> None:
    """100 at-risk SKUs, threshold=1 → severity capped at 10.0."""
    ri = _ri_for_scorer(
        inventory_risk_rows=[
            {"sku": f"SKU-{i}", "status": "stockout_risk"} for i in range(100)
        ],
        thresholds={"INV-001": 1.0},
    )
    score = compute_impact_score("INV-001", ri)
    # capped at 10.0, weight=6.67, score=6670.0
    assert score == pytest.approx(6.67 * 10.0 * 100.0, rel=1e-3)


def test_impact_scorer_unknown_rule_returns_zero() -> None:
    """An unrecognised rule_id must return 0.0, never raise."""
    ri = _ri_for_scorer()
    assert compute_impact_score("UNKNOWN-999", ri) == 0.0


def test_rule_engine_evaluate_sets_impact_score() -> None:
    """RuleEngine.evaluate() must populate impact_score > 0 on fired results."""
    rules = get_rules()
    engine = RuleEngine(rules)
    ri = RuleInput(
        tenant_id="t1",
        snapshot_date=date.today(),
        contribution_margin_pct=10.0,  # triggers EXC-001 (floor 30.0)
        thresholds={"EXC-001": 30.0},
    )
    results = engine.evaluate(ri)
    exc_results = [r for r in results if r.rule_id == "EXC-001"]
    assert len(exc_results) == 1
    assert exc_results[0].impact_score > 0.0


def test_rule_engine_evaluate_impact_score_zero_for_unknown_rule() -> None:
    """A custom rule with an unknown rule_id gets impact_score=0.0 (no crash)."""
    rule = _make_dummy_rule(rule_id="CUSTOM-XYZ")
    engine = RuleEngine([rule])
    results = engine.evaluate(_make_rule_input())
    assert len(results) == 1
    assert results[0].impact_score == 0.0


def test_rule_engine_job_writes_impact_score_to_db() -> None:
    """run_rule_engine_job must persist impact_score on created Recommendation rows."""
    from backend.app.db.models import Recommendation as RecModel

    db_engine, session_local = _make_rule_engine_engine()
    try:
        db: Session = session_local()
        tenant = Tenant(name="Impact Score Co", slug="impact-score-co", is_active=True)
        db.add(tenant)
        db.commit()
        tenant_id = tenant.id
        db.close()

        # Use a real rule that will fire (EXC-001 via get_rules)
        from worker.app.rules.pack import get_rules as _get_rules

        rules = _get_rules()

        # Seed an ExecutiveKpiSnapshot so _build_rule_input finds metrics
        db2: Session = session_local()
        today = date.today()
        db2.add(
            ExecutiveKpiSnapshot(
                tenant_id=tenant_id,
                snapshot_date=today,
                period_start_date=today,
                period_end_date=today,
                blended_roas=0.5,           # triggers ACQ-001 (floor 1.5)
                contribution_margin_pct=5.0, # triggers EXC-001 (floor 30.0)
            )
        )
        db2.commit()
        db2.close()

        run_rule_engine_job(session_factory=session_local, rules=rules)

        db3: Session = session_local()
        recs = db3.scalars(
            select(RecModel).where(RecModel.tenant_id == tenant_id)
        ).all()
        assert len(recs) >= 1
        for rec in recs:
            assert rec.impact_score >= 0.0, (
                f"impact_score must be non-negative; got {rec.impact_score} for {rec.rule_id}"
            )
        # At least one recommendation must have a non-zero score
        assert any(rec.impact_score > 0.0 for rec in recs)
        db3.close()
    finally:
        Base.metadata.drop_all(bind=db_engine)


# ===========================================================================
# T-056: Recommendation confidence model
# ===========================================================================

from worker.app.rules.confidence import compute_confidence_level  # noqa: E402


def _ri_conf(**kwargs: object) -> RuleInput:
    """Minimal RuleInput for confidence unit tests."""
    return RuleInput(
        tenant_id="conf-tenant",
        snapshot_date=date.today(),
        **kwargs,  # type: ignore[arg-type]
    )


# --- Base confidence (fresh data, no row-level overrides) ---


def test_confidence_exc001_fresh_is_high() -> None:
    assert compute_confidence_level("EXC-001", _ri_conf()) == "high"


def test_confidence_acq001_fresh_is_high() -> None:
    assert compute_confidence_level("ACQ-001", _ri_conf()) == "high"


def test_confidence_ret001_fresh_is_high() -> None:
    assert compute_confidence_level("RET-001", _ri_conf()) == "high"


def test_confidence_inv001_fresh_is_medium() -> None:
    assert compute_confidence_level("INV-001", _ri_conf()) == "medium"


def test_confidence_ops001_fresh_is_medium() -> None:
    assert compute_confidence_level("OPS-001", _ri_conf()) == "medium"


def test_confidence_mrg001_fresh_is_low() -> None:
    assert compute_confidence_level("MRG-001", _ri_conf()) == "low"


def test_confidence_unknown_rule_defaults_to_medium() -> None:
    assert compute_confidence_level("UNKNOWN-XYZ", _ri_conf()) == "medium"


# --- Staleness cap ---


def test_confidence_staleness_3_days_caps_high_at_medium() -> None:
    """3 days stale: EXC-001 base=high is capped to medium."""
    ri = _ri_conf(data_freshness_days=3)
    assert compute_confidence_level("EXC-001", ri) == "medium"


def test_confidence_staleness_6_days_caps_high_at_medium() -> None:
    ri = _ri_conf(data_freshness_days=6)
    assert compute_confidence_level("EXC-001", ri) == "medium"


def test_confidence_staleness_7_days_caps_to_low() -> None:
    """7+ days stale: anything → low."""
    ri = _ri_conf(data_freshness_days=7)
    assert compute_confidence_level("EXC-001", ri) == "low"


def test_confidence_staleness_10_days_caps_to_low() -> None:
    ri = _ri_conf(data_freshness_days=10)
    assert compute_confidence_level("ACQ-001", ri) == "low"


def test_confidence_staleness_2_days_no_cap() -> None:
    """2 days stale: EXC-001 base=high is unchanged."""
    ri = _ri_conf(data_freshness_days=2)
    assert compute_confidence_level("EXC-001", ri) == "high"


# --- Row-level source confidence (INV-001) ---


def test_confidence_inv001_majority_low_rows_downgrades_to_low() -> None:
    """INV-001 with 2/3 flagged rows reporting 'low' → medium downgraded to low."""
    ri = _ri_conf(
        inventory_risk_rows=[
            {"sku": "A", "status": "stockout_risk", "confidence": "low"},
            {"sku": "B", "status": "stockout_risk", "confidence": "low"},
            {"sku": "C", "status": "stockout_risk", "confidence": "medium"},
        ]
    )
    assert compute_confidence_level("INV-001", ri) == "low"


def test_confidence_inv001_minority_low_rows_stays_medium() -> None:
    """INV-001 with 1/3 rows 'low' — not a majority → stays medium."""
    ri = _ri_conf(
        inventory_risk_rows=[
            {"sku": "A", "status": "stockout_risk", "confidence": "low"},
            {"sku": "B", "status": "stockout_risk", "confidence": "high"},
            {"sku": "C", "status": "stockout_risk", "confidence": "medium"},
        ]
    )
    assert compute_confidence_level("INV-001", ri) == "medium"


def test_confidence_inv001_ignores_non_risk_rows() -> None:
    """Rows that are not at-risk status are ignored in majority calculation."""
    ri = _ri_conf(
        inventory_risk_rows=[
            {"sku": "A", "status": "healthy", "confidence": "low"},
            {"sku": "B", "status": "healthy", "confidence": "low"},
            {"sku": "C", "status": "stockout_risk", "confidence": "high"},
        ]
    )
    # Only C is flagged; 0/1 are "low" → no downgrade
    assert compute_confidence_level("INV-001", ri) == "medium"


# --- Row-level source confidence (OPS-001) ---


def test_confidence_ops001_majority_low_rows_downgrades_to_low() -> None:
    """OPS-001 with 2/2 flagged rows 'low' → medium downgraded to low."""
    ri = _ri_conf(
        operational_impact_rows=[
            {"sku": "X", "stockout_lost_revenue_estimate": 600.0, "confidence": "low"},
            {"sku": "Y", "stockout_lost_revenue_estimate": 800.0, "confidence": "low"},
        ],
        thresholds={"OPS-001": 500.0},
    )
    assert compute_confidence_level("OPS-001", ri) == "low"


def test_confidence_ops001_majority_high_stays_medium() -> None:
    ri = _ri_conf(
        operational_impact_rows=[
            {"sku": "X", "stockout_lost_revenue_estimate": 600.0, "confidence": "high"},
            {"sku": "Y", "stockout_lost_revenue_estimate": 800.0, "confidence": "high"},
        ],
        thresholds={"OPS-001": 500.0},
    )
    # Row confidence high, but OPS-001 base is medium — no downgrade
    assert compute_confidence_level("OPS-001", ri) == "medium"


# --- Combined staleness + row downgrade ---


def test_confidence_staleness_applied_after_row_downgrade() -> None:
    """INV-001: row downgrade → low, then 4-day staleness cap (medium) has no further effect."""
    ri = _ri_conf(
        data_freshness_days=4,
        inventory_risk_rows=[
            {"sku": "A", "status": "stockout_risk", "confidence": "low"},
            {"sku": "B", "status": "stockout_risk", "confidence": "low"},
        ],
    )
    # base=medium, downgraded to low by rows, cap=medium → min(low, medium) = low
    assert compute_confidence_level("INV-001", ri) == "low"


# --- Engine integration ---


def test_rule_engine_evaluate_replaces_hardcoded_medium() -> None:
    """evaluate() must set confidence_level dynamically, not always 'medium'."""
    rules = get_rules()
    engine = RuleEngine(rules)
    # MRG-001 fires with 2 margin drift breaches
    ri = RuleInput(
        tenant_id="t1",
        snapshot_date=date.today(),
        margin_drift_rows=[
            {"channel": "google", "threshold_exceeded": True},
            {"channel": "meta", "threshold_exceeded": True},
        ],
        thresholds={"MRG-001": 1.0},
    )
    results = engine.evaluate(ri)
    mrg_results = [r for r in results if r.rule_id == "MRG-001"]
    assert len(mrg_results) == 1
    assert mrg_results[0].confidence_level == "low"


def test_rule_engine_evaluate_exc001_fresh_is_high() -> None:
    """EXC-001 with fresh data must produce confidence_level='high'."""
    rules = get_rules()
    engine = RuleEngine(rules)
    ri = RuleInput(
        tenant_id="t1",
        snapshot_date=date.today(),
        contribution_margin_pct=10.0,
        data_freshness_days=0,
        thresholds={"EXC-001": 30.0},
    )
    results = engine.evaluate(ri)
    exc_results = [r for r in results if r.rule_id == "EXC-001"]
    assert len(exc_results) == 1
    assert exc_results[0].confidence_level == "high"


# ===========================================================================
# T-057: Recommendation evidence payload assembler
# ===========================================================================

from worker.app.rules.evidence import build_evidence  # noqa: E402


def _ri_ev(**kwargs: object) -> RuleInput:
    """Minimal RuleInput for evidence unit tests."""
    return RuleInput(
        tenant_id="ev-tenant",
        snapshot_date=date.today(),
        **kwargs,  # type: ignore[arg-type]
    )


# --- Envelope fields present in all payloads ---


def test_evidence_envelope_fields_present() -> None:
    """Every evidence payload must include the common envelope keys."""
    ri = _ri_ev(contribution_margin_pct=20.0, thresholds={"EXC-001": 30.0})
    ev = build_evidence("EXC-001", ri)
    assert ev["rule_id"] == "EXC-001"
    assert ev["threshold_value"] == 30.0
    assert ev["data_freshness_days"] == 0
    assert ev["base_currency"] == "USD"


# --- EXC-001 ---


def test_evidence_exc001_values() -> None:
    ri = _ri_ev(
        contribution_margin_pct=22.0,
        thresholds={"EXC-001": 30.0},
        base_currency="GBP",
    )
    ev = build_evidence("EXC-001", ri)
    assert ev["actual_cm_pct"] == 22.0
    assert ev["floor_pct"] == 30.0
    assert ev["gap_pp"] == pytest.approx(8.0)
    assert ev["base_currency"] == "GBP"


# --- ACQ-001 ---


def test_evidence_acq001_values() -> None:
    ri = _ri_ev(blended_roas=1.2, thresholds={"ACQ-001": 1.5})
    ev = build_evidence("ACQ-001", ri)
    assert ev["actual_roas"] == 1.2
    assert ev["floor_roas"] == 1.5
    assert ev["gap"] == pytest.approx(0.3)


# --- RET-001 ---


def test_evidence_ret001_values() -> None:
    ri = _ri_ev(repeat_purchase_rate_pct=14.0, thresholds={"RET-001": 20.0})
    ev = build_evidence("RET-001", ri)
    assert ev["actual_rpr_pct"] == 14.0
    assert ev["floor_pct"] == 20.0
    assert ev["gap_pp"] == pytest.approx(6.0)


# --- INV-001 ---


def test_evidence_inv001_full_sku_list() -> None:
    """All at-risk SKUs must appear in evidence (no truncation)."""
    rows = [
        {"sku": f"SKU-{i}", "status": "stockout_risk",
         "capital_at_risk": 100.0, "days_to_stockout": 2.0, "confidence": "medium"}
        for i in range(10)
    ]
    ri = _ri_ev(inventory_risk_rows=rows, thresholds={"INV-001": 1.0})
    ev = build_evidence("INV-001", ri)
    assert ev["at_risk_count"] == 10
    assert len(ev["at_risk_skus"]) == 10
    assert ev["total_capital_at_risk"] == pytest.approx(1000.0)


def test_evidence_inv001_sku_fields() -> None:
    rows = [
        {"sku": "BOOT-01", "status": "critical_low",
         "capital_at_risk": 250.0, "days_to_stockout": 3.0, "confidence": "high"}
    ]
    ri = _ri_ev(inventory_risk_rows=rows)
    ev = build_evidence("INV-001", ri)
    sku = ev["at_risk_skus"][0]
    assert sku["sku"] == "BOOT-01"
    assert sku["status"] == "critical_low"
    assert sku["capital_at_risk"] == 250.0
    assert sku["days_to_stockout"] == 3.0
    assert sku["confidence"] == "high"


def test_evidence_inv001_excludes_healthy_skus() -> None:
    rows = [
        {"sku": "A", "status": "healthy", "capital_at_risk": 0.0},
        {"sku": "B", "status": "stockout_risk", "capital_at_risk": 500.0},
    ]
    ri = _ri_ev(inventory_risk_rows=rows)
    ev = build_evidence("INV-001", ri)
    assert ev["at_risk_count"] == 1
    assert ev["at_risk_skus"][0]["sku"] == "B"


# --- OPS-001 ---


def test_evidence_ops001_full_sku_list() -> None:
    rows = [
        {"sku": f"P-{i}", "stockout_lost_revenue_estimate": 600.0, "confidence": "medium"}
        for i in range(8)
    ]
    ri = _ri_ev(operational_impact_rows=rows, thresholds={"OPS-001": 500.0})
    ev = build_evidence("OPS-001", ri)
    assert ev["flagged_count"] == 8
    assert len(ev["flagged_skus"]) == 8
    assert ev["total_revenue_at_risk"] == pytest.approx(4800.0)


def test_evidence_ops001_excludes_below_threshold_rows() -> None:
    rows = [
        {"sku": "X", "stockout_lost_revenue_estimate": 200.0, "confidence": "high"},
        {"sku": "Y", "stockout_lost_revenue_estimate": 900.0, "confidence": "medium"},
    ]
    ri = _ri_ev(operational_impact_rows=rows, thresholds={"OPS-001": 500.0})
    ev = build_evidence("OPS-001", ri)
    assert ev["flagged_count"] == 1
    assert ev["flagged_skus"][0]["sku"] == "Y"
    assert ev["total_revenue_at_risk"] == pytest.approx(900.0)


# --- MRG-001 ---


def test_evidence_mrg001_full_entry_list() -> None:
    entries = [
        {"channel": "google", "category": "footwear",
         "threshold_exceeded": True, "drift_pct": 5.2, "actual_margin_pct": 18.0},
        {"channel": "meta", "category": "bags",
         "threshold_exceeded": True, "drift_pct": 3.1, "actual_margin_pct": 22.5},
        {"channel": "organic", "category": "all",
         "threshold_exceeded": False, "drift_pct": 0.5, "actual_margin_pct": 35.0},
    ]
    ri = _ri_ev(margin_drift_rows=entries, thresholds={"MRG-001": 1.0})
    ev = build_evidence("MRG-001", ri)
    assert ev["breach_count"] == 2
    assert len(ev["affected_entries"]) == 2
    channels = {e["channel"] for e in ev["affected_entries"]}
    assert channels == {"google", "meta"}


def test_evidence_mrg001_entry_fields() -> None:
    entries = [
        {"channel": "google", "category": "footwear",
         "threshold_exceeded": True, "drift_pct": 5.2, "actual_margin_pct": 18.0}
    ]
    ri = _ri_ev(margin_drift_rows=entries)
    ev = build_evidence("MRG-001", ri)
    entry = ev["affected_entries"][0]
    assert entry["channel"] == "google"
    assert entry["category"] == "footwear"
    assert entry["drift_pct"] == 5.2
    assert entry["actual_margin_pct"] == 18.0


# --- Unknown rule fallback ---


def test_evidence_unknown_rule_returns_envelope_only() -> None:
    ri = _ri_ev(data_freshness_days=1)
    ev = build_evidence("CUSTOM-999", ri)
    assert ev["rule_id"] == "CUSTOM-999"
    assert ev["threshold_value"] == 0.0
    assert ev["data_freshness_days"] == 1
    # No extra keys beyond the envelope
    assert set(ev.keys()) == {"rule_id", "threshold_value", "data_freshness_days", "base_currency"}


# --- Engine integration ---


def test_rule_engine_evaluate_sets_evidence() -> None:
    """evaluate() must populate non-empty evidence on every fired result."""
    rules = get_rules()
    engine = RuleEngine(rules)
    ri = RuleInput(
        tenant_id="t1",
        snapshot_date=date.today(),
        contribution_margin_pct=10.0,
        thresholds={"EXC-001": 30.0},
    )
    results = engine.evaluate(ri)
    exc_results = [r for r in results if r.rule_id == "EXC-001"]
    assert len(exc_results) == 1
    ev = exc_results[0].evidence
    assert ev["rule_id"] == "EXC-001"
    assert "actual_cm_pct" in ev
    assert "gap_pp" in ev


# --- Task integration ---


def test_rule_engine_job_writes_evidence_to_db() -> None:
    """run_rule_engine_job must persist evidence JSON on Recommendation rows."""
    from backend.app.db.models import Recommendation as RecModel

    db_engine, session_local = _make_rule_engine_engine()
    try:
        db: Session = session_local()
        tenant = Tenant(name="Evidence Co", slug="evidence-co", is_active=True)
        db.add(tenant)
        db.commit()
        tenant_id = tenant.id
        db.close()

        from worker.app.rules.pack import get_rules as _get_rules

        rules = _get_rules()

        db2: Session = session_local()
        today = date.today()
        db2.add(
            ExecutiveKpiSnapshot(
                tenant_id=tenant_id,
                snapshot_date=today,
                period_start_date=today,
                period_end_date=today,
                blended_roas=0.5,
                contribution_margin_pct=5.0,
            )
        )
        db2.commit()
        db2.close()

        run_rule_engine_job(session_factory=session_local, rules=rules)

        db3: Session = session_local()
        recs = db3.scalars(
            select(RecModel).where(RecModel.tenant_id == tenant_id)
        ).all()
        assert len(recs) >= 1
        for rec in recs:
            assert isinstance(rec.evidence, dict), (
                f"evidence must be a dict for {rec.rule_id}"
            )
            assert rec.evidence.get("rule_id") == rec.rule_id, (
                f"evidence.rule_id must match rec.rule_id for {rec.rule_id}"
            )
        db3.close()
    finally:
        Base.metadata.drop_all(bind=db_engine)
