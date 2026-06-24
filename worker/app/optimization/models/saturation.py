"""Hill saturation curve model for advertising response modeling.

This module implements the Hill equation (also called saturation curve) commonly
used in marketing mix modeling to represent diminishing returns from advertising
spend. The curve models how conversions increase with spend, eventually reaching
a saturation point.

Mathematical Formula:
    conversions = max_conv * (spend^n / (k^n + spend^n))

Where:
    - max_conv: Maximum possible conversions (saturation point)
    - k: Half-saturation spend (spend achieving 50% of max conversions)
    - n: Shape parameter (steepness of the curve)

The Hill curve is widely used because:
1. It captures diminishing returns realistically
2. Parameters have clear business interpretation
3. It fits well to typical ad channel behavior
4. It can model both gradual and sharp saturation

Example:
    # Fit curve to historical data
    curve = HillCurve()
    curve.fit(spend_data=[1000, 2000, 3000], conversion_data=[50, 80, 95])
    
    # Predict conversions for new spend level
    predicted_conv = curve.predict(spend=2500)
    
    # Get fitted parameters
    params = curve.get_params()
    # {'max_conv': 100.0, 'k': 1500.0, 'n': 2.5}
"""

from collections.abc import Sequence

import numpy as np
from scipy.optimize import curve_fit


