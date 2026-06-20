"""E5: Add user_notification_preferences and notifications tables.

Revision ID: 20260620_0065
Revises: 20260620_0064
Create Date: 2026-06-20 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260620_0065"
down_revision = "20260620_0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # E5: User notification preferences (FR-007, FR-108)
    op.create_table(
        "user_notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("alert_category", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="both"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_notification_preferences_user_id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_user_notification_preferences_tenant_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tenant_id", "alert_category", name="uq_user_notification_preference_per_category"),
    )

    # E5: Notification inbox (FR-123, FR-124, FR-125)
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unread"),
        sa.Column("deep_link", sa.String(500), nullable=True),
        sa.Column("context_data", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_notifications_tenant_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notifications_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_status", "notifications", ["user_id", "status"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", "notifications")
    op.drop_index("ix_notifications_user_status", "notifications")
    op.drop_table("notifications")
    op.drop_table("user_notification_preferences")
