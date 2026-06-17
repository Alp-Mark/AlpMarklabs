"""Add executive KPI snapshots table for daily KPI/drift computation.

Revision ID: 20260525_0014
Revises: 20260522_0013
Create Date: 2026-05-25 10:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0014"
down_revision = "20260522_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executive_kpi_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_start_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("revenue_amount", sa.Float(), nullable=False),
        sa.Column("ad_spend_amount", sa.Float(), nullable=False),
        sa.Column("blended_roas", sa.Float(), nullable=False),
        sa.Column("contribution_margin_pct", sa.Float(), nullable=False),
        sa.Column("drift", sa.JSON(), nullable=False),
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
            "snapshot_date",
            name="uq_executive_kpi_snapshot_per_tenant_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("executive_kpi_snapshots")
