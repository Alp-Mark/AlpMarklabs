"""segment_margin_snapshots

Revision ID: 20260525_0020
Revises: 20260525_0019
Create Date: 2026-05-25

Creates segment_margin_snapshots table for FR-041 contribution margin
per customer segment (new, returning, high_value, at_risk, churned).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0020"
down_revision = "20260525_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "segment_margin_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("segment_type", sa.String(length=50), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("customer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cogs", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shipping_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("returns_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acquisition_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "contribution_margin_amount",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "contribution_margin_pct",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
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
            "segment_type",
            "snapshot_date",
            name="uq_segment_margin_per_tenant_segment_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("segment_margin_snapshots")
