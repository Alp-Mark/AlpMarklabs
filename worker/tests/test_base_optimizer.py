"""Tests for BaseOptimizer abstract class.

This test suite verifies:
1. Abstract class cannot be instantiated directly
2. Concrete subclasses can be instantiated
3. run() method orchestrates the workflow correctly
4. Missing abstract methods raise TypeError
"""

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from worker.app.optimization.strategies.base import BaseOptimizer


class TestBaseOptimizerInstantiation:
    """Test that BaseOptimizer enforces abstract method implementation."""
    
    def test_cannot_instantiate_abstract_class(self) -> None:
        """BaseOptimizer cannot be instantiated directly."""
        strategy_id = uuid4()
        db = MagicMock()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseOptimizer(strategy_id=strategy_id, db=db)  # type: ignore
    
    def test_missing_fetch_training_data_raises_error(self) -> None:
        """Subclass missing fetch_training_data cannot be instantiated."""
        
        class IncompleteOptimizer(BaseOptimizer):
            def train_models(self) -> None:
                pass
            
            def optimize(self) -> dict[str, Any]:
                return {}
            
            def generate_recommendation(self) -> dict[str, Any]:
                return {}
        
        strategy_id = uuid4()
        db = MagicMock()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteOptimizer(strategy_id=strategy_id, db=db)  # type: ignore
    
    def test_missing_train_models_raises_error(self) -> None:
        """Subclass missing train_models cannot be instantiated."""
        
        class IncompleteOptimizer(BaseOptimizer):
            def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> Any:
                return None
            
            def optimize(self) -> dict[str, Any]:
                return {}
            
            def generate_recommendation(self) -> dict[str, Any]:
                return {}
        
        strategy_id = uuid4()
        db = MagicMock()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteOptimizer(strategy_id=strategy_id, db=db)  # type: ignore
    
    def test_missing_optimize_raises_error(self) -> None:
        """Subclass missing optimize cannot be instantiated."""
        
        class IncompleteOptimizer(BaseOptimizer):
            def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> Any:
                return None
            
            def train_models(self) -> None:
                pass
            
            def generate_recommendation(self) -> dict[str, Any]:
                return {}
        
        strategy_id = uuid4()
        db = MagicMock()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteOptimizer(strategy_id=strategy_id, db=db)  # type: ignore
    
    def test_missing_generate_recommendation_raises_error(self) -> None:
        """Subclass missing generate_recommendation cannot be instantiated."""
        
        class IncompleteOptimizer(BaseOptimizer):
            def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> Any:
                return None
            
            def train_models(self) -> None:
                pass
            
            def optimize(self) -> dict[str, Any]:
                return {}
        
        strategy_id = uuid4()
        db = MagicMock()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteOptimizer(strategy_id=strategy_id, db=db)  # type: ignore


