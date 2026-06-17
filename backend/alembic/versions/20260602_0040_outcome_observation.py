"""Add outcome observation columns to recommendations (FR-069, FR-077 / T-063)

Revision ID: 20260602_0040
Revises: 20260602_0039
Create Date: 2026-06-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260602_0040"
down_revision = "20260602_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column(
            "implemented_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "outcome_observed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "outcome_metrics_before",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "outcome_metrics_after",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "outcome_impact_summary",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "implemented_at")
    op.drop_column("recommendations", "outcome_observed_at")
    op.drop_column("recommendations", "outcome_metrics_before")
    op.drop_column("recommendations", "outcome_metrics_after")
    op.drop_column("recommendations", "outcome_impact_summary")
