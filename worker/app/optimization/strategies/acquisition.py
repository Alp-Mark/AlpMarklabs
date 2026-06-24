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

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
from backend.app.db.models import GoogleAdSpend, MetaAdSpend, ShopifyOrder
from scipy.optimize import minimize
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from worker.app.optimization.models.saturation import HillCurve
from worker.app.optimization.strategies.base import BaseOptimizer
from worker.app.optimization.utils.monitoring import (
    log_data_quality_issue,
    log_model_performance,
)


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
        
        # Fetch order counts by date (proxy for conversions)
        orders_query = (
            select(
                func.date(ShopifyOrder.order_created_at).label("order_date"),
                func.count().label("order_count"),
            )
            .where(ShopifyOrder.tenant_id == tenant_id)
            .where(func.date(ShopifyOrder.order_created_at) >= start_date)
            .where(func.date(ShopifyOrder.order_created_at) <= end_date)
            .where(ShopifyOrder.is_refunded == False)  # noqa: E712
            .group_by(func.date(ShopifyOrder.order_created_at))
            .order_by(func.date(ShopifyOrder.order_created_at))
        )
        orders_raw = self.db.execute(orders_query).all()
        
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
        
        # Validate each channel has enough data
        if len(meta_spend_list) < 7:
            log_data_quality_issue(
                tenant_id=tenant_id,
                strategy_name="budget_allocation",
                issue_type="insufficient_meta_data",
                details={"days_with_spend": len(meta_spend_list), "required": 7},
                severity="error",
            )
            raise ValueError(
                f"Insufficient Meta ad spend data: only {len(meta_spend_list)} days. "
                f"Need at least 7 days."
            )
        
        if len(google_spend_list) < 7:
            log_data_quality_issue(
                tenant_id=tenant_id,
                strategy_name="budget_allocation",
                issue_type="insufficient_google_data",
                details={"days_with_spend": len(google_spend_list), "required": 7},
                severity="error",
            )
            raise ValueError(
                f"Insufficient Google ad spend data: only "
                f"{len(google_spend_list)} days. Need at least 7 days."
            )
        
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
        
        Raises:
            ValueError: If training data is None or has insufficient points
            RuntimeError: If curve fitting fails for either channel
        """
        if self.training_data is None:
            raise ValueError("Must call fetch_training_data before training models")
        
        meta_data = self.training_data["meta"]
        google_data = self.training_data["google"]
        
        # Fit Meta curve
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
            
            # Log performance (no tenant_id yet - called from base)
            # log_model_performance will be called later with full context
        except Exception as e:
            raise RuntimeError(f"Failed to fit Meta Hill curve: {e}") from e
        
        # Fit Google curve
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
            
            # Log performance (no tenant_id yet - called from base)
            # log_model_performance will be called later with full context
        except Exception as e:
            raise RuntimeError(f"Failed to fit Google Hill curve: {e}") from e
        
        # Store models in parent class attribute
        self.models = {
            "meta": self.meta_curve,
            "google": self.google_curve,
        }
    
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
        
        return {
            "meta_spend": float(optimal_meta),
            "google_spend": float(optimal_google),
            "meta_pct": float(optimal_meta / self.current_budget * 100),
            "google_pct": float(optimal_google / self.current_budget * 100),
            "expected_conversions": float(expected_total_conv),
            "current_conversions": float(current_total_conv),
            "lift_pct": float(lift_pct),
        }
    
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
