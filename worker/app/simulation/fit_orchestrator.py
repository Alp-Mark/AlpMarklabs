"""Orchestrate response function fitting for all simulation domains (T-118).

This service fetches snapshot data for each domain and calls the appropriate
fit function to produce ResponseFunction objects. These functions are then
stored and consumed by the T-081 scipy.optimize continuous optimizer.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from worker.app.simulation.response_functions import (
    DataGateError,
    ResponseFunction,
    fit_acquisition,
    fit_executive,
    fit_inventory,
    fit_margin,
    fit_operations,
    fit_retention,
)
from worker.app.simulation.snapshot_fetcher import (
    fetch_acquisition_data,
    fetch_executive_data,
    fetch_inventory_data,
    fetch_margin_data,
    fetch_operations_data,
    fetch_retention_data,
)


class ResponseFunctionFitter:
    """Orchestrates fitting all response functions for a tenant."""

    def __init__(self, db: Session, tenant_id: Any, lookback_days: int = 120):
        """Initialize fitter for a specific tenant.

        Parameters
        ----------
        db:
            SQLAlchemy session.
        tenant_id:
            Tenant UUID.
        lookback_days:
            Days of history to consider when fitting (default 120).
        """
        self.db = db
        self.tenant_id = tenant_id
        self.lookback_days = lookback_days

    def fit_acquisition(self) -> ResponseFunction | None:
        """Fit ROAS response to ad spend.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.
        """
        try:
            data, window = fetch_acquisition_data(
                self.db, self.tenant_id, self.lookback_days
            )
            if not data:
                return None
            return fit_acquisition(data, window)
        except DataGateError:
            return None

    def fit_margin(self, driver_type: str) -> ResponseFunction | None:
        """Fit margin response to cost driver %.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.

        Parameters
        ----------
        driver_type:
            Cost driver type (e.g. "shipping", "cogs").
        """
        try:
            data, window = fetch_margin_data(
                self.db, self.tenant_id, driver_type, self.lookback_days
            )
            if not data:
                return None
            return fit_margin(data, window)
        except DataGateError:
            return None

    def fit_retention(self) -> ResponseFunction | None:
        """Fit repeat purchase rate response to CRM intervention time proxy.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.
        """
        try:
            data, window = fetch_retention_data(
                self.db, self.tenant_id, self.lookback_days
            )
            if not data:
                return None
            return fit_retention(data, window)
        except DataGateError:
            return None

    def fit_inventory(self, sku_id: Any) -> ResponseFunction | None:
        """Fit days-to-stockout response to reorder point.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.

        Parameters
        ----------
        sku_id:
            SKU UUID to fit for.
        """
        try:
            data, window = fetch_inventory_data(
                self.db, self.tenant_id, sku_id, self.lookback_days
            )
            if not data:
                return None
            return fit_inventory(data, window)
        except DataGateError:
            return None

    def fit_operations(self) -> ResponseFunction | None:
        """Fit logistics cost response to volume.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.
        """
        try:
            data, window = fetch_operations_data(
                self.db, self.tenant_id, self.lookback_days
            )
            if not data:
                return None
            return fit_operations(data, window)
        except DataGateError:
            return None

    def fit_executive(self) -> ResponseFunction | None:
        """Fit contribution margin response to ad spend.

        Returns ResponseFunction if sufficient data exists, None if data gate fails.
        """
        try:
            data, window = fetch_executive_data(
                self.db, self.tenant_id, self.lookback_days
            )
            if not data:
                return None
            return fit_executive(data, window)
        except DataGateError:
            return None

    def fit_all_domains(
        self,
    ) -> dict[str, ResponseFunction | None]:
        """Fit all available domains for the tenant.

        Returns a dict with domain names as keys and ResponseFunction (or None
        if data gate failed) as values.

        Note: This is a convenience method for orchestrating multiple fits.
        It does NOT fit inventory per-SKU — that should be done separately
        in domain-specific logic (T-062, T-063, etc.).
        """
        return {
            "acquisition": self.fit_acquisition(),
            "margin": self.fit_margin("default"),  # Simplified — adjust as needed
            "retention": self.fit_retention(),
            "operations": self.fit_operations(),
            "executive": self.fit_executive(),
        }
