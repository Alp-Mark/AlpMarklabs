"""Tests for domain alert handlers (T-075).

Tests cover:
- All 6 domain handlers with various alert scenarios
- Urgency calculation based on confidence levels
- Persona routing and escalation logic
- Domain-specific context building
- Edge cases (missing data, boundary values, multi-domain scenarios)
"""

from __future__ import annotations

import pytest

from worker.app.simulation.alert_generator import AlertDecision
from worker.app.simulation.domain_alert_handlers import DomainAlertHandler


class TestUrgencyCalculation:
    """Test urgency calculation from confidence scores."""

    def test_high_urgency_above_threshold(self) -> None:
        """High confidence (>= 0.75) should produce HIGH urgency."""
        urgency = DomainAlertHandler._calculate_urgency(0.90)
        assert urgency == "HIGH"

    def test_high_urgency_at_threshold(self) -> None:
        """Confidence exactly at threshold (0.75) should produce HIGH."""
        urgency = DomainAlertHandler._calculate_urgency(0.75)
        assert urgency == "HIGH"

    def test_medium_urgency_between_thresholds(self) -> None:
        """Confidence between 0.5 and 0.75 should produce MEDIUM."""
        urgency = DomainAlertHandler._calculate_urgency(0.60)
        assert urgency == "MEDIUM"

    def test_medium_urgency_at_lower_boundary(self) -> None:
        """Confidence exactly at 0.5 should produce MEDIUM."""
        urgency = DomainAlertHandler._calculate_urgency(0.50)
        assert urgency == "MEDIUM"

    def test_low_urgency_below_threshold(self) -> None:
        """Confidence below 0.5 should produce LOW urgency."""
        urgency = DomainAlertHandler._calculate_urgency(0.30)
        assert urgency == "LOW"

    def test_low_urgency_minimal(self) -> None:
        """Very low confidence should produce LOW urgency."""
        urgency = DomainAlertHandler._calculate_urgency(0.01)
        assert urgency == "LOW"


