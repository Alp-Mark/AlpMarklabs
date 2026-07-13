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
from typing import TypedDict

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
# Influencer: partnership cycles — 38-day cycle
_INFLUENCER_EPOCH = date(2026, 1, 5)
# Email/SMS: campaign waves — 28-day cycle (monthly cadence)
_EMAIL_EPOCH = date(2026, 1, 15)
# TV/Streaming: ad flight cycles — 50-day cycle (longer commitment periods)
_TV_EPOCH = date(2026, 1, 20)
# Affiliate: commission period cycles — 30-day cycle
_AFFILIATE_EPOCH = date(2026, 1, 8)

# ── Multi-Channel Configuration ────────────────────────────────────────────────
# Additional marketing channels beyond Meta/Google.
# When Klaviyo is integrated, email data will sync here with channel_name="email".


class ChannelConfig(TypedDict):
    """Type definition for multi-channel configuration."""
    base_spend: int
    base_cac: int
    cac_at_2x_pct: int
    campaigns: list[str]


class InfluencerProfile(TypedDict):
    """Individual influencer profile for granular tracking."""
    name: str
    handle: str
    tier: str  # "nano", "micro", "macro"
    niche: str
    followers: int
    monthly_fee: int  # Total fee for month-long campaign
    code: str  # Discount code
    cac: int  # Expected CAC


# ── Influencer Roster (10 real sports/fitness influencers) ─────────────────────
# Individual influencers hired by One8 for campaigns.
# Each gets unique discount code, tracked separately.
INFLUENCER_ROSTER: list[InfluencerProfile] = [
    # ── Nano influencers (1K-10K followers, ₹1-3K/post, 2-3 posts/month) ────
    {
        "name": "Priya Mehta",
        "handle": "@fitwithpriya",
        "tier": "nano",
        "niche": "fitness",
        "followers": 8500,
        "monthly_fee": 6000,  # ₹6K for 3 posts
        "code": "PRIYA10",
        "cac": 750,  # Low CAC (high engagement, niche audience)
    },
    {
        "name": "Arjun Desai",
        "handle": "@mumbai_runner",
        "tier": "nano",
        "niche": "running",
        "followers": 6200,
        "monthly_fee": 4500,  # ₹4.5K for 3 posts
        "code": "ARJUN15",
        "cac": 820,
    },
    {
        "name": "Neha Sharma",
        "handle": "@yogawithneha",
        "tier": "nano",
        "niche": "yoga",
        "followers": 9800,
        "monthly_fee": 7500,  # ₹7.5K for 3 posts
        "code": "NEHA10",
        "cac": 890,
    },
    # ── Micro influencers (10K-100K, ₹5-15K/post, 2 posts/month) ────────────
    {
        "name": "Rohan Kapoor",
        "handle": "@rohans_fitness",
        "tier": "micro",
        "niche": "gym/strength",
        "followers": 32000,
        "monthly_fee": 14000,  # ₹14K for 2 posts
        "code": "ROHAN15",
        "cac": 980,
    },
    {
        "name": "Anjali Rao",
        "handle": "@fitandfabulous_anj",
        "tier": "micro",
        "niche": "lifestyle fitness",
        "followers": 48000,
        "monthly_fee": 18000,  # ₹18K for 2 posts
        "code": "ANJALI20",
        "cac": 1050,
    },
    {
        "name": "Kabir Singh",
        "handle": "@cricket_coach_kabir",
        "tier": "micro",
        "niche": "cricket training",
        "followers": 55000,
        "monthly_fee": 20000,  # ₹20K for 2 posts
        "code": "KABIR15",
        "cac": 1120,
    },
    {
        "name": "Shreya Iyer",
        "handle": "@shreyasfitjourney",
        "tier": "micro",
        "niche": "weight loss",
        "followers": 68000,
        "monthly_fee": 24000,  # ₹24K for 2 posts
        "code": "SHREYA20",
        "cac": 1180,
    },
    # ── Macro influencers (100K-500K, ₹20-50K/post, 1-2 posts/month) ────────
    {
        "name": "Aditya Verma",
        "handle": "@aditya_athlete",
        "tier": "macro",
        "niche": "sports nutrition",
        "followers": 180000,
        "monthly_fee": 70000,  # ₹70K for 2 posts
        "code": "ADITYA15",
        "cac": 1650,  # Higher CAC (brand awareness, harder attribution)
    },
    {
        "name": "Meera Patel",
        "handle": "@meerasportsstyle",
        "tier": "macro",
        "niche": "athleisure/lifestyle",
        "followers": 240000,
        "monthly_fee": 80000,  # ₹80K for 2 posts
        "code": "MEERA20",
        "cac": 1780,
    },
    {
        "name": "Vikram Malhotra",
        "handle": "@vikrams_training",
        "tier": "macro",
        "niche": "personal training/HIIT",
        "followers": 320000,
        "monthly_fee": 100000,  # ₹1L for 2 posts
        "code": "VIKRAM15",
        "cac": 1920,  # Highest CAC (largest reach, lowest conversion rate)
    },
]


