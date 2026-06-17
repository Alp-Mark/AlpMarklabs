"""Add customer_id column to shopify_orders table.

Revision ID: 20260525_0016
Revises: 20260525_0015
Create Date: 2026-05-25 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0016"
down_revision = "20260525_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_orders",
        sa.Column("customer_id", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shopify_orders", "customer_id")
