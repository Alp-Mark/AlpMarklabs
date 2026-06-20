"""user_is_platform_admin

Revision ID: 0055
Revises: 0054
Create Date: 2026-06-19

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260619_0055"
down_revision = "20260619_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_platform_admin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_platform_admin')
