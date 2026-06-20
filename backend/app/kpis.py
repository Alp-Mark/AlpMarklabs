"""KPI metadata registry for AlpMark Intelligence Platform.

This module defines all key performance indicators tracked in the system,
including their definitions, formulas, data sources, and persona ownership.

KPIs are organized by domain:
- executive: Strategic business health metrics
- growth: Acquisition and media efficiency metrics
- retention: Customer retention and lifetime value metrics
- finance: Financial performance and margin metrics
- operations: Inventory and operational efficiency metrics
"""

from typing import Final, TypedDict


class KPIMetadata(TypedDict):
    """Metadata for a single KPI."""

    key: str  # Unique identifier (e.g. "contribution_margin_pct")
    name: str  # Display name
    description: str  # What this metric measures
    formula: str  # How it's calculated
    unit: str  # Unit of measurement (e.g. "percent", "dollars", "days")
    domain: str  # Which persona owns this (executive, growth, retention, etc.)
    data_sources: list[str]  # Where the data comes from
    good_direction: str  # "higher" or "lower" is better
    target_range: str  # Optional guidance on healthy values


# Executive / Strategic KPIs
CONTRIBUTION_MARGIN_PCT: Final[str] = "contribution_margin_pct"
BLENDED_ROAS: Final[str] = "blended_roas"
REVENUE_GROWTH_RATE: Final[str] = "revenue_growth_rate"

# Growth KPIs
CAC_PAYBACK_PERIOD: Final[str] = "cac_payback_period"
CAC_BY_CHANNEL: Final[str] = "cac_by_channel"
CHANNEL_ROAS: Final[str] = "channel_roas"

# Retention KPIs
REPEAT_PURCHASE_RATE: Final[str] = "repeat_purchase_rate"
CUSTOMER_LIFETIME_VALUE: Final[str] = "customer_lifetime_value"
CHURN_RATE: Final[str] = "churn_rate"

# Finance KPIs
GROSS_PROFIT_MARGIN: Final[str] = "gross_profit_margin"
RETURN_RATE_PCT: Final[str] = "return_rate_pct"
AVERAGE_ORDER_VALUE: Final[str] = "average_order_value"

# Operations KPIs
INVENTORY_TURNOVER: Final[str] = "inventory_turnover"
DAYS_OF_INVENTORY: Final[str] = "days_of_inventory"
STOCKOUT_RATE: Final[str] = "stockout_rate"

# Intelligence / Platform KPIs
TIME_TO_INSIGHT: Final[str] = "time_to_insight"
RECOMMENDATION_ACCEPTANCE_RATE: Final[str] = "recommendation_acceptance_rate"


