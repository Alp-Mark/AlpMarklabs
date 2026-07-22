"""add user profile_picture_url

Revision ID: 20260722_0073
Revises: 20260722_0072
Create Date: 2026-07-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260722_0073"
down_revision = "20260722_0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("profile_picture_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "profile_picture_url")
