"""Add impact_score column to recommendations (FR-071 / T-055)

Revision ID: 20260525_0034
Revises: 20260525_0033
Create Date: 2026-05-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0034"
down_revision = "20260525_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "impact_score",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "impact_score")