# KPI Metadata Registry
KPI_REGISTRY: Final[dict[str, KPIMetadata]] = {
    CONTRIBUTION_MARGIN_PCT: {
        "key": CONTRIBUTION_MARGIN_PCT,
        "name": "Contribution Margin %",
        "description": (
            "Percentage of revenue remaining after variable costs "
            "(COGS + shipping + fulfillment + ad spend)"
        ),
        "formula": (
            "(Revenue - COGS - Shipping - Fulfillment - Ad Spend) / "
            "Revenue × 100"
        ),
        "unit": "percent",
        "domain": "executive",
        "data_sources": ["Shopify Orders", "Meta Ads", "Google Ads", "Cost Inputs"],
        "good_direction": "higher",
        "target_range": "30-50% for healthy D2C brands",
    },
    BLENDED_ROAS: {
        "key": BLENDED_ROAS,
        "name": "Blended ROAS",
        "description": "Return on ad spend across all channels",
        "formula": "Total Revenue / Total Ad Spend",
        "unit": "ratio",
        "domain": "executive",
        "data_sources": ["Shopify Orders", "Meta Ads", "Google Ads"],
        "good_direction": "higher",
        "target_range": "2.5-4.0 typical for D2C",
    },
    REVENUE_GROWTH_RATE: {
        "key": REVENUE_GROWTH_RATE,
        "name": "Revenue Growth Rate",
        "description": "Month-over-month or year-over-year revenue growth",
        "formula": (
            "(Current Period Revenue - Prior Period Revenue) / "
            "Prior Period Revenue × 100"
        ),
        "unit": "percent",
        "domain": "executive",
        "data_sources": ["Shopify Orders"],
        "good_direction": "higher",
        "target_range": "10-30% MoM for high-growth brands",
    },
    CAC_PAYBACK_PERIOD: {
        "key": CAC_PAYBACK_PERIOD,
        "name": "CAC Payback Period",
        "description": (
            "Time to recover customer acquisition cost from "
            "contribution margin"
        ),
        "formula": "CAC / (Average Order Value × Contribution Margin %)",
        "unit": "days",
        "domain": "growth",
        "data_sources": ["Meta Ads", "Google Ads", "Shopify Orders"],
        "good_direction": "lower",
        "target_range": "60-120 days is healthy",
    },
    CAC_BY_CHANNEL: {
        "key": CAC_BY_CHANNEL,
        "name": "CAC by Channel",
        "description": "Customer acquisition cost per marketing channel",
        "formula": "Channel Ad Spend / New Customers from Channel",
        "unit": "dollars",
        "domain": "growth",
        "data_sources": ["Meta Ads", "Google Ads", "Shopify Orders"],
        "good_direction": "lower",
        "target_range": "Varies by product; track relative efficiency",
    },
    CHANNEL_ROAS: {
        "key": CHANNEL_ROAS,
        "name": "Channel ROAS",
        "description": "Return on ad spend for individual channels",
        "formula": "Channel Revenue / Channel Ad Spend",
        "unit": "ratio",
        "domain": "growth",
        "data_sources": ["Meta Ads", "Google Ads", "Shopify Orders"],
        "good_direction": "higher",
        "target_range": "3.0+ for Meta, 4.0+ for Google typical",
    },
    REPEAT_PURCHASE_RATE: {
        "key": REPEAT_PURCHASE_RATE,
        "name": "Repeat Purchase Rate",
        "description": "Percentage of customers who make a second purchase",
        "formula": "Customers with 2+ Orders / Total Customers × 100",
        "unit": "percent",
        "domain": "retention",
        "data_sources": ["Shopify Orders"],
        "good_direction": "higher",
        "target_range": "20-40% within 90 days is strong",
    },
    CUSTOMER_LIFETIME_VALUE: {
        "key": CUSTOMER_LIFETIME_VALUE,
        "name": "Customer Lifetime Value (LTV)",
        "description": "Predicted total contribution margin from a customer",
        "formula": (
            "Average Order Value × Purchase Frequency × "
            "Contribution Margin % × Customer Lifespan"
        ),
        "unit": "dollars",
        "domain": "retention",
        "data_sources": ["Shopify Orders", "Cost Inputs"],
        "good_direction": "higher",
        "target_range": "3-5× CAC for sustainable growth",
    },
    CHURN_RATE: {
        "key": CHURN_RATE,
        "name": "Churn Rate",
        "description": "Percentage of customers who stop purchasing",
        "formula": "Customers Lost in Period / Customers at Start of Period × 100",
        "unit": "percent",
        "domain": "retention",
        "data_sources": ["Shopify Orders"],
        "good_direction": "lower",
        "target_range": "5-10% monthly for subscription; lower for repurchase",
    },
    GROSS_PROFIT_MARGIN: {
        "key": GROSS_PROFIT_MARGIN,
        "name": "Gross Profit Margin",
        "description": "Revenue minus COGS as percentage of revenue",
        "formula": "(Revenue - COGS) / Revenue × 100",
        "unit": "percent",
        "domain": "finance",
        "data_sources": ["Shopify Orders", "Cost Inputs"],
        "good_direction": "higher",
        "target_range": "40-70% for D2C physical goods",
    },
    RETURN_RATE_PCT: {
        "key": RETURN_RATE_PCT,
        "name": "Return Rate %",
        "description": "Percentage of orders that are returned",
        "formula": "Returned Orders / Total Orders × 100",
        "unit": "percent",
        "domain": "finance",
        "data_sources": ["Shopify Orders"],
        "good_direction": "lower",
        "target_range": "5-15% typical for apparel; <5% for other goods",
    },
    AVERAGE_ORDER_VALUE: {
        "key": AVERAGE_ORDER_VALUE,
        "name": "Average Order Value (AOV)",
        "description": "Average revenue per order",
        "formula": "Total Revenue / Number of Orders",
        "unit": "dollars",
        "domain": "finance",
        "data_sources": ["Shopify Orders"],
        "good_direction": "higher",
        "target_range": "Varies by product; track trends",
    },
    INVENTORY_TURNOVER: {
        "key": INVENTORY_TURNOVER,
        "name": "Inventory Turnover",
        "description": "How many times inventory is sold and replaced in a period",
        "formula": "COGS / Average Inventory Value",
        "unit": "ratio",
        "domain": "operations",
        "data_sources": ["Shopify Inventory", "Cost Inputs"],
        "good_direction": "higher",
        "target_range": "4-8× annually for most D2C",
    },
    DAYS_OF_INVENTORY: {
        "key": DAYS_OF_INVENTORY,
        "name": "Days of Inventory",
        "description": "Average days of inventory on hand",
        "formula": "365 / Inventory Turnover",
        "unit": "days",
        "domain": "operations",
        "data_sources": ["Shopify Inventory", "Cost Inputs"],
        "good_direction": "lower",
        "target_range": "45-90 days typical",
    },
    STOCKOUT_RATE: {
        "key": STOCKOUT_RATE,
        "name": "Stockout Rate",
        "description": "Percentage of SKUs that are out of stock",
        "formula": "SKUs with Zero Inventory / Total Active SKUs × 100",
        "unit": "percent",
        "domain": "operations",
        "data_sources": ["Shopify Inventory"],
        "good_direction": "lower",
        "target_range": "<5% for optimal availability",
    },
    TIME_TO_INSIGHT: {
        "key": TIME_TO_INSIGHT,
        "name": "Time to Insight",
        "description": "Time from data sync to actionable recommendation",
        "formula": "Measured from last connector sync to recommendation generation",
        "unit": "minutes",
        "domain": "intelligence",
        "data_sources": ["Platform Activity Logs"],
        "good_direction": "lower",
        "target_range": "<60 minutes for standard workflows",
    },
    RECOMMENDATION_ACCEPTANCE_RATE: {
        "key": RECOMMENDATION_ACCEPTANCE_RATE,
        "name": "Recommendation Acceptance Rate",
        "description": "Percentage of recommendations approved and implemented",
        "formula": "Approved Recommendations / Total Recommendations × 100",
        "unit": "percent",
        "domain": "intelligence",
        "data_sources": ["Platform Recommendation Logs"],
        "good_direction": "higher",
        "target_range": "40-60% indicates good targeting",
    },
}


def get_kpi_metadata(kpi_key: str) -> KPIMetadata | None:
    """Get metadata for a specific KPI by key."""
    return KPI_REGISTRY.get(kpi_key)


def get_all_kpis() -> dict[str, KPIMetadata]:
    """Get all KPI metadata."""
    return KPI_REGISTRY


def get_kpis_by_domain(domain: str) -> dict[str, KPIMetadata]:
    """Get all KPIs for a specific domain (persona)."""
    return {
        key: metadata
        for key, metadata in KPI_REGISTRY.items()
        if metadata["domain"] == domain
    }
