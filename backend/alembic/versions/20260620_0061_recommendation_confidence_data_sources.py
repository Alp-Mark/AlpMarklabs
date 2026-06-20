"""Add confidence_score and data_sources to recommendations.

Revision ID: 20260620_0061
Revises: 20260620_0060
Create Date: 2026-06-20 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260620_0061"
down_revision = "20260620_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confidence_score (numeric 0-1)
    op.add_column(
        "recommendations",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )
    
    # Add data_sources (JSON array of connector sources)
    op.add_column(
        "recommendations",
        sa.Column("data_sources", sa.JSON(), nullable=False, server_default="[]"),
    )
    
    # Backfill confidence_score from existing confidence_level
    # Mapping: very_low=0.2, low=0.4, medium=0.6, high=0.8, very_high=0.95
    op.execute("""
        UPDATE recommendations
        SET confidence_score = CASE confidence_level
            WHEN 'very_low' THEN 0.2
            WHEN 'low' THEN 0.4
            WHEN 'medium' THEN 0.6
            WHEN 'high' THEN 0.8
            WHEN 'very_high' THEN 0.95
            ELSE 0.5
        END
        WHERE confidence_score IS NULL
    """)
    
    # Make confidence_score non-nullable after backfill
    op.alter_column("recommendations", "confidence_score", nullable=False)


def downgrade() -> None:
    op.drop_column("recommendations", "data_sources")
    op.drop_column("recommendations", "confidence_score")
