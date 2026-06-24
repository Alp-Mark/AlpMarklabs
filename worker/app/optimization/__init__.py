"""Optimization engine for AlpMark Intelligence Platform.

This package contains the mathematical optimization logic for generating
data-driven recommendations across key business domains:

- Acquisition: Budget allocation optimization using Hill curve saturation
- Finance: Pricing optimization using elasticity models
- Retention: Campaign targeting using propensity scoring
- Operations: Inventory optimization using demand forecasting

Architecture
------------
- strategies/: Domain-specific optimization strategies
- models/: Mathematical models (Hill curves, elasticity, forecasting)
- utils/: Shared utilities (S3 storage, metrics, validators)

Usage
-----
Optimization runs are triggered by Celery workers and store results in:
- optimization_runs table (full optimization output)
- optimization_recommendations table (user-facing recommendations)
- fitted_models table (trained model metadata + S3 references)
"""

__version__ = "0.1.0"
