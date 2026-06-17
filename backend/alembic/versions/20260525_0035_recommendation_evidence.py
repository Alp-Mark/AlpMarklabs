"""Add evidence column to recommendations (FR-071 / T-057)

Revision ID: 20260525_0035
Revises: 20260525_0034
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0035"
down_revision = "20260525_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "evidence",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "evidence")
