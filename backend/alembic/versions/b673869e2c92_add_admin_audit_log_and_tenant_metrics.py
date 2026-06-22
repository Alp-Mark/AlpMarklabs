"""add admin audit log and tenant metrics

Revision ID: b673869e2c92
Revises: 20260620_0065
Create Date: 2026-06-22 16:04:23.741111
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b673869e2c92'
down_revision = '20260620_0065'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create admin_audit_logs table for platform-level audit trail
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),  # Nullable for platform-wide actions
        sa.Column('admin_user_id', sa.UUID(), nullable=False),  # Who performed the action
        sa.Column('action_type', sa.String(100), nullable=False),  # e.g., tenant_created, tenant_suspended
        sa.Column('resource_type', sa.String(100), nullable=False),  # e.g., tenant, user
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=False, server_default='{}'),  # Before/after state
        sa.Column('reason', sa.Text(), nullable=True),  # Optional reason for action
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_audit_logs_tenant_id', 'admin_audit_logs', ['tenant_id'])
    op.create_index('ix_admin_audit_logs_admin_user_id', 'admin_audit_logs', ['admin_user_id'])
    op.create_index('ix_admin_audit_logs_action_type', 'admin_audit_logs', ['action_type'])
    op.create_index('ix_admin_audit_logs_created_at', 'admin_audit_logs', ['created_at'])

    # Add fields to tenants table for lifecycle tracking
    op.add_column('tenants', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    op.add_column('tenants', sa.Column('status_reason', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add last_login_at to users table for activity tracking
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove added columns
    op.drop_column('users', 'last_login_at')
    op.drop_column('tenants', 'deleted_at')
    op.drop_column('tenants', 'suspended_at')
    op.drop_column('tenants', 'status_reason')
    op.drop_column('tenants', 'status')
    
    # Drop indexes and table
    op.drop_index('ix_admin_audit_logs_created_at', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_action_type', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_admin_user_id', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_tenant_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
