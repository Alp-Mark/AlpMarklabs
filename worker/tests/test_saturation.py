"""Tests for Hill saturation curve model.

This test suite verifies:
1. Fitting to historical data works correctly
2. Predictions match expected values
3. Parameters are extracted correctly
4. RMSE calculation is accurate
5. Validation catches invalid inputs
6. RMSE < 5% on synthetic data (task requirement)
"""

import numpy as np
import pytest
from worker.app.optimization.models.saturation import HillCurve


class TestHillCurveFit:
    """Test fitting Hill curves to data."""
    
    def test_fit_with_valid_data(self) -> None:
        """Fit succeeds with valid spend and conversion data."""
        curve = HillCurve()
        
        spend = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        conversions = [40.0, 70.0, 85.0, 92.0, 96.0]
        
        curve.fit(spend_data=spend, conversion_data=conversions)
        
        assert curve.is_fitted is True
        assert curve.max_conv is not None
        assert curve.k is not None
        assert curve.n is not None
        assert curve.max_conv > 0
        assert curve.k > 0
        assert curve.n > 0
    
    def test_fit_sets_reasonable_parameters(self) -> None:
        """Fitted parameters are in reasonable ranges."""
        curve = HillCurve()
        
        spend = [500.0, 1000.0, 2000.0, 3000.0, 4000.0]
        conversions = [30.0, 50.0, 75.0, 85.0, 90.0]
        
        curve.fit(spend_data=spend, conversion_data=conversions)
        
        # Type narrowing: is_fitted guarantees parameters are not None
        assert curve.is_fitted
        assert curve.max_conv is not None
        assert curve.k is not None
        assert curve.n is not None
        
        # max_conv should be >= max observed conversions
        assert curve.max_conv >= max(conversions)
        
        # k should be within spend range
        assert curve.k >= min(spend)
        assert curve.k <= max(spend)
        
        # n should be reasonable (between 0.5 and 10)
        assert 0.5 <= curve.n <= 10.0
    
    def test_fit_with_numpy_arrays(self) -> None:
        """Fit works with numpy arrays as input."""
        curve = HillCurve()
        
        spend = np.array([1000.0, 2000.0, 3000.0])
        conversions = np.array([40.0, 70.0, 85.0])
        
        curve.fit(spend_data=spend, conversion_data=conversions)
        
        assert curve.is_fitted is True
    
    def test_fit_empty_arrays_raises_error(self) -> None:
        """Fitting with empty arrays raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            curve.fit(spend_data=[], conversion_data=[])
    
    def test_fit_mismatched_lengths_raises_error(self) -> None:
        """Fitting with different length arrays raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="must have same length"):
            curve.fit(spend_data=[1000.0, 2000.0], conversion_data=[40.0])
    
    def test_fit_negative_spend_raises_error(self) -> None:
        """Fitting with negative spend raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="must be non-negative"):
            curve.fit(
                spend_data=[-1000.0, 2000.0, 3000.0],
                conversion_data=[40.0, 70.0, 85.0],
            )
    
    def test_fit_negative_conversions_raises_error(self) -> None:
        """Fitting with negative conversions raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="must be non-negative"):
            curve.fit(
                spend_data=[1000.0, 2000.0, 3000.0],
                conversion_data=[40.0, -70.0, 85.0],
            )
    
    def test_fit_nan_values_raises_error(self) -> None:
        """Fitting with NaN values raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="contains NaN"):
            curve.fit(
                spend_data=[1000.0, np.nan, 3000.0],
                conversion_data=[40.0, 70.0, 85.0],
            )
    
    def test_fit_too_few_points_raises_error(self) -> None:
        """Fitting with fewer than 3 points raises ValueError."""
        curve = HillCurve()
        
        with pytest.raises(ValueError, match="at least 3 data points"):
            curve.fit(spend_data=[1000.0, 2000.0], conversion_data=[40.0, 70.0])


class TestHillCurvePredict:
    """Test prediction functionality."""
    
    def test_predict_single_value(self) -> None:
        """Predict works for single spend value."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0, 4000.0],
            conversion_data=[40.0, 70.0, 85.0, 92.0],
        )
        
        prediction = curve.predict(2500)
        
        assert isinstance(prediction, np.ndarray)
        assert len(prediction) == 1
        assert prediction[0] > 0
        # Should be between 70 and 85 (interpolation)
        assert 70 < prediction[0] < 85
    
    def test_predict_multiple_values(self) -> None:
        """Predict works for array of spend values."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0, 4000.0],
            conversion_data=[40.0, 70.0, 85.0, 92.0],
        )
        
        predictions = curve.predict([1500, 2500, 3500])
        
        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 3
        assert all(p > 0 for p in predictions)
    
    def test_predict_zero_spend(self) -> None:
        """Predict with zero spend returns zero conversions."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0],
            conversion_data=[40.0, 70.0, 85.0],
        )
        
        prediction = curve.predict(0)
        
        # Zero spend should give near-zero conversions
        assert prediction[0] < 1.0
    
    def test_predict_high_spend_approaches_max(self) -> None:
        """Predict with very high spend approaches max_conv."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0, 4000.0],
            conversion_data=[40.0, 70.0, 85.0, 92.0],
        )
        
        # Type narrowing
        assert curve.max_conv is not None
        
        # Very high spend should approach max_conv
        prediction = curve.predict(100000)
        
        # Should be close to max_conv (within 5%)
        assert prediction[0] > curve.max_conv * 0.95
    
    def test_predict_before_fit_raises_error(self) -> None:
        """Predict before fitting raises RuntimeError."""
        curve = HillCurve()
        
        with pytest.raises(RuntimeError, match="must be fitted"):
            curve.predict(1000)
    
    def test_predict_negative_spend_raises_error(self) -> None:
        """Predict with negative spend raises ValueError."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0],
            conversion_data=[40.0, 70.0, 85.0],
        )
        
        with pytest.raises(ValueError, match="must be non-negative"):
            curve.predict(-1000)


