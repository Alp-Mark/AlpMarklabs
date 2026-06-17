"""Add base_currency and locale to tenants (NFR-022 / T-052)

Revision ID: 20260525_0031
Revises: 20260525_0030
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa

revision = "20260525_0031"
down_revision = "20260525_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "base_currency",
            sa.String(10),
            nullable=False,
            server_default="USD",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "locale",
            sa.String(20),
            nullable=False,
            server_default="en-US",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "locale")
    op.drop_column("tenants", "base_currency")
