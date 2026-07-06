#!/usr/bin/env python3
"""
Seed One8 tenant with realistic business data.

One8 is Virat Kohli's premium Indian lifestyle brand.

Data generation philosophy:
    Data generates analytics — not the other way around.
    Every parameter here is an observable business metric (CAC, AOV, spend).
    The optimizer discovers saturation curves from this data; we never pre-define them.

Usage:
    railway run python3 scripts/seed_one8_realistic.py
"""

import math
import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text  # noqa: E402

ONE8_TENANT_ID = "23165fa5-150b-4b6c-a637-b3dd24532c4d"

# ── One8 brand business parameters ────────────────────────────────────────────
# These are observable business KPIs — not mathematical model constants.
# The analytics engine discovers everything else from the resulting data.
ONE8_BRAND = {
    # Normal daily ad budgets
    "meta_base_spend":   180_000,   # ₹1.8L/day on Meta at steady state
    "google_base_spend": 110_000,   # ₹1.1L/day on Google at steady state

    # CAC at the base spend levels above (₹ per paid conversion)
    # Meta: brand/discovery — broader audience, higher cost per conversion
    # Google: search intent — in-market audience, lower cost per conversion
    "meta_base_cac":   920,
    "google_base_cac": 650,

    # Diminishing returns as a business statement:
    #   "When we double Meta spend, our CAC rises by 30%."
    #   "When we double Google spend, our CAC rises by 45%."
    # Google saturates faster because search demand volume is finite.
    # The optimizer will fit its own curve to the resulting data and
    # discover the exponent — we never set k, n, or max_conversions directly.
    "meta_cac_at_2x_spend_increase_pct":   30,
    "google_cac_at_2x_spend_increase_pct": 45,

    # Organic demand — orders NOT driven by Meta or Google spend.
    # Sources: Virat Kohli celebrity pull, TV/streaming ads, PR, direct traffic.
    "organic_orders_per_day": 50,

    # Order economics
    "base_aov":        6_500,   # ₹6,500 average order (premium sportswear)
    "aov_std_dev":     2_500,
    "return_rate":     0.12,    # 12% of orders are eventually returned
    "refund_min_days": 3,       # returns take at least 3 days
    "refund_max_days": 10,

    # Customer base — One8 has a loyal repeat-buyer pool
    "loyal_pool_size":    2_000,  # known repeat customers
    "repeat_order_share": 0.25,   # 25% of daily orders from repeat buyers
}

# ── Campaign cycle epochs (fixed so seed + simulator stay in sync) ─────────────
# Meta: collection launch campaigns — 45-day cycle
_META_EPOCH   = date(2026, 1, 1)
# Google: search/shopping campaigns — 33-day cycle, different epoch = independent timing
_GOOGLE_EPOCH = date(2026, 1, 10)

# Pre-generated loyal customer pool (deterministic IDs, shared with simulator)
_LOYAL_POOL = [
    f"loyal_{i:05d}" for i in range(1, int(ONE8_BRAND["loyal_pool_size"]) + 1)
]


# ── Seasonality helpers ────────────────────────────────────────────────────────

def get_seasonality_multiplier(d: datetime) -> float:
    """
    Seasonal demand multiplier for One8.
    Applied to ORGANIC orders and AOV only — NOT to paid conversions.
    Keeping paid channels clean lets the optimizer fit accurate saturation curves.
    """
    month = d.month
    day   = d.day

    if (month == 10 and day >= 24) or (month == 11 and day <= 15):
        diwali_center = datetime(d.year, 11, 1)
        gap = abs((d - diwali_center).days)
        if gap <= 3:
            return 2.0
        if gap <= 10:
            return 1.6
        return 1.3

    if month in (3, 4, 5):
        return 1.5   # IPL
    if month == 10 and day < 24:
        return 1.4   # World Cup
    if (month == 12 and day >= 20) or (month == 1 and day <= 10):
        return 1.3  # New Year
    if month == 2 and 10 <= day <= 15:
        return 1.2   # Valentine's
    if month in (6, 7, 8):
        return 0.85  # Summer lull
    return 1.0


