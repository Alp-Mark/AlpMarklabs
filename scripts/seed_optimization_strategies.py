"""Seed default optimization strategies for the One8 demo tenant.

This creates 4 foundational optimization strategies across key business domains:
- Acquisition: Budget allocation optimizer
- Finance: Pricing optimization
- Retention: Campaign targeting optimizer
- Operations: Inventory reorder optimization

How to run
----------
Point ``DATABASE_URL`` at the target database and run from the repository root::

    DATABASE_URL="postgresql://user:pass@host:port/db" python scripts/seed_optimization_strategies.py

Or, with the Railway CLI::

    railway run python scripts/seed_optimization_strategies.py

Or for local development::

    python3 scripts/seed_optimization_strategies.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime

# Ensure the repository root is importable when run as a plain script
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Prefer public database URL for Railway compatibility
_public_db_url = os.getenv("DATABASE_PUBLIC_URL")
if _public_db_url:
    os.environ["DATABASE_URL"] = _public_db_url

from backend.app.db.models import OptimizationStrategy, Tenant  # noqa: E402
from backend.app.db.session import SessionLocal  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

# Tenant slug to look up (works in both local and production)
TENANT_SLUG = "one8"


def seed_optimization_strategies() -> None:
    """Create 4 default optimization strategies for One8 tenant."""
    db = SessionLocal()
    
    try:
        # Look up One8 tenant by slug
        tenant = db.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        if not tenant:
            print(f"❌ Tenant with slug '{TENANT_SLUG}' not found")
            print("   Available tenants:")
            for t in db.scalars(select(Tenant).order_by(Tenant.created_at)):
                print(f"   - {t.slug} (ID: {t.id})")
            return
        
        tenant_id = tenant.id
        print(f"✅ Found tenant: {tenant.name} (ID: {tenant_id})")
        
        # Delete existing optimization strategies for this tenant (idempotent)
        existing_count = db.scalar(
            select(func.count())
            .select_from(OptimizationStrategy)
            .where(OptimizationStrategy.tenant_id == tenant_id)
        )
        
        if existing_count and existing_count > 0:
            db.execute(
                delete(OptimizationStrategy).where(
                    OptimizationStrategy.tenant_id == tenant_id
                )
            )
            print(f"🗑️  Deleted {existing_count} existing optimization strategies for {tenant.name}")
        
        # Define 4 default strategies
        strategies = [
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                domain="acquisition",
                strategy_name="budget_allocation",
                strategy_type="hill_curve_saturation",
                is_enabled=False,  # Start disabled, will enable after testing
                config={
                    "description": "Optimize ad spend allocation across channels using Hill saturation curves",
                    "min_budget_per_channel": 1000.0,
                    "max_budget_shift_pct": 0.25,  # Don't shift more than 25% at once
                    "lookback_days": 90,
                    "confidence_threshold": 0.7,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                domain="finance",
                strategy_name="pricing_optimization",
                strategy_type="elasticity_model",
                is_enabled=False,
                config={
                    "description": "Optimize product pricing based on demand elasticity and margin targets",
                    "min_margin_pct": 0.30,  # Never go below 30% margin
                    "max_price_change_pct": 0.15,  # Max 15% price change per iteration
                    "elasticity_lookback_days": 60,
                    "confidence_threshold": 0.75,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                domain="retention",
                strategy_name="retention_campaign_targeting",
                strategy_type="propensity_scoring",
                is_enabled=False,
                config={
                    "description": "Optimize retention campaign targeting using churn propensity scores",
                    "target_segments": ["at_risk", "promising", "lapsed"],
                    "min_propensity_score": 0.6,
                    "max_campaign_frequency_days": 14,  # Don't spam customers
                    "lookback_days": 90,
                    "confidence_threshold": 0.7,
                },
            ),
            OptimizationStrategy(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                domain="operations",
                strategy_name="inventory_reorder_optimization",
                strategy_type="demand_forecasting",
                is_enabled=False,
                config={
                    "description": "Optimize inventory reorder points and quantities using demand forecasting",
                    "forecast_horizon_days": 30,
                    "safety_stock_multiplier": 1.5,  # 50% buffer above forecasted demand
                    "max_inventory_value_pct": 0.20,  # Cap at 20% of average monthly revenue
                    "min_turnover_ratio": 4.0,  # Prefer at least 4 turns per year
                    "confidence_threshold": 0.65,
                },
            ),
        ]
        
        # Insert all strategies
        db.add_all(strategies)
        db.commit()
        
        print(f"✅ Created {len(strategies)} optimization strategies for {tenant.name}:")
        for s in strategies:
            print(f"   • {s.domain:15} | {s.strategy_name:35} | {s.strategy_type}")
        
        # Verify count
        final_count = db.scalar(
            select(func.count())
            .select_from(OptimizationStrategy)
            .where(OptimizationStrategy.tenant_id == tenant_id)
        )
        print(f"\n📊 Verification: {final_count} strategies in database for {tenant.name}")
        
        if final_count != 4:
            print(f"⚠️  WARNING: Expected 4 strategies but found {final_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding optimization strategies: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding optimization strategies for One8 tenant...")
    seed_optimization_strategies()
    print("✨ Done!")
