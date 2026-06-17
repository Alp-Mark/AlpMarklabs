"""operational_impact_snapshots

Revision ID: 20260525_0030
Revises: 20260525_0029
Create Date: 2026-05-25

Creates operational_impact_snapshots table — daily per-SKU computation
covering FR-064 (stockout lost revenue + repeat-purchase risk),
FR-065 (logistics cost burden), and FR-066 (operational return analytics).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260525_0030"
down_revision = "20260525_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_impact_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("product_title", sa.String(length=255), nullable=False),
        sa.Column("variant_title", sa.String(length=255), nullable=True),
        # FR-064
        sa.Column("inventory_status", sa.String(length=20), nullable=False),
        sa.Column(
            "daily_velocity_30d",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "avg_unit_price", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "days_to_restock_estimate",
            sa.Float(),
            nullable=False,
            server_default="7",
        ),
        sa.Column("stockout_lost_revenue_estimate", sa.Float(), nullable=True),
        sa.Column(
            "repeat_purchase_risk",
            sa.String(length=10),
            nullable=False,
            server_default="none",
        ),
        # FR-065
        sa.Column("logistics_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("logistics_cost_total_30d", sa.Float(), nullable=True),
        sa.Column("logistics_margin_impact_pct", sa.Float(), nullable=True),
        # FR-066
        sa.Column(
            "units_sold_30d", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "return_quantity_30d", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "return_rate_30d_pct", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("return_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("return_cost_total_30d", sa.Float(), nullable=True),
        # Meta
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
            name="uq_operational_impact_per_tenant_sku_date",
        ),
    )
    op.create_index(
        "ix_operational_impact_snapshots_tenant_date",
        "operational_impact_snapshots",
        ["tenant_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operational_impact_snapshots_tenant_date",
        table_name="operational_impact_snapshots",
    )
    op.drop_table("operational_impact_snapshots")