MULTI_CHANNELS: dict[str, ChannelConfig] = {
    "influencer": {
        "base_spend":   25_000,   # ₹25K/day avg across all 10 influencers
        "base_cac":     1_100,    # Blended CAC across nano/micro/macro
        "cac_at_2x_pct": 50,      # Saturates quickly (limited quality influencers)
        "campaigns": [inf["name"] for inf in INFLUENCER_ROSTER],  # Individual tracking
    },
    "email": {
        "base_spend":   15_000,   # ₹15K/day (Klaviyo fees + SMS)
        "base_cac":     380,      # Low CAC (owned audience)
        "cac_at_2x_pct": 20,      # Minimal saturation (list size is constraint)
        "campaigns": ["Win-Back", "Abandoned Cart", "Product Launch"],
    },
    "tv_streaming": {
        "base_spend":   50_000,   # ₹50K/day (Hotstar, Sony Liv during cricket)
        "base_cac":     1_500,    # High CAC (brand awareness play, hard to attribute)
        "cac_at_2x_pct": 65,      # Heavy saturation (frequency burnout)
        "campaigns": ["IPL Sponsorship", "World Cup Ads", "Brand Films"],
    },
    "affiliate": {
        "base_spend":   20_000,   # ₹20K/day (CashKaro, GoPaisa, etc.)
        "base_cac":     750,      # Mid CAC (performance-based)
        "cac_at_2x_pct": 35,      # Moderate saturation (finite affiliate reach)
        "campaigns": ["Cashback Networks", "Coupon Sites", "Rewards Programs"],
    },
}

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


def influencer_campaign_phase(d: date) -> float:
    """Influencer spend multiplier from partnership cycle (38-day period)."""
    phase = (d - _INFLUENCER_EPOCH).days % 38
    if 5 <= phase <= 18:
        return 1.7   # 2-week collab push
    if phase <= 25:
        return 1.2   # wind-down
    return 0.95


def email_campaign_phase(d: date) -> float:
    """Email/SMS spend multiplier from campaign wave cycle (28-day period)."""
    phase = (d - _EMAIL_EPOCH).days % 28
    if 8 <= phase <= 12:
        return 1.5   # 5-day big push (product launch, sale)
    if phase <= 18:
        return 1.15  # wind-down
    return 0.90


def tv_campaign_phase(d: date) -> float:
    """TV/Streaming spend multiplier from ad flight cycle (50-day period)."""
    phase = (d - _TV_EPOCH).days % 50
    if 10 <= phase <= 30:
        return 1.8   # 3-week heavy flight
    if phase <= 40:
        return 1.1   # wind-down
    return 0.70  # dark period (no TV)


def affiliate_campaign_phase(d: date) -> float:
    """Affiliate spend multiplier from commission period cycle (30-day period)."""
    phase = (d - _AFFILIATE_EPOCH).days % 30
    if 12 <= phase <= 20:
        return 1.6   # 9-day bonus commission period
    if phase <= 25:
        return 1.2   # wind-down
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


