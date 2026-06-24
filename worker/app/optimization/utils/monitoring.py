"""Monitoring and logging utilities for optimization engine.

This module provides structured logging and error tracking for optimization runs,
integrating with Sentry for production error monitoring.

Usage
-----
```python
from worker.app.optimization.utils.monitoring import (
    log_optimization_start,
    log_optimization_success,
    log_optimization_failure,
)

# Start optimization run
log_optimization_start(tenant_id, strategy_name="budget_allocation")

try:
    # Run optimization...
    result = run_optimizer()
    log_optimization_success(run_id, metrics={"accuracy": 0.87, "runtime": 12.3})
except Exception as e:
    log_optimization_failure(run_id, error=e)
```

Environment Variables
--------------------
- SENTRY_DSN: Sentry Data Source Name for error tracking (optional)
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sentry_sdk
from sentry_sdk import capture_exception, capture_message

logger = logging.getLogger(__name__)

# Initialize Sentry if DSN is configured
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring
        traces_sample_rate=0.1,  # 10% sampling for performance
        # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions
        profiles_sample_rate=0.1,  # 10% sampling for profiling
        environment=os.getenv("ENVIRONMENT", "production"),
        # Enable Celery integration
        integrations=[],  # Celery integration auto-enabled if sentry-sdk[celery] installed
    )
    logger.info("Sentry monitoring initialized")
else:
    logger.warning("Sentry DSN not configured - error tracking disabled")


def log_optimization_start(
    tenant_id: UUID | str,
    strategy_name: str,
    domain: str | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Log the start of an optimization run.
    
    Parameters
    ----------
    tenant_id : UUID | str
        Tenant identifier.
    strategy_name : str
        Name of the optimization strategy (e.g., "budget_allocation").
    domain : str, optional
        Business domain (e.g., "acquisition", "finance").
    config : dict, optional
        Strategy configuration parameters.
    
    Examples
    --------
    >>> log_optimization_start(
    ...     tenant_id="abc123",
    ...     strategy_name="budget_allocation",
    ...     domain="acquisition",
    ...     config={"lookback_days": 90}
    ... )
    """
    tenant_id_str = str(tenant_id)
    
    # Structured log
    logger.info(
        f"Starting optimization run: {strategy_name}",
        extra={
            "tenant_id": tenant_id_str,
            "strategy_name": strategy_name,
            "domain": domain,
            "config": config,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    
    # Send breadcrumb to Sentry
    if SENTRY_DSN:
        sentry_sdk.add_breadcrumb(
            category="optimization",
            message=f"Started {strategy_name} for tenant {tenant_id_str}",
            level="info",
            data={
                "tenant_id": tenant_id_str,
                "strategy_name": strategy_name,
                "domain": domain,
            },
        )


def log_optimization_success(
    run_id: UUID | str,
    tenant_id: UUID | str | None = None,
    strategy_name: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    """Log successful completion of an optimization run.
    
    Parameters
    ----------
    run_id : UUID | str
        Optimization run identifier.
    tenant_id : UUID | str, optional
        Tenant identifier.
    strategy_name : str, optional
        Name of the optimization strategy.
    metrics : dict, optional
        Performance metrics (e.g., {"accuracy": 0.87, "runtime": 12.3}).
    
    Examples
    --------
    >>> log_optimization_success(
    ...     run_id="run_xyz",
    ...     tenant_id="abc123",
    ...     strategy_name="budget_allocation",
    ...     metrics={"accuracy": 0.87, "runtime": 12.3, "improvement": 0.082}
    ... )
    """
    run_id_str = str(run_id)
    tenant_id_str = str(tenant_id) if tenant_id else None
    
    # Structured log
    logger.info(
        f"Optimization run completed successfully: {run_id_str}",
        extra={
            "run_id": run_id_str,
            "tenant_id": tenant_id_str,
            "strategy_name": strategy_name,
            "metrics": metrics,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    
    # Send breadcrumb to Sentry
    if SENTRY_DSN:
        sentry_sdk.add_breadcrumb(
            category="optimization",
            message=f"Completed run {run_id_str}",
            level="info",
            data={
                "run_id": run_id_str,
                "tenant_id": tenant_id_str,
                "strategy_name": strategy_name,
                "metrics": metrics,
            },
        )


def log_optimization_failure(
    run_id: UUID | str,
    error: Exception,
    tenant_id: UUID | str | None = None,
    strategy_name: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Log failure of an optimization run and send error to Sentry.
    
    Parameters
    ----------
    run_id : UUID | str
        Optimization run identifier.
    error : Exception
        The exception that caused the failure.
    tenant_id : UUID | str, optional
        Tenant identifier.
    strategy_name : str, optional
        Name of the optimization strategy.
    context : dict, optional
        Additional context about the failure.
    
    Examples
    --------
    >>> try:
    ...     result = run_optimizer()
    ... except ValueError as e:
    ...     log_optimization_failure(
    ...         run_id="run_xyz",
    ...         error=e,
    ...         tenant_id="abc123",
    ...         strategy_name="budget_allocation",
    ...         context={"input_data_rows": 1000}
    ...     )
    """
    run_id_str = str(run_id)
    tenant_id_str = str(tenant_id) if tenant_id else None
    
    # Structured error log
    logger.error(
        f"Optimization run failed: {run_id_str} - {type(error).__name__}: {str(error)}",
        extra={
            "run_id": run_id_str,
            "tenant_id": tenant_id_str,
            "strategy_name": strategy_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        exc_info=True,
    )
    
    # Send error to Sentry with context
    if SENTRY_DSN:
        with sentry_sdk.push_scope() as scope:
            # Add context tags
            scope.set_tag("optimization_run_id", run_id_str)
            if tenant_id_str:
                scope.set_tag("tenant_id", tenant_id_str)
            if strategy_name:
                scope.set_tag("strategy_name", strategy_name)
            
            # Add extra context
            scope.set_context(
                "optimization",
                {
                    "run_id": run_id_str,
                    "tenant_id": tenant_id_str,
                    "strategy_name": strategy_name,
                    "context": context,
                },
            )
            
            # Capture the exception
            capture_exception(error)


def log_data_quality_issue(
    tenant_id: UUID | str,
    strategy_name: str,
    issue_type: str,
    details: dict[str, Any] | None = None,
    severity: str = "warning",
) -> None:
    """Log data quality issues that may affect optimization accuracy.
    
    Parameters
    ----------
    tenant_id : UUID | str
        Tenant identifier.
    strategy_name : str
        Name of the optimization strategy.
    issue_type : str
        Type of data quality issue (e.g., "insufficient_data", "stale_data").
    details : dict, optional
        Additional details about the issue.
    severity : str, default "warning"
        Severity level: "info", "warning", or "error".
    
    Examples
    --------
    >>> log_data_quality_issue(
    ...     tenant_id="abc123",
    ...     strategy_name="budget_allocation",
    ...     issue_type="insufficient_data",
    ...     details={"required_days": 90, "available_days": 45},
    ...     severity="warning"
    ... )
    """
    tenant_id_str = str(tenant_id)
    
    # Map severity to log level
    log_level = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }.get(severity, logging.WARNING)
    
    # Structured log
    logger.log(
        log_level,
        f"Data quality issue for {strategy_name}: {issue_type}",
        extra={
            "tenant_id": tenant_id_str,
            "strategy_name": strategy_name,
            "issue_type": issue_type,
            "details": details,
            "severity": severity,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    
    # Send to Sentry if severity is error
    if SENTRY_DSN and severity == "error":
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("tenant_id", tenant_id_str)
            scope.set_tag("strategy_name", strategy_name)
            scope.set_tag("issue_type", issue_type)
            scope.set_context(
                "data_quality",
                {
                    "tenant_id": tenant_id_str,
                    "strategy_name": strategy_name,
                    "issue_type": issue_type,
                    "details": details,
                },
            )
            capture_message(
                f"Data quality issue: {issue_type} for {strategy_name}",
                level="error",
            )


def log_model_performance(
    tenant_id: UUID | str,
    strategy_name: str,
    model_type: str,
    metrics: dict[str, float],
    threshold_checks: dict[str, bool] | None = None,
) -> None:
    """Log model performance metrics for monitoring.
    
    Parameters
    ----------
    tenant_id : UUID | str
        Tenant identifier.
    strategy_name : str
        Name of the optimization strategy.
    model_type : str
        Type of model (e.g., "hill_curve", "elasticity").
    metrics : dict
        Performance metrics (e.g., {"r_squared": 0.87, "mape": 0.12}).
    threshold_checks : dict, optional
        Boolean checks for minimum performance thresholds.
    
    Examples
    --------
    >>> log_model_performance(
    ...     tenant_id="abc123",
    ...     strategy_name="budget_allocation",
    ...     model_type="hill_curve",
    ...     metrics={"r_squared": 0.87, "mape": 0.12},
    ...     threshold_checks={"meets_minimum_accuracy": True}
    ... )
    """
    tenant_id_str = str(tenant_id)
    
    # Determine log level based on threshold checks
    log_level = logging.INFO
    if threshold_checks and not all(threshold_checks.values()):
        log_level = logging.WARNING
    
    # Structured log
    logger.log(
        log_level,
        f"Model performance for {strategy_name} ({model_type}): {metrics}",
        extra={
            "tenant_id": tenant_id_str,
            "strategy_name": strategy_name,
            "model_type": model_type,
            "metrics": metrics,
            "threshold_checks": threshold_checks,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    
    # Send breadcrumb to Sentry
    if SENTRY_DSN:
        sentry_sdk.add_breadcrumb(
            category="model_performance",
            message=f"{model_type} performance logged for {strategy_name}",
            level="info",
            data={
                "tenant_id": tenant_id_str,
                "strategy_name": strategy_name,
                "model_type": model_type,
                "metrics": metrics,
                "threshold_checks": threshold_checks,
            },
        )
