"""Create alert_thresholds and alert_recipients tables (T-072).

Revision ID: 20260611_0047
Revises: 20260610_0046
Create Date: 2026-06-11 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260611_0047"
down_revision = "20260610_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_thresholds table
    op.create_table(
        "alert_thresholds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("comparison_operator", sa.String(10), nullable=False, server_default="<"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
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
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_alert_thresholds_user"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_alert_thresholds_tenant"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "alert_type",
            "metric_name",
            name="uq_alert_threshold_per_tenant_type_metric",
        ),
    )
    op.create_index(
        "ix_alert_thresholds_tenant_id",
        "alert_thresholds",
        ["tenant_id"],
        unique=False,
    )

    # Create alert_recipients table
    op.create_table(
        "alert_recipients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_alert_recipients_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_alert_recipients_user"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "channel",
            name="uq_alert_recipient_per_user_channel",
        ),
    )
    op.create_index(
        "ix_alert_recipients_tenant_id",
        "alert_recipients",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_alert_recipients_user_id",
        "alert_recipients",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alert_recipients_user_id", table_name="alert_recipients")
    op.drop_index("ix_alert_recipients_tenant_id", table_name="alert_recipients")
    op.drop_table("alert_recipients")

    op.drop_index("ix_alert_thresholds_tenant_id", table_name="alert_thresholds")
    op.drop_table("alert_thresholds")
