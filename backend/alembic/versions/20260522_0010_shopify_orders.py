"""Add Shopify orders table for sync task.

Revision ID: 20260522_0010
Revises: 20260522_0009
Create Date: 2026-05-23 00:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0010"
down_revision = "20260522_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopify_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("external_order_id", sa.String(length=100), nullable=False),
        sa.Column("order_number", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("order_created_at", sa.DateTime(timezone=True), nullable=False),
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
            "external_order_id",
            name="uq_shopify_order_per_connector",
        ),
    )


def downgrade() -> None:
    op.drop_table("shopify_orders")
