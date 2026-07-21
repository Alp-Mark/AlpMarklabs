"""Optimization strategies for each business domain.

Each strategy module implements:
- fit(): Train model on historical data
- optimize(): Find optimal configuration given constraints
- recommend(): Generate user-facing recommendation from optimization result
"""

from worker.app.optimization.strategies.acquisition import (
    BudgetAllocationOptimizer,
)
from worker.app.optimization.strategies.multi_channel import (
    MultiChannelAllocator,
)

__all__ = ["BudgetAllocationOptimizer", "MultiChannelAllocator"]
