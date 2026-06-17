"""inventory_risk_snapshots

Revision ID: 20260525_0028
Revises: 20260525_0027
Create Date: 2026-05-25

Creates inventory_risk_snapshots table for FR-058 to FR-062 daily
inventory risk computation per SKU.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0028"
down_revision = "20260525_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_risk_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("product_title", sa.String(length=255), nullable=False),
        sa.Column("variant_title", sa.String(length=255), nullable=True),
        sa.Column(
            "current_quantity", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("reorder_point", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "daily_velocity_30d", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("days_to_stockout", sa.Float(), nullable=True),
        sa.Column(
            "weekly_velocity_90d", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("weeks_of_cover", sa.Float(), nullable=True),
        sa.Column("days_since_last_sale", sa.Integer(), nullable=True),
        sa.Column("capital_at_risk", sa.Float(), nullable=True),
        sa.Column(
            "seasonal_adjustment_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("confidence", sa.String(length=10), nullable=False),
        sa.Column("data_completeness", sa.String(length=50), nullable=False),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "sku",
            "snapshot_date",
            name="uq_inventory_risk_per_tenant_sku_date",
        ),
    )
    op.create_index(
        "ix_inventory_risk_snapshots_tenant_date",
        "inventory_risk_snapshots",
        ["tenant_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_risk_snapshots_tenant_date",
        table_name="inventory_risk_snapshots",
    )
    op.drop_table("inventory_risk_snapshots")
