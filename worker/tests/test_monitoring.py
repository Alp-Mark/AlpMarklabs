"""Unit tests for monitoring utilities.

Tests structured logging and Sentry integration for optimization runs.
"""

import logging
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from worker.app.optimization.utils.monitoring import (
    log_data_quality_issue,
    log_model_performance,
    log_optimization_failure,
    log_optimization_start,
    log_optimization_success,
)


@pytest.fixture
def mock_sentry():
    """Mock Sentry SDK for testing."""
    with patch("worker.app.optimization.utils.monitoring.sentry_sdk") as mock_sdk:
        # Mock scope context manager
        mock_scope = MagicMock()
        mock_sdk.push_scope.return_value.__enter__.return_value = mock_scope
        yield mock_sdk, mock_scope


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch("worker.app.optimization.utils.monitoring.logger") as mock_log:
        yield mock_log


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for testing."""
    return UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def sample_run_id():
    """Sample run ID for testing."""
    return UUID("22222222-2222-4222-8222-222222222222")


class TestLogOptimizationStart:
    """Tests for log_optimization_start function."""
    
    def test_log_start_with_all_params(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging optimization start with all parameters."""
        # Arrange
        mock_sdk, mock_scope = mock_sentry
        strategy_name = "budget_allocation"
        domain = "acquisition"
        config = {"lookback_days": 90}
        
        # Act
        log_optimization_start(
            tenant_id=sample_tenant_id,
            strategy_name=strategy_name,
            domain=domain,
            config=config,
        )
        
        # Assert - logger called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert strategy_name in call_args[0][0]
        assert call_args[1]["extra"]["tenant_id"] == str(sample_tenant_id)
        assert call_args[1]["extra"]["strategy_name"] == strategy_name
        assert call_args[1]["extra"]["domain"] == domain
        assert call_args[1]["extra"]["config"] == config
    
    def test_log_start_with_string_tenant_id(self, mock_logger, mock_sentry):
        """Test logging with string tenant ID."""
        # Act
        log_optimization_start(
            tenant_id="tenant_abc123",
            strategy_name="pricing_optimization",
        )
        
        # Assert
        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["tenant_id"] == "tenant_abc123"
    
    def test_log_start_minimal_params(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging with only required parameters."""
        # Act
        log_optimization_start(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
        )
        
        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["domain"] is None
        assert call_args[1]["extra"]["config"] is None


class TestLogOptimizationSuccess:
    """Tests for log_optimization_success function."""
    
    def test_log_success_with_all_params(self, mock_logger, mock_sentry, sample_run_id, sample_tenant_id):
        """Test logging optimization success with all parameters."""
        # Arrange
        mock_sdk, mock_scope = mock_sentry
        metrics = {"accuracy": 0.87, "runtime": 12.3, "improvement": 0.082}
        
        # Act
        log_optimization_success(
            run_id=sample_run_id,
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            metrics=metrics,
        )
        
        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert str(sample_run_id) in call_args[0][0]
        assert call_args[1]["extra"]["run_id"] == str(sample_run_id)
        assert call_args[1]["extra"]["tenant_id"] == str(sample_tenant_id)
        assert call_args[1]["extra"]["metrics"] == metrics
    
    def test_log_success_minimal_params(self, mock_logger, mock_sentry, sample_run_id):
        """Test logging success with only run_id."""
        # Act
        log_optimization_success(run_id=sample_run_id)
        
        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["extra"]["tenant_id"] is None
        assert call_args[1]["extra"]["strategy_name"] is None


class TestLogOptimizationFailure:
    """Tests for log_optimization_failure function."""
    
    def test_log_failure_with_exception(self, mock_logger, mock_sentry, sample_run_id, sample_tenant_id):
        """Test logging optimization failure with exception."""
        # Arrange
        mock_sdk, mock_scope = mock_sentry
        error = ValueError("Invalid input data")
        context = {"input_rows": 1000}
        
        # Act
        log_optimization_failure(
            run_id=sample_run_id,
            error=error,
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            context=context,
        )
        
        # Assert - logger called with error level
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert str(sample_run_id) in call_args[0][0]
        assert "ValueError" in call_args[0][0]
        assert call_args[1]["extra"]["error_type"] == "ValueError"
        assert call_args[1]["extra"]["error_message"] == "Invalid input data"
        assert call_args[1]["exc_info"] is True
    
    def test_log_failure_different_exception_types(self, mock_logger, mock_sentry, sample_run_id):
        """Test logging with different exception types."""
        # Test with different exception types
        exceptions = [
            ValueError("Value error"),
            KeyError("Missing key"),
            RuntimeError("Runtime error"),
        ]
        
        for exc in exceptions:
            # Act
            log_optimization_failure(run_id=sample_run_id, error=exc)
            
            # Assert
            call_args = mock_logger.error.call_args
            assert call_args[1]["extra"]["error_type"] == type(exc).__name__
            assert call_args[1]["extra"]["error_message"] == str(exc)


class TestLogDataQualityIssue:
    """Tests for log_data_quality_issue function."""
    
    def test_log_warning_severity(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging data quality issue with warning severity."""
        # Arrange
        details = {"required_days": 90, "available_days": 45}
        
        # Act
        log_data_quality_issue(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            issue_type="insufficient_data",
            details=details,
            severity="warning",
        )
        
        # Assert
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING
        assert "insufficient_data" in call_args[0][1]
        assert call_args[1]["extra"]["details"] == details
    
    def test_log_error_severity_sends_to_sentry(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test that error severity sends message to Sentry."""
        # Arrange
        mock_sdk, mock_scope = mock_sentry
        
        # Act
        log_data_quality_issue(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            issue_type="critical_data_missing",
            severity="error",
        )
        
        # Assert - logger called with error level
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR
    
    def test_log_info_severity(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging with info severity."""
        # Act
        log_data_quality_issue(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            issue_type="data_refreshed",
            severity="info",
        )
        
        # Assert
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO


class TestLogModelPerformance:
    """Tests for log_model_performance function."""
    
    def test_log_performance_with_good_metrics(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging model performance with good metrics."""
        # Arrange
        metrics = {"r_squared": 0.87, "mape": 0.12}
        threshold_checks = {"meets_minimum_accuracy": True}
        
        # Act
        log_model_performance(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            model_type="hill_curve",
            metrics=metrics,
            threshold_checks=threshold_checks,
        )
        
        # Assert - log level should be INFO when all thresholds pass
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO
        assert call_args[1]["extra"]["metrics"] == metrics
        assert call_args[1]["extra"]["threshold_checks"] == threshold_checks
    
    def test_log_performance_with_failed_thresholds(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging model performance with failed threshold checks."""
        # Arrange
        metrics = {"r_squared": 0.45, "mape": 0.35}
        threshold_checks = {"meets_minimum_accuracy": False}
        
        # Act
        log_model_performance(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            model_type="hill_curve",
            metrics=metrics,
            threshold_checks=threshold_checks,
        )
        
        # Assert - log level should be WARNING when thresholds fail
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING
    
    def test_log_performance_without_threshold_checks(self, mock_logger, mock_sentry, sample_tenant_id):
        """Test logging without threshold checks."""
        # Arrange
        metrics = {"r_squared": 0.87}
        
        # Act
        log_model_performance(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            model_type="hill_curve",
            metrics=metrics,
        )
        
        # Assert
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO
        assert call_args[1]["extra"]["threshold_checks"] is None


class TestIntegration:
    """Integration tests for monitoring workflow."""
    
    def test_complete_optimization_workflow(
        self, mock_logger, mock_sentry, sample_tenant_id, sample_run_id
    ):
        """Test complete optimization workflow logging."""
        # Start
        log_optimization_start(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            domain="acquisition",
        )
        
        # Model performance
        log_model_performance(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            model_type="hill_curve",
            metrics={"r_squared": 0.87},
        )
        
        # Success
        log_optimization_success(
            run_id=sample_run_id,
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            metrics={"runtime": 12.3},
        )
        
        # Assert - all logging calls made
        assert mock_logger.info.call_count == 2
        assert mock_logger.log.call_count == 1
    
    def test_optimization_failure_workflow(
        self, mock_logger, mock_sentry, sample_tenant_id, sample_run_id
    ):
        """Test optimization failure workflow."""
        # Start
        log_optimization_start(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
        )
        
        # Data quality issue
        log_data_quality_issue(
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
            issue_type="insufficient_data",
            severity="warning",
        )
        
        # Failure
        error = ValueError("Not enough data")
        log_optimization_failure(
            run_id=sample_run_id,
            error=error,
            tenant_id=sample_tenant_id,
            strategy_name="budget_allocation",
        )
        
        # Assert
        assert mock_logger.info.call_count == 1  # start
        assert mock_logger.log.call_count == 1  # data quality warning
        assert mock_logger.error.call_count == 1  # failure
