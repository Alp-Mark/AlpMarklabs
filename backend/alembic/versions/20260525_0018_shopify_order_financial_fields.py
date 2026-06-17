"""shopify_order_financial_fields

Revision ID: 20260525_0018
Revises: 20260525_0017
Create Date: 2026-05-25

Adds discount_amount, shipping_amount, refund_amount, and is_refunded to
shopify_orders.  These are required by:
  - FR-048  discount and shipping as cost drivers
  - FR-042  return/refund as retention signal per cohort
  - FR-065  fulfillment cost visibility
  - FR-066  operational returns view
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0018"
down_revision = "20260525_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_orders",
        sa.Column("discount_amount", sa.Float(), nullable=True),
    )
    op.add_column(
        "shopify_orders",
        sa.Column("shipping_amount", sa.Float(), nullable=True),
    )
    op.add_column(
        "shopify_orders",
        sa.Column("refund_amount", sa.Float(), nullable=True),
    )
    op.add_column(
        "shopify_orders",
        sa.Column(
            "is_refunded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("shopify_orders", "is_refunded")
    op.drop_column("shopify_orders", "refund_amount")
    op.drop_column("shopify_orders", "shipping_amount")
    op.drop_column("shopify_orders", "discount_amount")
