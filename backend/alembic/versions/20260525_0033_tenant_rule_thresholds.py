"""Add tenant_rule_thresholds table (FR-071 / T-054)

Revision ID: 20260525_0033
Revises: 20260525_0032
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0033"
down_revision = "20260525_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_rule_thresholds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("threshold_unit", sa.String(30), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("suggested_value", sa.Float(), nullable=True),
        sa.Column("is_customised", sa.Boolean(), nullable=False, server_default="false"),
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
            "rule_id",
            name="uq_tenant_rule_threshold_per_tenant_rule",
        ),
    )


def downgrade() -> None:
    op.drop_table("tenant_rule_thresholds")