def get_weekend_multiplier(d: datetime) -> float:
    """Fri–Sun shopping uplift (organic demand only)."""
    wd = d.weekday()
    if wd == 4:
        return 1.25
    if wd == 5:
        return 1.40
    if wd == 6:
        return 1.35
    return 1.0


# ── Campaign phase helpers (calendar-date based, consistent across runs) ────────

def meta_campaign_phase(d: date) -> float:
    """Meta spend multiplier from collection launch cycle (45-day period)."""
    phase = (d - _META_EPOCH).days % 45
    if 3 <= phase <= 16:
        return 1.9   # 2-week launch burst
    if phase <= 22:
        return 1.3   # wind-down
    return 1.0


def google_campaign_phase(d: date) -> float:
    """Google spend multiplier from search campaign cycle (33-day period)."""
    phase = (d - _GOOGLE_EPOCH).days % 33
    if 12 <= phase <= 21:
        return 1.6   # 10-day search push
    if phase <= 26:
        return 1.15  # wind-down
    return 1.0


# ── Spend generators ───────────────────────────────────────────────────────────

def get_meta_spend(d: date, growth_start: date, growth_days: int) -> int:
    """Meta daily spend with independent campaign cycle, growth trend, and variance."""
    days_elapsed = max(0, (d - growth_start).days)
    growth       = 1.0 + min(1.0, days_elapsed / growth_days) * 0.10
    phase        = meta_campaign_phase(d)
    variance     = random.uniform(0.85, 1.15)
    weekend_cut  = 0.88 if d.weekday() in (5, 6) else 1.0
    return max(
        0,
        int(ONE8_BRAND["meta_base_spend"] * growth * phase * variance * weekend_cut),
    )


def get_google_spend(d: date, growth_start: date, growth_days: int) -> int:
    """Google daily spend with campaign cycle, growth trend, and variance."""
    days_elapsed = max(0, (d - growth_start).days)
    growth       = 1.0 + min(1.0, days_elapsed / growth_days) * 0.10
    phase        = google_campaign_phase(d)
    variance     = random.uniform(0.88, 1.12)
    weekend_cut  = 0.92 if d.weekday() in (5, 6) else 1.0
    return max(
        0,
        int(ONE8_BRAND["google_base_spend"] * growth * phase * variance * weekend_cut),
    )


# ── Conversion calculators (CAC-driven — no pre-defined model parameters) ───────

def _paid_conversions(spend: int | float, base_spend: int | float,
                      base_cac: int | float,
                      cac_increase_at_2x_pct: int | float) -> int:
    """
    Paid conversions from ad spend using CAC with diminishing returns.

        effective_CAC = base_cac × (spend / base_spend) ^ exponent
        conversions   = spend / effective_CAC

    The exponent is derived from the business metric
    "CAC increases X% when spend doubles" — it is never set directly.
    The optimizer fits its own saturation curve to the resulting spend/conversion data.
    """
    if spend <= 0:
        return 0
    cac_at_2x    = 1.0 + cac_increase_at_2x_pct / 100.0
    exponent     = math.log(cac_at_2x) / math.log(2)   # e.g. log(1.30)/log(2) ≈ 0.38
    effective_cac = base_cac * (spend / base_spend) ** exponent
    return max(0, int(spend / effective_cac))


def get_meta_conversions(meta_spend: int) -> int:
    return _paid_conversions(
        meta_spend,
        ONE8_BRAND["meta_base_spend"],
        ONE8_BRAND["meta_base_cac"],
        ONE8_BRAND["meta_cac_at_2x_spend_increase_pct"],
    )


def get_google_conversions(google_spend: int) -> int:
    return _paid_conversions(
        google_spend,
        ONE8_BRAND["google_base_spend"],
        ONE8_BRAND["google_base_cac"],
        ONE8_BRAND["google_cac_at_2x_spend_increase_pct"],
    )


def get_organic_orders(d: datetime) -> int:
    """
    Orders not driven by Meta or Google spend.
    ALL seasonality and weekend uplift lives here — not in paid channels.
    This keeps the paid spend→conversion signal clean for the optimizer.
    """
    base    = ONE8_BRAND["organic_orders_per_day"]
    season  = get_seasonality_multiplier(d)
    weekend = get_weekend_multiplier(d)
    noise   = random.uniform(0.85, 1.15)
    return max(0, int(base * season * weekend * noise))


