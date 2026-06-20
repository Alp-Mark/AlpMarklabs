"""roles and rbac system

Revision ID: 0058
Revises: 0057
Create Date: 2026-06-20

"""
import json
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260620_0058"
down_revision = "20260619_0057"
branch_labels = None
depends_on = None


# System role permissions mapping
SYSTEM_ROLE_PERMISSIONS = {
    "brand_admin": [
        "admin.members",
        "admin.roles",
        "admin.billing",
        "admin.integrations",
        "admin.settings",
        "admin.audit",
    ],
    "executive_owner": [
        "executive.view",
        "executive.targets",
        "executive.approve",
        "executive.simulate",
        "intel.recommendations.view",
        "intel.recommendations.approve",
        "intel.simulations.run",
        "intel.simulations.view",
        "intel.insights.view",
        "intel.alerts.manage",
    ],
    "growth_performance_manager": [
        "growth.view",
        "growth.analyze",
        "growth.simulate",
        "intel.recommendations.view",
        "intel.recommendations.review",
        "intel.simulations.run",
        "intel.simulations.view",
        "intel.insights.view",
        "intel.alerts.manage",
    ],
    "retention_crm_manager": [
        "retention.view",
        "retention.analyze",
        "retention.simulate",
        "intel.recommendations.view",
        "intel.recommendations.review",
        "intel.simulations.run",
        "intel.simulations.view",
        "intel.insights.view",
        "intel.alerts.manage",
    ],
    "finance_controller": [
        "finance.view",
        "finance.edit_costs",
        "finance.analyze",
        "intel.recommendations.view",
        "intel.recommendations.review",
        "intel.insights.view",
    ],
    "operations_inventory_manager": [
        "operations.view",
        "operations.inventory",
        "operations.analyze",
        "intel.recommendations.view",
        "intel.recommendations.review",
        "intel.insights.view",
        "intel.alerts.manage",
    ],
}


def upgrade() -> None:
    # 1. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('permissions', JSONB, nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_role_tenant_name')
    )
    op.create_index(op.f('ix_roles_tenant_id'), 'roles', ['tenant_id'], unique=False)

    # 2. Add role_id column to tenant_memberships (nullable initially)
    op.add_column('tenant_memberships', sa.Column('role_id', UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_tenant_memberships_role_id'), 'tenant_memberships', ['role_id'], unique=False)
    op.create_foreign_key('fk_tenant_memberships_role_id', 'tenant_memberships', 'roles', ['role_id'], ['id'])

    # 3. Seed system roles for all tenants
    connection = op.get_bind()
    
    # Get all tenants
    tenants = connection.execute(sa.text("SELECT id FROM tenants")).fetchall()
    
    for tenant_row in tenants:
        tenant_id = tenant_row[0]
        
        # Create system roles for this tenant
        for role_name, permissions in SYSTEM_ROLE_PERMISSIONS.items():
            role_id = uuid.uuid4()
            connection.execute(
                sa.text("""
                    INSERT INTO roles (id, tenant_id, name, permissions, is_system, created_at, updated_at)
                    VALUES (:id, :tenant_id, :name, :permissions, true, now(), now())
                """),
                {
                    "id": role_id,
                    "tenant_id": tenant_id,
                    "name": role_name,
                    "permissions": json.dumps(permissions)
                }
            )
    
    # 4. Migrate existing role strings to role_id FKs
    # Update each membership to point to the corresponding role
    connection.execute(sa.text("""
        UPDATE tenant_memberships tm
        SET role_id = r.id
        FROM roles r
        WHERE tm.tenant_id = r.tenant_id
        AND tm.role = r.name
        AND r.is_system = true
    """))
    
    # 5. Make role_id NOT NULL (all memberships should now have role_id)
    op.alter_column('tenant_memberships', 'role_id', nullable=False)


def downgrade() -> None:
    # Remove role_id column and constraint
    op.drop_constraint('fk_tenant_memberships_role_id', 'tenant_memberships', type_='foreignkey')
    op.drop_index(op.f('ix_tenant_memberships_role_id'), table_name='tenant_memberships')
    op.drop_column('tenant_memberships', 'role_id')
    
    # Drop roles table
    op.drop_index(op.f('ix_roles_tenant_id'), table_name='roles')
    op.drop_table('roles')
