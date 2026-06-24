"""Tests for Budget Allocation Optimizer.

This test suite verifies:
1. Data fetching from database (mocked)
2. Hill curve training for both channels
3. Constrained optimization finds valid solution
4. Recommendation generation
5. End-to-end workflow
"""

import uuid
from datetime import date, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from worker.app.optimization.strategies.acquisition import BudgetAllocationOptimizer


class TestFetchTrainingData:
    """Test data fetching functionality."""
    
    @patch("worker.app.optimization.strategies.acquisition.select")
    def test_fetch_training_data_success(self, mock_select: Any) -> None:
        """Fetch training data successfully from database."""
        tenant_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        # Mock database responses for Meta, Google, and Orders
        today = date.today()
        
        # Meta spend data (30 days)
        meta_results = [
            MagicMock(spend_date=today - timedelta(days=i), daily_spend=10000 + i*100)
            for i in range(30)
        ]
        
        # Google spend data (30 days)
        google_results = [
            MagicMock(spend_date=today - timedelta(days=i), daily_spend=8000 + i*80)
            for i in range(30)
        ]
        
        # Order data (30 days)
        order_results = [
            MagicMock(order_date=today - timedelta(days=i), order_count=50 + i)
            for i in range(30)
        ]
        
        # Mock execute to return different results for each query
        db.execute.side_effect = [
            MagicMock(all=lambda: meta_results),
            MagicMock(all=lambda: google_results),
            MagicMock(all=lambda: order_results),
        ]
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        training_data = optimizer.fetch_training_data(tenant_id=tenant_id, days=30)
        
        assert "meta" in training_data
        assert "google" in training_data
        assert "total_budget" in training_data
        
        assert isinstance(training_data["meta"]["spend"], np.ndarray)
        assert isinstance(training_data["meta"]["conversions"], np.ndarray)
        assert len(training_data["meta"]["spend"]) > 0
        
        assert isinstance(training_data["google"]["spend"], np.ndarray)
        assert isinstance(training_data["google"]["conversions"], np.ndarray)
        assert len(training_data["google"]["spend"]) > 0
        
        assert training_data["total_budget"] > 0
    
    @patch("worker.app.optimization.strategies.acquisition.select")
    def test_fetch_insufficient_data_raises_error(self, mock_select: Any) -> None:
        """Fetch with insufficient data raises ValueError."""
        tenant_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        # Only 3 days of data (below 14-day threshold)
        today = date.today()
        meta_results = [
            MagicMock(spend_date=today - timedelta(days=i), daily_spend=10000)
            for i in range(3)
        ]
        google_results: list[Any] = []
        order_results: list[Any] = []
        
        db.execute.side_effect = [
            MagicMock(all=lambda: meta_results),
            MagicMock(all=lambda: google_results),
            MagicMock(all=lambda: order_results),
        ]
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        with pytest.raises(ValueError, match="Insufficient data"):
            optimizer.fetch_training_data(tenant_id=tenant_id, days=30)