def get_channel_spend(
    channel_name: str,
    d: date,
    growth_start: date,
    growth_days: int,
) -> int:
    """Generic spend generator for any multi-channel (influencer, email, TV, affiliate)."""
    config = MULTI_CHANNELS[channel_name]
    days_elapsed = max(0, (d - growth_start).days)
    growth = 1.0 + min(1.0, days_elapsed / growth_days) * 0.10
    
    # Channel-specific phase function
    phase_funcs = {
        "influencer": influencer_campaign_phase,
        "email": email_campaign_phase,
        "tv_streaming": tv_campaign_phase,
        "affiliate": affiliate_campaign_phase,
    }
    phase = phase_funcs[channel_name](d)
    
    variance = random.uniform(0.85, 1.15)
    
    # Email/affiliate run 7 days; TV has dark periods; influencer has weekend lift
    if channel_name == "influencer":
        weekend_mult = 1.15 if d.weekday() in (5, 6) else 1.0
    elif channel_name == "tv_streaming":
        weekend_mult = 0.80 if d.weekday() in (5, 6) else 1.0  # TV ads cheaper on weekends
    else:
        weekend_mult = 1.0
    
    return max(
        0,
        int(config["base_spend"] * growth * phase * variance * weekend_mult),
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


def get_channel_conversions(channel_name: str, channel_spend: int) -> int:
    """Generic conversions calculator for any multi-channel."""
    config = MULTI_CHANNELS[channel_name]
    return _paid_conversions(
        channel_spend,
        config["base_spend"],
        config["base_cac"],
        config["cac_at_2x_pct"],
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

    engine = create_engine(
        db_url,
        pool_pre_ping=True,    # reconnect between batches if proxy dropped
        pool_recycle=30,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,          # enable TCP keepalives
            "keepalives_idle": 10,    # first keepalive after 10 s idle
            "keepalives_interval": 5, # retry every 5 s
            "keepalives_count": 5,    # give up after 5 failed probes
        },
    )

    print("=" * 70)
    print("🏏  One8 (Virat Kohli Brand) — data-first seed")
    print("=" * 70)
    print(f"Tenant : {ONE8_TENANT_ID}")
    print(f"Days   : {days}")
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
        "meta_ad_spends", "google_ad_spends", "marketing_channel_spends",
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
    # Generate through yesterday only — today is the daily simulator's job.
    # end_dt is "yesterday 23:59" so the seed never partially-covers today.
    end_dt       = datetime.now() - timedelta(days=1)
    end_dt       = end_dt.replace(hour=23, minute=59, second=59)
    growth_start = (end_dt - timedelta(days=days - 1)).date()
    print(
        f"Range  : "
        f"{end_dt.date() - timedelta(days=days - 1)} \u2192 {end_dt.date()} (yesterday)"
    )
    print()

    meta_batch:   list[dict] = []
    google_batch: list[dict] = []
    multi_channel_batch: list[dict] = []  # For influencer, email, TV, affiliate
    orders_batch: list[dict] = []

    total_meta_spend   = 0
    total_google_spend = 0
    total_multi_channel_spend = {ch: 0.0 for ch in MULTI_CHANNELS.keys()}
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

        # ── Multi-Channel ad spend (influencer, email, TV, affiliate) ─────────
        for channel_name, config in MULTI_CHANNELS.items():
            
            # ── Special handling for influencer channel (individual tracking) ─
            if channel_name == "influencer":
                # Each influencer is a separate campaign with monthly fees
                # Not all influencers active every month (realistic scheduling)
                month_str = d.strftime("%Y%m")  # e.g., "202605" for May 2026
                
                for influencer in INFLUENCER_ROSTER:
                    # Influencer activity: 60% chance active in any given month
                    # Use deterministic hash so same influencer always active/inactive same month
                    is_active_this_month = hash(f"{influencer['name']}_{month_str}") % 10 < 6
                    
                    if not is_active_this_month:
                        continue
                    
                    # Monthly fee amortized across ~30 days
                    # Campaign "launches" on day 1-5 of month (most spend on launch day)
                    day_of_month = d.day
                    if day_of_month <= 5:
                        # Launch day: 40% of monthly fee
                        daily_spend = influencer["monthly_fee"] * 0.4
                    elif day_of_month <= 15:
                        # Mid-campaign: 30% spread across 10 days
                        daily_spend = influencer["monthly_fee"] * 0.3 / 10
                    elif day_of_month <= 25:
                        # Wind-down: 20% spread across 10 days
                        daily_spend = influencer["monthly_fee"] * 0.2 / 10
                    else:
                        # Tail: 10% spread across end of month
                        daily_spend = influencer["monthly_fee"] * 0.1 / 5
                    
                    # Conversions based on individual CAC (not generic channel CAC)
                    daily_conversions = max(0, int(daily_spend / influencer["cac"]))
                    
                    # Revenue: conversions × AOV (use seasonal AOV)
                    daily_revenue_est = daily_conversions * get_seasonal_aov(current_dt)
                    
                    multi_channel_batch.append({
                        "id":                   str(uuid.uuid4()),
                        "tenant_id":            ONE8_TENANT_ID,
                        "connector_id":         connector_id,
                        "channel_name":         "influencer",
                        "external_campaign_id": (
                            f"influencer_{influencer['handle'].replace('@', '')}_{month_str}"
                        ),
                        "campaign_name":        f"{influencer['name']} ({influencer['niche'].title()})",
                        "spend_date":           d,
                        "currency":             "INR",
                        "spend_amount":         float(daily_spend),
                        "conversions":          daily_conversions,
                        "revenue":              float(daily_revenue_est),
                        "impressions":          None,  # Not tracked for influencers
                        "clicks":               None,  # Not tracked for influencers
                        "synced_at":            datetime.utcnow(),
                        "created_at":           datetime.utcnow(),
                        "updated_at":           datetime.utcnow(),
                    })
                    
                    total_multi_channel_spend["influencer"] += daily_spend
            
            # ── Other channels (email, TV, affiliate): generic campaign logic ─
            else:
                channel_spend = get_channel_spend(channel_name, d, growth_start, days)
                channel_conv = get_channel_conversions(channel_name, channel_spend)
                
                num_campaigns = len(config["campaigns"])
                for campaign in config["campaigns"]:
                    multi_channel_batch.append({
                        "id":                   str(uuid.uuid4()),
                        "tenant_id":            ONE8_TENANT_ID,
                        "connector_id":         connector_id,
                        "channel_name":         channel_name,
                        "external_campaign_id": (
                            f"{channel_name}_{campaign.replace(' ', '_')}_{d.strftime('%Y%m%d')}"
                        ),
                        "campaign_name":        campaign,
                        "spend_date":           d,
                        "currency":             "INR",
                        "spend_amount":         float(channel_spend / num_campaigns),
                        "conversions":          int(channel_conv / num_campaigns),
                        "revenue":              None,  # Will be attributed via orders table
                        "impressions":          None,
                        "clicks":               None,
                        "synced_at":            datetime.utcnow(),
                        "created_at":           datetime.utcnow(),
                        "updated_at":           datetime.utcnow(),
                    })
                
                total_multi_channel_spend[channel_name] += channel_spend

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

    CHUNK = 100  # rows per committed batch — Railway proxy is very slow

    if meta_batch:
        print(f"   Meta ad spend:   {len(meta_batch):,} rows (in {CHUNK}-row batches)")
        for i in range(0, len(meta_batch), CHUNK):
            chunk = meta_batch[i: i + CHUNK]
            for attempt in range(3):
                try:
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
                        """), chunk)
                    break  # success
                except Exception as exc:
                    if attempt == 2:
                        raise
                    print(f"     ⚠️  batch {i}–{i+CHUNK} attempt {attempt+1} failed, retrying…")
                    import time
                    time.sleep(2)

    if google_batch:
        print(f"   Google ad spend: {len(google_batch):,} rows (in {CHUNK}-row batches)")
        for i in range(0, len(google_batch), CHUNK):
            chunk = google_batch[i: i + CHUNK]
            for attempt in range(3):
                try:
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
                    break  # success
                except Exception as exc:
                    if attempt == 2:
                        raise
                    print(f"     ⚠️  batch {i}–{i+CHUNK} attempt {attempt+1} failed, retrying…")
                    import time
                    time.sleep(2)

    if multi_channel_batch:
        print(f"   Multi-channel:   {len(multi_channel_batch):,} rows "
              f"(in {CHUNK}-row batches)")
        for i in range(0, len(multi_channel_batch), CHUNK):
            chunk = multi_channel_batch[i: i + CHUNK]
            for attempt in range(3):
                try:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO marketing_channel_spends (
                                id, tenant_id, connector_id, channel_name,
                                external_campaign_id, campaign_name,
                                spend_date, currency, spend_amount,
                                conversions, revenue, impressions, clicks,
                                synced_at, created_at, updated_at
                            ) VALUES (
                                :id, :tenant_id, :connector_id, :channel_name,
                                :external_campaign_id, :campaign_name,
                                :spend_date, :currency, :spend_amount,
                                :conversions, :revenue, :impressions, :clicks,
                                :synced_at, :created_at, :updated_at
                            ) ON CONFLICT DO NOTHING
                        """), chunk)
                    break  # success
                except Exception as exc:
                    if attempt == 2:
                        raise
                    print(f"     ⚠️  batch {i}–{i+CHUNK} attempt {attempt+1} failed, retrying…")
                    import time
                    time.sleep(2)
            end = min(i + CHUNK, len(multi_channel_batch))
            print(f"     committed {end:,} / {len(multi_channel_batch):,}")

    if orders_batch:
        print(f"   Orders:          {len(orders_batch):,} rows"
              f" (in {CHUNK}-row batches)")
        for i in range(0, len(orders_batch), CHUNK):
            chunk = orders_batch[i: i + CHUNK]
            for attempt in range(3):
                try:
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
                    break  # success
                except Exception as exc:
                    if attempt == 2:
                        raise
                    print(f"     ⚠️  batch {i}–{i+CHUNK} attempt {attempt+1} failed, retrying…")
                    import time
                    time.sleep(2)
            end = min(i + CHUNK, len(orders_batch))
            print(f"     committed {end:,} / {len(orders_batch):,}")

    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE connector_integrations SET last_synced_at = :now WHERE id = :cid"
        ), {"cid": connector_id, "now": datetime.utcnow()})

    # ── Step 5: cost inputs (realistic One8 sportswear economics) ─────────────
    # These drive Contribution Margin and CAC Payback on the dashboard.
    # Source: premium Indian D2C sportswear benchmarks (PUMA collab tier).
    print("💰 Seeding cost inputs...")
    cost_rows = [
        {
            "id":            str(uuid.uuid4()),
            "tenant_id":     ONE8_TENANT_ID,
            "input_type":    "cogs",
            "tier_label":    "Product cost — apparel & accessories (35% of revenue)",
            "amount":        35.0,
            "unit":          "pct_of_revenue",
            "is_active":     True,
            "effective_date": date(2026, 1, 1),
        },
        {
            "id":            str(uuid.uuid4()),
            "tenant_id":     ONE8_TENANT_ID,
            "input_type":    "shipping",
            "tier_label":    "Domestic fulfillment — Delhivery/Shiprocket flat rate",
            "amount":        150.0,
            "unit":          "per_order",
            "is_active":     True,
            "effective_date": date(2026, 1, 1),
        },
        {
            "id":            str(uuid.uuid4()),
            "tenant_id":     ONE8_TENANT_ID,
            "input_type":    "return_processing",
            "tier_label":    "Reverse logistics + QC + restocking per return",
            "amount":        120.0,
            "unit":          "per_order",
            "is_active":     True,
            "effective_date": date(2026, 1, 1),
        },
        {
            "id":            str(uuid.uuid4()),
            "tenant_id":     ONE8_TENANT_ID,
            "input_type":    "ad_spend_vat",
            "tier_label":    "GST on digital advertising (India statutory 18%)",
            "amount":        18.0,
            "unit":          "pct_of_spend",
            "is_active":     True,
            "effective_date": date(2026, 1, 1),
        },
    ]
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM cost_inputs WHERE tenant_id = :tid
        """), {"tid": ONE8_TENANT_ID})
        conn.execute(text("""
            INSERT INTO cost_inputs (
                id, tenant_id, input_type, tier_label,
                amount, unit, is_active, effective_date
            ) VALUES (
                :id, :tenant_id, :input_type, :tier_label,
                :amount, :unit, :is_active, :effective_date
            )
        """), cost_rows)
    print("   ✅ 4 cost input rows seeded\n")

    # ── Step 6: inventory items + order line items (One8 × Agilitas Sports) ───
    # Real product catalog scraped from one8.com: 187 products / 1,075 variants.
    # COGS% per category = Agilitas Sports domestic manufacturing benchmarks
    # (no import duty — all made in India).
    print("📦 Seeding One8 × Agilitas product catalog (real SKUs from one8.com)...")

    import json
    from pathlib import Path as _Path

    products_file = _Path(__file__).parent.parent / "data" / "one8_products.json"
    with open(products_file) as _f:
        _catalog_data = json.load(_f)

    # COGS% by Shopify product_type (Agilitas domestic manufacturing)
    COGS_PCT: dict[str, float] = {
        "T-Shirt":       28.0,
        "Polo":          30.0,
        "Tank Top":      28.0,
        "Shorts":        30.0,
        "Leggings":      30.0,
        "Sweatshirt":    32.0,
        "Pants":         32.0,
        "Jacket":        34.0,
        "Caps":          26.0,
        "Sneakers":      36.0,
        "Cricket Shoes": 36.0,
    }
    DEFAULT_COGS_PCT = 32.0

    # Build variant list: (sku, product_title, variant_title, price, cost, stock)
    CATALOG: list[tuple[str, str, str, int, int, int]] = []
    for prod in _catalog_data["products"]:
        ptype = prod.get("product_type", "")
        cogs_pct = COGS_PCT.get(ptype, DEFAULT_COGS_PCT)
        title = prod["title"]
        for v in prod["variants"]:
            price = int(v["price"]) if v.get("price") else 0
            if price == 0:
                continue
            cost = max(1, int(price * cogs_pct / 100))
            sku = v.get("sku") or f"ONE8-{v['variant_id']}"
            variant_title = v.get("title", "")
            stock = max(0, v.get("inventory_quantity") or 0)
            CATALOG.append((sku, title, variant_title, price, cost, stock))

    print(f"   {len(CATALOG)} variants loaded")

    # Seed inventory items
    inv_rows = []
    for sku, title, variant, _price, cost, stock in CATALOG:
        inv_rows.append({
            "id":                         str(uuid.uuid4()),
            "tenant_id":                  ONE8_TENANT_ID,
            "connector_id":               connector_id,
            "external_inventory_item_id": f"one8_{sku}",
            "sku":                        sku,
            "product_title":              title,
            "variant_title":              variant,
            "available_quantity":         stock,
            "cost_per_unit":              float(cost),
            "synced_at":                  datetime.utcnow(),
        })

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM shopify_inventory_items WHERE tenant_id = :tid"
        ), {"tid": ONE8_TENANT_ID})
        # Batch insert in chunks of 200
        for i in range(0, len(inv_rows), 200):
            conn.execute(text("""
                INSERT INTO shopify_inventory_items (
                    id, tenant_id, connector_id, external_inventory_item_id,
                    sku, product_title, variant_title, available_quantity,
                    cost_per_unit, synced_at
                ) VALUES (
                    :id, :tenant_id, :connector_id, :external_inventory_item_id,
                    :sku, :product_title, :variant_title, :available_quantity,
                    :cost_per_unit, :synced_at
                ) ON CONFLICT DO NOTHING
            """), inv_rows[i: i + 200])
    print(f"   ✅ {len(CATALOG)} SKUs seeded")

    # Assign line items to all orders
    # Bucket variants by price tier for realistic order composition.
    print("   Creating line items (streaming batches)...")

    tier_low    = [c for c in CATALOG if c[3] <= 2_500]
    tier_mid    = [c for c in CATALOG if 2_501 <= c[3] <= 5_500]
    tier_high   = [c for c in CATALOG if c[3] > 5_500]
    accessories = [c for c in CATALOG if c[3] <= 2_000]

    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM shopify_order_line_items WHERE tenant_id = :tid"
        ), {"tid": ONE8_TENANT_ID})

    line_items_batch: list[dict] = []
    total_li = 0
    orders_processed = 0

    # Stream-process orders in batches of 1000 to avoid loading all 58K into memory
    offset = 0
    while True:
        with engine.connect() as conn:
            order_rows = conn.execute(text(
                "SELECT id, total_amount, order_created_at "
                "FROM shopify_orders WHERE tenant_id = :tid "
                "ORDER BY order_created_at LIMIT 1000 OFFSET :offset"
            ), {"tid": ONE8_TENANT_ID, "offset": offset}).fetchall()
        
        if not order_rows:
            break
        
        for row in order_rows:
            order_id, order_total, order_created_at = row[0], row[1], row[2]
            
            if order_total <= 2_800:
                pool = tier_low or tier_mid
            elif order_total <= 6_000:
                pool = tier_mid or tier_high
            else:
                pool = tier_high or tier_mid

            primary = random.choice(pool)
            items_for_order: list[tuple[tuple[str, str, str, int, int, int], int]] = [
                (primary, 1)
            ]
            if random.random() < 0.35 and accessories:
                acc = random.choice(accessories)
                if acc[0] != primary[0]:
                    items_for_order.append((acc, 1))

            for idx, (cat_row, qty) in enumerate(items_for_order):
                sku, title, variant, sell_price, _cost, _stock = cat_row
                line_items_batch.append({
                    "id":               str(uuid.uuid4()),
                    "tenant_id":        ONE8_TENANT_ID,
                    "order_id":         order_id,
                    "line_item_index":  idx,
                    "sku":              sku,
                    "product_title":    title,
                    "variant_title":    variant,
                    "quantity":         qty,
                    "unit_price":       float(sell_price),
                    "order_created_at": order_created_at,
                })
                total_li += 1

            orders_processed += 1
            
            if len(line_items_batch) >= 100:  # Smaller batch for Railway proxy
                for attempt in range(3):
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO shopify_order_line_items (
                                    id, tenant_id, order_id, line_item_index,
                                    sku, product_title, variant_title,
                                    quantity, unit_price, order_created_at
                                ) VALUES (
                                    :id, :tenant_id, :order_id, :line_item_index,
                                    :sku, :product_title, :variant_title,
                                    :quantity, :unit_price, :order_created_at
                                ) ON CONFLICT DO NOTHING
                            """), line_items_batch)
                        break  # success
                    except Exception as exc:
                        if attempt == 2:
                            raise
                        print(f"     ⚠️  line items batch attempt {attempt+1} failed, retrying…")
                        import time
                        time.sleep(2)
                print(f"     {orders_processed:,} orders → {total_li:,} line items")
                line_items_batch = []
        
        offset += 1000

    if line_items_batch:
        for attempt in range(3):
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO shopify_order_line_items (
                            id, tenant_id, order_id, line_item_index,
                            sku, product_title, variant_title,
                            quantity, unit_price, order_created_at
                        ) VALUES (
                            :id, :tenant_id, :order_id, :line_item_index,
                            :sku, :product_title, :variant_title,
                            :quantity, :unit_price, :order_created_at
                        ) ON CONFLICT DO NOTHING
                    """), line_items_batch)
                break  # success
            except Exception as exc:
                if attempt == 2:
                    raise
                print(f"     ⚠️  final line items batch attempt {attempt+1} failed, retrying…")
                import time
                time.sleep(2)

    avg_li = total_li / orders_processed if orders_processed else 0
    print(f"   ✅ {total_li:,} line items created ({avg_li:.1f} avg/order)\n")

    print("   ✅ Done\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_spend = total_meta_spend + total_google_spend + sum(total_multi_channel_spend.values())
    print("=" * 70)
    print("✅ SEED COMPLETE")
    print("=" * 70)
    print(f"  Meta spend:        ₹{total_meta_spend:>14,.0f}")
    print(f"  Google spend:      ₹{total_google_spend:>14,.0f}")
    for channel_name, channel_total in total_multi_channel_spend.items():
        label = f"  {channel_name.replace('_', ' ').title()} spend:"
        print(f"{label:22} ₹{channel_total:>14,.0f}")
    print(f"  Total spend:       ₹{total_spend:>14,.0f}")
    print(f"  Total orders:      {total_orders:>15,}")
    if total_orders:
        refund_pct = total_refunds / total_orders * 100
        print(f"  Refunded:          {total_refunds:>15,}  ({refund_pct:.1f}%)")
    print(f"  Net revenue:       ₹{total_revenue:>14,.0f}")
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
