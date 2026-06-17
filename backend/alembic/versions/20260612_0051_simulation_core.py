"""Create simulations and scenarios tables for T-081.

Revision ID: 20260612_0051
Revises: 20260612_0050
Create Date: 2026-06-12 00:00:00.000000

FR-081, FR-087 / T-081: Simulation core with baseline/upside/downside scenarios.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260612_0051"
down_revision = "20260612_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create simulations table
    op.create_table(
        "simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=True),
        sa.Column("domain", sa.String(30), nullable=False),
        sa.Column("simulation_type", sa.String(20), nullable=False, server_default="auto"),
        sa.Column("x_star", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence_level", sa.String(10), nullable=False),
        sa.Column("data_freshness_signal", sa.String(20), nullable=False, server_default="high"),
        sa.Column("metric_completeness_signal", sa.String(20), nullable=False, server_default="high"),
        sa.Column("baseline_scenario", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("upside_scenario", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("downside_scenario", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("simulation_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_simulations_recommendation_id"), "simulations", ["recommendation_id"], unique=False)
    op.create_index(op.f("ix_simulations_tenant_id"), "simulations", ["tenant_id"], unique=False)

    # Create scenarios table
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("simulation_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_type", sa.String(20), nullable=False),
        sa.Column("input_assumptions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("impact_deltas", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("rationale", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_id", "scenario_type", name="uq_scenario_per_simulation_type"),
    )
    op.create_index(op.f("ix_scenarios_simulation_id"), "scenarios", ["simulation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scenarios_simulation_id"), table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index(op.f("ix_simulations_recommendation_id"), table_name="simulations")
    op.drop_index(op.f("ix_simulations_tenant_id"), table_name="simulations")
    op.drop_table("simulations")
