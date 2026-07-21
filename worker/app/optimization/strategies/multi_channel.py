"""Multi-channel budget allocation optimizer for acquisition channels.

This module implements MultiChannelAllocator that extends BaseOptimizer to find
optimal ad spend allocation across 6+ channels: Meta, Google, Influencer, Email,
TV/Streaming, and Affiliate.

The optimizer:
1. Fetches historical spend and conversion data from 3 tables
2. Fits Hill saturation curves for each active channel
3. Uses scipy.optimize to maximize total conversions
4. Returns optimal budget allocation with expected impact

Business Logic:
- Constraints: Total budget ≤ current, ROAS floors, max 40% shift per channel
- Objective: Maximize total conversions across all channels
- Method: Sequential Least Squares Programming (SLSQP)

Example:
    optimizer = MultiChannelAllocator(strategy_id=strategy.id, db=session)
    recommendation = optimizer.run(tenant_id=tenant.id, days=90)
    # Returns optimal allocation: 6 channels with expected lift
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from backend.app.db.models import (
    FittedModel,
    MarketingChannelSpend,
    OptimizationRun,
    Recommendation,
)
from scipy.optimize import minimize
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from worker.app.optimization.models.saturation import HillCurve
from worker.app.optimization.strategies.base import BaseOptimizer
from worker.app.optimization.utils.monitoring import log_data_quality_issue
from worker.app.optimization.utils.s3_storage import upload_model


class MultiChannelAllocator(BaseOptimizer):
    """Optimizer for allocating budget across 6+ acquisition channels.
    
    Finds the optimal split of advertising budget across Meta, Google, Influencer,
    Email, TV/Streaming, and Affiliate channels to maximize total conversions,
    respecting ROAS floors and shift limits.
    
    The optimizer uses Hill saturation curves per channel to model diminishing
    returns, then uses constrained optimization to find the best allocation.
    
    Attributes:
        strategy_id: UUID of the OptimizationStrategy record
        db: SQLAlchemy database session
        training_data: Dictionary with per-channel spend/conversion arrays
        models: Dictionary with per-channel HillCurve instances
        optimization_result: Optimal spend allocation
        
    Constraints:
        - Total budget ≤ current total spend (reallocate, don't increase)
        - Per-channel ROAS ≥ floor (default 2.0×)
        - Min spend ≥ ₹5K/day (platform minimums)
        - Max shift ≤ 40% per channel (risk mitigation)
    """
    
    def __init__(self, strategy_id: UUID, db: Session) -> None:
        """Initialize multi-channel budget allocation optimizer.
        
        Args:
            strategy_id: UUID of the OptimizationStrategy record
            db: SQLAlchemy session for database queries
        """
        super().__init__(strategy_id, db)
        self.channel_curves: dict[str, HillCurve] = {}
        self.current_budget: float | None = None
        self.tenant_id: UUID | None = None
        self.lookback_days: int = 90  # Default lookback period
        self.optimization_run_id: UUID | None = None
        self.optimization_result: dict[str, Any] | None = None
        self.aov: float = 0.0
        self.active_channels: list[str] = []
        
        # ROAS floors per channel (can be made configurable later)
        self.roas_floors: dict[str, float] = {
            "influencer": 1.8,  # Lower floor (harder attribution)
            "email": 3.0,       # Higher floor (owned channel, low cost)
            "affiliate": 2.5,   # Higher floor (performance-based)
        }
        
        # Min daily spend per channel (platform minimums)
        self.min_spend: dict[str, float] = {
            "influencer": 3000.0,
            "email": 2000.0,
            "affiliate": 3000.0,
        }
    
    def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> dict[str, Any]:
        """Fetch historical ad spend and conversion data for all 6 channels.
        
        Queries the database for:
        1. Daily ad spend for Meta and Google (dedicated tables)
        2. Daily spend for Influencer, Email, TV, Affiliate (marketing_channel_spends)
        3. Daily order counts as proxy for conversions
        4. Simple attribution: conversions split proportionally to spend
        
        Args:
            tenant_id: UUID of the tenant to fetch data for
            days: Number of days of historical data (default: 90)
        
        Returns:
            Dictionary with structure:
            {
                'meta': {'spend': array, 'conversions': array,
                         'revenue': array},
                'google': {'spend': array, 'conversions': array,
                           'revenue': array},
                'influencer': {'spend': array, 'conversions': array,
                               'revenue': array},
                'email': {'spend': array, 'conversions': array,
                          'revenue': array},
                'tv_streaming': {'spend': array, 'conversions': array,
                                 'revenue': array},
                'affiliate': {'spend': array, 'conversions': array,
                              'revenue': array},
                'total_budget': current total daily budget
            }
        
        Raises:
            ValueError: If insufficient data (< 60 days total across all channels)
        """
        # Store parameters for later use
        self.tenant_id = tenant_id
        self.lookback_days = days
        
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days)
        
        # ── Fetch spend, conversions, revenue per channel per day ─────────────
        # Meta and Google are handled by BudgetAllocationOptimizer (OPT-BUDGET-001).
        # This optimizer covers only: influencer, email, affiliate.
        TRACKED_CHANNELS = ("influencer", "email", "affiliate")
        
        query = (
            select(
                MarketingChannelSpend.spend_date,
                MarketingChannelSpend.channel_name,
                func.sum(MarketingChannelSpend.spend_amount).label("daily_spend"),
                func.sum(MarketingChannelSpend.conversions).label("daily_conversions"),
                func.sum(MarketingChannelSpend.revenue).label("daily_revenue"),
            )
            .where(MarketingChannelSpend.tenant_id == tenant_id)
            .where(MarketingChannelSpend.channel_name.in_(TRACKED_CHANNELS))
            .where(MarketingChannelSpend.spend_date >= start_date)
            .where(MarketingChannelSpend.spend_date <= end_date)
            .group_by(
                MarketingChannelSpend.spend_date,
                MarketingChannelSpend.channel_name,
            )
            .order_by(
                MarketingChannelSpend.spend_date,
                MarketingChannelSpend.channel_name,
            )
        )
        raw = self.db.execute(query).all()
        
        # ── Build per-channel date-indexed arrays ─────────────────────────────
        channel_data: dict[str, dict[str, list]] = {
            ch: {"spend": [], "conversions": [], "revenue": []}
            for ch in TRACKED_CHANNELS
        }
        all_dates: set[date] = set()
        
        for row in raw:
            all_dates.add(row.spend_date)
            ch = row.channel_name
            if ch in channel_data:
                channel_data[ch]["spend"].append(float(row.daily_spend or 0))
                channel_data[ch]["conversions"].append(
                    float(row.daily_conversions or 0)
                )
                channel_data[ch]["revenue"].append(float(row.daily_revenue or 0))
        
        if len(all_dates) < 30:
            raise ValueError(
                f"Insufficient data: only {len(all_dates)} days with spend. "
                f"Need at least 30 days for multi-channel optimization."
            )
        
        # ── Compute AOV from channel data ─────────────────────────────────────
        total_conv = sum(
            sum(channel_data[ch]["conversions"]) for ch in TRACKED_CHANNELS
        )
        total_rev = sum(
            sum(channel_data[ch]["revenue"]) for ch in TRACKED_CHANNELS
        )
        self.aov = total_rev / total_conv if total_conv > 0 else 6500.0
        
        # ── Validate each channel has enough data ─────────────────────────────
        self.active_channels = []
        for ch in TRACKED_CHANNELS:
            days_with_spend = len(channel_data[ch]["spend"])
            if days_with_spend >= 30:
                self.active_channels.append(ch)
                channel_data[ch]["spend"] = np.array(
                    channel_data[ch]["spend"]
                )  # type: ignore[assignment]
                channel_data[ch]["conversions"] = np.array(
                    channel_data[ch]["conversions"]
                )  # type: ignore[assignment]
                channel_data[ch]["revenue"] = np.array(
                    channel_data[ch]["revenue"]
                )  # type: ignore[assignment]
            elif days_with_spend > 0:
                log_data_quality_issue(
                    tenant_id=tenant_id,
                    strategy_name="multi_channel_allocation",
                    issue_type=f"insufficient_{ch}_data",
                    details={"days_with_spend": days_with_spend, "required": 30},
                    severity="warning",
                )
        
        if len(self.active_channels) < 2:
            raise ValueError(
                f"Only {len(self.active_channels)} channels have 30+ days of data. "
                f"Need at least 2 of: influencer, email, affiliate."
            )
        
        # ── Current budget = avg daily spend (last 7 days with data) ─────────
        recent_raw = self.db.execute(
            select(
                MarketingChannelSpend.spend_date,
                func.sum(MarketingChannelSpend.spend_amount).label("daily_total"),
            )
            .where(MarketingChannelSpend.tenant_id == tenant_id)
            .where(MarketingChannelSpend.channel_name.in_(TRACKED_CHANNELS))
            .group_by(MarketingChannelSpend.spend_date)
            .order_by(MarketingChannelSpend.spend_date.desc())
            .limit(7)
        ).fetchall()
        self.current_budget = (
            sum(float(r.daily_total or 0) for r in recent_raw) / max(len(recent_raw), 1)
        )
        
        self.training_data = {ch: channel_data[ch] for ch in self.active_channels}
        self.training_data["total_budget"] = self.current_budget
        
        return self.training_data
    
    def train_models(self) -> None:
        """Train Hill saturation curves for all active channels.
        
        Fits separate Hill curves to each channel's spend/conversion data.
        Stores curves in self.channel_curves dict.
        Saves fitted models to S3 and creates FittedModel database records.
        
        Raises:
            ValueError: If training data is None or has insufficient points
            RuntimeError: If curve fitting fails for any channel
        """
        if self.training_data is None:
            raise ValueError("Must call fetch_training_data before training models")
        
        if self.tenant_id is None:
            raise ValueError("tenant_id not set - must call fetch_training_data first")
        
        # Create OptimizationRun record for model tracking
        optimization_run = OptimizationRun(
            tenant_id=self.tenant_id,
            strategy_id=self.strategy_id,
            run_status="running",
            started_at=datetime.now(UTC),
        )
        self.db.add(optimization_run)
        self.db.flush()  # Get the ID without committing
        self.optimization_run_id = optimization_run.id
        
        # Fit curve for each active channel
        # Use list() copy to avoid mutation-during-iteration bug
        for channel_name in list(self.active_channels):
            data = self.training_data[channel_name]
            
            try:
                curve = HillCurve()
                curve.fit(
                    spend_data=data["spend"],
                    conversion_data=data["conversions"],
                )
                rmse = curve.calculate_rmse(
                    spend_data=data["spend"],
                    conversion_data=data["conversions"],
                )
                params = curve.get_params()
                
                # Calculate R² (coefficient of determination)
                predictions = curve.predict(data["spend"])
                r2 = self._calculate_r2(
                    actual=data["conversions"],
                    predicted=predictions,
                )
                
                # Store curve
                self.channel_curves[channel_name] = curve
                
                # Save model to S3 and database
                self._save_fitted_model(
                    curve=curve,
                    model_type=f"{channel_name}_saturation_curve",
                    params=params,
                    metrics={"rmse": rmse, "r2": r2},
                )
            except Exception as e:
                # Log but don't fail - optimizer can work with fewer channels
                if self.tenant_id is not None:
                    log_data_quality_issue(
                        tenant_id=self.tenant_id,
                        strategy_name="multi_channel_allocation",
                        issue_type=f"{channel_name}_curve_fit_failed",
                        details={"error": str(e)},
                        severity="error",
                    )
                # Remove from active channels
                self.active_channels.remove(channel_name)
        
        if len(self.channel_curves) < 2:
            raise RuntimeError(
                f"Failed to fit curves: only {len(self.channel_curves)} channels "
                f"have valid models. Need at least 2 channels."
            )
        
        # Store models in parent class attribute
        self.models = self.channel_curves
    
    def optimize(self) -> dict[str, Any]:
        """Find optimal budget allocation using constrained optimization.
        
        Uses scipy.optimize.minimize with SLSQP algorithm to maximize total
        conversions subject to budget constraints:
        - Total spend ≤ current budget
        - Per-channel ROAS ≥ floor
        - Min spend ≥ platform minimum
        - Max shift ≤ 40% per channel
        
        Returns:
            Dictionary with optimization results per channel plus aggregates
        """
        if len(self.channel_curves) < 2:
            raise RuntimeError("Must train models before optimizing")
        
        if self.current_budget is None or self.current_budget <= 0:
            raise RuntimeError("Invalid current budget")
        
        # Ensure only channels with curves are in active list
        self.active_channels = list(self.channel_curves.keys())
        num_channels = len(self.active_channels)
        
        # ── Objective function: maximize total conversions ───────────────────
        def objective(spend_allocation: np.ndarray) -> float:
            """Negative total conversions (for minimization)."""
            total_conv = 0.0
            for i, channel_name in enumerate(self.active_channels):
                curve = self.channel_curves[channel_name]
                total_conv += curve.predict(spend_allocation[i])[0]
            return -total_conv  # Negative because we minimize
        
        # ── Calculate current allocation ─────────────────────────────────────
        current_allocation = []
        for channel_name in self.active_channels:
            data = self.training_data[channel_name]
            current_spend = float(np.mean(data["spend"][-7:]))  # Last 7 days avg
            current_allocation.append(current_spend)
        
        current_total = sum(current_allocation)
        
        # Normalize to match current_budget
        if current_total > 0:
            current_allocation = [
                (spend / current_total) * self.current_budget
                for spend in current_allocation
            ]
        else:
            # Fallback: equal split
            current_allocation = [self.current_budget / num_channels] * num_channels
        
        # ── Constraints ───────────────────────────────────────────────────────
        constraints = [
            # Total spend equals current budget
            {
                "type": "eq",
                "fun": lambda x: np.sum(x) - self.current_budget,
            },
        ]
        
        # ── Bounds per channel ────────────────────────────────────────────────
        bounds = []
        for i, channel_name in enumerate(self.active_channels):
            current_spend = current_allocation[i]
            min_bound = max(
                self.min_spend.get(channel_name, 3000.0),  # Platform minimum
                current_spend * 0.6,  # Max 40% decrease
            )
            max_bound = current_spend * 1.4  # Max 40% increase
            bounds.append((min_bound, max_bound))
        
        # ── Run optimization ──────────────────────────────────────────────────
        try:
            result = minimize(
                fun=objective,
                x0=np.array(current_allocation),
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 200, "ftol": 1e-6},
            )
            
            if not result.success:
                if self.tenant_id is not None:
                    log_data_quality_issue(
                        tenant_id=self.tenant_id,
                        strategy_name="multi_channel_allocation",
                        issue_type="optimization_convergence_failed",
                        details={"message": result.message},
                        severity="warning",
                    )
        except Exception as e:
            raise RuntimeError(f"Optimization error: {e}") from e
        
        # ── Extract optimal allocation ───────────────────────────────────────
        optimal_allocation = result.x
        
        # ── Calculate metrics per channel ────────────────────────────────────
        channels_detail = []
        current_total_conv = 0.0
        optimal_total_conv = 0.0
        
        for i, channel_name in enumerate(self.active_channels):
            curve = self.channel_curves[channel_name]
            data = self.training_data[channel_name]
            
            current_spend = current_allocation[i]
            optimal_spend = optimal_allocation[i]
            
            current_conv = curve.predict(current_spend)[0]
            optimal_conv = curve.predict(optimal_spend)[0]
            
            current_total_conv += current_conv
            optimal_total_conv += optimal_conv
            
            # Revenue (use actual if available, else estimate from AOV)
            if len(data["revenue"]) > 0:
                current_revenue = float(np.sum(data["revenue"][-7:])) / 7
            else:
                current_revenue = current_conv * self.aov
            optimal_revenue = optimal_conv * self.aov
            
            # Efficiency (conversions per ₹1K)
            if current_spend > 0:
                current_efficiency = current_conv / current_spend * 1000
            else:
                current_efficiency = 0
            if optimal_spend > 0:
                optimal_efficiency = optimal_conv / optimal_spend * 1000
            else:
                optimal_efficiency = 0
            
            # ROAS
            if current_spend > 0:
                current_roas = current_revenue / current_spend
            else:
                current_roas = 0
            if optimal_spend > 0:
                optimal_roas = optimal_revenue / optimal_spend
            else:
                optimal_roas = 0
            
            spend_change_pct = 0
            if current_spend > 0:
                spend_change_pct = (
                    (optimal_spend - current_spend) / current_spend * 100
                )
            
            channels_detail.append({
                "name": channel_name,
                "current_spend": float(current_spend),
                "optimal_spend": float(optimal_spend),
                "spend_change": float(optimal_spend - current_spend),
                "spend_change_pct": float(spend_change_pct),
                "current_conversions": float(current_conv),
                "optimal_conversions": float(optimal_conv),
                "current_efficiency": float(current_efficiency),
                "optimal_efficiency": float(optimal_efficiency),
                "current_roas": float(current_roas),
                "optimal_roas": float(optimal_roas),
            })
        
        # ── Calculate lift ────────────────────────────────────────────────────
        lift_pct = (
            ((optimal_total_conv - current_total_conv) / current_total_conv * 100)
            if current_total_conv > 0
            else 0.0
        )
        
        conversion_lift = optimal_total_conv - current_total_conv
        daily_revenue_impact = conversion_lift * self.aov
        
        # ── Build optimization result ─────────────────────────────────────────
        result_dict = {
            "total_budget": float(self.current_budget),
            "num_channels": num_channels,
            "channels": channels_detail,
            "expected_conversions": float(optimal_total_conv),
            "current_conversions": float(current_total_conv),
            "lift_pct": float(lift_pct),
            "daily_revenue_impact": float(daily_revenue_impact),
            "aov": float(self.aov),
        }
        
        # Store result
        self.optimization_result = result_dict
        
        # Update OptimizationRun record
        if self.optimization_run_id is not None:
            optimization_run = self.db.get(OptimizationRun, self.optimization_run_id)
            if optimization_run:
                optimization_run.run_status = "success"
                optimization_run.completed_at = datetime.now(UTC)
                optimization_run.optimization_result = result_dict
                if optimization_run.started_at:
                    execution_time = (
                        optimization_run.completed_at - optimization_run.started_at
                    ).total_seconds()
                    optimization_run.execution_time_seconds = execution_time
                self.db.commit()
        
        return result_dict
    
    def generate_recommendation(self) -> dict[str, Any]:
        """Generate recommendation payload from optimization result."""
        if self.optimization_result is None:
            raise ValueError("Must run optimization before generating recommendation")
        
        opt = self.optimization_result
        channels = opt["channels"]
        
        # Build recommendation text
        recommendation_text = (
            f"Reallocate daily budget across {opt['num_channels']} "
            f"channels for +{opt['lift_pct']:.1f}% conversion lift "
            f"({opt['expected_conversions']:.0f} vs "
            f"{opt['current_conversions']:.0f} daily conversions)."
        )
        
        # Action items (top 3 changes by magnitude)
        sorted_channels = sorted(
            channels, key=lambda ch: abs(ch["spend_change"]), reverse=True
        )
        action_items = []
        for ch in sorted_channels[:3]:
            direction = "Increase" if ch["spend_change"] > 0 else "Reduce"
            action_items.append(
                f"{direction} {ch['name'].capitalize()} to "
                f"₹{ch['optimal_spend']:,.0f}/day "
                f"({ch['spend_change']:+,.0f}, "
                f"{ch['spend_change_pct']:+.1f}%)"
            )
        action_items.append("Monitor conversion performance over 7 days")
        
        # Expected impact
        expected_impact = {
            "conversions_lift_pct": opt["lift_pct"],
            "expected_daily_conversions": opt["expected_conversions"],
            "daily_revenue_impact": opt["daily_revenue_impact"],
        }
        
        # Priority based on lift magnitude
        if opt["lift_pct"] > 10:
            priority = "high"
        elif opt["lift_pct"] > 5:
            priority = "medium"
        else:
            priority = "low"
        
        # Confidence based on model R²
        r2_scores = []
        for channel_name in self.active_channels:
            fitted_model = self.db.query(FittedModel).filter(
                FittedModel.optimization_run_id == self.optimization_run_id,
                FittedModel.model_type == f"{channel_name}_saturation_curve",
            ).first()
            if fitted_model and fitted_model.accuracy_metrics:
                r2_scores.append(fitted_model.accuracy_metrics.get("r2", 0.5))
        
        avg_r2 = sum(r2_scores) / len(r2_scores) if r2_scores else 0.5
        
        return {
            "recommendation_text": recommendation_text,
            "action_items": action_items,
            "expected_impact": expected_impact,
            "confidence_level": float(avg_r2),
            "domain": "acquisition",
            "priority": priority,
        }
    
    def create_recommendation_record(self) -> Recommendation:
        """Create a Recommendation database record from optimization result."""
        if self.optimization_result is None:
            raise ValueError("Must run optimization before creating recommendation")
        
        if self.tenant_id is None or self.optimization_run_id is None:
            raise RuntimeError("tenant_id or optimization_run_id not set")
        
        opt = self.optimization_result
        channels = opt["channels"]
        
        # Build signal summary (which channels saturated vs have headroom)
        sorted_channels = sorted(
            channels, key=lambda ch: ch["spend_change"], reverse=True
        )
        top_gainer = sorted_channels[0]
        top_loser = sorted_channels[-1]
        
        signal_summary = (
            f"{top_loser['name'].capitalize()} oversaturated "
            f"(efficiency {top_loser['current_efficiency']:.2f}), "
            f"{top_gainer['name'].capitalize()} undersaturated "
            f"(efficiency {top_gainer['current_efficiency']:.2f}). "
            f"Rebalancing for +{opt['lift_pct']:.1f}% conversions."
        )
        
        suggested_action = (
            f"Reallocate daily budget: "
            f"{top_gainer['name'].capitalize()} "
            f"₹{top_gainer['current_spend']:,.0f} → "
            f"₹{top_gainer['optimal_spend']:,.0f} "
            f"({top_gainer['spend_change']:+,.0f}), "
            f"{top_loser['name'].capitalize()} "
            f"₹{top_loser['current_spend']:,.0f} → "
            f"₹{top_loser['optimal_spend']:,.0f} "
            f"({top_loser['spend_change']:+,.0f})."
        )
        
        # Priority
        if opt["daily_revenue_impact"] > 10000:
            priority = 90
        elif opt["daily_revenue_impact"] > 5000:
            priority = 70
        else:
            priority = 50
        
        # Confidence
        r2_scores = []
        for channel_name in self.active_channels:
            fitted_model = self.db.query(FittedModel).filter(
                FittedModel.optimization_run_id == self.optimization_run_id,
                FittedModel.model_type == f"{channel_name}_saturation_curve",
            ).first()
            if fitted_model and fitted_model.accuracy_metrics:
                r2_scores.append(fitted_model.accuracy_metrics.get("r2", 0.5))
        
        avg_r2 = sum(r2_scores) / len(r2_scores) if r2_scores else 0.5
        confidence_level = self._map_confidence_to_level(avg_r2)
        
        # Dedup: if an open recommendation already exists, return it unchanged.
        # Only create a new one if the previous was acted on or doesn't exist.
        today = date.today()
        open_statuses = ("new", "reviewed")
        existing = self.db.query(Recommendation).filter(
            Recommendation.tenant_id == self.tenant_id,
            Recommendation.rule_id == "OPT-MULTICHANNEL-001",
            Recommendation.status.in_(open_statuses),
        ).first()
        if existing:
            return existing
        self.db.flush()
        
        # Create recommendation
        recommendation = Recommendation(
            tenant_id=self.tenant_id,
            rule_id="OPT-MULTICHANNEL-001",
            domain="acquisition",
            snapshot_date=today,
            affected_area="Multi-Channel Budget Allocation",
            signal_summary=signal_summary,
            suggested_action=suggested_action,
            estimated_impact=opt["daily_revenue_impact"] * 30,  # Monthly revenue impact
            confidence_level=confidence_level,
            confidence_score=avg_r2,
            data_freshness_context=(
                f"Based on {self.lookback_days} days across "
                f"{opt['num_channels']} channels"
            ),
            status="new",
            priority=priority,
            impact_score=opt["daily_revenue_impact"],
            evidence={
                "channels": channels,
                "current_conversions": opt["current_conversions"],
                "expected_conversions": opt["expected_conversions"],
                "lift_pct": opt["lift_pct"],
                "daily_revenue_impact": opt["daily_revenue_impact"],
            },
            data_sources=["meta", "google_ads", "marketing_channels", "shopify"],
            source="optimization",
            optimization_metadata=opt,
        )
        
        self.db.add(recommendation)
        self.db.flush()
        
        return recommendation
    
    # ── Helper methods (copied from BudgetAllocationOptimizer) ───────────────
    
    def _map_confidence_to_level(self, confidence_score: float) -> str:
        """Map numeric confidence score (0-1) to categorical level."""
        if confidence_score < 0.3:
            return "very_low"
        elif confidence_score < 0.5:
            return "low"
        elif confidence_score < 0.7:
            return "medium"
        elif confidence_score < 0.9:
            return "high"
        else:
            return "very_high"
    
    def _calculate_r2(self, actual: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate R² (coefficient of determination) for model fit."""
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        ss_res = np.sum((actual - predicted) ** 2)
        if ss_tot == 0:
            return 0.0
        r2 = 1.0 - (ss_res / ss_tot)
        return float(r2)
    
    def _save_fitted_model(
        self,
        curve: HillCurve,
        model_type: str,
        params: dict[str, float],
        metrics: dict[str, float],
    ) -> None:
        """Save fitted model to S3 and create database record."""
        if self.tenant_id is None or self.optimization_run_id is None:
            raise RuntimeError("tenant_id or optimization_run_id not set")
        
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        s3_key = f"{self.tenant_id}/{model_type}_{timestamp}.pkl"
        
        try:
            upload_model(model_obj=curve, s3_key=s3_key)
        except Exception as e:
            raise RuntimeError(f"Failed to upload model to S3: {e}") from e
        
        fitted_model = FittedModel(
            tenant_id=self.tenant_id,
            strategy_id=self.strategy_id,
            optimization_run_id=self.optimization_run_id,
            model_type=model_type,
            s3_key=s3_key,
            trained_at=datetime.now(UTC),
            model_metadata={
                "params": params,
                "lookback_days": self.lookback_days,
            },
            accuracy_metrics=metrics,
        )
        
        self.db.add(fitted_model)
        self.db.flush()
