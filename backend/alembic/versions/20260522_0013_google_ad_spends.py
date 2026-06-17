"""Add Google ad spend table for sync task.

Revision ID: 20260522_0013
Revises: 20260522_0012
Create Date: 2026-05-23 03:35:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0013"
down_revision = "20260522_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_ad_spends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("external_campaign_id", sa.String(length=100), nullable=False),
        sa.Column("campaign_name", sa.String(length=255), nullable=False),
        sa.Column("spend_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("spend_amount", sa.Float(), nullable=False),
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
            "external_campaign_id",
            "spend_date",
            name="uq_google_ad_spend_per_campaign_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("google_ad_spends")
