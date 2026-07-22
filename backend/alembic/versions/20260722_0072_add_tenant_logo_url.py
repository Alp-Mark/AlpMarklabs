"""add tenant logo_url

Revision ID: 20260722_0072
Revises: 20260722_0071
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260722_0072"
down_revision = "20260722_0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("logo_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tenants", "logo_url")
