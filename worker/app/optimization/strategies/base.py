"""Base optimizer class for all optimization strategies.

This module defines the abstract interface that all optimization strategies
must implement. The BaseOptimizer class enforces a consistent workflow across
different optimizer types while allowing domain-specific customization of each step.

Workflow:
1. fetch_training_data() - Retrieve historical data for model training
2. train_models() - Fit mathematical models (Hill, elasticity, forecasting)
3. optimize() - Run optimization algorithm to find best solution
4. generate_recommendation() - Convert result into actionable recommendation

Example:
    class BudgetAllocationOptimizer(BaseOptimizer):
        def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> pd.DataFrame:
            # Query orders, spend data from database
            return df
        
        def train_models(self) -> None:
            # Fit Hill saturation curves for each channel
            self.models = fit_hill_curves(self.training_data)
        
        def optimize(self) -> dict:
            # Use scipy.optimize to maximize ROAS
            return optimal_allocation
        
        def generate_recommendation(self) -> dict:
            # Create recommendation with expected impact
            return recommendation_payload
    
    # Run full workflow
    optimizer = BudgetAllocationOptimizer(strategy_id=strategy.id, db=session)
    recommendation = optimizer.run()
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


class BaseOptimizer(ABC):
    """Abstract base class for all optimization strategies.
    
    All optimizers must implement the abstract methods to define domain-specific
    logic. The run() method orchestrates the full workflow and is implemented in
    this base class.
    
    Attributes:
        strategy_id: UUID of the OptimizationStrategy record
        db: SQLAlchemy database session
        training_data: Data fetched for model training (set by fetch_training_data)
        models: Trained models (set by train_models)
        optimization_result: Result from optimize() method
    """
    
    def __init__(self, strategy_id: UUID, db: Session) -> None:
        """Initialize optimizer with strategy and database connection.
        
        Args:
            strategy_id: UUID of the OptimizationStrategy record in the database
            db: SQLAlchemy session for database queries
        """
        self.strategy_id = strategy_id
        self.db = db
        self.training_data: Any = None
        self.models: Any = None
        self.optimization_result: Any = None
    
    @abstractmethod
    def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> Any:
        """Fetch historical data for model training.
        
        This method should query the database for relevant historical data
        (orders, spend, inventory, etc.) based on the optimization strategy type.
        
        Args:
            tenant_id: UUID of the tenant to fetch data for
            days: Number of days of historical data to retrieve (default: 90)
        
        Returns:
            Training data in appropriate format (typically pandas DataFrame)
        
        Raises:
            ValueError: If insufficient data available for training
        """
        pass
    
    @abstractmethod
    def train_models(self) -> None:
        """Train mathematical models on the fetched training data.
        
        This method should fit models appropriate to the optimization strategy:
        - Budget allocation: Hill saturation curves
        - Pricing: Price elasticity models
        - Retention: Propensity scoring models
        - Inventory: Demand forecasting models
        
        The trained models should be stored in self.models for use in optimize().
        
        Raises:
            ValueError: If training data is None or insufficient
            RuntimeError: If model training fails
        """
        pass
    
    @abstractmethod
    def optimize(self) -> dict[str, Any]:
        """Run optimization algorithm to find the best solution.
        
        This method should use the trained models to find optimal values:
        - Budget allocation: Optimal spend per channel
        - Pricing: Optimal price points
        - Retention: Optimal campaign targeting
        - Inventory: Optimal reorder quantities and timing
        
        Returns:
            Dictionary containing optimization results with expected impact metrics
        
        Raises:
            ValueError: If models are not trained
            RuntimeError: If optimization fails to converge
        """
        pass
    
    @abstractmethod
    def generate_recommendation(self) -> dict[str, Any]:
        """Convert optimization result into actionable recommendation.
        
        This method should transform the optimization result into a recommendation
        payload that matches the AlpMark recommendations schema:
        - recommendation_text: Human-readable description
        - expected_impact: Projected improvement metrics
        - action_items: Specific steps to implement
        - confidence_level: Model confidence (0.0 to 1.0)
        
        Returns:
            Dictionary ready to insert into recommendations table
        
        Raises:
            ValueError: If optimization_result is None
        """
        pass
    
    def run(self, tenant_id: UUID, days: int = 90) -> dict[str, Any]:
        """Execute the full optimization workflow.
        
        This method orchestrates the complete optimization process:
        1. Fetch training data
        2. Train models
        3. Run optimization
        4. Generate recommendation
        
        This is a concrete method implemented in the base class. Subclasses
        should NOT override this method - they should implement the abstract
        methods that this method calls.
        
        Args:
            tenant_id: UUID of the tenant to optimize for
            days: Number of days of historical data to use (default: 90)
        
        Returns:
            Recommendation dictionary from generate_recommendation()
        
        Raises:
            ValueError: If any step fails due to invalid data
            RuntimeError: If training or optimization fails
        
        Example:
            optimizer = BudgetAllocationOptimizer(strategy_id=strategy.id, db=session)
            recommendation = optimizer.run(tenant_id=tenant.id, days=90)
            # recommendation contains actionable insights ready to insert into DB
        """
        # Step 1: Fetch training data
        self.training_data = self.fetch_training_data(tenant_id=tenant_id, days=days)
        
        # Step 2: Train models
        self.train_models()
        
        # Step 3: Run optimization
        self.optimization_result = self.optimize()
        
        # Step 4: Generate recommendation
        recommendation = self.generate_recommendation()
        
        return recommendation