# ── Order attribute helpers ────────────────────────────────────────────────────

def get_seasonal_aov(d: datetime) -> int:
    """AOV adjusted for season. Premium brands see larger baskets during festivals."""
    season = get_seasonality_multiplier(d)
    if season >= 2.0:
        mult = 1.30   # Diwali: gifting, premium tier
    elif season >= 1.5:
        mult = 1.10   # IPL: fan merchandise bundles
    elif season <= 0.85:
        mult = 0.92   # Summer: clearance / casual
    else:
        mult = 1.0
    return max(
        1_000,
        int(random.gauss(ONE8_BRAND["base_aov"] * mult, ONE8_BRAND["aov_std_dev"])),
    )


def get_discount(order_value: int, m_phase: float, g_phase: float) -> int:
    """Discount during campaign bursts to drive conversion rate."""
    if m_phase >= 1.9:
        return int(order_value * 0.15)   # Meta collection launch
    if g_phase >= 1.6:
        return int(order_value * 0.08)   # Google search push
    return 0


def pick_customer_id() -> str:
    """25% chance of a loyal repeat customer, 75% new."""
    if random.random() < ONE8_BRAND["repeat_order_share"]:
        return random.choice(_LOYAL_POOL)
    return f"new_{uuid.uuid4().hex[:10]}"



