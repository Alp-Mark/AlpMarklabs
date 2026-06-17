"""Add connector integrations table.

Revision ID: 20260522_0006
Revises: 20260522_0005
Create Date: 2026-05-22 22:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260522_0006"
down_revision = "20260522_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("auth_mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=True),
        sa.Column("oauth_state", sa.String(length=128), nullable=True),
        sa.Column("credential_ref", sa.String(length=255), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            name="uq_connector_per_tenant_source",
        ),
    )


def downgrade() -> None:
    op.drop_table("connector_integrations")
