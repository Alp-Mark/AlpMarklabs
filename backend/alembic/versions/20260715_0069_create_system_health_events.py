"""Create system_health_events table for failure tracking.

Revision ID: 20260715_0069
Revises: 20260715_0068
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260715_0069"
down_revision = "20260715_0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for event_type
    event_type_enum = sa.Enum(
        "sync_failure",
        "api_error",
        "data_anomaly",
        "connection_lost",
        "rate_limit_exceeded",
        name="system_health_event_type",
        create_type=True,
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # Create ENUM type for severity (reuse same values as audit_events)
    severity_enum = sa.Enum(
        "critical",
        "important",
        "info",
        "debug",
        name="system_health_severity",
        create_type=True,
    )
    severity_enum.create(op.get_bind(), checkfirst=True)

    # Create system_health_events table
    op.create_table(
        "system_health_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "sync_failure",
                "api_error",
                "data_anomaly",
                "connection_lost",
                "rate_limit_exceeded",
                name="system_health_event_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "critical", "important", "info", "debug", name="system_health_severity"
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_system_health_tenant_resolved_created",
        "system_health_events",
        ["tenant_id", "resolved_at", "created_at"],
    )
    op.create_index(
        "ix_system_health_tenant_service",
        "system_health_events",
        ["tenant_id", "service_name"],
    )
    op.create_index(
        "ix_system_health_severity",
        "system_health_events",
        ["severity", "resolved_at"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_system_health_severity", table_name="system_health_events")
    op.drop_index("ix_system_health_tenant_service", table_name="system_health_events")
    op.drop_index(
        "ix_system_health_tenant_resolved_created", table_name="system_health_events"
    )

    # Drop table
    op.drop_table("system_health_events")

    # Drop ENUM types
    sa.Enum(name="system_health_severity").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="system_health_event_type").drop(op.get_bind(), checkfirst=True)