class TestKPIAlertHandler:
    """Test KPI alert routing to Executive Owner (PER-01)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.88
    ) -> AlertDecision:
        """Helper to create AlertDecision."""
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-3.2,
            value=value,
            threshold_value=2.5,
            comparison_operator="<",
            reasoning="Test anomaly",
        )

    def test_kpi_alert_routes_to_executive_owner(self) -> None:
        """KPI alert should route to PER-01."""
        alert_decision = self._create_alert_decision(1.8)
        domain_alert = DomainAlertHandler.handle_kpi_alert(
            alert_decision=alert_decision,
            metric_name="Contribution Margin %",
            baseline_value=45.0,
            target_value=50.0,
        )
        assert domain_alert.primary_persona == "PER-01_EXECUTIVE_OWNER"
        assert domain_alert.domain == "kpi"

    def test_kpi_alert_high_confidence(self) -> None:
        """High-confidence KPI alert should be HIGH urgency."""
        alert_decision = self._create_alert_decision(1.5, confidence=0.92)
        domain_alert = DomainAlertHandler.handle_kpi_alert(
            alert_decision=alert_decision,
            metric_name="ROAS",
            baseline_value=2.5,
            target_value=3.0,
        )
        assert domain_alert.urgency == "HIGH"
        assert domain_alert.confidence == 0.92

    def test_kpi_alert_includes_cross_metric_impact(self) -> None:
        """KPI alert context should include cross-metric impact."""
        alert_decision = self._create_alert_decision(1.8)
        cross_metric_impact = {
            "ROAS": -12,
            "Repeat Purchase Rate": -5,
        }
        domain_alert = DomainAlertHandler.handle_kpi_alert(
            alert_decision=alert_decision,
            metric_name="Contribution Margin %",
            baseline_value=45.0,
            target_value=50.0,
            cross_metric_impact=cross_metric_impact,
        )
        assert domain_alert.context["cross_metric_impact"] == cross_metric_impact

    def test_kpi_alert_calculates_deviation_percent(self) -> None:
        """KPI alert context should calculate deviation percentage."""
        alert_decision = self._create_alert_decision(40.0)
        domain_alert = DomainAlertHandler.handle_kpi_alert(
            alert_decision=alert_decision,
            metric_name="Margin %",
            baseline_value=50.0,
            target_value=55.0,
        )
        # Deviation: (40 - 50) / 50 * 100 = -20%
        assert domain_alert.context["deviation_percent"] == -20.0


class TestAcquisitionAlertHandler:
    """Test acquisition alert routing to Growth Manager (PER-02)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.85
    ) -> AlertDecision:
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-3.8,
            value=value,
            threshold_value=2.0,
            comparison_operator="<",
            reasoning="Acquisition anomaly",
        )

    def test_acquisition_alert_routes_to_growth_manager(self) -> None:
        """Acquisition alert should route to PER-02."""
        alert_decision = self._create_alert_decision(1.2)
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Meta Ads",
            metric_name="ROAS",
            baseline_metric=2.5,
            current_spend=5000,
        )
        assert domain_alert.primary_persona == "PER-02_GROWTH_MANAGER"
        assert domain_alert.domain == "acquisition"

    def test_acquisition_alert_escalates_to_executive_on_high_spend(self) -> None:
        """High-urgency, high-spend acquisition alert escalates to PER-01."""
        alert_decision = self._create_alert_decision(1.0, confidence=0.92)
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Google Ads",
            metric_name="ROAS",
            baseline_metric=2.5,
            current_spend=8000,  # Over 5000 threshold
        )
        assert "PER-01_EXECUTIVE_OWNER" in domain_alert.secondary_recipients

    def test_acquisition_alert_no_escalation_low_urgency(self) -> None:
        """Low-urgency acquisition alert should not escalate."""
        alert_decision = self._create_alert_decision(2.3, confidence=0.40)
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Meta Ads",
            metric_name="ROAS",
            baseline_metric=2.5,
            current_spend=8000,
        )
        assert len(domain_alert.secondary_recipients) == 0

    def test_acquisition_alert_includes_cac_breakdown(self) -> None:
        """Acquisition alert context should include CAC by channel."""
        alert_decision = self._create_alert_decision(1.2)
        cac_by_channel = {
            "Meta": 45,
            "Google": 52,
            "TikTok": 38,
        }
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Meta Ads",
            metric_name="CAC",
            baseline_metric=40,
            current_spend=3000,
            cac_by_channel=cac_by_channel,
        )
        assert domain_alert.context["cac_by_channel"] == cac_by_channel

    def test_acquisition_alert_suggests_action_on_decline(self) -> None:
        """Declining metric should suggest reallocation action."""
        alert_decision = self._create_alert_decision(1.5)  # Below baseline
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Meta Ads",
            metric_name="ROAS",
            baseline_metric=2.5,
            current_spend=5000,
        )
        assert "reallocate" in domain_alert.context["suggested_action"].lower()


