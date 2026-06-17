"""cost_input_versions

Revision ID: 20260525_0026
Revises: 20260525_0025
Create Date: 2026-05-25

Creates cost_input_versions table for FR-052 / NFR-013 full version
history of every cost input from first value captured in AlpMark onward.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0026"
down_revision = "20260525_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_input_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cost_input_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("prior_amount", sa.Float(), nullable=True),
        sa.Column("new_amount", sa.Float(), nullable=False),
        sa.Column("prior_unit", sa.String(length=50), nullable=True),
        sa.Column("new_unit", sa.String(length=50), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("variance_reason", sa.String(length=150), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cost_input_id"], ["cost_inputs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cost_input_versions_cost_input_id",
        "cost_input_versions",
        ["cost_input_id", "version_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cost_input_versions_cost_input_id",
        table_name="cost_input_versions",
    )
    op.drop_table("cost_input_versions")
