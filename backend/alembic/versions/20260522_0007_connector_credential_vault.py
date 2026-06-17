"""Add connector credential vault table.

Revision ID: 20260522_0007
Revises: 20260522_0006
Create Date: 2026-05-22 23:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260522_0007"
down_revision = "20260522_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_credential_vault",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("secret_type", sa.String(length=30), nullable=False),
        sa.Column("secret_ciphertext", sa.String(length=2000), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("key_version", sa.String(length=50), nullable=False),
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
        sa.ForeignKeyConstraint(["connector_id"], ["connector_integrations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connector_id", name="uq_connector_credential_connector"),
    )


def downgrade() -> None:
    op.drop_table("connector_credential_vault")
