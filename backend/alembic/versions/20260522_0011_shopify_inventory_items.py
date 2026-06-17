"""Add Shopify inventory items table for sync task.

Revision ID: 20260522_0011
Revises: 20260522_0010
Create Date: 2026-05-23 01:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0011"
down_revision = "20260522_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopify_inventory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("external_inventory_item_id", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("product_title", sa.String(length=255), nullable=False),
        sa.Column("variant_title", sa.String(length=255), nullable=True),
        sa.Column("available_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_integrations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connector_id",
            "external_inventory_item_id",
            name="uq_shopify_inventory_item_per_connector",
        ),
    )


def downgrade() -> None:
    op.drop_table("shopify_inventory_items")
