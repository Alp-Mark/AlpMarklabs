"""Add retention_daily_snapshots and cohort_retention_snapshots tables.

Revision ID: 20260525_0017
Revises: 20260525_0016
Create Date: 2026-05-25 13:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0017"
down_revision = "20260525_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_daily_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_customers", sa.Integer(), nullable=False),
        sa.Column("repeat_customers", sa.Integer(), nullable=False),
        sa.Column("repeat_purchase_rate_pct", sa.Float(), nullable=False),
        sa.Column("trend_30d", sa.Float(), nullable=True),
        sa.Column("trend_60d", sa.Float(), nullable=True),
        sa.Column("trend_90d", sa.Float(), nullable=True),
        sa.Column("expected_repurchase_cadence_days", sa.Float(), nullable=True),
        sa.Column("lifecycle_funnel", sa.JSON(), nullable=False),
        sa.Column("churn_risk_summary", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "snapshot_date",
            name="uq_retention_daily_per_tenant_date",
        ),
    )
    op.create_table(
        "cohort_retention_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_month", sa.String(length=7), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("cohort_size", sa.Integer(), nullable=False),
        sa.Column("repeat_customer_count", sa.Integer(), nullable=False),
        sa.Column("repeat_purchase_rate_pct", sa.Float(), nullable=False),
        sa.Column("days_since_cohort_start", sa.Integer(), nullable=False),
        sa.Column("avg_days_to_second_order", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "cohort_month",
            "snapshot_date",
            name="uq_cohort_retention_per_tenant_cohort_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("cohort_retention_snapshots")
    op.drop_table("retention_daily_snapshots")
