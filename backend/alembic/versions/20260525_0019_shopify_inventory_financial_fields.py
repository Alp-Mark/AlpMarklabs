"""shopify_inventory_financial_fields

Revision ID: 20260525_0019
Revises: 20260525_0018
Create Date: 2026-05-25

Adds reorder_point, cost_per_unit, and location_id to shopify_inventory_items.
These are required by:
  - FR-059  low-stock flag when available_quantity < reorder_point per SKU
  - FR-062  capital tied up = available_quantity * cost_per_unit
  - FR-063  per-warehouse/location inventory view
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0019"
down_revision = "20260525_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_inventory_items",
        sa.Column("reorder_point", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shopify_inventory_items",
        sa.Column("cost_per_unit", sa.Float(), nullable=True),
    )
    op.add_column(
        "shopify_inventory_items",
        sa.Column("location_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shopify_inventory_items", "location_id")
    op.drop_column("shopify_inventory_items", "cost_per_unit")
    op.drop_column("shopify_inventory_items", "reorder_point")
