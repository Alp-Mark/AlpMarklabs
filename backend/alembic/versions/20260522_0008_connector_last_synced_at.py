"""Add last_synced_at to connector integrations.

Revision ID: 20260522_0008
Revises: 20260522_0007
Create Date: 2026-05-22 23:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0008"
down_revision = "20260522_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connector_integrations",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("connector_integrations", "last_synced_at")
