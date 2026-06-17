"""FR-125 / T-079: Create immutable alert event log table for audit trail.

Tracks all alert-related events: creation, acknowledgement, dismissal, and
escalation rule changes. Every event is append-only with actor identity and
timestamp.

Revision ID: 20260612_0049
Revises: 20260612_0048
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260612_0049"
down_revision = "20260612_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_event_log table
    op.create_table(
        "alert_event_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.String(255), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for efficient querying
    op.create_index(
        "ix_alert_event_log_tenant_id",
        "alert_event_log",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_alert_event_log_alert_id",
        "alert_event_log",
        ["alert_id"],
        unique=False,
    )
    op.create_index(
        "ix_alert_event_log_created_at",
        "alert_event_log",
        ["created_at"],
        unique=False,
    )
    # Composite index for fast tenant + alert_id lookups (alert history)
    op.create_index(
        "ix_alert_event_log_tenant_alert",
        "alert_event_log",
        ["tenant_id", "alert_id"],
        unique=False,
    )
    # Composite index for tenant + created_at (audit compliance queries)
    op.create_index(
        "ix_alert_event_log_tenant_created",
        "alert_event_log",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indices
    op.drop_index(
        "ix_alert_event_log_tenant_created",
        table_name="alert_event_log",
    )
    op.drop_index(
        "ix_alert_event_log_tenant_alert",
        table_name="alert_event_log",
    )
    op.drop_index(
        "ix_alert_event_log_created_at",
        table_name="alert_event_log",
    )
    op.drop_index(
        "ix_alert_event_log_alert_id",
        table_name="alert_event_log",
    )
    op.drop_index(
        "ix_alert_event_log_tenant_id",
        table_name="alert_event_log",
    )
    # Drop table
    op.drop_table("alert_event_log")