class HillCurve:
    """Hill saturation curve for modeling advertising response.
    
    Models the relationship between advertising spend and conversions using
    the Hill equation. The curve captures diminishing returns: initial spend
    generates high conversion rates, but additional spend yields progressively
    smaller gains as the channel saturates.
    
    Attributes:
        max_conv: Maximum conversions at saturation (fitted parameter)
        k: Half-saturation spend level (fitted parameter)
        n: Shape/steepness parameter (fitted parameter)
        is_fitted: Whether the model has been fitted to data
    
    Methods:
        fit(spend_data, conversion_data): Fit curve to historical data
        predict(spend): Predict conversions for given spend level(s)
        get_params(): Get fitted parameters as dictionary
        calculate_rmse(spend_data, conversion_data): Calculate prediction error
    """
    
    def __init__(self) -> None:
        """Initialize HillCurve with no fitted parameters."""
        self.max_conv: float | None = None
        self.k: float | None = None
        self.n: float | None = None
        self.is_fitted: bool = False
    
    @staticmethod
    def _hill_function(
        spend: np.ndarray, max_conv: float, k: float, n: float
    ) -> np.ndarray:
        """Hill equation: conv = max_conv * (spend^n / (k^n + spend^n)).
        
        Args:
            spend: Advertising spend (single value or array)
            max_conv: Maximum conversions at saturation
            k: Half-saturation spend
            n: Shape parameter (steepness)
        
        Returns:
            Predicted conversions
        """
        return max_conv * (np.power(spend, n) / (np.power(k, n) + np.power(spend, n)))
    
    def fit(
        self,
        spend_data: Sequence[float] | np.ndarray,
        conversion_data: Sequence[float] | np.ndarray,
    ) -> None:
        """Fit Hill curve to historical spend and conversion data.
        
        Uses scipy.optimize.curve_fit to find optimal parameters (max_conv, k, n)
        that minimize the difference between predicted and actual conversions.
        
        The fitting process:
        1. Converts input data to numpy arrays
        2. Estimates initial parameter guesses from data
        3. Uses non-linear least squares optimization to fit parameters
        4. Stores fitted parameters in the instance
        
        Args:
            spend_data: Historical advertising spend values
            conversion_data: Corresponding conversion counts
        
        Raises:
            ValueError: If data arrays are empty, have different lengths,
                       or contain invalid values (negative, NaN)
            RuntimeError: If curve fitting fails to converge
        
        Example:
            curve = HillCurve()
            curve.fit(
                spend_data=[1000, 2000, 3000, 4000],
                conversion_data=[40, 70, 85, 92]
            )
            # curve.max_conv ≈ 100, curve.k ≈ 1500, curve.n ≈ 2.0
        """
        # Convert to numpy arrays
        spend = np.array(spend_data, dtype=float)
        conversions = np.array(conversion_data, dtype=float)
        
        # Validation
        if len(spend) == 0 or len(conversions) == 0:
            raise ValueError("Input arrays cannot be empty")
        
        if len(spend) != len(conversions):
            raise ValueError(
                f"Spend and conversion arrays must have same length: "
                f"{len(spend)} != {len(conversions)}"
            )
        
        if np.any(spend < 0) or np.any(conversions < 0):
            raise ValueError("Spend and conversions must be non-negative")
        
        if np.any(np.isnan(spend)) or np.any(np.isnan(conversions)):
            raise ValueError("Input data contains NaN values")
        
        if len(spend) < 3:
            raise ValueError(
                "Need at least 3 data points to fit Hill curve (3 parameters)"
            )
        
        # Initial parameter guesses
        # max_conv: slightly above max observed conversions
        # k: median spend
        # n: default to 2.0 (reasonable shape parameter)
        max_conv_guess = np.max(conversions) * 1.2
        k_guess = np.median(spend)
        n_guess = 2.0
        
        # Bounds to keep parameters reasonable
        # max_conv: between max observed and 10x max
        # k: between min and max spend
        # n: between 0.5 (very gradual) and 10 (very steep)
        lower_bounds = [np.max(conversions), np.min(spend), 0.5]
        upper_bounds = [np.max(conversions) * 10, np.max(spend), 10.0]
        
        try:
            # Fit using non-linear least squares
            params, _ = curve_fit(
                f=self._hill_function,
                xdata=spend,
                ydata=conversions,
                p0=[max_conv_guess, k_guess, n_guess],
                bounds=(lower_bounds, upper_bounds),
                maxfev=5000,  # Max function evaluations
            )
            
            # Store fitted parameters
            self.max_conv = float(params[0])
            self.k = float(params[1])
            self.n = float(params[2])
            self.is_fitted = True
            
        except RuntimeError as e:
            raise RuntimeError(
                f"Failed to fit Hill curve: {e}. Try providing more diverse "
                f"data points or checking for outliers."
            ) from e
    
    def predict(self, spend: float | Sequence[float] | np.ndarray) -> np.ndarray:
        """Predict conversions for given spend level(s).
        
        Uses the fitted Hill curve to predict how many conversions would result
        from a specific advertising spend level (or array of levels).
        
        Args:
            spend: Advertising spend (single value or array)
        
        Returns:
            Predicted conversions (numpy array, same shape as input)
        
        Raises:
            RuntimeError: If model has not been fitted yet
            ValueError: If spend contains negative values
        
        Example:
            curve = HillCurve()
            curve.fit(spend_data=[...], conversion_data=[...])
            
            # Single prediction
            pred = curve.predict(2500)  # Returns array([75.3])
            
            # Multiple predictions
            preds = curve.predict([1000, 2000, 3000])
            # Returns array([45.2, 70.1, 85.3])
        """
        if not self.is_fitted:
            raise RuntimeError(
                "Model must be fitted before making predictions. "
                "Call fit(spend_data, conversion_data) first."
            )
        
        # Convert to numpy array
        spend_array = np.atleast_1d(np.array(spend, dtype=float))
        
        if np.any(spend_array < 0):
            raise ValueError("Spend must be non-negative")
        
        # Type narrowing: is_fitted check guarantees parameters are not None
        assert self.max_conv is not None
        assert self.k is not None
        assert self.n is not None
        
        # Predict using fitted parameters (always return array)
        result = self._hill_function(spend_array, self.max_conv, self.k, self.n)
        return np.atleast_1d(result)
    
    def get_params(self) -> dict[str, float]:
        """Get fitted parameters as dictionary.
        
        Returns dictionary containing the three fitted Hill curve parameters.
        Useful for inspecting the fitted model, saving parameters to database,
        or comparing parameters across different channels.
        
        Returns:
            Dictionary with keys 'max_conv', 'k', 'n' and their fitted values
        
        Raises:
            RuntimeError: If model has not been fitted yet
        
        Example:
            curve = HillCurve()
            curve.fit(spend_data=[...], conversion_data=[...])
            params = curve.get_params()
            # {'max_conv': 100.5, 'k': 1523.7, 'n': 2.3}
            
            # Interpret parameters:
            # - max_conv=100.5: Channel saturates at ~100 conversions
            # - k=1523.7: $1,524 spend achieves 50% of max (50 conversions)
            # - n=2.3: Moderately steep curve (typical for paid channels)
        """
        if not self.is_fitted:
            raise RuntimeError(
                "Model must be fitted before accessing parameters. "
                "Call fit(spend_data, conversion_data) first."
            )
        
        # Type narrowing: is_fitted check guarantees parameters are not None
        assert self.max_conv is not None
        assert self.k is not None
        assert self.n is not None
        
        return {
            "max_conv": self.max_conv,
            "k": self.k,
            "n": self.n,
        }
    
    def calculate_rmse(
        self,
        spend_data: Sequence[float] | np.ndarray,
        conversion_data: Sequence[float] | np.ndarray,
    ) -> float:
        """Calculate Root Mean Squared Error between predictions and actuals.
        
        RMSE measures the average prediction error in the same units as
        conversions. Lower RMSE indicates better fit. Useful for:
        - Validating model accuracy
        - Comparing different models
        - Setting confidence thresholds
        
        Args:
            spend_data: Spend values to predict for
            conversion_data: Actual conversions to compare against
        
        Returns:
            RMSE value (same units as conversions)
        
        Raises:
            RuntimeError: If model has not been fitted yet
            ValueError: If arrays have different lengths
        
        Example:
            curve = HillCurve()
            curve.fit(train_spend, train_conversions)
            
            # Validate on test set
            rmse = curve.calculate_rmse(test_spend, test_conversions)
            
            # Check if model is accurate enough
            if rmse < 5.0:  # Less than 5 conversions error on average
                print("Model is accurate - deploy to production")
        """
        if not self.is_fitted:
            raise RuntimeError(
                "Model must be fitted before calculating RMSE. "
                "Call fit(spend_data, conversion_data) first."
            )
        
        spend = np.array(spend_data, dtype=float)
        conversions = np.array(conversion_data, dtype=float)
        
        if len(spend) != len(conversions):
            raise ValueError(
                f"Spend and conversion arrays must have same length: "
                f"{len(spend)} != {len(conversions)}"
            )
        
        # Predict and calculate RMSE
        predictions = self.predict(spend)
        squared_errors = np.power(predictions - conversions, 2)
        mean_squared_error = np.mean(squared_errors)
        rmse = np.sqrt(mean_squared_error)
        
        return float(rmse)
