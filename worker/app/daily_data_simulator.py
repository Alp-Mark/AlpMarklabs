"""
Daily Data Simulator for One8 Tenant

Simulates continuous Shopify and ad platform data ingestion by generating
realistic daily data. Runs as a scheduled Celery task.

This allows testing the optimization engine with a growing, realistic dataset
without needing actual platform connections.

ℹ️  NOTE: Generates simulated data for One8 test tenant for demo/testing purposes.
"""

import logging
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from backend.app.db.session import SessionLocal
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# One8 tenant configuration (test/demo tenant)
ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# Daily generation parameters (realistic for One8 brand)
DAILY_PARAMS = {
    "orders_min": 150,
    "orders_max": 350,
    "weekend_multiplier": 1.3,  # 30% more orders on weekends
    "avg_order_value": 6500,  # INR
    "aov_std_dev": 3000,
    "meta_spend_min": 150000,  # INR per day
    "meta_spend_max": 250000,
    "google_spend_min": 80000,
    "google_spend_max": 150000,
    "return_rate": 0.12,  # 12% returns
    "refund_delay_days_min": 3,
    "refund_delay_days_max": 10,
}

# Campaign names (consistent with seed data)
META_CAMPAIGNS = [
    "TOF_Prospecting_Lookalike",
    "MOF_Retargeting_Engagement",
    "BOF_Conversion_Purchase",
]

GOOGLE_CAMPAIGNS = [
    "Search_Brand_One8",
    "Search_Generic_Sportswear",
    "Display_Prospecting_Sports",
]


def get_connector_id(db: Session) -> str:
    """Get the Shopify connector ID for One8 tenant."""
    result = db.execute(
        text(
            """
        SELECT id FROM connector_integrations 
        WHERE tenant_id = :tid 
        LIMIT 1
        """
        ),
        {"tid": ONE8_TENANT_ID},
    ).fetchone()

    if not result:
        raise ValueError(f"No connector found for tenant {ONE8_TENANT_ID}")

    return str(result[0])


def generate_daily_orders(
    db: Session, connector_id: str, target_date: date
) -> dict[str, Any]:
    """
    Generate realistic orders for a specific date.
    
    Returns summary stats.
    """
    # Determine order volume based on day of week
    is_weekend = target_date.weekday() >= 5
    multiplier = DAILY_PARAMS["weekend_multiplier"] if is_weekend else 1.0

    num_orders = random.randint(
        int(DAILY_PARAMS["orders_min"] * multiplier),
        int(DAILY_PARAMS["orders_max"] * multiplier),
    )

    orders_batch = []
    total_revenue = Decimal("0")

    for _ in range(num_orders):
        # Generate order value (log-normal distribution)
        aov = max(
            1000,
            random.gauss(DAILY_PARAMS["avg_order_value"], DAILY_PARAMS["aov_std_dev"]),
        )

        # Order details
        subtotal = Decimal(str(aov))
        shipping = Decimal(str(random.choice([0, 99, 149])))
        tax = subtotal * Decimal("0.18")  # 18% GST
        total = subtotal + shipping + tax

        # Random timestamp during the day
        order_datetime = datetime.combine(target_date, datetime.min.time()).replace(
            hour=random.randint(0, 23),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )

        # Fulfillment status (92% fulfilled, 5% pending, 3% cancelled)
        fulfillment_status = random.choices(
            ["fulfilled", "pending", "cancelled"], weights=[0.92, 0.05, 0.03]
        )[0]

        financial_status = "paid" if fulfillment_status != "cancelled" else "refunded"

        # Generate unique external_order_id
        external_order_id = str(random.randint(10000000, 99999999))

        orders_batch.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_order_id": external_order_id,
                "customer_id": f"cust_{random.randint(1000, 99999)}",
                "order_number": external_order_id,
                "currency": "INR",
                "total_amount": float(total),
                "discount_amount": 0.0,
                "shipping_amount": float(shipping),
                "refund_amount": 0.0 if financial_status == "paid" else float(total),
                "is_refunded": financial_status != "paid",
                "order_created_at": order_datetime,
                "synced_at": datetime.utcnow(),
            }
        )

        if financial_status == "paid":
            total_revenue += total

    # Bulk insert
    if orders_batch:
        db.execute(
            text(
                """
            INSERT INTO shopify_orders (
                id, tenant_id, connector_id, external_order_id, customer_id,
                order_number, currency, total_amount, discount_amount,
                shipping_amount, refund_amount, is_refunded, order_created_at, synced_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_order_id, :customer_id,
                :order_number, :currency, :total_amount, :discount_amount,
                :shipping_amount, :refund_amount, :is_refunded,
                :order_created_at, :synced_at
            )
            """
            ),
            orders_batch,
        )
        db.commit()

    return {
        "orders_created": len(orders_batch),
        "revenue": float(total_revenue),
        "is_weekend": is_weekend,
    }