class TestHillCurveParams:
    """Test parameter extraction."""
    
    def test_get_params_returns_dict(self) -> None:
        """get_params returns dictionary with correct keys."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0],
            conversion_data=[40.0, 70.0, 85.0],
        )
        
        params = curve.get_params()
        
        assert isinstance(params, dict)
        assert "max_conv" in params
        assert "k" in params
        assert "n" in params
    
    def test_get_params_values_are_floats(self) -> None:
        """get_params returns float values."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0],
            conversion_data=[40.0, 70.0, 85.0],
        )
        
        params = curve.get_params()
        
        assert isinstance(params["max_conv"], float)
        assert isinstance(params["k"], float)
        assert isinstance(params["n"], float)
    
    def test_get_params_before_fit_raises_error(self) -> None:
        """get_params before fitting raises RuntimeError."""
        curve = HillCurve()
        
        with pytest.raises(RuntimeError, match="must be fitted"):
            curve.get_params()


class TestHillCurveRMSE:
    """Test RMSE calculation."""
    
    def test_calculate_rmse_on_training_data(self) -> None:
        """RMSE on training data is reasonably low."""
        curve = HillCurve()
        
        spend = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        conversions = [40.0, 70.0, 85.0, 92.0, 96.0]
        
        curve.fit(spend_data=spend, conversion_data=conversions)
        rmse = curve.calculate_rmse(spend_data=spend, conversion_data=conversions)
        
        # RMSE should be reasonably low on training data
        assert rmse >= 0
        assert rmse < 10  # Less than 10 conversions error
    
    def test_calculate_rmse_perfect_fit(self) -> None:
        """RMSE is near zero for perfect predictions."""
        curve = HillCurve()
        
        # Create synthetic data from known Hill curve
        spend = np.array([1000, 2000, 3000, 4000, 5000])
        # Generate perfect Hill curve data
        max_conv, k, n = 100.0, 2000.0, 2.0
        conversions = max_conv * (spend**n / (k**n + spend**n))
        
        curve.fit(spend_data=spend, conversion_data=conversions)
        rmse = curve.calculate_rmse(spend_data=spend, conversion_data=conversions)
        
        # RMSE should be very close to 0 for perfect fit
        assert rmse < 0.1
    
    def test_calculate_rmse_before_fit_raises_error(self) -> None:
        """calculate_rmse before fitting raises RuntimeError."""
        curve = HillCurve()
        
        with pytest.raises(RuntimeError, match="must be fitted"):
            curve.calculate_rmse(
                spend_data=[1000, 2000],
                conversion_data=[40, 70],
            )
    
    def test_calculate_rmse_mismatched_lengths_raises_error(self) -> None:
        """calculate_rmse with mismatched lengths raises ValueError."""
        curve = HillCurve()
        curve.fit(
            spend_data=[1000.0, 2000.0, 3000.0],
            conversion_data=[40.0, 70.0, 85.0],
        )
        
        with pytest.raises(ValueError, match="must have same length"):
            curve.calculate_rmse(
                spend_data=[1000.0, 2000.0],
                conversion_data=[40.0],
            )


