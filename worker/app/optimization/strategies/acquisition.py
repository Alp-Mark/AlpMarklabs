"""Budget allocation optimizer for acquisition channels.

This module implements the concrete BudgetAllocationOptimizer that extends
BaseOptimizer to find optimal ad spend allocation between Meta and Google Ads.

The optimizer:
1. Fetches historical ad spend and conversion data
2. Fits Hill saturation curves for each channel
3. Uses scipy.optimize to maximize total conversions
4. Returns optimal budget allocation with expected impact

Business Logic:
- Constraints: Each channel gets 15-60% of total budget
- Objective: Maximize total conversions across channels
- Method: Sequential Least Squares Programming (SLSQP)

Example:
    optimizer = BudgetAllocationOptimizer(strategy_id=strategy.id, db=session)
    recommendation = optimizer.run(tenant_id=tenant.id, days=90)
    # Returns optimal allocation: {"meta": 45%, "google": 55%} with expected lift
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from backend.app.db.models import (
    FittedModel,
    GoogleAdSpend,
    MetaAdSpend,
    OptimizationRun,
    Recommendation,
    ShopifyOrder,
)
from scipy.optimize import minimize
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from worker.app.optimization.models.saturation import HillCurve
from worker.app.optimization.strategies.base import BaseOptimizer
from worker.app.optimization.utils.monitoring import log_data_quality_issue
from worker.app.optimization.utils.s3_storage import upload_model


class BudgetAllocationOptimizer(BaseOptimizer):
    """Optimizer for allocating ad budget between Meta and Google Ads.
    
    Finds the optimal split of advertising budget between channels to maximize
    total conversions, respecting minimum and maximum allocation constraints.
    
    The optimizer uses Hill saturation curves to model diminishing returns per
    channel, then uses constrained optimization to find the best allocation.
    
    Attributes:
        strategy_id: UUID of the OptimizationStrategy record
        db: SQLAlchemy database session
        training_data: Dictionary with 'meta' and 'google' spend/conversion arrays
        models: Dictionary with 'meta' and 'google' HillCurve instances
        optimization_result: Optimal spend allocation
        
    Constraints:
        - Minimum allocation per channel: 15% of total budget
        - Maximum allocation per channel: 60% of total budget
        - Total allocation: 100% of current budget
    """
    
    def __init__(self, strategy_id: UUID, db: Session) -> None:
        """Initialize budget allocation optimizer.
        
        Args:
            strategy_id: UUID of the OptimizationStrategy record
            db: SQLAlchemy session for database queries
        """
        super().__init__(strategy_id, db)
        self.meta_curve: HillCurve | None = None
        self.google_curve: HillCurve | None = None
        self.current_budget: float | None = None
        self.tenant_id: UUID | None = None
        self.lookback_days: int = 90  # Default lookback period
        self.optimization_run_id: UUID | None = None
        self.optimization_result: dict[str, Any] | None = None
        # Single-channel mode: set when only one ad channel has data
        self.single_channel_mode: bool = False
        self.active_channel: str = "both"  # "meta", "google", or "both"
    
    def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> dict[str, Any]:
        """Fetch historical ad spend and conversion data for Meta and Google.
        
        Queries the database for:
        1. Daily ad spend for Meta and Google (aggregated across campaigns)
        2. Daily order counts as proxy for conversions
        3. Simple attribution: conversions split proportionally to spend
        
        Args:
            tenant_id: UUID of the tenant to fetch data for
            days: Number of days of historical data (default: 90)
        
        Returns:
            Dictionary with structure:
            {
                'meta': {
                    'spend': [array of daily spend values],
                    'conversions': [array of daily conversions]
                },
                'google': {
                    'spend': [array of daily spend values],
                    'conversions': [array of daily conversions]
                },
                'total_budget': current total daily budget
            }
        
        Raises:
            ValueError: If insufficient data (< 14 days with spend)
        """
        from datetime import UTC
        
        # Store parameters for later use
        self.tenant_id = tenant_id
        self.lookback_days = days
        
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days)
        
        # Fetch Meta ad spend aggregated by date
        meta_query = (
            select(
                MetaAdSpend.spend_date,
                func.sum(MetaAdSpend.spend_amount).label("daily_spend"),
            )
            .where(MetaAdSpend.tenant_id == tenant_id)
            .where(MetaAdSpend.spend_date >= start_date)
            .where(MetaAdSpend.spend_date <= end_date)
            .group_by(MetaAdSpend.spend_date)
            .order_by(MetaAdSpend.spend_date)
        )
        meta_spend_raw = self.db.execute(meta_query).all()
        
        # Fetch Google ad spend aggregated by date
        google_query = (
            select(
                GoogleAdSpend.spend_date,
                func.sum(GoogleAdSpend.spend_amount).label("daily_spend"),
            )
            .where(GoogleAdSpend.tenant_id == tenant_id)
            .where(GoogleAdSpend.spend_date >= start_date)
            .where(GoogleAdSpend.spend_date <= end_date)
            .group_by(GoogleAdSpend.spend_date)
            .order_by(GoogleAdSpend.spend_date)
        )
        google_spend_raw = self.db.execute(google_query).all()
        
        # Fetch order counts and revenue by date (proxy for conversions)
        orders_query = (
            select(
                func.date(ShopifyOrder.order_created_at).label("order_date"),
                func.count().label("order_count"),
                func.sum(ShopifyOrder.total_amount).label("total_revenue"),
            )
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(func.date(ShopifyOrder.order_created_at) >= start_date)
            .where(func.date(ShopifyOrder.order_created_at) <= end_date)
            .where(ShopifyOrder.is_refunded == False)  # noqa: E712
            .group_by(func.date(ShopifyOrder.order_created_at))
            .order_by(func.date(ShopifyOrder.order_created_at))
        )
        orders_raw = self.db.execute(orders_query).all()
        
        # Calculate AOV (average order value) from historical data
        total_orders = sum(row.order_count for row in orders_raw)
        total_revenue = sum(row.total_revenue or 0.0 for row in orders_raw)
        self.aov = total_revenue / total_orders if total_orders > 0 else 0.0
        
        # Build date-indexed dictionaries
        meta_spend_dict = {
            row.spend_date: float(row.daily_spend) for row in meta_spend_raw
        }
        google_spend_dict = {
            row.spend_date: float(row.daily_spend) for row in google_spend_raw
        }
        orders_dict = {row.order_date: int(row.order_count) for row in orders_raw}
        
        # Get all dates that have spend data
        all_spend_dates = sorted(
            set(meta_spend_dict.keys()) | set(google_spend_dict.keys())
        )
        
        if len(all_spend_dates) < 14:
            raise ValueError(
                f"Insufficient data for training: only {len(all_spend_dates)} days "
                f"with ad spend. Need at least 14 days."
            )
        
        # Prepare aligned arrays for each channel
        meta_spend_list = []
        meta_conv_list = []
        google_spend_list = []
        google_conv_list = []
        
        for spend_date in all_spend_dates:
            meta_spend = meta_spend_dict.get(spend_date, 0.0)
            google_spend = google_spend_dict.get(spend_date, 0.0)
            total_spend = meta_spend + google_spend
            
            # Get orders for this date
            orders = orders_dict.get(spend_date, 0)
            
            # Simple attribution: split conversions proportionally to spend
            # (In future: use proper attribution model)
            if total_spend > 0:
                meta_conv = orders * (meta_spend / total_spend)
                google_conv = orders * (google_spend / total_spend)
            else:
                # No spend = no attributed conversions
                meta_conv = 0.0
                google_conv = 0.0
            
            # Only include days with non-zero spend for that channel
            if meta_spend > 0:
                meta_spend_list.append(meta_spend)
                meta_conv_list.append(meta_conv)
            
            if google_spend > 0:
                google_spend_list.append(google_spend)
                google_conv_list.append(google_conv)
        
        # Validate each channel has enough data — detect single-channel mode
        meta_ok = len(meta_spend_list) >= 7
        google_ok = len(google_spend_list) >= 7

        if not meta_ok and not google_ok:
            raise ValueError(
                f"Insufficient data for both channels. "
                f"Meta: {len(meta_spend_list)} days, Google: {len(google_spend_list)} days. "
                f"Need at least 7 days per active channel."
            )

        if not meta_ok and google_ok:
            log_data_quality_issue(
                tenant_id=tenant_id,
                strategy_name="budget_allocation",
                issue_type="insufficient_meta_data",
                details={"days_with_spend": len(meta_spend_list), "required": 7},
                severity="warning",
            )
            self.single_channel_mode = True
            self.active_channel = "google"

        if not google_ok and meta_ok:
            log_data_quality_issue(
                tenant_id=tenant_id,
                strategy_name="budget_allocation",
                issue_type="insufficient_google_data",
                details={"days_with_spend": len(google_spend_list), "required": 7},
                severity="warning",
            )
            self.single_channel_mode = True
            self.active_channel = "meta"
        
        # Calculate current budget (average daily spend over last 7 days)
        recent_dates = all_spend_dates[-7:]
        recent_total_spend = sum(
            meta_spend_dict.get(d, 0.0) + google_spend_dict.get(d, 0.0)
            for d in recent_dates
        )
        self.current_budget = recent_total_spend / 7  # Average daily budget
        
        return {
            "meta": {
                "spend": np.array(meta_spend_list),
                "conversions": np.array(meta_conv_list),
            },
            "google": {
                "spend": np.array(google_spend_list),
                "conversions": np.array(google_conv_list),
            },
            "total_budget": self.current_budget,
        }
    
    def train_models(self) -> None:
        """Train Hill saturation curves for Meta and Google channels.
        
        Fits separate Hill curves to each channel's spend/conversion data.
        Stores curves in self.meta_curve and self.google_curve.
        Saves fitted models to S3 and creates FittedModel database records.
        
        Raises:
            ValueError: If training data is None or has insufficient points
            RuntimeError: If curve fitting fails for either channel
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
        
        meta_data = self.training_data["meta"]
        google_data = self.training_data["google"]
        
        # Fit Meta curve (only if channel has data)
        if self.active_channel in ("meta", "both") and len(meta_data["spend"]) >= 7:
            try:
                self.meta_curve = HillCurve()
                self.meta_curve.fit(
                    spend_data=meta_data["spend"],
                    conversion_data=meta_data["conversions"],
                )
                meta_rmse = self.meta_curve.calculate_rmse(
                    spend_data=meta_data["spend"],
                    conversion_data=meta_data["conversions"],
                )
                meta_params = self.meta_curve.get_params()
                meta_predictions = self.meta_curve.predict(meta_data["spend"])
                meta_r2 = self._calculate_r2(
                    actual=meta_data["conversions"],
                    predicted=meta_predictions,
                )
                self._save_fitted_model(
                    curve=self.meta_curve,
                    model_type="meta_saturation_curve",
                    params=meta_params,
                    metrics={"rmse": meta_rmse, "r2": meta_r2},
                )
            except Exception as e:
                raise RuntimeError(f"Failed to fit Meta Hill curve: {e}") from e
        
        # Fit Google curve (only if channel has data)
        if self.active_channel in ("google", "both") and len(google_data["spend"]) >= 7:
            try:
                self.google_curve = HillCurve()
                self.google_curve.fit(
                    spend_data=google_data["spend"],
                    conversion_data=google_data["conversions"],
                )
                google_rmse = self.google_curve.calculate_rmse(
                    spend_data=google_data["spend"],
                    conversion_data=google_data["conversions"],
                )
                google_params = self.google_curve.get_params()
                google_predictions = self.google_curve.predict(google_data["spend"])
                google_r2 = self._calculate_r2(
                    actual=google_data["conversions"],
                    predicted=google_predictions,
                )
                self._save_fitted_model(
                    curve=self.google_curve,
                    model_type="google_saturation_curve",
                    params=google_params,
                    metrics={"rmse": google_rmse, "r2": google_r2},
                )
            except Exception as e:
                raise RuntimeError(f"Failed to fit Google Hill curve: {e}") from e
        
        # Store models in parent class attribute
        self.models = {
            "meta": self.meta_curve,
            "google": self.google_curve,
        }
    
    def _optimize_single_channel(self) -> dict[str, Any]:
        """Saturation analysis for brands running only one ad channel.

        Instead of cross-channel reallocation, analyses whether the single
        active channel is approaching diminishing returns and recommends a
        spend cap or channel diversification.
        """
        channel = self.active_channel  # "meta" or "google"
        curve = self.meta_curve if channel == "meta" else self.google_curve
        data_key = channel  # "meta" or "google"

        if curve is None:
            raise RuntimeError(f"No fitted curve for {channel}")

        spend_data = self.training_data[data_key]["spend"]
        conv_data = self.training_data[data_key]["conversions"]

        current_spend = float(np.mean(spend_data[-7:]))
        current_conv = float(curve.predict(current_spend)[0])

        # Find saturation knee: spend where marginal return drops below 30% of
        # the return at 10% of current spend (a simple efficiency threshold)
        low_spend = current_spend * 0.1
        baseline_marginal = float(
            curve.predict(low_spend * 1.1)[0] - curve.predict(low_spend)[0]
        )
        threshold = baseline_marginal * 0.30

        # Walk up spend from 10% to 200% to find knee
        knee_spend = current_spend  # default: no saturation detected
        test_points = np.linspace(low_spend, current_spend * 2, 100)
        for i in range(1, len(test_points)):
            marginal = float(
                curve.predict(test_points[i])[0] - curve.predict(test_points[i - 1])[0]
            )
            if marginal < threshold:
                knee_spend = float(test_points[i])
                break

        saturated = current_spend > knee_spend * 1.05
        saturation_pct = min(100, round(current_spend / knee_spend * 100))

        # Revenue at current vs knee spend
        knee_conv = float(curve.predict(knee_spend)[0])
        aov = getattr(self, "aov", 0.0)
        wasted_daily = max(0.0, (current_conv - knee_conv)) * aov

        # Efficiency trend: first-quarter vs last-quarter of data
        q = max(1, len(spend_data) // 4)
        early_eff = float(np.mean(conv_data[:q] / (spend_data[:q] / 1000 + 1e-9)))
        late_eff = float(np.mean(conv_data[-q:] / (spend_data[-q:] / 1000 + 1e-9)))
        eff_change_pct = round((late_eff - early_eff) / (early_eff + 1e-9) * 100, 1)

        result: dict[str, Any] = {
            "mode": "single_channel",
            "channel": channel,
            "current_spend": current_spend,
            "current_conversions": current_conv,
            "knee_spend": knee_spend,
            "saturated": saturated,
            "saturation_pct": saturation_pct,
            "efficiency_change_pct": eff_change_pct,
            "wasted_daily_revenue": wasted_daily,
            "aov": aov,
            # Dummy lift fields (cross-channel not applicable)
            "lift_pct": 0.0,
            "daily_revenue_impact": -wasted_daily if saturated else 0.0,
        }
        self.optimization_result = result
        return result

    def optimize(self) -> dict[str, Any]:
        """Find optimal budget allocation using constrained optimization.
        
        Uses scipy.optimize.minimize with SLSQP algorithm to maximize total
        conversions subject to budget constraints:
        - Total spend = current budget
        - 15% ≤ meta_spend / total_budget ≤ 60%
        - 15% ≤ google_spend / total_budget ≤ 60%
        
        Returns:
            Dictionary with optimization results:
            {
                'meta_spend': optimal Meta daily spend,
                'google_spend': optimal Google daily spend,
                'meta_pct': Meta percentage of budget,
                'google_pct': Google percentage of budget,
                'expected_conversions': total predicted conversions,
                'current_conversions': baseline conversions,
                'lift_pct': expected improvement percentage
            }
        
        Raises:
            RuntimeError: If models are not trained or optimization fails
        """
        # Single-channel brands: run saturation analysis instead
        if self.single_channel_mode:
            return self._optimize_single_channel()

        try:
            if self.meta_curve is None or self.google_curve is None:
                raise RuntimeError("Must train models before optimizing")
            
            if self.current_budget is None or self.current_budget <= 0:
                raise RuntimeError("Invalid current budget")
            
            # Objective function: maximize total conversions (minimize negative)
            def objective(spend_allocation: np.ndarray) -> float:
                """Objective function: negative total conversions (for minimization)."""
                assert self.meta_curve is not None
                assert self.google_curve is not None
                meta_spend, google_spend = spend_allocation
                meta_conv = self.meta_curve.predict(meta_spend)[0]
                google_conv = self.google_curve.predict(google_spend)[0]
                total_conv = meta_conv + google_conv
                return -total_conv  # Negative because we minimize
            
            # Constraints
            constraints = [
                # Total spend equals current budget
                {
                    "type": "eq",
                    "fun": lambda x: x[0] + x[1] - self.current_budget,
                },
            ]
            
            # Bounds: 15% to 60% of budget per channel
            bounds = [
                (0.15 * self.current_budget, 0.60 * self.current_budget),  # Meta
                (0.15 * self.current_budget, 0.60 * self.current_budget),  # Google
            ]
            
            # Initial guess: current allocation (proportional to recent spend)
            meta_data = self.training_data["meta"]
            google_data = self.training_data["google"]
            current_meta = float(np.mean(meta_data["spend"][-7:]))
            current_google = float(np.mean(google_data["spend"][-7:]))
            current_total = current_meta + current_google
            
            if current_total > 0:
                initial_meta = self.current_budget * (current_meta / current_total)
                initial_google = self.current_budget * (current_google / current_total)
            else:
                # Fallback: 50/50 split
                initial_meta = self.current_budget * 0.5
                initial_google = self.current_budget * 0.5
            
            initial_guess = np.array([initial_meta, initial_google])
            
            # Run optimization
            try:
                result = minimize(
                    fun=objective,
                    x0=initial_guess,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options={"maxiter": 100, "ftol": 1e-6},
                )
                
                if not result.success:
                    raise RuntimeError(
                        f"Optimization failed to converge: {result.message}"
                    )
                
            except Exception as e:
                raise RuntimeError(f"Optimization error: {e}") from e
            
            # Extract optimal allocation
            optimal_meta, optimal_google = result.x
            
            # Calculate expected conversions
            expected_meta_conv = self.meta_curve.predict(optimal_meta)[0]
            expected_google_conv = self.google_curve.predict(optimal_google)[0]
            expected_total_conv = expected_meta_conv + expected_google_conv
            
            # Calculate current baseline conversions
            current_meta_conv = self.meta_curve.predict(current_meta)[0]
            current_google_conv = self.google_curve.predict(current_google)[0]
            current_total_conv = current_meta_conv + current_google_conv
            
            # Calculate lift
            lift_pct = (
                ((expected_total_conv - current_total_conv) / current_total_conv * 100)
                if current_total_conv > 0
                else 0.0
            )
            
            # Calculate revenue impact using AOV
            conversion_lift = expected_total_conv - current_total_conv
            daily_revenue_impact = conversion_lift * self.aov if hasattr(self, 'aov') else 0.0
            
            # Calculate current efficiency metrics (conversions per rupee spent)
            current_meta_efficiency = current_meta_conv / current_meta if current_meta > 0 else 0.0
            current_google_efficiency = current_google_conv / current_google if current_google > 0 else 0.0
            
            # Calculate optimal efficiency metrics
            optimal_meta_efficiency = expected_meta_conv / optimal_meta if optimal_meta > 0 else 0.0
            optimal_google_efficiency = expected_google_conv / optimal_google if optimal_google > 0 else 0.0
            
            # Calculate marginal returns (how much each channel responds to additional spend)
            meta_marginal = self.meta_curve.predict(current_meta * 1.1)[0] - current_meta_conv
            google_marginal = self.google_curve.predict(current_google * 1.1)[0] - current_google_conv
            
            # Determine root cause (which channel is saturated vs has headroom)
            meta_spend_change = optimal_meta - current_meta
            google_spend_change = optimal_google - current_google
            
            # Build optimization result with rich context
            result = {
                "meta_spend": float(optimal_meta),
                "google_spend": float(optimal_google),
                "meta_pct": float(optimal_meta / self.current_budget * 100),
                "google_pct": float(optimal_google / self.current_budget * 100),
                "expected_conversions": float(expected_total_conv),
                "current_conversions": float(current_total_conv),
                "lift_pct": float(lift_pct),
                "daily_revenue_impact": float(daily_revenue_impact),
                "aov": float(self.aov) if hasattr(self, 'aov') else 0.0,
                # Current state per channel
                "current_meta_spend": float(current_meta),
                "current_google_spend": float(current_google),
                "current_meta_conversions": float(current_meta_conv),
                "current_google_conversions": float(current_google_conv),
                # Efficiency metrics (conversions per ₹1000 spent)
                "current_meta_efficiency": float(current_meta_efficiency * 1000),
                "current_google_efficiency": float(current_google_efficiency * 1000),
                "optimal_meta_efficiency": float(optimal_meta_efficiency * 1000),
                "optimal_google_efficiency": float(optimal_google_efficiency * 1000),
                # Marginal returns
                "meta_marginal_return": float(meta_marginal),
                "google_marginal_return": float(google_marginal),
                # Spend changes
                "meta_spend_change": float(meta_spend_change),
                "google_spend_change": float(google_spend_change),
                "meta_spend_change_pct": float((meta_spend_change / current_meta * 100) if current_meta > 0 else 0.0),
                "google_spend_change_pct": float((google_spend_change / current_google * 100) if current_google > 0 else 0.0),
            }
            
            # Store result in instance variable
            self.optimization_result = result
            
            # Update OptimizationRun record in database
            if self.optimization_run_id is not None:
                optimization_run = self.db.get(
                    OptimizationRun, self.optimization_run_id
                )
                if optimization_run:
                    optimization_run.run_status = "success"
                    optimization_run.completed_at = datetime.now(UTC)
                    optimization_run.optimization_result = result
                    
                    # Calculate execution time
                    if optimization_run.started_at:
                        execution_time = (
                            optimization_run.completed_at - optimization_run.started_at
                        ).total_seconds()
                        optimization_run.execution_time_seconds = execution_time
                    
                    # Store input snapshot metadata
                    optimization_run.input_snapshot_ids = [
                        {
                            "current_meta_spend": float(current_meta),
                            "current_google_spend": float(current_google),
                            "lookback_days": len(meta_data["spend"]),
                            "total_budget": float(self.current_budget),
                        }
                    ]
                    
                    self.db.commit()
            
            return result
        
        except Exception as e:
            # Mark optimization run as failed
            if self.optimization_run_id is not None:
                optimization_run = self.db.get(
                    OptimizationRun, self.optimization_run_id
                )
                if optimization_run:
                    optimization_run.run_status = "failed"
                    optimization_run.completed_at = datetime.now(UTC)
                    # Truncate to field limit
                    optimization_run.error_message = str(e)[:1000]
                    
                    # Calculate execution time even for failures
                    if optimization_run.started_at:
                        execution_time = (
                            optimization_run.completed_at - optimization_run.started_at
                        ).total_seconds()
                        optimization_run.execution_time_seconds = execution_time
                    
                    self.db.commit()
            
            # Re-raise the exception
            raise

    
    def generate_recommendation(self) -> dict[str, Any]:
        """Generate recommendation payload from optimization result.
        
        Transforms the optimization result into a recommendation format
        compatible with the AlpMark recommendations schema.
        
        Returns:
            Dictionary with recommendation details:
            {
                'recommendation_text': human-readable description,
                'action_items': list of specific actions,
                'expected_impact': metrics dictionary,
                'confidence_level': model confidence (0.0 to 1.0),
                'domain': 'acquisition',
                'priority': 'high' | 'medium' | 'low'
            }
        
        Raises:
            ValueError: If optimization_result is None
        """
        if self.optimization_result is None:
            raise ValueError("Must run optimization before generating recommendation")
        
        opt = self.optimization_result
        
        # Calculate confidence based on model fit quality
        if self.meta_curve is None or self.google_curve is None:
            raise RuntimeError("Models not trained")
        
        meta_rmse = self.meta_curve.calculate_rmse(
            spend_data=self.training_data["meta"]["spend"],
            conversion_data=self.training_data["meta"]["conversions"],
        )
        google_rmse = self.google_curve.calculate_rmse(
            spend_data=self.training_data["google"]["spend"],
            conversion_data=self.training_data["google"]["conversions"],
        )
        
        # Lower RMSE = higher confidence (capped at 0.95)
        meta_conf = min(0.95, 1.0 - (meta_rmse / 100))
        google_conf = min(0.95, 1.0 - (google_rmse / 100))
        overall_confidence = (meta_conf + google_conf) / 2
        
        # Build recommendation text
        recommendation_text = (
            f"Reallocate daily ad budget for maximum conversions: "
            f"Meta {opt['meta_pct']:.1f}% (₹{opt['meta_spend']:,.0f}), "
            f"Google {opt['google_pct']:.1f}% (₹{opt['google_spend']:,.0f}). "
            f"Expected lift: +{opt['lift_pct']:.1f}% conversions "
            f"({opt['expected_conversions']:.0f} vs {opt['current_conversions']:.0f})."
        )
        
        # Action items
        action_items = [
            (
                f"Adjust Meta Ads daily budget to ₹{opt['meta_spend']:,.0f} "
                f"({opt['meta_pct']:.1f}% of total)"
            ),
            (
                f"Adjust Google Ads daily budget to ₹{opt['google_spend']:,.0f} "
                f"({opt['google_pct']:.1f}% of total)"
            ),
            "Monitor conversion performance over 7 days",
            "Re-optimize after collecting new data",
        ]
        
        # Expected impact metrics
        expected_impact = {
            "conversions_lift_pct": opt["lift_pct"],
            "expected_daily_conversions": opt["expected_conversions"],
            "current_daily_conversions": opt["current_conversions"],
            "meta_allocation_pct": opt["meta_pct"],
            "google_allocation_pct": opt["google_pct"],
        }
        
        # Priority based on lift magnitude
        if opt["lift_pct"] > 10:
            priority = "high"
        elif opt["lift_pct"] > 5:
            priority = "medium"
        else:
            priority = "low"
        
        return {
            "recommendation_text": recommendation_text,
            "action_items": action_items,
            "expected_impact": expected_impact,
            "confidence_level": float(overall_confidence),
            "domain": "acquisition",
            "priority": priority,
        }
    
    def _create_single_channel_recommendation(self, opt: dict[str, Any]) -> Recommendation:
        """Create a saturation-warning recommendation for single-channel brands."""
        channel_name = "Meta" if opt["channel"] == "meta" else "Google"
        today = date.today()
        saturated = opt["saturated"]
        eff_change = opt["efficiency_change_pct"]
        current_spend = opt["current_spend"]
        knee_spend = opt["knee_spend"]
        wasted = opt["wasted_daily_revenue"]
        aov = opt["aov"]

        if saturated:
            signal_summary = (
                f"{channel_name} spend is ₹{current_spend:,.0f}/day — "
                f"{opt['saturation_pct']}% past the saturation knee (₹{knee_spend:,.0f}/day). "
                f"Efficiency dropped {abs(eff_change):.1f}% over the period."
            )
            suggested_action = (
                f"Cap {channel_name} spend at ₹{knee_spend:,.0f}/day to eliminate "
                f"~₹{wasted:,.0f}/day in diminishing-return waste. "
                f"Reallocate the saved ₹{current_spend - knee_spend:,.0f}/day "
                f"to test a second acquisition channel."
            )
            impact = wasted
            priority = 80 if wasted > 5000 else 55
        else:
            signal_summary = (
                f"{channel_name} is your only active acquisition channel. "
                f"Efficiency has changed {eff_change:+.1f}% over the period. "
                f"Spend is ₹{current_spend:,.0f}/day — below saturation point."
            )
            suggested_action = (
                f"Your {channel_name} spend is not yet saturating. "
                f"Consider testing a second channel (e.g., {'Google' if channel_name == 'Meta' else 'Meta'}) "
                f"to reduce single-channel dependency and unlock additional growth."
            )
            impact = 0.0
            priority = 35

        optimization_metadata = {
            "optimization_run_id": str(self.optimization_run_id),
            "mode": "single_channel",
            "channel": opt["channel"],
            "current_spend": current_spend,
            "knee_spend": knee_spend,
            "saturated": saturated,
            "saturation_pct": opt["saturation_pct"],
            "efficiency_change_pct": eff_change,
            "wasted_daily_revenue": wasted,
            "aov": aov,
        }

        # Dedup: if an open recommendation already exists, return it unchanged.
        # Only create a new one if the previous was acted on or doesn't exist.
        rule_id = f"OPT-SATURATION-{opt['channel'].upper()}"
        open_statuses = ("new", "reviewed")
        existing = self.db.query(Recommendation).filter(
            Recommendation.tenant_id == self.tenant_id,
            Recommendation.rule_id == rule_id,
            Recommendation.status.in_(open_statuses),
        ).first()
        if existing:
            return existing

        fitted_model = self.db.query(FittedModel).filter(
            FittedModel.optimization_run_id == self.optimization_run_id,
        ).first()

        recommendation = Recommendation(
            tenant_id=self.tenant_id,
            rule_id=rule_id,
            domain="acquisition",
            snapshot_date=today,
            affected_area=f"{channel_name} Ads Saturation",
            signal_summary=signal_summary,
            suggested_action=suggested_action,
            estimated_impact=impact,
            confidence_level="medium",
            confidence_score=0.6,
            data_freshness_context=f"Based on {self.lookback_days} days of {channel_name} spend data",
            status="new",
            priority=priority,
            impact_score=impact,
            evidence=opt,
            data_sources=[opt["channel"], "shopify"],
            source="optimization",
            optimization_metadata=optimization_metadata,
            fitted_model_id=fitted_model.id if fitted_model else None,
        )
        self.db.add(recommendation)
        self.db.flush()
        return recommendation

    def create_recommendation_record(self) -> Recommendation:
        """Create a Recommendation database record from optimization result.
        
        This method creates an actual user-facing recommendation with
        source='optimization' and links to the fitted models.
        
        Returns:
            Recommendation: Persisted recommendation record
        
        Raises:
            ValueError: If optimization_result is None
            RuntimeError: If required data is missing
        """
        if self.optimization_result is None:
            raise ValueError("Must run optimization before creating recommendation")
        
        if self.tenant_id is None:
            raise RuntimeError("tenant_id not set")
        
        if self.optimization_run_id is None:
            raise RuntimeError("optimization_run_id not set")
        
        opt = self.optimization_result

        # ── Single-channel path ───────────────────────────────────────────────
        if self.single_channel_mode:
            return self._create_single_channel_recommendation(opt)

        # ── Dual-channel path (existing logic below) ──────────────────────────
        
        # Get model metadata for optimization_metadata field
        meta_model = self.db.query(FittedModel).filter(
            FittedModel.optimization_run_id == self.optimization_run_id,
            FittedModel.model_type == "meta_saturation_curve",
        ).first()
        
        google_model = self.db.query(FittedModel).filter(
            FittedModel.optimization_run_id == self.optimization_run_id,
            FittedModel.model_type == "google_saturation_curve",
        ).first()
        
        # Build optimization metadata with rich channel-level detail
        optimization_metadata = {
            "optimization_run_id": str(self.optimization_run_id),
            "expected_conversions": opt["expected_conversions"],
            "current_conversions": opt["current_conversions"],
            "lift_pct": opt["lift_pct"],
            "daily_revenue_impact": opt.get("daily_revenue_impact", 0.0),
            "aov": opt.get("aov", 0.0),
            "meta_allocation": {
                "current_spend": opt.get("current_meta_spend", 0.0),
                "optimal_spend": opt["meta_spend"],
                "current_pct": opt.get("current_meta_spend", 0.0) / self.current_budget * 100 if self.current_budget > 0 else 0,
                "optimal_pct": opt["meta_pct"],
                "spend_change": opt.get("meta_spend_change", 0.0),
                "current_efficiency": opt.get("current_meta_efficiency", 0.0),
                "optimal_efficiency": opt.get("optimal_meta_efficiency", 0.0),
            },
            "google_allocation": {
                "current_spend": opt.get("current_google_spend", 0.0),
                "optimal_spend": opt["google_spend"],
                "current_pct": opt.get("current_google_spend", 0.0) / self.current_budget * 100 if self.current_budget > 0 else 0,
                "optimal_pct": opt["google_pct"],
                "spend_change": opt.get("google_spend_change", 0.0),
                "current_efficiency": opt.get("current_google_efficiency", 0.0),
                "optimal_efficiency": opt.get("optimal_google_efficiency", 0.0),
            },
            "model_accuracy": {
                "meta_r2": (
                    meta_model.accuracy_metrics.get("r2")
                    if meta_model and meta_model.accuracy_metrics
                    else None
                ),
                "google_r2": (
                    google_model.accuracy_metrics.get("r2")
                    if google_model and google_model.accuracy_metrics
                    else None
                ),
            },
        }
        
        # Calculate confidence score (average of model R² scores)
        confidence_score = 0.5  # default
        if (
            meta_model
            and meta_model.accuracy_metrics
            and google_model
            and google_model.accuracy_metrics
        ):
            meta_r2 = meta_model.accuracy_metrics.get("r2", 0.0)
            google_r2 = google_model.accuracy_metrics.get("r2", 0.0)
            confidence_score = (meta_r2 + google_r2) / 2
        
        # Map numeric confidence to categorical level
        confidence_level = self._map_confidence_to_level(confidence_score)
        
        # Determine root cause and build rich signal summary
        meta_change = opt.get("meta_spend_change", 0.0)
        google_change = opt.get("google_spend_change", 0.0)
        
        # Identify which channel is saturated vs has headroom
        if abs(meta_change) > abs(google_change):
            if meta_change < 0:
                root_cause = f"Meta Ads hitting saturation: efficiency declining from {opt.get('current_meta_efficiency', 0):.2f} to {opt.get('optimal_meta_efficiency', 0):.2f} conversions per ₹1k"
                primary_channel = "Meta"
                change_direction = "reduce"
            else:
                root_cause = f"Meta Ads has untapped potential: could improve from {opt.get('current_meta_efficiency', 0):.2f} to {opt.get('optimal_meta_efficiency', 0):.2f} conversions per ₹1k"
                primary_channel = "Meta"
                change_direction = "increase"
        else:
            if google_change < 0:
                root_cause = f"Google Ads hitting saturation: efficiency declining from {opt.get('current_google_efficiency', 0):.2f} to {opt.get('optimal_google_efficiency', 0):.2f} conversions per ₹1k"
                primary_channel = "Google"
                change_direction = "reduce"
            else:
                root_cause = f"Google Ads has untapped potential: could improve from {opt.get('current_google_efficiency', 0):.2f} to {opt.get('optimal_google_efficiency', 0):.2f} conversions per ₹1k"
                primary_channel = "Google"
                change_direction = "increase"
        
        signal_summary = (
            f"Meta efficiency {opt.get('current_meta_efficiency', opt.get('meta_allocation', {}).get('current_efficiency', 0)):.2f}× "
            f"vs Google {opt.get('current_google_efficiency', opt.get('google_allocation', {}).get('current_efficiency', 0)):.2f}× — "
            f"reallocate ₹{abs(opt.get('meta_allocation', {}).get('spend_change', 0) or 0):,.0f}/day "
            f"for +{opt.get('lift_pct', 0):.1f}% conversion lift"
        )

        suggested_action = (
            f"{change_direction.capitalize()} {primary_channel} to ₹{opt['meta_spend' if primary_channel == 'Meta' else 'google_spend']:,.0f}/day "
            f"(currently ₹{opt.get('current_meta_spend' if primary_channel == 'Meta' else 'current_google_spend', 0):,.0f}/day). "
            f"Adjust {'Google' if primary_channel == 'Meta' else 'Meta'} to ₹{opt['google_spend' if primary_channel == 'Meta' else 'meta_spend']:,.0f}/day "
            f"to maintain total budget of ₹{self.current_budget:,.0f}/day"
        )

        
        # Calculate priority based on revenue impact
        daily_revenue_impact = opt.get("daily_revenue_impact", 0.0)
        if daily_revenue_impact > 10000:  # ₹10k+/day
            priority = 90  # high
        elif daily_revenue_impact > 5000:  # ₹5k+/day
            priority = 70  # medium-high
        elif daily_revenue_impact > 1000:  # ₹1k+/day
            priority = 50  # medium
        else:
            priority = 30  # low
        
        # Dedup: if an open recommendation already exists, return it unchanged.
        # Only create a new one if the previous was acted on or doesn't exist.
        today = date.today()
        open_statuses = ("new", "reviewed")
        existing = self.db.query(Recommendation).filter(
            Recommendation.tenant_id == self.tenant_id,
            Recommendation.rule_id == "OPT-BUDGET-001",
            Recommendation.status.in_(open_statuses),
        ).first()
        if existing:
            return existing
        self.db.flush()
        
        # Create recommendation
        recommendation = Recommendation(
            tenant_id=self.tenant_id,
            rule_id="OPT-BUDGET-001",  # Optimization-based rule ID
            domain="acquisition",
            snapshot_date=today,
            affected_area=f"{primary_channel} Ads Budget Reallocation",
            signal_summary=signal_summary,
            suggested_action=suggested_action,
            estimated_impact=daily_revenue_impact * 30,  # Monthly revenue impact
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            data_freshness_context=(
                f"Based on {self.lookback_days} days of ad spend "
                f"and conversion data"
            ),
            status="new",
            priority=priority,
            impact_score=daily_revenue_impact,  # Revenue impact as score
            evidence={
                # Overall impact
                "current_conversions": opt["current_conversions"],
                "expected_conversions": opt["expected_conversions"],
                "lift_pct": opt["lift_pct"],
                "daily_revenue_impact": opt.get("daily_revenue_impact", 0.0),
                "aov": opt.get("aov", 0.0),
                # Meta channel detail
                "meta": {
                    "current_spend": opt.get("current_meta_spend", 0.0),
                    "optimal_spend": opt["meta_spend"],
                    "spend_change": opt.get("meta_spend_change", 0.0),
                    "spend_change_pct": opt.get("meta_spend_change_pct", 0.0),
                    "current_conversions": opt.get("current_meta_conversions", 0.0),
                    "current_efficiency": opt.get("current_meta_efficiency", 0.0),
                    "optimal_efficiency": opt.get("optimal_meta_efficiency", 0.0),
                    "marginal_return": opt.get("meta_marginal_return", 0.0),
                },
                # Google channel detail
                "google": {
                    "current_spend": opt.get("current_google_spend", 0.0),
                    "optimal_spend": opt["google_spend"],
                    "spend_change": opt.get("google_spend_change", 0.0),
                    "spend_change_pct": opt.get("google_spend_change_pct", 0.0),
                    "current_conversions": opt.get("current_google_conversions", 0.0),
                    "current_efficiency": opt.get("current_google_efficiency", 0.0),
                    "optimal_efficiency": opt.get("optimal_google_efficiency", 0.0),
                    "marginal_return": opt.get("google_marginal_return", 0.0),
                },
                # Model quality
                "model_r2_meta": (
                    meta_model.accuracy_metrics.get("r2")
                    if meta_model and meta_model.accuracy_metrics
                    else None
                ),
                "model_r2_google": (
                    google_model.accuracy_metrics.get("r2")
                    if google_model and google_model.accuracy_metrics
                    else None
                ),
            },
            data_sources=["meta", "google_ads", "shopify"],
            source="optimization",
            optimization_metadata=optimization_metadata,
            fitted_model_id=meta_model.id if meta_model else None,
        )
        
        self.db.add(recommendation)
        self.db.flush()  # Get the ID without committing
        
        return recommendation
    
    def _map_confidence_to_level(self, confidence_score: float) -> str:
        """Map numeric confidence score (0-1) to categorical level.
        
        Args:
            confidence_score: Numeric confidence (0.0 to 1.0)
        
        Returns:
            Confidence level: very_low, low, medium, high, very_high
        """
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
    
    def _calculate_r2(
        self,
        actual: np.ndarray,
        predicted: np.ndarray,
    ) -> float:
        """Calculate R² (coefficient of determination) for model fit.
        
        R² represents the proportion of variance in the dependent variable
        that is predictable from the independent variable. Ranges from 0 to 1,
        where 1 indicates perfect fit.
        
        Args:
            actual: Actual observed values
            predicted: Model predicted values
        
        Returns:
            R² score (0.0 to 1.0, or negative for very poor fits)
        """
        # Total sum of squares (variance in actual data)
        ss_tot = np.sum((actual - np.mean(actual)) ** 2)
        
        # Residual sum of squares (unexplained variance)
        ss_res = np.sum((actual - predicted) ** 2)
        
        # R² = 1 - (unexplained variance / total variance)
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
        """Save fitted model to S3 and create database record.
        
        Args:
            curve: Fitted HillCurve instance to save
            model_type: Type identifier (e.g., "meta_saturation_curve")
            params: Model parameters from get_params()
            metrics: Training metrics (rmse, r2, etc.)
        
        Raises:
            RuntimeError: If S3 upload or database insert fails
        """
        if self.tenant_id is None:
            raise RuntimeError("tenant_id not set")
        
        if self.optimization_run_id is None:
            raise RuntimeError("optimization_run_id not set")
        
        # Generate S3 key with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        s3_key = f"{self.tenant_id}/{model_type}_{timestamp}.pkl"
        
        # Upload pickled model to S3
        try:
            upload_model(model_obj=curve, s3_key=s3_key)
        except Exception as e:
            raise RuntimeError(f"Failed to upload model to S3: {e}") from e
        
        # Create database record
        try:
            fitted_model = FittedModel(
                tenant_id=self.tenant_id,
                strategy_id=self.strategy_id,
                optimization_run_id=self.optimization_run_id,
                model_type=model_type,
                s3_key=s3_key,
                trained_at=datetime.now(UTC),
                model_metadata={
                    "params": params,
                    "training_date": datetime.now(UTC).isoformat(),
                },
                accuracy_metrics=metrics,
            )
            self.db.add(fitted_model)
            self.db.commit()
        except Exception as e:
            # Rollback on database error
            self.db.rollback()
            raise RuntimeError(f"Failed to save fitted model to database: {e}") from e
