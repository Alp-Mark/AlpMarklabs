"""Create export_shares table for T-086 scoped export sharing.

Revision ID: 20260613_0052
Revises: 20260612_0051
Create Date: 2026-06-13 00:00:00.000000

T-086: Scoped export sharing with permission checks.
Tracks which user shared a simulation export with which recipient.
Enforces permission checks at share creation time.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260613_0052"
down_revision = "20260612_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create export_shares table
    op.create_table(
        "export_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("simulation_id", sa.Uuid(), nullable=False),
        sa.Column("shared_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("shared_with_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shared_by_user_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["shared_with_user_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "simulation_id",
            "shared_by_user_id",
            "shared_with_user_id",
            name="uq_export_share_per_sim_sharer_recipient",
        ),
    )
    op.create_index(
        op.f("ix_export_shares_shared_by_user_id"),
        "export_shares",
        ["shared_by_user_id"],
        unique=False
    )
    op.create_index(
        op.f("ix_export_shares_shared_with_user_id"),
        "export_shares",
        ["shared_with_user_id"],
        unique=False
    )
    op.create_index(
        op.f("ix_export_shares_simulation_id"),
        "export_shares",
        ["simulation_id"],
        unique=False
    )
    op.create_index(
        op.f("ix_export_shares_tenant_id"),
        "export_shares",
        ["tenant_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_export_shares_tenant_id"), table_name="export_shares"
    )
    op.drop_index(
        op.f("ix_export_shares_simulation_id"), table_name="export_shares"
    )
    op.drop_index(
        op.f("ix_export_shares_shared_with_user_id"), table_name="export_shares"
    )
    op.drop_index(
        op.f("ix_export_shares_shared_by_user_id"), table_name="export_shares"
    )
    op.drop_table("export_shares")
