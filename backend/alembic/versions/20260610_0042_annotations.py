"""Add annotations table for analysis views and cohorts (FR-033, FR-045, FR-068 / T-065)

Revision ID: 20260610_0042
Revises: 20260602_0041
Create Date: 2026-06-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260610_0042"
down_revision = "20260602_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("saved_view_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("annotation_type", sa.String(50), nullable=True),
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
        sa.ForeignKeyConstraint(["saved_view_id"], ["saved_analysis_views.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_annotations_tenant_id", "annotations", ["tenant_id"])
    op.create_index("ix_annotations_saved_view_id", "annotations", ["saved_view_id"])
    op.create_index("ix_annotations_created_by_id", "annotations", ["created_by_id"])
    op.create_index("ix_annotations_event_date", "annotations", ["event_date"])


def downgrade() -> None:
    op.drop_index("ix_annotations_event_date", table_name="annotations")
    op.drop_index("ix_annotations_created_by_id", table_name="annotations")
    op.drop_index("ix_annotations_saved_view_id", table_name="annotations")
    op.drop_index("ix_annotations_tenant_id", table_name="annotations")
    op.drop_table("annotations")