class TestMarginAlertHandler:
    """Test margin alert routing to Finance Controller (PER-04)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.82
    ) -> AlertDecision:
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=2.5,
            value=value,
            threshold_value=40.0,
            comparison_operator="<",
            reasoning="Margin anomaly",
        )

    def test_margin_alert_routes_to_finance_controller(self) -> None:
        """Margin alert should route to PER-04."""
        alert_decision = self._create_alert_decision(38.5)
        domain_alert = DomainAlertHandler.handle_margin_alert(
            alert_decision=alert_decision,
            margin_type="Contribution Margin %",
            baseline_margin=42.0,
        )
        assert domain_alert.primary_persona == "PER-04_FINANCE_CONTROLLER"
        assert domain_alert.domain == "margin"

    def test_margin_alert_includes_cost_drivers(self) -> None:
        """Margin alert context should include cost driver breakdown."""
        alert_decision = self._create_alert_decision(38.5)
        cost_drivers = {
            "COGS": -2.5,
            "Shipping": -1.2,
            "Returns": -0.8,
        }
        domain_alert = DomainAlertHandler.handle_margin_alert(
            alert_decision=alert_decision,
            margin_type="Channel Margin",
            baseline_margin=42.0,
            cost_drivers=cost_drivers,
        )
        assert domain_alert.context["cost_drivers"] == cost_drivers

    def test_margin_alert_calculates_margin_gap(self) -> None:
        """Margin alert should calculate margin gap."""
        alert_decision = self._create_alert_decision(40.0)
        domain_alert = DomainAlertHandler.handle_margin_alert(
            alert_decision=alert_decision,
            margin_type="Contribution Margin %",
            baseline_margin=45.0,
        )
        assert domain_alert.context["margin_gap"] == 5.0
        assert domain_alert.context["gap_percent"] == pytest.approx(11.11, abs=0.1)

    def test_margin_alert_includes_variance_reason(self) -> None:
        """Margin alert context should include variance reason tag."""
        alert_decision = self._create_alert_decision(38.0)
        domain_alert = DomainAlertHandler.handle_margin_alert(
            alert_decision=alert_decision,
            margin_type="Product Category Margin",
            baseline_margin=42.0,
            variance_reason="shipping_rate_increase",
        )
        assert (
            domain_alert.context["variance_reason"] == "shipping_rate_increase"
        )


class TestRetentionAlertHandler:
    """Test retention alert routing to Retention Manager (PER-03)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.80
    ) -> AlertDecision:
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-2.8,
            value=value,
            threshold_value=55.0,
            comparison_operator="<",
            reasoning="Retention anomaly",
        )

    def test_retention_alert_routes_to_retention_manager(self) -> None:
        """Retention alert should route to PER-03."""
        alert_decision = self._create_alert_decision(48.0)
        domain_alert = DomainAlertHandler.handle_retention_alert(
            alert_decision=alert_decision,
            metric_name="Repeat Purchase Rate",
            baseline_rate=55.0,
        )
        assert domain_alert.primary_persona == "PER-03_RETENTION_MANAGER"
        assert domain_alert.domain == "retention"

    def test_retention_alert_includes_cohort_info(self) -> None:
        """Retention alert context should include cohort information."""
        alert_decision = self._create_alert_decision(45.0)
        segment_info = {
            "segment": "new_customers",
            "age_days": 45,
        }
        domain_alert = DomainAlertHandler.handle_retention_alert(
            alert_decision=alert_decision,
            metric_name="Repeat Purchase Rate",
            baseline_rate=55.0,
            cohort_id="cohort_2026_05",
            at_risk_count=240,
            segment_info=segment_info,
        )
        assert domain_alert.context["cohort_id"] == "cohort_2026_05"
        assert domain_alert.context["at_risk_count"] == 240
        assert domain_alert.context["segment_info"] == segment_info

    def test_retention_alert_calculates_rate_change(self) -> None:
        """Retention alert should calculate rate change."""
        alert_decision = self._create_alert_decision(50.0)
        domain_alert = DomainAlertHandler.handle_retention_alert(
            alert_decision=alert_decision,
            metric_name="Churn Rate",
            baseline_rate=8.0,
        )
        # For churn: higher is worse, so change = baseline - current = 8 - 50
        # But this doesn't make sense; test should reflect actual semantics
        # Assuming current = 50 is way above baseline 8, so rate_change = 8 - 50
        assert domain_alert.context["rate_change"] == 8.0 - 50.0


