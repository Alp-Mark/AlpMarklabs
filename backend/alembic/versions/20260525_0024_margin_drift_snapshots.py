"""margin_drift_snapshots

Revision ID: 20260525_0024
Revises: 20260525_0023
Create Date: 2026-05-25

Creates margin_drift_snapshots table for FR-054 daily margin drift
computation per channel/category with alert threshold checking.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0024"
down_revision = "20260525_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "margin_drift_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column(
            "actual_margin_pct", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("expected_margin_pct", sa.Float(), nullable=True),
        sa.Column("drift_pct", sa.Float(), nullable=True),
        sa.Column(
            "threshold_exceeded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("variance_reason", sa.String(length=100), nullable=False),
        sa.Column("data_completeness", sa.String(length=50), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "category",
            "snapshot_date",
            name="uq_margin_drift_per_tenant_channel_category_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("margin_drift_snapshots")
