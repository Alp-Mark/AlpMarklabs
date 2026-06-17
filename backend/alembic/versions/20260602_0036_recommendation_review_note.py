"""Add review_note column to recommendations (FR-073 / T-059)

Revision ID: 20260602_0036
Revises: 20260525_0035
Create Date: 2026-06-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260602_0036"
down_revision = "20260525_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column("review_note", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "review_note")
