"""Influencer Portfolio Optimizer - per-influencer budget allocation.

Optimizes spend across individual influencers within the influencer channel
to maximize conversions while maintaining efficiency thresholds.

Uses Hill saturation curves fitted per influencer to identify:
- Top performers (increase budget)
- Underperformers (pause or reduce)
- Declining performers (flag for review)
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from backend.app.db.models import (
    FittedModel,
    MarketingChannelSpend,
    OptimizationRun,
    OptimizationStrategy,
    Recommendation,
    ShopifyOrder,
)
from scipy.optimize import minimize
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from worker.app.optimization.curves import HillCurve  # type: ignore[import-untyped]
from worker.app.optimization.storage import upload_model  # type: ignore[import-untyped]
from worker.app.utils.data_quality import log_data_quality_issue  # type: ignore[import-untyped]


class InfluencerPortfolioOptimizer:
    """Optimize budget allocation across individual influencers.
    
    Treats each influencer as separate entity, fits Hill curves,
    and recommends optimal allocation to maximize conversions.
    """
    
    def __init__(self, db: Session, strategy_id: UUID) -> None:
        """Initialize optimizer with database session and strategy ID.
        
        Args:
            db: SQLAlchemy database session
            strategy_id: UUID of optimization strategy record
        """
        self.db = db
        self.strategy_id = strategy_id
        
        # Fetch strategy config
        strategy = db.get(OptimizationStrategy, strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        self.strategy_name = strategy.strategy_name
        
        # State attributes (set during execution)
        self.tenant_id: UUID | None = None
        self.lookback_days: int = 90
        self.training_data: dict[str, Any] | None = None
        self.influencer_curves: dict[str, HillCurve] = {}
        self.active_influencers: list[str] = []
        self.optimization_result: dict[str, Any] | None = None
        self.optimization_run_id: UUID | None = None
        self.current_budget: float = 0.0
        self.aov: float = 6500.0  # Default AOV, updated from data
        self.models: dict[str, HillCurve] = {}
        
        # Min spend per influencer (₹1K/day minimum to keep active)
        self.min_spend_per_influencer = 1000.0
        
        # Max shift per influencer (60% change allowed - more aggressive than channels)
        self.max_shift_pct = 0.6
    
    def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> dict[str, Any]:
        """Fetch historical influencer spend and conversion data.
        
        Queries marketing_channel_spends for influencer channel,
        groups by campaign_id (individual influencer),
        joins with orders for conversions.
        
        Args:
            tenant_id: UUID of tenant to fetch data for
            days: Number of days of historical data (default: 90)
        
        Returns:
            Dictionary with structure:
            {
                'influencer_name_1': {
                    'spend': array, 'conversions': array, 'revenue': array
                },
                'influencer_name_2': {...},
                ...
                'total_budget': current total daily budget
            }
        
        Raises:
            ValueError: If insufficient data (< 30 days per influencer, < 2 active)
        """
        self.tenant_id = tenant_id
        self.lookback_days = days
        
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days)
        
        # ── Fetch influencer spend data ──────────────────────────────────────
        # Group by external_campaign_id (each campaign = one influencer from seed)
        influencer_query = (
            select(
                MarketingChannelSpend.external_campaign_id,
                MarketingChannelSpend.spend_date,
                func.sum(MarketingChannelSpend.spend_amount).label("daily_spend"),
                func.sum(MarketingChannelSpend.conversions).label(
                    "daily_conversions"
                ),
                func.sum(MarketingChannelSpend.revenue).label("daily_revenue"),
            )
            .where(MarketingChannelSpend.tenant_id == tenant_id)
            .where(MarketingChannelSpend.channel_name == "influencer")
            .where(MarketingChannelSpend.spend_date >= start_date)
            .where(MarketingChannelSpend.spend_date <= end_date)
            .group_by(
                MarketingChannelSpend.external_campaign_id,
                MarketingChannelSpend.spend_date,
            )
            .order_by(
                MarketingChannelSpend.external_campaign_id,
                MarketingChannelSpend.spend_date,
            )
        )
        influencer_raw = self.db.execute(influencer_query).all()
        
        if not influencer_raw:
            raise ValueError(
                "No influencer spend data found for tenant "
                f"{tenant_id} in last {days} days"
            )
        
        # ── Fetch order data for AOV calculation ─────────────────────────────
        orders_query = (
            select(
                func.count().label("order_count"),
                func.sum(ShopifyOrder.total_amount).label("total_revenue"),
            )
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(func.date(ShopifyOrder.order_created_at) >= start_date)
            .where(func.date(ShopifyOrder.order_created_at) <= end_date)
            .where(ShopifyOrder.is_refunded == False)  # noqa: E712
        )
        orders_result = self.db.execute(orders_query).first()
        
        if orders_result and orders_result.order_count > 0:
            total_orders = orders_result.order_count
            total_revenue = orders_result.total_revenue or 0.0
            self.aov = total_revenue / total_orders
        
        # ── Build influencer-indexed dictionaries ────────────────────────────
        # Structure: {external_campaign_id: {date: {spend, conversions, revenue}}}
        influencer_dict: dict[str, dict[date, dict[str, float]]] = {}
        
        for row in influencer_raw:
            campaign_id = row.external_campaign_id
            if campaign_id not in influencer_dict:
                influencer_dict[campaign_id] = {}
            
            influencer_dict[campaign_id][row.spend_date] = {
                "spend": float(row.daily_spend),
                "conversions": float(row.daily_conversions or 0),
                "revenue": float(row.daily_revenue or 0),
            }
        
        # ── Get all dates with spend data ────────────────────────────────────
        all_dates = sorted(
            {
                spend_date
                for influencer_data in influencer_dict.values()
                for spend_date in influencer_data.keys()
            }
        )
        
        if len(all_dates) < 30:
            raise ValueError(
                f"Insufficient data for training: only {len(all_dates)} days "
                f"with influencer spend. Need at least 30 days."
            )
        
        # ── Prepare aligned arrays per influencer ────────────────────────────
        influencer_data: dict[str, dict[str, list]] = {}
        
        for campaign_id, date_data in influencer_dict.items():
            influencer_data[campaign_id] = {
                "spend": [],
                "conversions": [],
                "revenue": [],
            }
            
            # Build arrays aligned to all_dates
            for d in all_dates:
                if d in date_data:
                    influencer_data[campaign_id]["spend"].append(
                        date_data[d]["spend"]
                    )
                    influencer_data[campaign_id]["conversions"].append(
                        date_data[d]["conversions"]
                    )
                    influencer_data[campaign_id]["revenue"].append(
                        date_data[d]["revenue"]
                    )
        
        # ── Validate each influencer has enough data ──────────────────────────
        self.active_influencers = []
        
        for campaign_id, data in influencer_data.items():
            days_with_spend = len([s for s in data["spend"] if s > 0])
            
            if days_with_spend >= 30:  # Min 30 days for Hill curve fitting
                self.active_influencers.append(campaign_id)
                # Convert to numpy arrays
                data["spend"] = np.array(data["spend"])  # type: ignore[assignment]
                data["conversions"] = np.array(data["conversions"])  # type: ignore[assignment]
                data["revenue"] = np.array(data["revenue"])  # type: ignore[assignment]
            else:
                # Log data quality issue but don't fail
                if days_with_spend > 0:
                    log_data_quality_issue(
                        tenant_id=tenant_id,
                        strategy_name="influencer_portfolio_allocation",
                        issue_type=f"insufficient_{campaign_id}_data",
                        details={
                            "days_with_spend": days_with_spend,
                            "required": 30,
                        },
                        severity="warning",
                    )
        
        if len(self.active_influencers) < 2:
            raise ValueError(
                f"Insufficient active influencers: only "
                f"{len(self.active_influencers)} influencers with 30+ days "
                f"of data. Need at least 2."
            )
        
        # ── Calculate current budget (avg daily spend over last 7 days) ──────
        recent_total_spend = 0.0
        
        for campaign_id in self.active_influencers:
            data = influencer_data[campaign_id]
            # Sum last 7 days of spend
            recent_total_spend += float(np.sum(data["spend"][-7:]))
        
        self.current_budget = recent_total_spend / 7  # Average daily budget
        
        # Store full influencer_data
        self.training_data = {
            inf: influencer_data[inf] for inf in self.active_influencers
        }
        self.training_data["total_budget"] = self.current_budget
        
        return self.training_data
    
    def train_models(self) -> None:
        """Train Hill saturation curves for all active influencers.
        
        Fits separate Hill curves to each influencer's spend/conversion data.
        Stores curves in self.influencer_curves dict.
        Saves fitted models to S3 and creates FittedModel database records.
        
        Raises:
            ValueError: If training data is None or has insufficient points
            RuntimeError: If curve fitting fails for majority of influencers
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
        
        # Fit curve for each active influencer
        for campaign_id in self.active_influencers:
            data = self.training_data[campaign_id]
            
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
                self.influencer_curves[campaign_id] = curve
                
                # Save model to S3 and database
                self._save_fitted_model(
                    curve=curve,
                    model_type=f"{campaign_id}_saturation_curve",
                    params=params,
                    metrics={"rmse": rmse, "r2": r2},
                )
            except Exception as e:
                # Log but don't fail - optimizer can work with fewer influencers
                if self.tenant_id is not None:
                    log_data_quality_issue(
                        tenant_id=self.tenant_id,
                        strategy_name="influencer_portfolio_allocation",
                        issue_type=f"{campaign_id}_curve_fit_failed",
                        details={"error": str(e)},
                        severity="error",
                    )
                # Remove from active influencers
                self.active_influencers.remove(campaign_id)
        
        if len(self.influencer_curves) < 2:
            raise RuntimeError(
                f"Failed to fit curves: only {len(self.influencer_curves)} "
                f"influencers have valid models. Need at least 2."
            )
        
        # Store models in parent class attribute
        self.models = self.influencer_curves
    
    def optimize(self) -> dict[str, Any]:
        """Find optimal budget allocation using constrained optimization.
        
        Uses scipy.optimize.minimize with SLSQP algorithm to maximize total
        conversions subject to budget constraints:
        - Total spend ≤ current budget
        - Min spend ≥ ₹1K/day per influencer
        - Max shift ≤ 60% per influencer
        
        Returns:
            Dictionary with optimization results per influencer plus aggregates
        """
        if len(self.influencer_curves) < 2:
            raise RuntimeError("Must train models before optimizing")
        
        if self.current_budget is None or self.current_budget <= 0:
            raise RuntimeError("Invalid current budget")
        
        # Ensure only influencers with curves are in active list
        self.active_influencers = list(self.influencer_curves.keys())
        num_influencers = len(self.active_influencers)
        
        # ── Objective function: maximize total conversions ───────────────────
        def objective(spend_allocation: np.ndarray) -> float:
            """Negative total conversions (for minimization)."""
            total_conv = 0.0
            for i, campaign_id in enumerate(self.active_influencers):
                curve = self.influencer_curves[campaign_id]
                total_conv += curve.predict(spend_allocation[i])[0]
            return -total_conv  # Negative because we minimize
        
        # ── Calculate current allocation ─────────────────────────────────────
        current_allocation = []
        if self.training_data is None:
            raise RuntimeError("Training data is None")
        
        for campaign_id in self.active_influencers:
            data = self.training_data[campaign_id]
            # Last 7 days average
            current_spend = float(np.mean(data["spend"][-7:]))
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
            equal_split = self.current_budget / num_influencers
            current_allocation = [equal_split] * num_influencers
        
        # ── Constraints ───────────────────────────────────────────────────────
        constraints = [
            # Total spend equals current budget
            {
                "type": "eq",
                "fun": lambda x: np.sum(x) - self.current_budget,
            },
        ]
        
        # ── Bounds per influencer ─────────────────────────────────────────────
        bounds = []
        for i, _campaign_id in enumerate(self.active_influencers):
            current_spend = current_allocation[i]
            min_bound = max(
                self.min_spend_per_influencer,  # Platform minimum
                current_spend * (1 - self.max_shift_pct),  # Max decrease
            )
            max_bound = current_spend * (1 + self.max_shift_pct)  # Max increase
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
                        strategy_name="influencer_portfolio_allocation",
                        issue_type="optimization_convergence_failed",
                        details={"message": result.message},
                        severity="warning",
                    )
        except Exception as e:
            raise RuntimeError(f"Optimization error: {e}") from e
        
        # ── Extract optimal allocation ───────────────────────────────────────
        optimal_allocation = result.x
        
        # ── Calculate metrics per influencer ─────────────────────────────────
        influencers_detail = []
        current_total_conv = 0.0
        optimal_total_conv = 0.0
        
        if self.training_data is None:
            raise RuntimeError("Training data is None")
        
        for i, campaign_id in enumerate(self.active_influencers):
            curve = self.influencer_curves[campaign_id]
            data = self.training_data[campaign_id]
            
            current_spend = current_allocation[i]
            optimal_spend = optimal_allocation[i]
            
            current_conv = curve.predict(current_spend)[0]
            optimal_conv = curve.predict(optimal_spend)[0]
            
            current_total_conv += current_conv
            optimal_total_conv += optimal_conv
            
            # Efficiency (conversions per ₹1K)
            if current_spend > 0:
                current_efficiency = current_conv / current_spend * 1000
            else:
                current_efficiency = 0
            if optimal_spend > 0:
                optimal_efficiency = optimal_conv / optimal_spend * 1000
            else:
                optimal_efficiency = 0
            
            # CAC
            if current_conv > 0:
                current_cac = current_spend / current_conv
            else:
                current_cac = 0
            if optimal_conv > 0:
                optimal_cac = optimal_spend / optimal_conv
            else:
                optimal_cac = 0
            
            spend_change_pct = 0
            if current_spend > 0:
                spend_change_pct = (
                    (optimal_spend - current_spend) / current_spend * 100
                )
            
            # Determine action
            if abs(spend_change_pct) < 5:
                action = "maintain"
            elif spend_change_pct > 0:
                action = "increase"
            else:
                action = "reduce"
            
            influencers_detail.append({
                "campaign_id": campaign_id,
                "action": action,
                "current_spend": float(current_spend),
                "optimal_spend": float(optimal_spend),
                "spend_change": float(optimal_spend - current_spend),
                "spend_change_pct": float(spend_change_pct),
                "current_conversions": float(current_conv),
                "optimal_conversions": float(optimal_conv),
                "current_efficiency": float(current_efficiency),
                "optimal_efficiency": float(optimal_efficiency),
                "current_cac": float(current_cac),
                "optimal_cac": float(optimal_cac),
            })
        
        # ── Calculate lift ────────────────────────────────────────────────────
        if current_total_conv > 0:
            lift_pct = (
                (optimal_total_conv - current_total_conv)
                / current_total_conv
                * 100
            )
        else:
            lift_pct = 0.0
        
        conversion_lift = optimal_total_conv - current_total_conv
        daily_revenue_impact = conversion_lift * self.aov
        
        # Group by action
        to_pause: list[dict[str, Any]] = [
            inf
            for inf in influencers_detail
            if inf["action"] == "reduce"
            and inf["spend_change_pct"] < -40  # type: ignore[operator]
        ]
        to_increase: list[dict[str, Any]] = [
            inf for inf in influencers_detail if inf["action"] == "increase"
        ]
        to_maintain: list[dict[str, Any]] = [
            inf for inf in influencers_detail if inf["action"] == "maintain"
        ]
        to_reduce: list[dict[str, Any]] = [
            inf
            for inf in influencers_detail
            if inf["action"] == "reduce"
            and inf["spend_change_pct"] >= -40  # type: ignore[operator]
        ]
        
        # ── Build optimization result ─────────────────────────────────────────
        result_dict = {
            "total_budget": float(self.current_budget),
            "num_influencers": num_influencers,
            "influencers": influencers_detail,
            "grouped_actions": {
                "pause": to_pause,
                "reduce": to_reduce,
                "increase": to_increase,
                "maintain": to_maintain,
            },
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
        grouped = opt["grouped_actions"]
        
        # Build recommendation text
        num_pause = len(grouped["pause"])
        num_increase = len(grouped["increase"])
        num_reduce = len(grouped["reduce"])
        
        recommendation_text = (
            f"Influencer Portfolio Reallocation: Pause {num_pause}, "
            f"increase {num_increase}, reduce {num_reduce} for "
            f"+{opt['lift_pct']:.1f}% conversion lift "
            f"({opt['expected_conversions']:.0f} vs "
            f"{opt['current_conversions']:.0f} daily conversions)."
        )
        
        # Action items
        action_items = []
        
        # Top 3 to increase
        top_increases = sorted(
            grouped["increase"],
            key=lambda x: x["spend_change"],
            reverse=True,
        )[:3]
        for inf in top_increases:
            action_items.append(
                f"Increase {inf['campaign_id']}: "
                f"₹{inf['current_spend']:,.0f} → ₹{inf['optimal_spend']:,.0f} "
                f"({inf['spend_change']:+,.0f}, {inf['spend_change_pct']:+.1f}%)"
            )
        
        # Influencers to pause
        for inf in grouped["pause"]:
            action_items.append(
                f"Pause {inf['campaign_id']}: "
                f"CAC ₹{inf['current_cac']:,.0f}, "
                f"efficiency {inf['current_efficiency']:.2f} (underperforming)"
            )
        
        action_items.append("Monitor performance over 14 days")
        
        # Expected impact
        expected_impact = {
            "conversions_lift_pct": opt["lift_pct"],
            "expected_daily_conversions": opt["expected_conversions"],
            "daily_revenue_impact": opt["daily_revenue_impact"],
        }
        
        # Priority based on lift magnitude
        if opt["lift_pct"] > 15:
            priority = "high"
        elif opt["lift_pct"] > 8:
            priority = "medium"
        else:
            priority = "low"
        
        # Confidence based on model R²
        r2_scores = []
        for campaign_id in self.active_influencers:
            fitted_model = self.db.query(FittedModel).filter(
                FittedModel.optimization_run_id == self.optimization_run_id,
                FittedModel.model_type == f"{campaign_id}_saturation_curve",
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
        grouped = opt["grouped_actions"]
        
        # Build signal summary
        top_performer = max(
            opt["influencers"], key=lambda x: x["current_efficiency"]
        )
        worst_performer = min(
            opt["influencers"], key=lambda x: x["current_efficiency"]
        )
        
        signal_summary = (
            f"Influencer portfolio inefficient: {len(grouped['pause'])} "
            f"underperformers (CAC > avg), {len(grouped['increase'])} "
            f"high-performers undersaturated. Best: {top_performer['campaign_id']} "
            f"(efficiency {top_performer['current_efficiency']:.2f}), "
            f"Worst: {worst_performer['campaign_id']} "
            f"(efficiency {worst_performer['current_efficiency']:.2f}). "
            f"Rebalancing for +{opt['lift_pct']:.1f}% conversions."
        )
        
        # Build suggested action
        pause_list = ", ".join([inf["campaign_id"] for inf in grouped["pause"][:3]])
        increase_list = ", ".join(
            [inf["campaign_id"] for inf in grouped["increase"][:3]]
        )
        
        suggested_action = (
            f"Pause {len(grouped['pause'])} influencers ({pause_list}...), "
            f"increase {len(grouped['increase'])} high-performers "
            f"({increase_list}...)."
        )
        
        # Priority
        if opt["daily_revenue_impact"] > 50000:
            priority = 90
        elif opt["daily_revenue_impact"] > 25000:
            priority = 70
        else:
            priority = 50
        
        # Confidence
        r2_scores = []
        for campaign_id in self.active_influencers:
            fitted_model = self.db.query(FittedModel).filter(
                FittedModel.optimization_run_id == self.optimization_run_id,
                FittedModel.model_type == f"{campaign_id}_saturation_curve",
            ).first()
            if fitted_model and fitted_model.accuracy_metrics:
                r2_scores.append(fitted_model.accuracy_metrics.get("r2", 0.5))
        
        avg_r2 = sum(r2_scores) / len(r2_scores) if r2_scores else 0.5
        confidence_level = self._map_confidence_to_level(avg_r2)
        
        # Delete previous OPT-INFLUENCER-PORTFOLIO-001 recommendations
        today = date.today()
        self.db.execute(
            delete(Recommendation).where(
                Recommendation.tenant_id == self.tenant_id,
                Recommendation.rule_id == "OPT-INFLUENCER-PORTFOLIO-001",
            )
        )
        self.db.flush()
        
        # Create recommendation
        recommendation = Recommendation(
            tenant_id=self.tenant_id,
            rule_id="OPT-INFLUENCER-PORTFOLIO-001",
            domain="acquisition",
            snapshot_date=today,
            affected_area="Influencer Portfolio Allocation",
            signal_summary=signal_summary,
            suggested_action=suggested_action,
            estimated_impact=opt["daily_revenue_impact"],
            confidence_level=confidence_level,
            confidence_score=avg_r2,
            data_freshness_context=(
                f"Based on {self.lookback_days} days across "
                f"{opt['num_influencers']} influencers"
            ),
            status="new",
            priority=priority,
            impact_score=opt["daily_revenue_impact"],
            evidence={
                "influencers": opt["influencers"],
                "grouped_actions": grouped,
                "current_conversions": opt["current_conversions"],
                "expected_conversions": opt["expected_conversions"],
                "lift_pct": opt["lift_pct"],
                "daily_revenue_impact": opt["daily_revenue_impact"],
            },
            data_sources=["marketing_channels", "shopify"],
            source="optimization",
            optimization_metadata=opt,
        )
        
        self.db.add(recommendation)
        self.db.flush()
        
        return recommendation
    
    # ── Helper methods ────────────────────────────────────────────────────────
    
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
