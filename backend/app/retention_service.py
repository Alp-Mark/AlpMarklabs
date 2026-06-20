"""Retention dashboard business logic and calculations."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import ShopifyOrder
from backend.app.schemas.retention import (
    CohortRetention,
    CustomerSegment,
    RetentionDashboardResponse,
)

if TYPE_CHECKING:
    from uuid import UUID


def calculate_retention_dashboard(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> RetentionDashboardResponse:
    """Calculate retention dashboard metrics for a tenant and date range.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        period_start: Start of analysis period (inclusive)
        period_end: End of analysis period (inclusive)

    Returns:
        RetentionDashboardResponse with retention and cohort metrics
    """
    # Query all orders in period
    orders_query = (
        select(ShopifyOrder)
        .where(ShopifyOrder.tenant_id == tenant_id)
        .where(ShopifyOrder.order_created_at >= period_start)
        .where(ShopifyOrder.order_created_at <= period_end)
        .order_by(ShopifyOrder.order_created_at)
    )
    orders = list(db.execute(orders_query).scalars().all())

    # Calculate last synced timestamp
    last_synced_query = (
        select(func.max(ShopifyOrder.synced_at))
        .where(ShopifyOrder.tenant_id == tenant_id)
    )
    last_synced = db.execute(last_synced_query).scalar()

    # Group orders by customer
    customer_orders: dict[str, list[ShopifyOrder]] = {}
    for order in orders:
        customer_id = order.customer_id
        if customer_id is None:
            # Skip orders without customer_id (guest checkouts)
            continue
        if customer_id not in customer_orders:
            customer_orders[customer_id] = []
        customer_orders[customer_id].append(order)

    # Calculate basic metrics
    total_customers = len(customer_orders)
    repeat_customers = sum(1 for orders in customer_orders.values() if len(orders) >= 2)
    repeat_purchase_rate = (
        (repeat_customers / total_customers * 100) if total_customers > 0 else None
    )

    total_orders = len(orders)
    avg_orders_per_customer = (
        total_orders / total_customers if total_customers > 0 else None
    )

    # Calculate customer lifetime value
    total_revenue = sum(order.total_amount for order in orders)
    avg_customer_lifetime_value = (
        total_revenue / total_customers if total_customers > 0 else None
    )

    # Calculate average days between purchases (for repeat customers)
    days_between_purchases: list[float] = []
    for _customer_id, customer_order_list in customer_orders.items():
        if len(customer_order_list) >= 2:
            sorted_orders = sorted(
                customer_order_list, key=lambda o: o.order_created_at
            )
            for i in range(1, len(sorted_orders)):
                days_diff = (
                    sorted_orders[i].order_created_at
                    - sorted_orders[i - 1].order_created_at
                ).days
                days_between_purchases.append(float(days_diff))

    avg_days_between_purchases = (
        sum(days_between_purchases) / len(days_between_purchases)
        if days_between_purchases
        else None
    )

    # Calculate churn risk (customers with only 1 order and > 60 days since order)
    churn_risk_customers = 0
    sixty_days_ago = period_end - timedelta(days=60)
    for _customer_id, customer_order_list in customer_orders.items():
        if len(customer_order_list) == 1:
            order_date = customer_order_list[0].order_created_at.date()
            if order_date <= sixty_days_ago:
                churn_risk_customers += 1

    # Calculate cohort retention
    cohort_retention = _calculate_cohort_retention(
        db=db, tenant_id=tenant_id, period_start=period_start, period_end=period_end
    )

    # Calculate customer segments
    customer_segments = _calculate_customer_segments(customer_orders)

    return RetentionDashboardResponse(
        total_customers=total_customers,
        repeat_customers=repeat_customers,
        repeat_purchase_rate=repeat_purchase_rate,
        avg_orders_per_customer=avg_orders_per_customer,
        avg_customer_lifetime_value=avg_customer_lifetime_value,
        avg_days_between_purchases=avg_days_between_purchases,
        churn_risk_customers=churn_risk_customers,
        cohort_retention=cohort_retention,
        customer_segments=customer_segments,
        period_start=period_start,
        period_end=period_end,
        data_last_synced_at=last_synced.isoformat() if last_synced else None,
        currency="USD",
    )


def _calculate_cohort_retention(
    db: Session,
    tenant_id: UUID,
    period_start: date,
    period_end: date,
) -> list[CohortRetention]:
    """Calculate retention by cohort month.

    A cohort is defined by the month of a customer's first order.
    """
    # Get all orders for tenant (not just in period) to determine first order
    all_orders_query = (
        select(
            ShopifyOrder.customer_id,
            func.min(ShopifyOrder.order_created_at).label("first_order_date"),
        )
        .where(ShopifyOrder.tenant_id == tenant_id)
        .group_by(ShopifyOrder.customer_id)
    )
    first_orders = {
        row.customer_id: row.first_order_date
        for row in db.execute(all_orders_query).all()
    }

    # Group customers by cohort month
    cohorts: dict[str, set[str]] = {}
    for customer_id, first_order_date in first_orders.items():
        cohort_month = first_order_date.strftime("%Y-%m")
        if cohort_month not in cohorts:
            cohorts[cohort_month] = set()
        cohorts[cohort_month].add(customer_id)

    # Calculate retention for each cohort
    cohort_retention_list: list[CohortRetention] = []
    for cohort_month, customer_ids in sorted(cohorts.items()):
        cohort_start_date = date.fromisoformat(f"{cohort_month}-01")
        
        # Only include cohorts within analysis period
        if cohort_start_date > period_end:
            continue

        cohort_size = len(customer_ids)

        # Calculate retention for months 0-3
        retained_counts = _calculate_cohort_retained_customers(
            db=db,
            tenant_id=tenant_id,
            customer_ids=customer_ids,
            cohort_start_date=cohort_start_date,
        )

        retention_rate_month_1 = (
            (retained_counts[1] / cohort_size * 100)
            if cohort_size > 0 and retained_counts[1] is not None
            else None
        )
        retention_rate_month_2 = (
            (retained_counts[2] / cohort_size * 100)
            if cohort_size > 0 and retained_counts[2] is not None
            else None
        )
        retention_rate_month_3 = (
            (retained_counts[3] / cohort_size * 100)
            if cohort_size > 0 and retained_counts[3] is not None
            else None
        )

        cohort_retention_list.append(
            CohortRetention(
                cohort_month=cohort_month,
                cohort_size=cohort_size,
                month_0_retained=retained_counts[0] or cohort_size,
                month_1_retained=retained_counts[1],
                month_2_retained=retained_counts[2],
                month_3_retained=retained_counts[3],
                retention_rate_month_1=retention_rate_month_1,
                retention_rate_month_2=retention_rate_month_2,
                retention_rate_month_3=retention_rate_month_3,
            )
        )

    return cohort_retention_list


def _calculate_cohort_retained_customers(
    db: Session,
    tenant_id: UUID,
    customer_ids: set[str],
    cohort_start_date: date,
) -> dict[int, int | None]:
    """Calculate how many customers from cohort ordered in months 0-3."""
    retained: dict[int, int | None] = {0: None, 1: None, 2: None, 3: None}

    for month_offset in range(4):
        month_start = cohort_start_date + timedelta(days=30 * month_offset)
        month_end = cohort_start_date + timedelta(days=30 * (month_offset + 1))

        # Count distinct customers who ordered in this month window
        orders_query = (
            select(func.count(func.distinct(ShopifyOrder.customer_id)))
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(ShopifyOrder.customer_id.in_(customer_ids))
            .where(ShopifyOrder.order_created_at >= month_start)
            .where(ShopifyOrder.order_created_at < month_end)
        )
        count = db.execute(orders_query).scalar()
        retained[month_offset] = count if count is not None else None

    return retained


def _calculate_customer_segments(
    customer_orders: dict[str, list[ShopifyOrder]],
) -> list[CustomerSegment]:
    """Segment customers by order frequency and value."""
    segments: list[CustomerSegment] = []

    # Segment: One-time buyers
    one_time_customers = [
        (cid, orders) for cid, orders in customer_orders.items() if len(orders) == 1
    ]
    if one_time_customers:
        one_time_revenue = sum(
            order.total_amount for _, orders in one_time_customers for order in orders
        )
        one_time_avg_value = one_time_revenue / len(one_time_customers)
        segments.append(
            CustomerSegment(
                segment_name="One-time Buyers",
                customer_count=len(one_time_customers),
                avg_order_value=one_time_avg_value,
                avg_order_frequency=1.0,
                total_revenue=one_time_revenue,
                is_at_risk=True,  # One-time buyers at risk of churn
            )
        )

    # Segment: Repeat buyers (2-4 orders)
    repeat_customers = [
        (cid, orders)
        for cid, orders in customer_orders.items()
        if 2 <= len(orders) <= 4
    ]
    if repeat_customers:
        repeat_revenue = sum(
            order.total_amount for _, orders in repeat_customers for order in orders
        )
        repeat_order_count = sum(len(orders) for _, orders in repeat_customers)
        repeat_avg_value = repeat_revenue / repeat_order_count
        repeat_avg_frequency = repeat_order_count / len(repeat_customers)
        segments.append(
            CustomerSegment(
                segment_name="Repeat Buyers",
                customer_count=len(repeat_customers),
                avg_order_value=repeat_avg_value,
                avg_order_frequency=repeat_avg_frequency,
                total_revenue=repeat_revenue,
                is_at_risk=False,
            )
        )

    # Segment: Loyal customers (5+ orders)
    loyal_customers = [
        (cid, orders) for cid, orders in customer_orders.items() if len(orders) >= 5
    ]
    if loyal_customers:
        loyal_revenue = sum(
            order.total_amount for _, orders in loyal_customers for order in orders
        )
        loyal_order_count = sum(len(orders) for _, orders in loyal_customers)
        loyal_avg_value = loyal_revenue / loyal_order_count
        loyal_avg_frequency = loyal_order_count / len(loyal_customers)
        segments.append(
            CustomerSegment(
                segment_name="Loyal Customers",
                customer_count=len(loyal_customers),
                avg_order_value=loyal_avg_value,
                avg_order_frequency=loyal_avg_frequency,
                total_revenue=loyal_revenue,
                is_at_risk=False,
            )
        )

    return segments
