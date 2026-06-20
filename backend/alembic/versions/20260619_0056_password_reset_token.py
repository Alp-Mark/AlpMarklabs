"""password_reset_token

Revision ID: 0056
Revises: 0055
Create Date: 2026-06-19

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260619_0056"
down_revision = "20260619_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_password_reset_tokens_email'), 'password_reset_tokens', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_password_reset_tokens_email'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
