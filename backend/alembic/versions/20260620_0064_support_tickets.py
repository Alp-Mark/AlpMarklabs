"""Add support_tickets table.

Revision ID: 20260620_0064
Revises: 20260620_0063
Create Date: 2026-06-20 09:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260620_0064"
down_revision = "20260620_0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # E4: Support ticket lifecycle management (FR-092, FR-093, FR-099, FR-100, FR-101)
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("resolution_category", sa.String(50), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_support_tickets_tenant_id"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_support_tickets_created_by_user_id"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], name="fk_support_tickets_assigned_to_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("support_tickets")