def generate_daily_refunds(db: Session, connector_id: str) -> dict[str, Any]:
    """
    Generate refunds for orders from 3-10 days ago.
    
    Simulates the natural delay in returns.
    """
    # Get eligible orders (paid, not refunded, 3-10 days old)
    min_age = datetime.utcnow() - timedelta(days=DAILY_PARAMS["refund_delay_days_max"])
    max_age = datetime.utcnow() - timedelta(days=DAILY_PARAMS["refund_delay_days_min"])

    eligible_orders = db.execute(
        text(
            """
        SELECT id, external_order_id, total_amount, order_created_at
        FROM shopify_orders
        WHERE tenant_id = :tid
        AND is_refunded = false
        AND order_created_at BETWEEN :min_age AND :max_age
        ORDER BY RANDOM()
        LIMIT 100
        """
        ),
        {"tid": ONE8_TENANT_ID, "min_age": min_age, "max_age": max_age},
    ).fetchall()

    if not eligible_orders:
        return {"refunds_created": 0, "refund_amount": 0.0}

    # Select orders for refund based on return rate
    num_refunds = int(len(eligible_orders) * DAILY_PARAMS["return_rate"])
    refund_orders = random.sample(
        list(eligible_orders), min(num_refunds, len(eligible_orders))
    )

    refunds_batch = []
    total_refund_amount = Decimal("0")

    for order in refund_orders:
        refund_date = datetime.utcnow()
        external_refund_id = f"refund_{random.randint(1000000, 9999999)}"

        refunds_batch.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_refund_id": external_refund_id,
                "order_id": order[0],
                "external_order_id": order[1],
                "refund_amount": order[2],
                "reason": random.choice(
                    ["customer_request", "defective", "size_issue", "changed_mind"]
                ),
                "refund_created_at": refund_date,
                "synced_at": refund_date,
                "created_at": refund_date,
            }
        )

        total_refund_amount += Decimal(str(order[2]))

    # Insert refunds
    if refunds_batch:
        db.execute(
            text(
                """
            INSERT INTO shopify_refunds (
                id, tenant_id, connector_id, external_refund_id,
                order_id, external_order_id,
                refund_amount, reason, refund_created_at, synced_at, created_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_refund_id,
                :order_id, :external_order_id,
                :refund_amount, :reason, :refund_created_at, :synced_at, :created_at
            )
            """
            ),
            refunds_batch,
        )
        db.commit()

    return {
        "refunds_created": len(refunds_batch),
        "refund_amount": float(total_refund_amount),
    }


