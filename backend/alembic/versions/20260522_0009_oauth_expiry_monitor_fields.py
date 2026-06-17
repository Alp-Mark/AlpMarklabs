"""Add OAuth expiry monitoring fields to connector integrations.

Revision ID: 20260522_0009
Revises: 20260522_0008
Create Date: 2026-05-23 00:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0009"
down_revision = "20260522_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connector_integrations",
        sa.Column("oauth_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "connector_integrations",
        sa.Column(
            "oauth_expiry_warning_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "connector_integrations",
        sa.Column(
            "oauth_expired_alert_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("connector_integrations", "oauth_expired_alert_sent_at")
    op.drop_column("connector_integrations", "oauth_expiry_warning_sent_at")
    op.drop_column("connector_integrations", "oauth_expires_at")
