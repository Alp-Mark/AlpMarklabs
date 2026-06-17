"""inventory_risk_thresholds

Revision ID: 20260525_0027
Revises: 20260525_0026
Create Date: 2026-05-25

Creates inventory_risk_thresholds table for FR-060/FR-061/FR-062
configurable alert thresholds per tenant × category.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0027"
down_revision = "20260525_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_risk_thresholds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column(
            "stockout_alert_days",
            sa.Float(),
            nullable=False,
            server_default="7.0",
        ),
        sa.Column(
            "overstock_weeks_threshold",
            sa.Float(),
            nullable=False,
            server_default="12.0",
        ),
        sa.Column(
            "slow_moving_min_qty",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "slow_moving_min_weeks_cover",
            sa.Float(),
            nullable=False,
            server_default="4.0",
        ),
        sa.Column(
            "slow_moving_min_capital",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "category",
            name="uq_inventory_risk_threshold_per_tenant_category",
        ),
    )


def downgrade() -> None:
    op.drop_table("inventory_risk_thresholds")
