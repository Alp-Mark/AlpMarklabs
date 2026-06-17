"""Add saved analysis views and share metadata (FR-032, FR-034 / T-064)

Revision ID: 20260602_0041
Revises: 20260602_0040
Create Date: 2026-06-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260602_0041"
down_revision = "20260602_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_analysis_views",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("filters_config", sa.JSON(), nullable=False),
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
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_saved_analysis_views_tenant_id",
        "saved_analysis_views",
        ["tenant_id"],
    )
    op.create_index(
        "ix_saved_analysis_views_created_by_id",
        "saved_analysis_views",
        ["created_by_id"],
    )

    op.create_table(
        "analysis_view_shares",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("saved_view_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("shared_by_id", sa.UUID(), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("scope", sa.String(30), nullable=False, server_default="tenant"),
        sa.Column("one_time_token", sa.String(128), nullable=True, unique=True),
        sa.Column(
            "shared_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["saved_view_id"], ["saved_analysis_views.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["shared_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_view_shares_saved_view_id",
        "analysis_view_shares",
        ["saved_view_id"],
    )
    op.create_index(
        "ix_analysis_view_shares_tenant_id",
        "analysis_view_shares",
        ["tenant_id"],
    )
    op.create_index(
        "ix_analysis_view_shares_shared_by_id",
        "analysis_view_shares",
        ["shared_by_id"],
    )


def downgrade() -> None:
    op.drop_table("analysis_view_shares")
    op.drop_table("saved_analysis_views")
