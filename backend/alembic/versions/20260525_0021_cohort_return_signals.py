"""cohort_return_signals

Revision ID: 20260525_0021
Revises: 20260525_0020
Create Date: 2026-05-25

Creates cohort_return_signals table for FR-042 return/refund data as
a retention signal per cohort — completely separate from the operational
returns view.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0021"
down_revision = "20260525_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cohort_return_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_month", sa.String(length=7), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("cohort_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refunded_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("return_rate_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "repeat_purchase_rate_pct",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
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
            "cohort_month",
            "snapshot_date",
            name="uq_cohort_return_signal_per_tenant_cohort_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("cohort_return_signals")
