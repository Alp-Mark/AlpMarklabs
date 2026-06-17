"""cost_inputs

Revision ID: 20260525_0025
Revises: 20260525_0024
Create Date: 2026-05-25

Creates cost_inputs table for FR-050 tiered/banded cost inputs managed
by the Finance Controller, including FR-051 high-impact confirmation
workflow for COGS changes.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0025"
down_revision = "20260525_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_inputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("input_type", sa.String(length=50), nullable=False),
        sa.Column("tier_label", sa.String(length=150), nullable=False),
        sa.Column("weight_min_kg", sa.Float(), nullable=True),
        sa.Column("weight_max_kg", sa.Float(), nullable=True),
        sa.Column("destination_zone", sa.String(length=50), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "confirmation_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cost_inputs_tenant_type",
        "cost_inputs",
        ["tenant_id", "input_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_cost_inputs_tenant_type", table_name="cost_inputs")
    op.drop_table("cost_inputs")