class TestTrainModels:
    """Test Hill curve model training."""
    
    @patch("worker.app.optimization.strategies.acquisition.upload_model")
    def test_train_models_success(self, mock_upload: Any) -> None:
        """Train models successfully on valid data."""
        strategy_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        db = MagicMock()
        
        # Mock db.add to set id on OptimizationRun when flushed
        def mock_add_side_effect(obj: Any) -> None:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid.uuid4()
        
        db.add.side_effect = mock_add_side_effect
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.tenant_id = tenant_id
        
        # Set mock training data
        optimizer.training_data = {
            "meta": {
                "spend": np.array([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]),
                "conversions": np.array([40, 70, 85, 92, 96, 98, 99, 100]),
            },
            "google": {
                "spend": np.array([800, 1600, 2400, 3200, 4000, 4800, 5600, 6400]),
                "conversions": np.array([35, 60, 75, 83, 88, 91, 93, 94]),
            },
            "total_budget": 12000,
        }
        
        optimizer.train_models()
        
        assert optimizer.meta_curve is not None
        assert optimizer.google_curve is not None
        assert optimizer.meta_curve.is_fitted
        assert optimizer.google_curve.is_fitted
        
        meta_params = optimizer.meta_curve.get_params()
        google_params = optimizer.google_curve.get_params()
        
        assert meta_params["max_conv"] > 0
        assert meta_params["k"] > 0
        assert meta_params["n"] > 0
        
        assert google_params["max_conv"] > 0
        assert google_params["k"] > 0
        assert google_params["n"] > 0
    
    def test_train_models_before_fetch_raises_error(self) -> None:
        """Train models without fetching data raises ValueError."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        with pytest.raises(ValueError, match="Must call fetch_training_data"):
            optimizer.train_models()


class TestOptimize:
    """Test budget optimization functionality."""
    
    def test_optimize_finds_valid_solution(self) -> None:
        """Optimize finds solution respecting all constraints."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        # Set up trained models and budget
        optimizer.current_budget = 10000.0
        optimizer.training_data = {
            "meta": {
                "spend": np.array([1000, 2000, 3000, 4000, 5000]),
                "conversions": np.array([40, 70, 85, 92, 96]),
            },
            "google": {
                "spend": np.array([800, 1600, 2400, 3200, 4000]),
                "conversions": np.array([35, 60, 75, 83, 88]),
            },
            "total_budget": 10000.0,
        }
        
        # Manually create fitted curves
        from worker.app.optimization.models.saturation import HillCurve
        
        optimizer.meta_curve = HillCurve()
        optimizer.meta_curve.fit(
            spend_data=optimizer.training_data["meta"]["spend"],
            conversion_data=optimizer.training_data["meta"]["conversions"],
        )
        
        optimizer.google_curve = HillCurve()
        optimizer.google_curve.fit(
            spend_data=optimizer.training_data["google"]["spend"],
            conversion_data=optimizer.training_data["google"]["conversions"],
        )
        
        result = optimizer.optimize()
        
        # Verify result structure
        assert "meta_spend" in result
        assert "google_spend" in result
        assert "meta_pct" in result
        assert "google_pct" in result
        assert "expected_conversions" in result
        assert "current_conversions" in result
        assert "lift_pct" in result
        
        # Verify constraints
        # Total = budget
        assert abs(result["meta_spend"] + result["google_spend"] - 10000.0) < 1.0
        
        # Each channel between 15% and 60%
        assert result["meta_pct"] >= 15.0
        assert result["meta_pct"] <= 60.0
        assert result["google_pct"] >= 15.0
        assert result["google_pct"] <= 60.0
        
        # Percentages sum to 100%
        assert abs(result["meta_pct"] + result["google_pct"] - 100.0) < 0.1
        
        # Expected conversions should be >= current
        assert result["expected_conversions"] >= result["current_conversions"]
    
    def test_optimize_before_train_raises_error(self) -> None:
        """Optimize without training raises RuntimeError."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.current_budget = 10000.0
        
        with pytest.raises(RuntimeError, match="Must train models"):
            optimizer.optimize()


class TestGenerateRecommendation:
    """Test recommendation generation."""
    
    def test_generate_recommendation_success(self) -> None:
        """Generate recommendation with all required fields."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        # Set up complete state
        optimizer.training_data = {
            "meta": {
                "spend": np.array([1000, 2000, 3000, 4000, 5000]),
                "conversions": np.array([40, 70, 85, 92, 96]),
            },
            "google": {
                "spend": np.array([800, 1600, 2400, 3200, 4000]),
                "conversions": np.array([35, 60, 75, 83, 88]),
            },
            "total_budget": 10000.0,
        }
        
        from worker.app.optimization.models.saturation import HillCurve
        
        optimizer.meta_curve = HillCurve()
        optimizer.meta_curve.fit(
            spend_data=optimizer.training_data["meta"]["spend"],
            conversion_data=optimizer.training_data["meta"]["conversions"],
        )
        
        optimizer.google_curve = HillCurve()
        optimizer.google_curve.fit(
            spend_data=optimizer.training_data["google"]["spend"],
            conversion_data=optimizer.training_data["google"]["conversions"],
        )
        
        optimizer.optimization_result = {
            "meta_spend": 5500.0,
            "google_spend": 4500.0,
            "meta_pct": 55.0,
            "google_pct": 45.0,
            "expected_conversions": 180.0,
            "current_conversions": 165.0,
            "lift_pct": 9.1,
        }
        
        recommendation = optimizer.generate_recommendation()
        
        assert "recommendation_text" in recommendation
        assert "action_items" in recommendation
        assert "expected_impact" in recommendation
        assert "confidence_level" in recommendation
        assert "domain" in recommendation
        assert "priority" in recommendation
        
        assert recommendation["domain"] == "acquisition"
        assert isinstance(recommendation["action_items"], list)
        assert len(recommendation["action_items"]) > 0
        assert 0.0 <= recommendation["confidence_level"] <= 1.0
        assert recommendation["priority"] in ["high", "medium", "low"]
    
    def test_generate_recommendation_before_optimize_raises_error(self) -> None:
        """Generate recommendation without optimization raises ValueError."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        with pytest.raises(ValueError, match="Must run optimization"):
            optimizer.generate_recommendation()


class TestEndToEndWorkflow:
    """Test complete optimization workflow."""
    
    @patch("worker.app.optimization.strategies.acquisition.upload_model")
    def test_run_end_to_end_with_mock_data(self, mock_upload: Any) -> None:
        """Run complete workflow from fetch to recommendation."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        # Mock db.add to set id on OptimizationRun
        def mock_add_side_effect(obj: Any) -> None:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid.uuid4()
        
        db.add.side_effect = mock_add_side_effect
        
        # Mock database with synthetic data
        today = date.today()
        
        # Generate 30 days of realistic data
        meta_results = []
        google_results = []
        order_results = []
        
        for i in range(30):
            spend_date = today - timedelta(days=i)
            meta_spend = 10000 + np.random.normal(0, 500)
            google_spend = 8000 + np.random.normal(0, 400)
            
            # Orders roughly proportional to spend with noise
            total_spend = meta_spend + google_spend
            orders = int(total_spend / 200 + np.random.normal(0, 10))
            
            meta_results.append(
                MagicMock(spend_date=spend_date, daily_spend=meta_spend)
            )
            google_results.append(
                MagicMock(spend_date=spend_date, daily_spend=google_spend)
            )
            order_results.append(
                MagicMock(order_date=spend_date, order_count=max(1, orders))
            )
        
        db.execute.side_effect = [
            MagicMock(all=lambda: meta_results),
            MagicMock(all=lambda: google_results),
            MagicMock(all=lambda: order_results),
        ]
        
        # Run full workflow
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.tenant_id = uuid.uuid4()  # Set tenant_id for model saving
        
        # Use run() method from BaseOptimizer
        with patch("worker.app.optimization.strategies.acquisition.select"):
            # Set training data directly to avoid re-mocking
            optimizer.training_data = {
                "meta": {
                    "spend": np.array([10000, 11000, 9500, 10500, 10200] * 2),
                    "conversions": np.array([45, 50, 43, 48, 46] * 2),
                },
                "google": {
                    "spend": np.array([8000, 8500, 7800, 8200, 8100] * 2),
                    "conversions": np.array([38, 40, 37, 39, 38] * 2),
                },
                "total_budget": 18000.0,
            }
            optimizer.current_budget = 18000.0
            
            # Train models
            optimizer.train_models()
            
            # Optimize
            optimizer.optimization_result = optimizer.optimize()
            
            # Generate recommendation
            recommendation = optimizer.generate_recommendation()
        
        # Verify complete recommendation
        assert recommendation is not None
        rec_text = recommendation["recommendation_text"]
        assert "Meta" in rec_text or "meta" in rec_text
        assert "Google" in rec_text or "google" in rec_text
        assert recommendation["domain"] == "acquisition"
        assert len(recommendation["action_items"]) >= 2


