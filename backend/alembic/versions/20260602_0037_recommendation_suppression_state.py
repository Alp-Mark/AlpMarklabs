"""Add recommendation_suppression_states table (FR-074 / T-060)

Revision ID: 20260602_0037
Revises: 20260602_0036
Create Date: 2026-06-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0037"
down_revision = "20260602_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_suppression_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("rejection_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suppressed_until", sa.Date(), nullable=True),
        sa.Column("is_overridden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rejection_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("suppression_window_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "rule_id", name="uq_suppression_per_tenant_rule"
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendation_suppression_states")
