"""Add severity, category, and persona filtering to audit_events.

Revision ID: 20260715_0068
Revises: 20260713_0067
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260715_0068"
down_revision = "20260713_0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for severity
    severity_enum = sa.Enum(
        "critical",
        "important",
        "info",
        "debug",
        name="audit_event_severity",
        create_type=True,
    )
    severity_enum.create(op.get_bind(), checkfirst=True)

    # Add severity column (defaults to 'info' for existing records)
    op.add_column(
        "audit_events",
        sa.Column(
            "severity",
            sa.Enum(
                "critical", "important", "info", "debug", name="audit_event_severity"
            ),
            nullable=False,
            server_default="info",
        ),
    )

    # Add category column (defaults to 'system' for existing records)
    op.add_column(
        "audit_events",
        sa.Column(
            "category",
            sa.String(length=50),
            nullable=False,
            server_default="system",
        ),
    )

    # Add is_system_generated flag (defaults to false for existing records)
    op.add_column(
        "audit_events",
        sa.Column(
            "is_system_generated",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Add visible_to_personas array (NULL = visible to all)
    op.add_column(
        "audit_events",
        sa.Column(
            "visible_to_personas",
            sa.JSON(),
            nullable=True,
        ),
    )

    # Backfill existing sync events to debug severity and data_sync category
    op.execute("""
        UPDATE audit_events
        SET 
            severity = 'debug',
            category = 'data_sync',
            is_system_generated = true,
            visible_to_personas = '["brand_admin", "super_admin"]'::json
        WHERE action IN (
            'connector.shopify_orders_synced',
            'connector.shopify_inventory_synced'
        )
    """)

    # Backfill user action events to important severity
    op.execute("""
        UPDATE audit_events
        SET 
            severity = 'important',
            category = 'user_action'
        WHERE action IN (
            'user.invited',
            'account.activated',
            'member.role_updated',
            'member.deactivated'
        )
    """)

    # Backfill tenant events to important severity
    op.execute("""
        UPDATE audit_events
        SET 
            severity = 'important',
            category = 'tenant_management'
        WHERE action IN (
            'tenant.created',
            'tenant.updated'
        )
    """)

    # Create indexes for efficient querying
    op.create_index(
        "ix_audit_events_tenant_severity_created",
        "audit_events",
        ["tenant_id", "severity", "created_at"],
    )
    op.create_index(
        "ix_audit_events_tenant_category_created",
        "audit_events",
        ["tenant_id", "category", "created_at"],
    )
    op.create_index(
        "ix_audit_events_system_generated",
        "audit_events",
        ["tenant_id", "is_system_generated", "created_at"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_audit_events_system_generated", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_category_created", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_severity_created", table_name="audit_events")

    # Drop columns
    op.drop_column("audit_events", "visible_to_personas")
    op.drop_column("audit_events", "is_system_generated")
    op.drop_column("audit_events", "category")
    op.drop_column("audit_events", "severity")

    # Drop ENUM type
    sa.Enum(name="audit_event_severity").drop(op.get_bind(), checkfirst=True)
