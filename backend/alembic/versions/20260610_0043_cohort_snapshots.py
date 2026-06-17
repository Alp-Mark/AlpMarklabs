"""FR-037 / T-066: Cohort snapshots for side-by-side comparison.

Revision ID: 20260610_0043
Revises: 20260610_0042
Create Date: 2026-06-10

"""

from alembic import op
import sqlalchemy as sa

revision = "20260610_0043"
down_revision = "20260610_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cohort_snapshots table for cohort comparison."""
    op.create_table(
        "cohort_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_start_date", sa.Date(), nullable=False),
        sa.Column("cohort_end_date", sa.Date(), nullable=False),
        sa.Column("cohort_grain", sa.String(50), nullable=False),
        sa.Column("observation_window_days", sa.Integer(), nullable=False),
        sa.Column("customer_count", sa.Integer(), nullable=False),
        sa.Column("repeat_rate", sa.Float(), nullable=False),
        sa.Column("churn_rate", sa.Float(), nullable=False),
        sa.Column("avg_order_value", sa.Float(), nullable=False),
        sa.Column("total_revenue", sa.Float(), nullable=False),
        sa.Column("repeat_purchase_frequency", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_cohort_snapshots_tenant", "cohort_snapshots", ["tenant_id"])
    op.create_index(
        "ix_cohort_snapshots_cohort_dates",
        "cohort_snapshots",
        ["cohort_start_date", "cohort_end_date"],
    )
    op.create_index(
        "ix_cohort_snapshots_window",
        "cohort_snapshots",
        ["observation_window_days"],
    )


def downgrade() -> None:
    """Drop cohort_snapshots table."""
    op.drop_index("ix_cohort_snapshots_window", "cohort_snapshots")
    op.drop_index("ix_cohort_snapshots_cohort_dates", "cohort_snapshots")
    op.drop_index("ix_cohort_snapshots_tenant", "cohort_snapshots")
    op.drop_table("cohort_snapshots")
