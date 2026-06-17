"""margin_drift_thresholds

Revision ID: 20260525_0023
Revises: 20260525_0022
Create Date: 2026-05-25

Creates margin_drift_thresholds table for FR-053 Finance Controller
per-channel/category drift alert threshold profiles.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0023"
down_revision = "20260525_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "margin_drift_thresholds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("threshold_pct", sa.Float(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_mdt_created_by"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "category",
            name="uq_margin_drift_threshold_per_tenant_channel_category",
        ),
    )


def downgrade() -> None:
    op.drop_table("margin_drift_thresholds")
