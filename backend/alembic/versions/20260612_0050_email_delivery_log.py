"""FR-116 / T-079: Create immutable email delivery log table for notification tracking.

Revision ID: 20260612_0050
Revises: 20260612_0049
Create Date: 2026-06-12 19:15:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260612_0050"
down_revision = "20260612_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.String(255), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_email_delivery_log_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_email_delivery_log_user_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_delivery_log"),
    )
    # Index for querying delivery status by tenant
    op.create_index(
        "ix_email_delivery_log_tenant_id",
        "email_delivery_log",
        ["tenant_id"],
        unique=False,
    )
    # Index for user-level delivery history
    op.create_index(
        "ix_email_delivery_log_user_id",
        "email_delivery_log",
        ["user_id"],
        unique=False,
    )
    # Index for alert-specific delivery tracking
    op.create_index(
        "ix_email_delivery_log_alert_id",
        "email_delivery_log",
        ["alert_id"],
        unique=False,
    )
    # Index for delivery status filtering by created date
    op.create_index(
        "ix_email_delivery_log_created_at",
        "email_delivery_log",
        ["created_at"],
        unique=False,
    )
    # Composite index for tenant + status queries (e.g., all failed/pending emails for a tenant)
    op.create_index(
        "ix_email_delivery_log_tenant_status",
        "email_delivery_log",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_delivery_log_tenant_status",
        table_name="email_delivery_log",
    )
    op.drop_index(
        "ix_email_delivery_log_created_at",
        table_name="email_delivery_log",
    )
    op.drop_index(
        "ix_email_delivery_log_alert_id",
        table_name="email_delivery_log",
    )
    op.drop_index(
        "ix_email_delivery_log_user_id",
        table_name="email_delivery_log",
    )
    op.drop_index(
        "ix_email_delivery_log_tenant_id",
        table_name="email_delivery_log",
    )
    op.drop_table("email_delivery_log")
