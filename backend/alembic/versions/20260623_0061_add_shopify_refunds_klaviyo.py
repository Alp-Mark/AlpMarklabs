"""add shopify refunds and klaviyo campaigns tables

Revision ID: 20260623_0061
Revises: b673869e2c92
Create Date: 2026-06-23 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260623_0061'
down_revision = 'b673869e2c92'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create shopify_refunds table
    op.create_table(
        'shopify_refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_refund_id', sa.String(100), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('external_order_id', sa.String(100), nullable=True),
        sa.Column('refund_amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('refund_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connector_id'], ['connector_integrations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['shopify_orders.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'connector_id', 'external_refund_id', name='uq_shopify_refund_per_connector')
    )
    op.create_index('ix_shopify_refunds_tenant_id', 'shopify_refunds', ['tenant_id'])
    op.create_index('ix_shopify_refunds_connector_id', 'shopify_refunds', ['connector_id'])
    op.create_index('ix_shopify_refunds_order_id', 'shopify_refunds', ['order_id'])
    op.create_index('ix_shopify_refunds_refund_created_at', 'shopify_refunds', ['refund_created_at'])

    # Create klaviyo_campaigns table
    op.create_table(
        'klaviyo_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('external_campaign_id', sa.String(100), nullable=True),
        sa.Column('campaign_name', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recipients', sa.Integer(), nullable=False, default=0),
        sa.Column('opens', sa.Integer(), nullable=False, default=0),
        sa.Column('clicks', sa.Integer(), nullable=False, default=0),
        sa.Column('conversions', sa.Integer(), nullable=True),
        sa.Column('revenue', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_klaviyo_campaigns_tenant_id', 'klaviyo_campaigns', ['tenant_id'])
    op.create_index('ix_klaviyo_campaigns_sent_at', 'klaviyo_campaigns', ['sent_at'])


def downgrade() -> None:
    op.drop_table('klaviyo_campaigns')
    op.drop_table('shopify_refunds')
