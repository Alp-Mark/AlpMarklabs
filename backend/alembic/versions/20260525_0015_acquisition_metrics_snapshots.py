"""Add acquisition metrics snapshots table for daily per-channel computation.

Revision ID: 20260525_0015
Revises: 20260525_0014
Create Date: 2026-05-25 11:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0015"
down_revision = "20260525_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_metrics_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("ad_spend_amount", sa.Float(), nullable=False),
        sa.Column("revenue_attributed", sa.Float(), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("roas", sa.Float(), nullable=False),
        sa.Column("cac", sa.Float(), nullable=False),
        sa.Column("contribution_margin_pct", sa.Float(), nullable=False),
        sa.Column("payback_period_days", sa.Float(), nullable=False),
        sa.Column("payback_upside_days", sa.Float(), nullable=False),
        sa.Column("payback_downside_days", sa.Float(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "channel",
            "snapshot_date",
            name="uq_acquisition_metrics_per_tenant_channel_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("acquisition_metrics_snapshots")
