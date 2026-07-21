"""create_marketing_channel_spends

Revision ID: 20260721_0070
Revises: 20260715_0069
Create Date: 2026-07-21

Creates marketing_channel_spends table for multi-channel budget optimizer.
Stores daily spend, conversions, and revenue for non-Meta/Google channels:
influencer, email, tv_streaming, affiliate.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260721_0070"
down_revision = "20260715_0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketing_channel_spends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("channel_name", sa.String(50), nullable=False),
        sa.Column("spend_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("spend_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel_name",
            "spend_date",
            name="uq_marketing_channel_spend_per_channel_date",
        ),
    )
    op.create_index(
        "ix_marketing_channel_spends_tenant_date",
        "marketing_channel_spends",
        ["tenant_id", "spend_date"],
    )
    op.create_index(
        "ix_marketing_channel_spends_tenant_channel",
        "marketing_channel_spends",
        ["tenant_id", "channel_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_channel_spends_tenant_channel")
    op.drop_index("ix_marketing_channel_spends_tenant_date")
    op.drop_table("marketing_channel_spends")
