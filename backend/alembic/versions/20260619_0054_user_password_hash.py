"""user_password_hash

Revision ID: 0054
Revises: 0053
Create Date: 2026-06-19

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260619_0054"
down_revision = "20260613_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