class TestInventoryAlertHandler:
    """Test inventory alert routing to Operations Manager (PER-05)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.85
    ) -> AlertDecision:
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-4.2,
            value=value,
            threshold_value=10.0,
            comparison_operator="<",
            reasoning="Inventory anomaly",
        )

    def test_inventory_alert_routes_to_operations_manager(self) -> None:
        """Inventory alert should route to PER-05."""
        alert_decision = self._create_alert_decision(2.0)
        domain_alert = DomainAlertHandler.handle_inventory_alert(
            alert_decision=alert_decision,
            sku_id="SKU-042",
            risk_type="STOCKOUT_RISK",
            baseline_level=50.0,
        )
        assert domain_alert.primary_persona == "PER-05_OPERATIONS_MANAGER"
        assert domain_alert.domain == "inventory"

    def test_inventory_alert_escalates_high_urgency_stockout(self) -> None:
        """High-urgency stockout alert should escalate to PER-01."""
        alert_decision = self._create_alert_decision(1.0, confidence=0.91)
        domain_alert = DomainAlertHandler.handle_inventory_alert(
            alert_decision=alert_decision,
            sku_id="SKU-042",
            risk_type="STOCKOUT_RISK",
            baseline_level=50.0,
            days_to_stockout=3,
            estimated_lost_revenue=18000,
        )
        assert "PER-01_EXECUTIVE_OWNER" in domain_alert.secondary_recipients

    def test_inventory_alert_no_escalation_overstock(self) -> None:
        """Overstock alert should not escalate to executive."""
        alert_decision = self._create_alert_decision(200, confidence=0.88)
        domain_alert = DomainAlertHandler.handle_inventory_alert(
            alert_decision=alert_decision,
            sku_id="SKU-999",
            risk_type="OVERSTOCK_RISK",
            baseline_level=50.0,
            estimated_lost_revenue=2000,
        )
        assert len(domain_alert.secondary_recipients) == 0

    def test_inventory_alert_includes_stockout_projection(self) -> None:
        """Inventory alert context should include days-to-stockout."""
        alert_decision = self._create_alert_decision(3.0)
        domain_alert = DomainAlertHandler.handle_inventory_alert(
            alert_decision=alert_decision,
            sku_id="SKU-042",
            risk_type="STOCKOUT_RISK",
            baseline_level=50.0,
            days_to_stockout=5,
            estimated_lost_revenue=15000,
            location_id="warehouse_1",
        )
        assert domain_alert.context["days_to_stockout"] == 5
        assert domain_alert.context["estimated_lost_revenue"] == 15000
        assert domain_alert.context["location_id"] == "warehouse_1"


class TestOperationsAlertHandler:
    """Test operations alert routing to Operations Manager (PER-05)."""

    def _create_alert_decision(self, value: float, confidence: float = 0.87
    ) -> AlertDecision:
        return AlertDecision(
            should_fire=True,
            confidence=confidence,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=3.1,
            value=value,
            threshold_value=5.0,
            comparison_operator=">",
            reasoning="Operations anomaly",
        )

    def test_operations_alert_routes_to_operations_manager(self) -> None:
        """Operations alert should route to PER-05."""
        alert_decision = self._create_alert_decision(8.2)
        domain_alert = DomainAlertHandler.handle_operations_alert(
            alert_decision=alert_decision,
            metric_name="Return Rate",
            baseline_metric=3.5,
        )
        assert domain_alert.primary_persona == "PER-05_OPERATIONS_MANAGER"
        assert domain_alert.domain == "operations"

    def test_operations_alert_includes_top_skus(self) -> None:
        """Operations alert context should include top SKUs driving issue."""
        alert_decision = self._create_alert_decision(8.2)
        top_skus = ["SKU-042", "SKU-051", "SKU-018"]
        domain_alert = DomainAlertHandler.handle_operations_alert(
            alert_decision=alert_decision,
            metric_name="Return Rate",
            baseline_metric=3.5,
            top_skus=top_skus,
            cost_impact=4500,
            risk_category="RETURN_SPIKE",
        )
        assert domain_alert.context["top_skus"] == top_skus
        assert domain_alert.context["cost_impact"] == 4500
        assert domain_alert.context["risk_category"] == "RETURN_SPIKE"

    def test_operations_alert_calculates_change_percent(self) -> None:
        """Operations alert should calculate percentage change."""
        alert_decision = self._create_alert_decision(4.5)
        domain_alert = DomainAlertHandler.handle_operations_alert(
            alert_decision=alert_decision,
            metric_name="Shipping Cost per Unit",
            baseline_metric=3.0,
        )
        # Change: (4.5 - 3.0) / 3.0 * 100 = 50%
        assert domain_alert.context["change"] == 50.0


class TestDomainAlertStructure:
    """Test DomainAlert dataclass and structure."""

    def test_domain_alert_has_required_fields(self) -> None:
        """DomainAlert should populate all required fields."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.88,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-2.5,
            value=1.5,
            threshold_value=2.0,
            comparison_operator="<",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Meta",
            metric_name="ROAS",
            baseline_metric=2.5,
            current_spend=5000,
        )
        assert domain_alert.domain is not None
        assert domain_alert.primary_persona is not None
        assert domain_alert.urgency is not None
        assert domain_alert.context is not None
        assert domain_alert.channels is not None
        assert domain_alert.reasoning is not None

    def test_domain_alert_default_channels(self) -> None:
        """DomainAlert should have default channels."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.80,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=2.0,
            value=42.0,
            threshold_value=40.0,
            comparison_operator=">",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_margin_alert(
            alert_decision=alert_decision,
            margin_type="Margin %",
            baseline_margin=45.0,
        )
        assert "in_app" in domain_alert.channels
        assert "email" in domain_alert.channels


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_kpi_alert_with_zero_baseline(self) -> None:
        """KPI alert with zero baseline should handle division gracefully."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.85,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=1.5,
            value=5.0,
            threshold_value=1.0,
            comparison_operator=">",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_kpi_alert(
            alert_decision=alert_decision,
            metric_name="KPI",
            baseline_value=0.0,
            target_value=10.0,
        )
        # Deviation should be 0 when baseline is 0
        assert domain_alert.context["deviation_percent"] == 0

    def test_acquisition_alert_with_missing_optional_data(self) -> None:
        """Acquisition alert should handle missing optional parameters."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.75,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-1.8,
            value=45.0,
            threshold_value=40.0,
            comparison_operator=">",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_acquisition_alert(
            alert_decision=alert_decision,
            channel_name="Google Ads",
            metric_name="CAC",
            baseline_metric=50.0,
            current_spend=3000,
            cac_by_channel=None,
            payback_days=None,
        )
        assert domain_alert.context["cac_by_channel"] == {}
        assert domain_alert.context["payback_days"] is None

    def test_inventory_alert_very_high_confidence(self) -> None:
        """Very high-confidence inventory alert (0.99)."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.99,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-5.5,
            value=0.5,
            threshold_value=5.0,
            comparison_operator="<",
            reasoning="Critical",
        )
        domain_alert = DomainAlertHandler.handle_inventory_alert(
            alert_decision=alert_decision,
            sku_id="SKU-CRITICAL",
            risk_type="STOCKOUT_RISK",
            baseline_level=100.0,
            days_to_stockout=1,
            estimated_lost_revenue=50000,
        )
        assert domain_alert.urgency == "HIGH"
        assert domain_alert.confidence == 0.99

    def test_retention_alert_with_empty_segment_info(self) -> None:
        """Retention alert should handle empty segment info dict."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.72,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=-1.9,
            value=52.0,
            threshold_value=50.0,
            comparison_operator="<",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_retention_alert(
            alert_decision=alert_decision,
            metric_name="Repeat Purchase Rate",
            baseline_rate=58.0,
            segment_info={},
        )
        assert domain_alert.context["segment_info"] == {}

    def test_operations_alert_with_empty_sku_list(self) -> None:
        """Operations alert should handle empty top SKUs list."""
        alert_decision = AlertDecision(
            should_fire=True,
            confidence=0.81,
            threshold_crossed=True,
            is_anomalous=True,
            z_score=2.3,
            value=6.5,
            threshold_value=5.0,
            comparison_operator=">",
            reasoning="Test",
        )
        domain_alert = DomainAlertHandler.handle_operations_alert(
            alert_decision=alert_decision,
            metric_name="Return Rate",
            baseline_metric=3.2,
            top_skus=[],
        )
        assert domain_alert.context["top_skus"] == []
