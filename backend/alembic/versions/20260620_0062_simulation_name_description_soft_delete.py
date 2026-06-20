"""Add name, description, and soft delete to simulations.

Revision ID: 20260620_0062
Revises: 20260620_0061
Create Date: 2026-06-20 13:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

revision = "20260620_0062"
down_revision = "20260620_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add name field (user-provided label for simulation)
    op.add_column(
        "simulations",
        sa.Column("name", sa.String(length=255), nullable=True),
    )
    
    # Add description field (user notes about simulation)
    op.add_column(
        "simulations",
        sa.Column("description", sa.Text(), nullable=True),
    )
    
    # Add is_deleted for soft delete (preserve audit trail)
    op.add_column(
        "simulations",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=text("false"),
        ),
    )
    
    # Add updated_at for tracking rename/edits
    op.add_column(
        "simulations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("simulations", "updated_at")
    op.drop_column("simulations", "is_deleted")
    op.drop_column("simulations", "description")
    op.drop_column("simulations", "name")
