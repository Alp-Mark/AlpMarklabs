"""Add health_status to connector integrations.

Revision ID: 20260620_0063
Revises: 20260620_0062
Create Date: 2026-06-20 08:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260620_0063"
down_revision = "20260620_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add health_status column (computed from sync/freshness/errors)
    op.add_column(
        "connector_integrations",
        sa.Column(
            "health_status",
            sa.String(20),
            nullable=False,
            server_default="unknown",
        ),
    )


def downgrade() -> None:
    op.drop_column("connector_integrations", "health_status")
