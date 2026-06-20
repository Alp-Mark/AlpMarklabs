"""Pydantic schemas for Growth Dashboard endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class ChannelPerformance(BaseModel):
    """Performance metrics for a single marketing channel."""

    model_config = ConfigDict(from_attributes=True)

    channel: str  # "meta", "google_ads", "organic", etc.
    total_spend: float  # Total ad spend in period
    total_revenue: float  # Revenue attributed to this channel
    roas: float | None  # Return on ad spend (revenue / spend)
    orders_count: int  # Number of orders attributed
    new_customers: int  # Number of first-time customers
    cac: float | None  # Customer acquisition cost (spend / new_customers)
    cac_payback_days: float | None  # Days to recover CAC
    contribution_margin: float  # Revenue - costs
    contribution_margin_pct: float  # Contribution margin as % of revenue
    trend: str  # "improving", "stable", "declining"


class CampaignPerformance(BaseModel):
    """Performance metrics for individual campaigns."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: str
    campaign_name: str
    channel: str  # "meta" or "google_ads"
    spend: float
    revenue: float | None  # Revenue attributed to this campaign
    roas: float | None
    orders_count: int
    cac: float | None
    is_underperforming: bool  # Below threshold targets


class GrowthDashboardResponse(BaseModel):
    """Growth dashboard response with channel and campaign performance."""

    model_config = ConfigDict(from_attributes=True)

    # Blended Metrics (all channels combined)
    total_spend: float
    total_revenue: float
    blended_roas: float | None
    total_orders: int
    total_new_customers: int
    blended_cac: float | None
    blended_contribution_margin_pct: float

    # Per-Channel Breakdown
    channel_performance: list[ChannelPerformance]

    # Top/Bottom Campaigns
    top_campaigns: list[CampaignPerformance]  # Top 5 by ROAS
    underperforming_campaigns: list[CampaignPerformance]  # Below threshold

    # Metadata
    period_start: date
    period_end: date
    data_last_synced_at: str | None
    currency: str