def seed_realistic_data(days: int = 120) -> None:
    """Seed One8 with realistic business data (data-first model)."""

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(
            "\u274c DATABASE_URL not set. "
            "Run with: railway run python3 scripts/seed_one8_realistic.py"
        )
        sys.exit(1)

    engine = create_engine(db_url)

    print("=" * 70)
    print("🏏  One8 (Virat Kohli Brand) — data-first seed")
    print("=" * 70)
    print(f"Tenant : {ONE8_TENANT_ID}")
    print(f"Days   : {days}")
    print(
        f"Range  : "
        f"{datetime.now().date() - timedelta(days=days - 1)} → {datetime.now().date()}"
    )
    print()

    # ── Step 1: connector ─────────────────────────────────────────────────────
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id FROM connector_integrations"
                " WHERE tenant_id = :tid AND source = 'shopify'"
            ),
            {"tid": ONE8_TENANT_ID},
        ).fetchone()
    if not row:
        print("❌ No Shopify connector found. Run seed_one8_data.py first.")
        sys.exit(1)
    connector_id = str(row[0])
    print(f"✅ Connector: {connector_id}\n")

    # ── Step 2: wipe ──────────────────────────────────────────────────────────
    print("🗑️  Wiping existing One8 data...")
    tables = [
        "shopify_order_line_items", "shopify_orders",
        "meta_ad_spends", "google_ad_spends",
        "recommendations",
        "fitted_models",        # must be before optimization_runs (FK)
        "optimization_runs",
        "executive_kpi_snapshots", "acquisition_metrics_snapshots",
        "retention_daily_snapshots",
    ]
    total_deleted = 0
    for table in tables:
        try:
            with engine.begin() as conn:
                r = conn.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id = :tid"),
                    {"tid": ONE8_TENANT_ID},
                )
                if r.rowcount:
                    print(f"   {table}: {r.rowcount:,} rows")
                    total_deleted += r.rowcount
        except Exception as e:
            if "does not exist" not in str(e):
                print(f"   ⚠️  {table}: {e}")
    print(f"   ✅ {total_deleted:,} rows removed\n")

    # ── Step 3: generate ──────────────────────────────────────────────────────
    end_dt       = datetime.now()
    growth_start = (end_dt - timedelta(days=days - 1)).date()

    meta_batch:   list[dict] = []
    google_batch: list[dict] = []
    orders_batch: list[dict] = []

    total_meta_spend   = 0
    total_google_spend = 0
    total_orders       = 0
    total_revenue      = Decimal("0")
    total_refunds      = 0

    print("📊 Generating data (oldest → newest)...")
    print(f"  {'Date':<12} {'Meta ₹':>9} {'→conv':>6} {'Google ₹':>10} {'→conv':>6} "
          f"{'Organic':>8} {'Total':>6} {'Revenue ₹':>12}")
    print("  " + "-" * 74)

    for day_offset in range(days - 1, -1, -1):   # oldest first
        current_dt = end_dt - timedelta(days=day_offset)
        d          = current_dt.date()

        # ── Spend (each channel uses its own independent campaign cycle) ──────
        meta_spend   = get_meta_spend(d, growth_start, days)
        google_spend = get_google_spend(d, growth_start, days)

        # ── Paid conversions (CAC model — no Hill curve parameters pre-defined)
        meta_paid   = get_meta_conversions(meta_spend)
        google_paid = get_google_conversions(google_spend)

        # ── Organic (all seasonality lives here, keeping paid channels clean) ─
        organic = get_organic_orders(current_dt)

        # Small daily noise on the total
        total_daily = max(
            0,
            int((meta_paid + google_paid + organic) * random.uniform(0.94, 1.06)),
        )

        m_phase = meta_campaign_phase(d)
        g_phase = google_campaign_phase(d)

        # ── Orders ────────────────────────────────────────────────────────────
        daily_revenue  = Decimal("0")
        daily_refunds  = 0
        for _ in range(total_daily):
            order_value = get_seasonal_aov(current_dt)
            discount    = get_discount(order_value, m_phase, g_phase)
            net_value   = max(500, order_value - discount)

            order_dt = current_dt.replace(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
            )

            # Orders ≥3 days old have a 12% chance of having been returned
            is_refunded   = (day_offset >= ONE8_BRAND["refund_min_days"]
                             and random.random() < ONE8_BRAND["return_rate"])
            refund_amount = float(net_value) if is_refunded else 0.0
            if is_refunded:
                daily_refunds += 1

            ext_id = f"ONE8{random.randint(100_000, 999_999)}"
            orders_batch.append({
                "id":                str(uuid.uuid4()),
                "tenant_id":         ONE8_TENANT_ID,
                "connector_id":      connector_id,
                "external_order_id": ext_id,
                "customer_id":       pick_customer_id(),
                "order_number":      ext_id,
                "currency":          "INR",
                "total_amount":      float(net_value),
                "discount_amount":   float(discount),
                "shipping_amount":   0.0,
                "refund_amount":     refund_amount,
                "is_refunded":       is_refunded,
                "order_created_at":  order_dt,
                "synced_at":         datetime.utcnow(),
            })
            if not is_refunded:
                daily_revenue += Decimal(str(net_value))

        # ── Meta ad spend (3 campaigns) ───────────────────────────────────────
        for campaign in ["Acquisition - Broad", "Retargeting", "Collection Launch"]:
            meta_batch.append({
                "id":                   str(uuid.uuid4()),
                "tenant_id":            ONE8_TENANT_ID,
                "connector_id":         connector_id,
                "external_campaign_id": (
                    f"meta_{campaign.replace(' ', '_')}_{d.strftime('%Y%m%d')}"
                ),
                "campaign_name":        campaign,
                "spend_date":           d,
                "currency":             "INR",
                "spend_amount":         float(meta_spend / 3),
                "synced_at":            datetime.utcnow(),
                "created_at":           datetime.utcnow(),
                "updated_at":           datetime.utcnow(),
            })

        # ── Google ad spend (3 campaigns) ─────────────────────────────────────
        for campaign in ["Search - Brand", "Search - Generic", "Shopping"]:
            google_batch.append({
                "id":                   str(uuid.uuid4()),
                "tenant_id":            ONE8_TENANT_ID,
                "connector_id":         connector_id,
                "external_campaign_id": (
                    f"google_{campaign.replace(' ', '_')}_{d.strftime('%Y%m%d')}"
                ),
                "campaign_name":        campaign,
                "spend_date":           d,
                "currency":             "INR",
                "spend_amount":         float(google_spend / 3),
                "synced_at":            datetime.utcnow(),
                "created_at":           datetime.utcnow(),
                "updated_at":           datetime.utcnow(),
            })

        total_meta_spend   += meta_spend
        total_google_spend += google_spend
        total_orders       += total_daily
        total_revenue      += daily_revenue
        total_refunds      += daily_refunds

        if day_offset % 15 == 0 or day_offset <= 2:
            print(
                f"  {d} | ₹{meta_spend:>8,.0f} →{meta_paid:>5} |"
                f" ₹{google_spend:>9,.0f} →{google_paid:>5} |"
                f" {organic:>7} | {total_daily:>5} | ₹{daily_revenue:>11,.0f}"
            )

    print("  " + "-" * 74)
    print()

    # ── Step 4: insert — separate committed transactions per table ────────────
    # Using separate transactions (not one big engine.begin()) avoids proxy
    # connection timeouts on long-running inserts over the public Railway proxy.
    print("💾 Inserting...")

    CHUNK = 2_000  # rows per committed batch

    if meta_batch:
        print(f"   Meta ad spend:   {len(meta_batch):,} rows")
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO meta_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id,
                    campaign_name,
                    spend_date, currency, spend_amount,
                    synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id,
                    :campaign_name,
                    :spend_date, :currency, :spend_amount,
                    :synced_at, :created_at, :updated_at
                ) ON CONFLICT DO NOTHING
            """), meta_batch)

    if google_batch:
        print(f"   Google ad spend: {len(google_batch):,} rows")
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO google_ad_spends (
                    id, tenant_id, connector_id, external_campaign_id,
                    campaign_name,
                    spend_date, currency, spend_amount,
                    synced_at, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_campaign_id,
                    :campaign_name,
                    :spend_date, :currency, :spend_amount,
                    :synced_at, :created_at, :updated_at
                ) ON CONFLICT DO NOTHING
            """), google_batch)

    if orders_batch:
        print(f"   Orders:          {len(orders_batch):,} rows"
              f" (in {CHUNK}-row batches)")
        for i in range(0, len(orders_batch), CHUNK):
            chunk = orders_batch[i: i + CHUNK]
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO shopify_orders (
                        id, tenant_id, connector_id,
                        external_order_id, customer_id,
                        order_number, currency, total_amount,
                        discount_amount,
                        shipping_amount, refund_amount, is_refunded,
                        order_created_at, synced_at
                    ) VALUES (
                        :id, :tenant_id, :connector_id,
                        :external_order_id, :customer_id,
                        :order_number, :currency, :total_amount,
                        :discount_amount,
                        :shipping_amount, :refund_amount, :is_refunded,
                        :order_created_at, :synced_at
                    ) ON CONFLICT
                        (tenant_id, connector_id, external_order_id)
                    DO NOTHING
                """), chunk)
            end = min(i + CHUNK, len(orders_batch))
            print(f"     committed {end:,} / {len(orders_batch):,}")

    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE connector_integrations SET last_synced_at = :now WHERE id = :cid"
        ), {"cid": connector_id, "now": datetime.utcnow()})

    print("   ✅ Done\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_spend = total_meta_spend + total_google_spend
    print("=" * 70)
    print("✅ SEED COMPLETE")
    print("=" * 70)
    print(f"  Meta spend:     ₹{total_meta_spend:>14,.0f}")
    print(f"  Google spend:   ₹{total_google_spend:>14,.0f}")
    print(f"  Total spend:    ₹{total_spend:>14,.0f}")
    print(f"  Total orders:   {total_orders:>15,}")
    if total_orders:
        refund_pct = total_refunds / total_orders * 100
        print(f"  Refunded:       {total_refunds:>15,}  ({refund_pct:.1f}%)")
    print(f"  Net revenue:    ₹{total_revenue:>14,.0f}")
    if total_spend:
        print(f"  Blended ROAS:   {float(total_revenue) / total_spend:>18.2f}\u00d7")
    if total_orders:
        print(f"  Avg order val:  \u20b9{float(total_revenue) / total_orders:>14,.0f}")
        print(f"  Blended CAC:    \u20b9{total_spend / total_orders:>14,.0f}")
    print("=" * 70)
    print()
    print("Next: trigger the optimizer so it fits curves on this data")
    print(
        "  railway run --service AlpMarklabs"
        " python3 scripts/trigger_railway_optimization.py"
    )
    print("=" * 70)


if __name__ == "__main__":
    seed_realistic_data(days=120)
