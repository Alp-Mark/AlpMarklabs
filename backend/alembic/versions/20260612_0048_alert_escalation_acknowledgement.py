"""Create alert acknowledgement, dismissal, and escalation rule tables.

T-078: Alert Escalation & Acknowledgement tracking.

Revision ID: 20260612_0048
Revises: 20260611_0047
Create Date: 2026-06-12 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260612_0048"
down_revision = "20260611_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create alert acknowledgement, dismissal, and escalation rule tables."""
    # AlertAcknowledgement table
    op.create_table(
        "alert_acknowledgements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "alert_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "alert_id",
            name="uq_alert_ack_per_tenant_user_alert",
        ),
    )

    # AlertDismissal table
    op.create_table(
        "alert_dismissals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "alert_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "dismiss_reason",
            sa.String(500),
            nullable=True,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "alert_id",
            name="uq_alert_dismiss_per_tenant_user_alert",
        ),
    )

    # EscalationRule table
    op.create_table(
        "escalation_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "alert_type",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "domain",
            sa.String(100),
            nullable=False,
        ),
        sa.Column(
            "unacknowledged_hours",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "escalation_to_roles",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "alert_type",
            "domain",
            name="uq_escalation_rule_per_tenant_type_domain",
        ),
    )

    # Create indices for common queries
    op.create_index(
        "ix_alert_ack_tenant_alert",
        "alert_acknowledgements",
        ["tenant_id", "alert_id"],
    )
    op.create_index(
        "ix_alert_ack_tenant_user",
        "alert_acknowledgements",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_alert_dismiss_tenant_alert",
        "alert_dismissals",
        ["tenant_id", "alert_id"],
    )
    op.create_index(
        "ix_alert_dismiss_tenant_user",
        "alert_dismissals",
        ["tenant_id", "user_id"],
    )
    op.create_index(
        "ix_escalation_rule_tenant_type",
        "escalation_rules",
        ["tenant_id", "alert_type"],
    )


def downgrade() -> None:
    """Drop alert acknowledgement, dismissal, and escalation rule tables."""
    op.drop_index("ix_escalation_rule_tenant_type", "escalation_rules")
    op.drop_index("ix_alert_dismiss_tenant_user", "alert_dismissals")
    op.drop_index("ix_alert_dismiss_tenant_alert", "alert_dismissals")
    op.drop_index("ix_alert_ack_tenant_user", "alert_acknowledgements")
    op.drop_index("ix_alert_ack_tenant_alert", "alert_acknowledgements")

    op.drop_table("escalation_rules")
    op.drop_table("alert_dismissals")
    op.drop_table("alert_acknowledgements")
