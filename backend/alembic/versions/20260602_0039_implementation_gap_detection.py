"""Add implementation gap detection columns to recommendations (FR-076 / T-062)

Revision ID: 20260602_0039
Revises: 20260602_0038
Create Date: 2026-06-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260602_0039"
down_revision = "20260602_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "implementation_gap_flag",
            sa.String(20),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "approved_at")
    op.drop_column("recommendations", "implementation_gap_flag")
