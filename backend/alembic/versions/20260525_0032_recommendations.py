"""Add recommendations table (FR-071 / T-053)

Revision ID: 20260525_0032
Revises: 20260525_0031
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0032"
down_revision = "20260525_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("domain", sa.String(30), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("affected_area", sa.String(255), nullable=False),
        sa.Column("signal_summary", sa.String(500), nullable=False),
        sa.Column("suggested_action", sa.String(500), nullable=False),
        sa.Column("estimated_impact", sa.Float(), nullable=True),
        sa.Column("confidence_level", sa.String(10), nullable=False),
        sa.Column("data_freshness_context", sa.String(255), nullable=False),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="new"
        ),
        sa.Column(
            "priority", sa.Integer(), nullable=False, server_default="50"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "rule_id",
            "snapshot_date",
            name="uq_recommendation_per_tenant_rule_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("recommendations")
