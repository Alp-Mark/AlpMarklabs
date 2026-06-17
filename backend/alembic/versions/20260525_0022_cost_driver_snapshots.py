"""cost_driver_snapshots

Revision ID: 20260525_0022
Revises: 20260525_0021
Create Date: 2026-05-25

Creates cost_driver_snapshots table for FR-048/FR-049 cost-driver
impact per driver type with recency-based confidence labeling.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0022"
down_revision = "20260525_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_driver_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("driver_type", sa.String(length=50), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("absolute_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pct_of_revenue", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "margin_impact_amount", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_platform", sa.String(length=50), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_label", sa.String(length=10), nullable=False),
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
            "driver_type",
            "snapshot_date",
            name="uq_cost_driver_per_tenant_driver_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("cost_driver_snapshots")
