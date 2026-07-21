"""create_tenant_goals

Revision ID: 20260722_0071
Revises: 20260721_0070
Create Date: 2026-07-22

Stores executive KPI targets per tenant. Each goal tracks a metric,
a target value, a target date, and whether it is pinned (shown on dashboard).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260722_0071"
down_revision = "20260721_0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("metric_key", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_goals_tenant_pinned",
        "tenant_goals",
        ["tenant_id", "is_pinned"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_goals_tenant_pinned")
    op.drop_table("tenant_goals")