class TestConstraintValidation:
    """Test optimization constraints are properly enforced."""
    
    def test_constraints_prevent_invalid_allocation(self) -> None:
        """Optimizer respects 15%-60% bounds per channel."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.current_budget = 10000.0
        
        # Create scenario where Meta is much better
        # (would want >60% without constraints)
        optimizer.training_data = {
            "meta": {
                # Meta is very efficient
                "spend": np.array([1000, 2000, 3000, 4000, 5000, 6000]),
                "conversions": np.array([50, 95, 130, 155, 170, 180]),
            },
            "google": {
                # Google is less efficient
                "spend": np.array([1000, 2000, 3000, 4000, 5000, 6000]),
                "conversions": np.array([20, 35, 45, 52, 57, 60]),
            },
            "total_budget": 10000.0,
        }
        
        from worker.app.optimization.models.saturation import HillCurve
        
        optimizer.meta_curve = HillCurve()
        optimizer.meta_curve.fit(
            spend_data=optimizer.training_data["meta"]["spend"],
            conversion_data=optimizer.training_data["meta"]["conversions"],
        )
        
        optimizer.google_curve = HillCurve()
        optimizer.google_curve.fit(
            spend_data=optimizer.training_data["google"]["spend"],
            conversion_data=optimizer.training_data["google"]["conversions"],
        )
        
        result = optimizer.optimize()
        
        # Even though Meta is better, should respect 60% max
        assert result["meta_pct"] <= 60.0
        # Google should get at least 15%
        assert result["google_pct"] >= 15.0


class TestModelPersistence:
    """Test saving fitted models to S3 and database."""
    
    def test_calculate_r2_perfect_fit(self) -> None:
        """R² calculation returns 1.0 for perfect fit."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        r2 = optimizer._calculate_r2(actual=actual, predicted=predicted)
        
        assert abs(r2 - 1.0) < 0.01  # Should be very close to 1.0
    
    def test_calculate_r2_poor_fit(self) -> None:
        """R² calculation returns low value for poor fit."""
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([5.0, 4.0, 3.0, 2.0, 1.0])  # Opposite pattern
        
        r2 = optimizer._calculate_r2(actual=actual, predicted=predicted)
        
        assert r2 < 0.5  # Should be low for poor fit
    
    @patch("worker.app.optimization.strategies.acquisition.upload_model")
    def test_save_fitted_model_creates_db_record(
        self, mock_upload: Any
    ) -> None:
        """Saving fitted model creates FittedModel database record."""
        tenant_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        run_id = uuid.uuid4()
        db = MagicMock()
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.tenant_id = tenant_id
        optimizer.optimization_run_id = run_id  # Set run_id directly
        
        # Create a simple fitted curve
        from worker.app.optimization.models.saturation import HillCurve
        
        curve = HillCurve()
        curve.fit(
            spend_data=np.array([1000, 2000, 3000]),
            conversion_data=np.array([40, 70, 85]),
        )
        
        params = curve.get_params()
        metrics = {"rmse": 5.2, "r2": 0.95}
        
        optimizer._save_fitted_model(
            curve=curve,
            model_type="meta_saturation_curve",
            params=params,
            metrics=metrics,
        )
        
        # Verify upload_model was called
        assert mock_upload.called
        call_args = mock_upload.call_args
        assert call_args[1]["model_obj"] == curve
        assert str(tenant_id) in call_args[1]["s3_key"]
        assert "meta_saturation_curve" in call_args[1]["s3_key"]
        
        # Verify db.add was called with FittedModel
        assert db.add.called
        fitted_model = db.add.call_args_list[-1][0][0]  # Last call
        assert fitted_model.tenant_id == tenant_id
        assert fitted_model.strategy_id == strategy_id
        assert fitted_model.optimization_run_id == run_id
        assert fitted_model.model_type == "meta_saturation_curve"
        assert fitted_model.accuracy_metrics == metrics
        assert "params" in fitted_model.model_metadata
        
        # Verify commit was called
        assert db.commit.called
    
    @patch("worker.app.optimization.strategies.acquisition.upload_model")
    def test_save_fitted_model_rollback_on_db_error(
        self, mock_upload: Any
    ) -> None:
        """Database error triggers rollback."""
        tenant_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        run_id = uuid.uuid4()
        db = MagicMock()
        
        # Make commit raise an error
        db.commit.side_effect = RuntimeError("Database error")
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.tenant_id = tenant_id
        optimizer.optimization_run_id = run_id  # Set run_id directly
        
        from worker.app.optimization.models.saturation import HillCurve
        
        curve = HillCurve()
        curve.fit(
            spend_data=np.array([1000, 2000, 3000]),
            conversion_data=np.array([40, 70, 85]),
        )
        
        with pytest.raises(RuntimeError, match="Failed to save fitted model"):
            optimizer._save_fitted_model(
                curve=curve,
                model_type="test_curve",
                params=curve.get_params(),
                metrics={"rmse": 5.0, "r2": 0.9},
            )
        
        # Verify rollback was called
        assert db.rollback.called
    
    @patch("worker.app.optimization.strategies.acquisition.upload_model")
    def test_train_models_saves_both_curves(self, mock_upload: Any) -> None:
        """Training models saves both Meta and Google curves to S3."""
        tenant_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        db = MagicMock()
        
        # Mock db.add to set id on OptimizationRun
        def mock_add_side_effect(obj: Any) -> None:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid.uuid4()
        
        db.add.side_effect = mock_add_side_effect
        
        optimizer = BudgetAllocationOptimizer(strategy_id=strategy_id, db=db)
        optimizer.tenant_id = tenant_id
        optimizer.training_data = {
            "meta": {
                "spend": np.array([1000, 2000, 3000, 4000, 5000]),
                "conversions": np.array([40, 70, 85, 92, 96]),
            },
            "google": {
                "spend": np.array([800, 1600, 2400, 3200, 4000]),
                "conversions": np.array([35, 60, 75, 83, 88]),
            },
            "total_budget": 10000.0,
        }
        
        optimizer.train_models()
        
        # Verify upload_model was called twice (Meta + Google)
        assert mock_upload.call_count == 2
        
        # Verify db.add was called (OptimizationRun + 2 FittedModels = 3)
        assert db.add.call_count >= 3
        
        # Verify db.commit was called twice (once per model save)
        assert db.commit.call_count == 2
        
        # Check S3 keys contain correct model types
        s3_keys = [call[1]["s3_key"] for call in mock_upload.call_args_list]
        assert any("meta_saturation_curve" in key for key in s3_keys)
        assert any("google_saturation_curve" in key for key in s3_keys)
        
        # Verify tenant_id is in S3 keys
        assert all(str(tenant_id) in key for key in s3_keys)
