"""shopify_order_line_items

Revision ID: 20260525_0029
Revises: 20260525_0028
Create Date: 2026-05-25

Creates shopify_order_line_items table — one row per line item per order.
Enables real per-SKU velocity computation in the inventory risk job.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0029"
down_revision = "20260525_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopify_order_line_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("line_item_index", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("product_title", sa.String(length=255), nullable=False),
        sa.Column("variant_title", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("order_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["order_id"], ["shopify_orders.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "order_id",
            "line_item_index",
            name="uq_shopify_order_line_item_per_order_index",
        ),
    )
    op.create_index(
        "ix_shopify_order_line_items_tenant_sku_date",
        "shopify_order_line_items",
        ["tenant_id", "sku", "order_created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shopify_order_line_items_tenant_sku_date",
        table_name="shopify_order_line_items",
    )
    op.drop_table("shopify_order_line_items")