class TestHillCurveSyntheticData:
    """Test RMSE < 5% requirement with synthetic data."""
    
    def test_rmse_less_than_5_percent_on_synthetic_data(self) -> None:
        """Fit to synthetic data achieves RMSE < 5% (task requirement).
        
        This test verifies the core requirement from Task 1.1:
        "Verify: Fit to synthetic data, RMSE < 5%"
        """
        # Generate synthetic data from a known Hill curve with realistic noise
        np.random.seed(42)  # For reproducibility
        
        # True parameters (what we're trying to recover)
        true_max_conv = 100.0
        true_k = 2500.0
        true_n = 2.0
        
        # Generate spend points across realistic range
        spend = np.array([500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7000, 10000])
        
        # Generate true conversions from Hill curve
        true_conversions = true_max_conv * (
            spend**true_n / (true_k**true_n + spend**true_n)
        )
        
        # Add realistic noise (~5% standard deviation)
        noise = np.random.normal(0, 0.05 * true_conversions)
        observed_conversions = true_conversions + noise
        # Ensure non-negative
        observed_conversions = np.maximum(observed_conversions, 0)
        
        # Fit curve to noisy data
        curve = HillCurve()
        curve.fit(spend_data=spend, conversion_data=observed_conversions)
        
        # Calculate RMSE
        rmse = curve.calculate_rmse(
            spend_data=spend,
            conversion_data=observed_conversions,
        )
        
        # Calculate RMSE as percentage of average conversions
        avg_conversions = np.mean(observed_conversions)
        rmse_percent = (rmse / avg_conversions) * 100
        
        # Verify RMSE < 5% (task requirement)
        assert rmse_percent < 5.0, (
            f"RMSE {rmse_percent:.2f}% exceeds 5% threshold. "
            f"Absolute RMSE: {rmse:.2f}, Average conversions: {avg_conversions:.2f}"
        )
        
        # Also verify parameters are reasonably close to true values
        params = curve.get_params()
        
        # max_conv should be within 20% of true value
        assert abs(params["max_conv"] - true_max_conv) / true_max_conv < 0.2
        
        # k should be within 30% of true value
        assert abs(params["k"] - true_k) / true_k < 0.3
        
        # n should be within 30% of true value
        assert abs(params["n"] - true_n) / true_n < 0.3
    
    def test_multiple_synthetic_scenarios(self) -> None:
        """Test RMSE < 5% across different curve shapes."""
        test_scenarios = [
            # (max_conv, k, n) - different curve characteristics
            (50.0, 1000.0, 1.5),   # Gradual saturation, low volume
            (200.0, 3000.0, 2.5),  # Steep saturation, high volume
            (100.0, 2000.0, 2.0),  # Moderate curve
        ]
        
        np.random.seed(123)
        
        for max_conv, k, n in test_scenarios:
            # Generate data
            spend = np.linspace(500, 10000, 15)
            true_conv = max_conv * (spend**n / (k**n + spend**n))
            noise = np.random.normal(0, 0.03 * true_conv)
            observed_conv = np.maximum(true_conv + noise, 0)
            
            # Fit and validate
            curve = HillCurve()
            curve.fit(spend_data=spend, conversion_data=observed_conv)
            rmse = curve.calculate_rmse(spend_data=spend, conversion_data=observed_conv)
            
            rmse_percent = (rmse / np.mean(observed_conv)) * 100
            
            assert rmse_percent < 5.0, (
                f"Scenario (max_conv={max_conv}, k={k}, n={n}) "
                f"failed: RMSE {rmse_percent:.2f}% > 5%"
            )


class TestHillCurveInitialization:
    """Test initialization behavior."""
    
    def test_new_curve_not_fitted(self) -> None:
        """New HillCurve starts in unfitted state."""
        curve = HillCurve()
        
        assert curve.is_fitted is False
        assert curve.max_conv is None
        assert curve.k is None
        assert curve.n is None
