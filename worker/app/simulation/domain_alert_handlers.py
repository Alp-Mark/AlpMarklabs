"""FR-110 / T-075: Domain Alert Handlers.

Routes alerts to the correct persona based on business domain and severity.
Each handler:
1. Takes an AlertDecision (from T-074) + domain-specific context
2. Determines urgency, primary persona, and domain-specific reasoning
3. Returns a DomainAlert with routing and context for the recipient

Six domains: KPI, Acquisition, Margin, Retention, Inventory, Operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from worker.app.simulation.alert_generator import AlertDecision


@dataclass
class DomainAlert:
    """Routed alert with domain context and routing information.

    Represents an alert after routing logic has been applied.
    Ready for escalation (T-076), delivery (T-077/T-078), and
    history logging (T-079/T-080).

    Attributes:
        domain: Business domain (kpi, acquisition, margin, retention,
                inventory, operations).
        primary_persona: Target persona code (e.g., PER-02_GROWTH_MANAGER).
        urgency: Severity level (HIGH, MEDIUM, LOW).
        confidence: Anomaly confidence score (0.0-1.0).
        context: Domain-specific context dict for the recipient.
        secondary_recipients: Optional escalation recipients (list of
                             persona codes).
        channels: Delivery channels (in_app, email, slack).
        reasoning: Domain-specific explanation of the alert.
    """

    domain: str
    primary_persona: str
    urgency: str
    confidence: float
    context: dict
    secondary_recipients: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=lambda: ["in_app", "email"])
    reasoning: str = ""


class DomainAlertHandler:
    """Routes alerts to correct persona with domain-specific context."""

    # Urgency mapping based on confidence
    @staticmethod
    def _calculate_urgency(confidence: float, baseline_threshold: float = 0.75) -> str:
        """Calculate urgency from anomaly confidence.

        Args:
            confidence: 0.0–1.0 from AnomalyResult.
            baseline_threshold: Confidence threshold for HIGH urgency.

        Returns:
            One of HIGH, MEDIUM, LOW.
        """
        if confidence >= baseline_threshold:
            return "HIGH"
        if confidence >= 0.5:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def handle_kpi_alert(
        alert_decision: AlertDecision,
        metric_name: str,
        baseline_value: float,
        target_value: float,
        cross_metric_impact: dict | None = None,
    ) -> DomainAlert:
        """Route KPI alert to Executive Owner.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            metric_name: KPI name (e.g., "Contribution Margin %").
            baseline_value: Expected/baseline value for this KPI.
            target_value: Target value set by executive.
            cross_metric_impact: Dict of affected metrics and projected
                                impact.

        Returns:
            DomainAlert routed to PER-01.
        """
        urgency = DomainAlertHandler._calculate_urgency(
            alert_decision.confidence
        )

        # Build context for executive-level decision
        context = {
            "metric": metric_name,
            "current_value": alert_decision.value,
            "baseline": baseline_value,
            "target": target_value,
            "deviation_percent": (
                ((alert_decision.value - baseline_value) / baseline_value * 100)
                if baseline_value != 0
                else 0
            ),
            "z_score": alert_decision.z_score,
            "cross_metric_impact": cross_metric_impact or {},
            "confidence": alert_decision.confidence,
        }

        impact_str = (
            ", ".join(cross_metric_impact.keys())
            if cross_metric_impact
            else "None"
        )
        reasoning = (
            f"Executive KPI Alert: {metric_name} at {alert_decision.value:.2f} "
            f"(baseline {baseline_value:.2f}, target {target_value:.2f}). "
            f"Anomaly confidence: {alert_decision.confidence:.2f}. "
            f"Cross-metric impact: {impact_str}."
        )

        return DomainAlert(
            domain="kpi",
            primary_persona="PER-01_EXECUTIVE_OWNER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=[],
            channels=["in_app", "email"],
            reasoning=reasoning,
        )

    @staticmethod
    def handle_acquisition_alert(
        alert_decision: AlertDecision,
        channel_name: str,
        metric_name: str,
        baseline_metric: float,
        current_spend: float,
        cac_by_channel: dict | None = None,
        payback_days: int | None = None,
    ) -> DomainAlert:
        """Route acquisition (channel efficiency) alert to Growth Manager.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            channel_name: Ad channel (e.g., "Meta Ads", "Google Ads").
            metric_name: Efficiency metric (e.g., "ROAS", "CAC").
            baseline_metric: Expected/baseline value.
            current_spend: Current ad spend for this channel.
            cac_by_channel: Dict of CAC across all channels for
                           comparison.
            payback_days: Customer payback period in days.

        Returns:
            DomainAlert routed to PER-02.
        """
        urgency = DomainAlertHandler._calculate_urgency(
            alert_decision.confidence
        )

        # High-confidence acquisition alerts may escalate to executive
        secondary_recipients = (
            ["PER-01_EXECUTIVE_OWNER"]
            if urgency == "HIGH" and current_spend > 5000
            else []
        )

        context = {
            "channel": channel_name,
            "metric": metric_name,
            "current_value": alert_decision.value,
            "baseline": baseline_metric,
            "change_percent": (
                ((alert_decision.value - baseline_metric) / baseline_metric * 100)
                if baseline_metric != 0
                else 0
            ),
            "spend_at_risk": current_spend,
            "cac_by_channel": cac_by_channel or {},
            "payback_days": payback_days,
            "z_score": alert_decision.z_score,
            "confidence": alert_decision.confidence,
            "suggested_action": (
                "Pause underperforming campaigns, reallocate to "
                "efficient channels"
                if alert_decision.value < baseline_metric
                else "Consider scaling effective channel"
            ),
        }

        reasoning = (
            f"Acquisition Alert: {channel_name} {metric_name} at "
            f"{alert_decision.value:.2f} (baseline {baseline_metric:.2f}). "
            f"Spend at risk: £{current_spend:,.0f}. Anomaly confidence: "
            f"{alert_decision.confidence:.2f}."
        )

        return DomainAlert(
            domain="acquisition",
            primary_persona="PER-02_GROWTH_MANAGER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=secondary_recipients,
            channels=["in_app", "email"],
            reasoning=reasoning,
        )

    @staticmethod
    def handle_margin_alert(
        alert_decision: AlertDecision,
        margin_type: str,
        baseline_margin: float,
        cost_drivers: dict | None = None,
        variance_reason: str | None = None,
    ) -> DomainAlert:
        """Route margin alert to Finance Controller.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            margin_type: Type of margin (e.g., "Contribution Margin %",
                        "Channel Margin").
            baseline_margin: Expected/baseline margin percentage.
            cost_drivers: Dict of cost driver impacts (e.g.,
                         {"COGS": -2.5, "Shipping": -1.2}).
            variance_reason: Reason tag for variance (e.g., "discount
                            spike", "return surge").

        Returns:
            DomainAlert routed to PER-04.
        """
        urgency = DomainAlertHandler._calculate_urgency(alert_decision.confidence)

        context = {
            "margin_type": margin_type,
            "current_margin": alert_decision.value,
            "baseline_margin": baseline_margin,
            "margin_gap": baseline_margin - alert_decision.value,
            "gap_percent": (
                ((baseline_margin - alert_decision.value) / baseline_margin * 100)
                if baseline_margin != 0
                else 0
            ),
            "cost_drivers": cost_drivers or {},
            "variance_reason": variance_reason or "Unspecified",
            "z_score": alert_decision.z_score,
            "confidence": alert_decision.confidence,
        }

        reasoning = (
            f"Finance Alert: {margin_type} at {alert_decision.value:.2f}% "
            f"(baseline {baseline_margin:.2f}%). "
            f"Gap: {baseline_margin - alert_decision.value:.2f}%. "
            f"Variance reason: {variance_reason or 'Investigate cost drivers'}. "
            f"Anomaly confidence: {alert_decision.confidence:.2f}."
        )

        return DomainAlert(
            domain="margin",
            primary_persona="PER-04_FINANCE_CONTROLLER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=[],
            channels=["in_app", "email"],
            reasoning=reasoning,
        )

    @staticmethod
    def handle_retention_alert(
        alert_decision: AlertDecision,
        metric_name: str,
        baseline_rate: float,
        cohort_id: str | None = None,
        at_risk_count: int | None = None,
        churn_window_days: int = 90,
        segment_info: dict | None = None,
    ) -> DomainAlert:
        """Route retention alert to Retention Manager.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            metric_name: Retention metric (e.g., "Repeat Purchase Rate",
                        "Churn Rate").
            baseline_rate: Expected/baseline retention rate.
            cohort_id: ID of the affected cohort (if applicable).
            at_risk_count: Number of at-risk customers in the segment.
            churn_window_days: Window for churn evaluation (default 90).
            segment_info: Dict with segment details (e.g.,
                         {"segment": "new_customers", "age_days": 45}).

        Returns:
            DomainAlert routed to PER-03.
        """
        urgency = DomainAlertHandler._calculate_urgency(alert_decision.confidence)

        context = {
            "metric": metric_name,
            "current_rate": alert_decision.value,
            "baseline_rate": baseline_rate,
            "rate_change": baseline_rate - alert_decision.value,
            "cohort_id": cohort_id,
            "at_risk_count": at_risk_count or 0,
            "churn_window_days": churn_window_days,
            "segment_info": segment_info or {},
            "z_score": alert_decision.z_score,
            "confidence": alert_decision.confidence,
        }

        reasoning = (
            f"Retention Alert: {metric_name} at {alert_decision.value:.2f}% "
            f"(baseline {baseline_rate:.2f}%). "
            f"Cohort: {cohort_id or 'N/A'}. "
            f"At-risk customers: {at_risk_count or 0}. "
            f"Anomaly confidence: {alert_decision.confidence:.2f}."
        )

        return DomainAlert(
            domain="retention",
            primary_persona="PER-03_RETENTION_MANAGER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=[],
            channels=["in_app", "email"],
            reasoning=reasoning,
        )

    @staticmethod
    def handle_inventory_alert(
        alert_decision: AlertDecision,
        sku_id: str,
        risk_type: str,
        baseline_level: float,
        days_to_stockout: int | None = None,
        estimated_lost_revenue: float | None = None,
        location_id: str | None = None,
    ) -> DomainAlert:
        """Route inventory alert to Operations Manager.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            sku_id: SKU identifier.
            risk_type: Type of risk (e.g., "STOCKOUT_RISK",
                      "OVERSTOCK_RISK").
            baseline_level: Expected inventory level.
            days_to_stockout: Estimated days until stockout (if
                             applicable).
            estimated_lost_revenue: Projected revenue loss from
                                   stockout/action needed.
            location_id: Warehouse/location ID (if multi-warehouse).

        Returns:
            DomainAlert routed to PER-05.
        """
        urgency = DomainAlertHandler._calculate_urgency(alert_decision.confidence)

        # Escalate high-urgency stockout risks to executive
        secondary_recipients = (
            ["PER-01_EXECUTIVE_OWNER"]
            if urgency == "HIGH" and risk_type == "STOCKOUT_RISK"
            else []
        )

        context = {
            "sku_id": sku_id,
            "risk_type": risk_type,
            "current_level": alert_decision.value,
            "baseline_level": baseline_level,
            "days_to_stockout": days_to_stockout,
            "estimated_lost_revenue": estimated_lost_revenue or 0,
            "location_id": location_id,
            "z_score": alert_decision.z_score,
            "confidence": alert_decision.confidence,
        }

        reasoning = (
            f"Inventory Alert: {sku_id} - {risk_type}. "
            f"Level: {alert_decision.value:.0f} (baseline {baseline_level:.0f}). "
        )
        if days_to_stockout:
            reasoning += (
                f"Days to stockout: {days_to_stockout}. "
                f"Projected loss: £{estimated_lost_revenue:,.0f}. "
            )
        reasoning += f"Anomaly confidence: {alert_decision.confidence:.2f}."

        return DomainAlert(
            domain="inventory",
            primary_persona="PER-05_OPERATIONS_MANAGER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=secondary_recipients,
            channels=["in_app", "email"],
            reasoning=reasoning,
        )

    @staticmethod
    def handle_operations_alert(
        alert_decision: AlertDecision,
        metric_name: str,
        baseline_metric: float,
        top_skus: list[str] | None = None,
        cost_impact: float | None = None,
        risk_category: str | None = None,
    ) -> DomainAlert:
        """Route operations alert (returns/fulfillment) to Operations
        Manager.

        Args:
            alert_decision: Decision from AlertGenerator (T-074).
            metric_name: Operational metric (e.g., "Return Rate",
                        "Shipping Cost per Unit").
            baseline_metric: Expected/baseline value.
            top_skus: Top SKUs driving the anomaly (sorted by impact).
            cost_impact: Projected cost impact (e.g., margin loss in £).
            risk_category: Category of risk (e.g., "RETURN_SPIKE",
                          "SHIPPING_COST_SPIKE").

        Returns:
            DomainAlert routed to PER-05.
        """
        urgency = DomainAlertHandler._calculate_urgency(alert_decision.confidence)

        context = {
            "metric": metric_name,
            "current_value": alert_decision.value,
            "baseline_value": baseline_metric,
            "change": (
                ((alert_decision.value - baseline_metric) / baseline_metric * 100)
                if baseline_metric != 0
                else 0
            ),
            "top_skus": top_skus or [],
            "cost_impact": cost_impact or 0,
            "risk_category": risk_category,
            "z_score": alert_decision.z_score,
            "confidence": alert_decision.confidence,
        }

        cost_impact_str = (
            f"£{cost_impact:,.0f}" if cost_impact is not None else "TBD"
        )
        reasoning = (
            f"Operations Alert: {metric_name} at {alert_decision.value:.2f} "
            f"(baseline {baseline_metric:.2f}). "
            f"Risk: {risk_category or 'Investigate'}. "
            f"Top affected SKUs: {', '.join(top_skus[:3]) if top_skus else 'N/A'}. "
            f"Cost impact: {cost_impact_str}. "
            f"Anomaly confidence: {alert_decision.confidence:.2f}."
        )

        return DomainAlert(
            domain="operations",
            primary_persona="PER-05_OPERATIONS_MANAGER",
            urgency=urgency,
            confidence=alert_decision.confidence,
            context=context,
            secondary_recipients=[],
            channels=["in_app", "email"],
            reasoning=reasoning,
        )