class TestConcreteOptimizerSubclass:
    """Test that concrete subclass can be instantiated and used."""
    
    @pytest.fixture
    def concrete_optimizer_class(self) -> type[BaseOptimizer]:
        """Create a concrete optimizer class for testing."""
        
        class ConcreteOptimizer(BaseOptimizer):
            """Minimal concrete implementation for testing."""
            
            def fetch_training_data(
                self, tenant_id: UUID, days: int = 90
            ) -> dict[str, Any]:
                """Return mock training data."""
                return {
                    "tenant_id": str(tenant_id),
                    "days": days,
                    "rows": 100,
                }
            
            def train_models(self) -> None:
                """Set mock trained models."""
                self.models = {
                    "model_type": "mock_model",
                    "accuracy": 0.85,
                }
            
            def optimize(self) -> dict[str, Any]:
                """Return mock optimization result."""
                return {
                    "optimal_value": 1000,
                    "expected_improvement": 0.15,
                }
            
            def generate_recommendation(self) -> dict[str, Any]:
                """Return mock recommendation."""
                return {
                    "recommendation_text": "Test recommendation",
                    "expected_impact": {"revenue_lift": 0.15},
                    "confidence_level": 0.85,
                }
        
        return ConcreteOptimizer
    
    def test_can_instantiate_concrete_subclass(
        self, concrete_optimizer_class: type[BaseOptimizer]
    ) -> None:
        """Concrete subclass with all abstract methods can be instantiated."""
        strategy_id = uuid4()
        db = MagicMock()
        
        optimizer = concrete_optimizer_class(strategy_id=strategy_id, db=db)
        
        assert optimizer.strategy_id == strategy_id
        assert optimizer.db is db
        assert optimizer.training_data is None
        assert optimizer.models is None
        assert optimizer.optimization_result is None
    
    def test_run_orchestrates_workflow(
        self, concrete_optimizer_class: type[BaseOptimizer]
    ) -> None:
        """run() method calls all abstract methods in correct order."""
        strategy_id = uuid4()
        tenant_id = uuid4()
        db = MagicMock()
        
        optimizer = concrete_optimizer_class(strategy_id=strategy_id, db=db)
        
        # Run the workflow
        recommendation = optimizer.run(tenant_id=tenant_id, days=60)
        
        # Verify each step was executed
        assert optimizer.training_data is not None
        assert optimizer.training_data["tenant_id"] == str(tenant_id)
        assert optimizer.training_data["days"] == 60
        
        assert optimizer.models is not None
        assert optimizer.models["model_type"] == "mock_model"
        
        assert optimizer.optimization_result is not None
        assert optimizer.optimization_result["optimal_value"] == 1000
        
        assert recommendation is not None
        assert recommendation["recommendation_text"] == "Test recommendation"
        assert recommendation["confidence_level"] == 0.85
    
    def test_run_default_days_parameter(
        self, concrete_optimizer_class: type[BaseOptimizer]
    ) -> None:
        """run() uses 90 days as default if not specified."""
        strategy_id = uuid4()
        tenant_id = uuid4()
        db = MagicMock()
        
        optimizer = concrete_optimizer_class(strategy_id=strategy_id, db=db)
        optimizer.run(tenant_id=tenant_id)
        
        # Default days should be 90
        assert optimizer.training_data["days"] == 90
    
    def test_run_custom_days_parameter(
        self, concrete_optimizer_class: type[BaseOptimizer]
    ) -> None:
        """run() respects custom days parameter."""
        strategy_id = uuid4()
        tenant_id = uuid4()
        db = MagicMock()
        
        optimizer = concrete_optimizer_class(strategy_id=strategy_id, db=db)
        optimizer.run(tenant_id=tenant_id, days=120)
        
        assert optimizer.training_data["days"] == 120


class TestWorkflowOrchestration:
    """Test that run() method properly orchestrates the workflow."""
    
    def test_workflow_sets_attributes_in_order(self) -> None:
        """run() sets training_data, models, optimization_result in sequence."""
        
        class TrackedOptimizer(BaseOptimizer):
            """Optimizer that tracks execution order."""
            
            def __init__(self, strategy_id: UUID, db: Any) -> None:
                super().__init__(strategy_id, db)
                self.execution_order: list[str] = []
            
            def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> dict:
                self.execution_order.append("fetch")
                assert self.training_data is None  # Not set yet
                return {"data": "mock"}
            
            def train_models(self) -> None:
                self.execution_order.append("train")
                assert self.training_data is not None  # Set by fetch
                assert self.models is None  # Not set yet
                self.models = {"trained": True}  # Set models for next step
            
            def optimize(self) -> dict[str, Any]:
                self.execution_order.append("optimize")
                assert self.models is not None  # Set by train
                assert self.optimization_result is None  # Not set yet
                return {"result": "mock"}
            
            def generate_recommendation(self) -> dict[str, Any]:
                self.execution_order.append("recommend")
                assert self.optimization_result is not None  # Set by optimize
                return {"rec": "mock"}
        
        strategy_id = uuid4()
        tenant_id = uuid4()
        db = MagicMock()
        
        optimizer = TrackedOptimizer(strategy_id=strategy_id, db=db)
        optimizer.run(tenant_id=tenant_id)
        
        # Verify execution order
        assert optimizer.execution_order == ["fetch", "train", "optimize", "recommend"]
    
    def test_run_returns_recommendation(self) -> None:
        """run() returns the result from generate_recommendation()."""
        
        class SimpleOptimizer(BaseOptimizer):
            def fetch_training_data(self, tenant_id: UUID, days: int = 90) -> None:
                return None
            
            def train_models(self) -> None:
                pass
            
            def optimize(self) -> dict[str, Any]:
                return {}
            
            def generate_recommendation(self) -> dict[str, Any]:
                return {"recommendation_id": "test-123"}
        
        strategy_id = uuid4()
        tenant_id = uuid4()
        db = MagicMock()
        
        optimizer = SimpleOptimizer(strategy_id=strategy_id, db=db)
        result = optimizer.run(tenant_id=tenant_id)
        
        assert result == {"recommendation_id": "test-123"}