def generate_daily_ad_spend(
    db: Session, connector_id: str, target_date: date
) -> dict[str, Any]:
    """Generate daily ad spend for Meta and Google."""
    meta_batch = []
    google_batch = []

    # Meta ad spend - distribute across campaigns
    daily_meta_total = Decimal(
        str(
            random.randint(
                int(DAILY_PARAMS["meta_spend_min"]),
                int(DAILY_PARAMS["meta_spend_max"]),
            )
        )
    )

    for campaign in META_CAMPAIGNS:
        campaign_spend = daily_meta_total / len(META_CAMPAIGNS)
        meta_batch.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_campaign_id": (
                    f"meta_{campaign}_{target_date.strftime('%Y%m%d')}"
                ),
                "campaign_name": campaign,
                "spend_date": target_date,
                "currency": "INR",
                "spend_amount": float(campaign_spend),
                "synced_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    # Google ad spend - distribute across campaigns
    daily_google_total = Decimal(
        str(
            random.randint(
                int(DAILY_PARAMS["google_spend_min"]),
                int(DAILY_PARAMS["google_spend_max"]),
            )
        )
    )

    for campaign in GOOGLE_CAMPAIGNS:
        campaign_spend = daily_google_total / len(GOOGLE_CAMPAIGNS)
        google_batch.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": ONE8_TENANT_ID,
                "connector_id": connector_id,
                "external_campaign_id": (
                    f"google_{campaign}_{target_date.strftime('%Y%m%d')}"
                ),
                "campaign_name": campaign,
                "spend_date": target_date,
                "currency": "INR",
                "spend_amount": float(campaign_spend),
                "synced_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    # Insert ad spend
    if meta_batch:
        db.execute(
            text(
                """
            INSERT INTO meta_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount,
                :synced_at, :created_at, :updated_at
            )
            """
            ),
            meta_batch,
        )

    if google_batch:
        db.execute(
            text(
                """
            INSERT INTO google_ad_spends (
                id, tenant_id, connector_id, external_campaign_id, campaign_name,
                spend_date, currency, spend_amount, synced_at, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :connector_id, :external_campaign_id, :campaign_name,
                :spend_date, :currency, :spend_amount,
                :synced_at, :created_at, :updated_at
            )
            """
            ),
            google_batch,
        )

    db.commit()

    return {
        "meta_spend": float(daily_meta_total),
        "google_spend": float(daily_google_total),
        "total_spend": float(daily_meta_total + daily_google_total),
    }


def run_daily_simulation(target_date: date | None = None) -> dict[str, Any]:
    """
    Run daily data simulation for One8 tenant.
    
    Args:
        target_date: Date to generate data for. Defaults to today.
    
    Returns:
        Summary statistics
    """
    if target_date is None:
        target_date = date.today()

    db = SessionLocal()

    try:
        # Check if data already exists for this date
        existing_orders = db.execute(
            text(
                """
            SELECT COUNT(*) FROM shopify_orders
            WHERE tenant_id = :tid
            AND order_created_at::date = :target_date
            """
            ),
            {"tid": ONE8_TENANT_ID, "target_date": target_date},
        ).scalar()

        if existing_orders and existing_orders > 0:
            return {
                "status": "skipped",
                "reason": f"Data already exists for {target_date}",
                "existing_orders": existing_orders,
            }

        # Get connector
        connector_id = get_connector_id(db)

        # Log data generation
        logger.info(
            f"Generating simulated data for One8 test tenant ({ONE8_TENANT_ID}) "
            f"for date {target_date}"
        )

        # Generate data
        orders_stats = generate_daily_orders(db, connector_id, target_date)
        refunds_stats = generate_daily_refunds(db, connector_id)
        ad_spend_stats = generate_daily_ad_spend(db, connector_id, target_date)

        logger.info(
            f"Successfully generated: {orders_stats['orders_created']} orders, "
            f"{refunds_stats['refunds_created']} refunds, "
            f"₹{ad_spend_stats['total_spend']:,.0f} ad spend"
        )

        return {
            "status": "success",
            "date": str(target_date),
            "orders": orders_stats,
            "refunds": refunds_stats,
            "ad_spend": ad_spend_stats,
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "date": str(target_date) if target_date else "unknown",
            "error": str(e),
        }

    finally:
        db.close()


# Convenience function for manual testing
def simulate_date_range(start_date: date, end_date: date) -> dict[str, Any]:
    """
    Simulate data for a range of dates.
    
    Useful for backfilling or testing.
    """
    current_date = start_date
    results = []

    while current_date <= end_date:
        result = run_daily_simulation(current_date)
        results.append(result)
        current_date += timedelta(days=1)

    return {
        "dates_processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }
