"""Pydantic schemas for Analytics endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class TopProduct(BaseModel):
    """Top-selling product with performance metrics."""

    model_config = ConfigDict(from_attributes=True)

    sku: str
    product_title: str
    variant_title: str | None
    quantity_sold: int
    total_revenue: float  # ₹ total revenue from this product
    avg_unit_price: float  # Average price per unit sold
    avg_quantity_per_order: float  # Avg quantity purchased in orders


class TopProductsResponse(BaseModel):
    """Top products endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    products: list[TopProduct]
    period_start: date
    period_end: date
    total_products_count: int  # Total unique products in period
    total_orders: int  # Total orders in period


class ChannelBreakdownItem(BaseModel):
    """Breakdown of orders/revenue by channel."""

    model_config = ConfigDict(from_attributes=True)

    # Channel: meta, google, email, influencer, tv_streaming, affiliate,
    # organic, direct
    channel_name: str
    order_count: int
    revenue: float  # ₹ total revenue from this channel
    revenue_pct: float  # Percentage of total revenue
    avg_order_value: float  # Average order value for this channel
    conversion_count: int | None  # Number of conversions (if tracked)


class ChannelBreakdownResponse(BaseModel):
    """Channel breakdown endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    channels: list[ChannelBreakdownItem]
    total_revenue: float
    total_orders: int
    period_start: date
    period_end: date
    currency: str
