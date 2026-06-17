"""Create acquisition_cohorts table for retention manager acquisition context.

FR-043 / T-070: Snapshots of acquisition metrics by cohort and channel.
Retention managers use this read-only data to understand incoming customer
quality differences for retention strategy analysis.

Revision ID: 20260610_0045
Revises: 20260610_0044
Create Date: 2026-06-10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260610_0045"
down_revision = "20260610_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_cohorts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("cohort_start_date", sa.Date(), nullable=False),
        sa.Column("cohort_end_date", sa.Date(), nullable=False),
        sa.Column("cohort_grain", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(100), nullable=False),
        sa.Column("new_customer_count", sa.Integer(), nullable=False),
        sa.Column("blended_cac", sa.Float(), nullable=False),
        sa.Column("first_order_aov", sa.Float(), nullable=False),
        sa.Column("total_acquisition_spend", sa.Float(), nullable=False),
        sa.Column("repeat_purchase_rate_90d", sa.Float(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "cohort_start_date",
            "cohort_end_date",
            "channel",
            name="uq_acquisition_cohort_per_tenant_period_channel",
        ),
    )
    op.create_index(
        "ix_acquisition_cohorts_tenant",
        "acquisition_cohorts",
        ["tenant_id"],
    )
    op.create_index(
        "ix_acquisition_cohorts_cohort_dates",
        "acquisition_cohorts",
        ["cohort_start_date", "cohort_end_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_acquisition_cohorts_cohort_dates")
    op.drop_index("ix_acquisition_cohorts_tenant")
    op.drop_table("acquisition_cohorts")
