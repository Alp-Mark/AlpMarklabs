"""Add billing and seat metadata to tenants.

Revision ID: 20260522_0002
Revises: 20260522_0001
Create Date: 2026-05-22 13:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260522_0002"
down_revision = "20260522_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "billing_plan",
            sa.String(length=50),
            nullable=False,
            server_default="starter",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "billing_cycle",
            sa.String(length=20),
            nullable=False,
            server_default="monthly",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "billing_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "seat_limit",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "seat_limit")
    op.drop_column("tenants", "billing_status")
    op.drop_column("tenants", "billing_cycle")
    op.drop_column("tenants", "billing_plan")
