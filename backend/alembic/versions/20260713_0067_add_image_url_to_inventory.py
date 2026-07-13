"""Add image_url column to shopify_inventory_items for product variant images

Revision ID: 20260713_0067
Revises: dfea8b94212e
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '20260713_0067'
down_revision = 'dfea8b94212e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_inventory_items",
        sa.Column(
            "image_url",
            sa.Text,
            nullable=True,
            comment="Product variant image URL from Shopify CDN",
        ),
    )


def downgrade() -> None:
    op.drop_column("shopify_inventory_items", "image_url")
