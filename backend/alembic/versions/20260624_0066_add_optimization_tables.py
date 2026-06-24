"""Add optimization engine tables and source column to recommendations

Revision ID: 20260624_0066
Revises: 20260623_0061
Create Date: 2026-06-24
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260624_0066'
down_revision = '20260623_0061'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add 'source' column to existing recommendations table
    op.add_column(
        "recommendations",
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default="threshold",
        ),
    )
    
    # 2. Create optimization_strategies table
    op.create_table(
        "optimization_strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(30), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "domain", "strategy_name",
            name="uq_strategy_per_tenant_domain"
        ),
    )
    op.create_index(
        "ix_optimization_strategies_tenant_id",
        "optimization_strategies",
        ["tenant_id"],
        unique=False,
    )
    
    # 3. Create optimization_runs table
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), nullable=False),
        sa.Column("run_status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_snapshot_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("optimization_result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["strategy_id"], ["optimization_strategies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_optimization_runs_tenant_id",
        "optimization_runs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_runs_strategy_id",
        "optimization_runs",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_runs_run_status",
        "optimization_runs",
        ["run_status"],
        unique=False,
    )
    
    # 4. Create fitted_models table
    op.create_table(
        "fitted_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_run_id", sa.Uuid(), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("model_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("accuracy_metrics", sa.JSON(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["strategy_id"], ["optimization_strategies.id"]),
        sa.ForeignKeyConstraint(["optimization_run_id"], ["optimization_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fitted_models_tenant_id",
        "fitted_models",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_fitted_models_strategy_id",
        "fitted_models",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        "ix_fitted_models_s3_key",
        "fitted_models",
        ["s3_key"],
        unique=True,
    )
    
    # 5. Create optimization_recommendations table
    op.create_table(
        "optimization_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_run_id", sa.Uuid(), nullable=False),
        sa.Column("fitted_model_id", sa.Uuid(), nullable=True),
        sa.Column("optimization_insight", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("alternative_scenarios", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"]),
        sa.ForeignKeyConstraint(["optimization_run_id"], ["optimization_runs.id"]),
        sa.ForeignKeyConstraint(["fitted_model_id"], ["fitted_models.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recommendation_id",
            name="uq_one_optimization_per_recommendation"
        ),
    )
    op.create_index(
        "ix_optimization_recommendations_recommendation_id",
        "optimization_recommendations",
        ["recommendation_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_recommendations_optimization_run_id",
        "optimization_recommendations",
        ["optimization_run_id"],
        unique=False,
    )
    
    # 6. Create optimization_experiments table
    op.create_table(
        "optimization_experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_name", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(30), nullable=False),
        sa.Column("experiment_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("control_group_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("treatment_group_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("control_metrics", sa.JSON(), nullable=True),
        sa.Column("treatment_metrics", sa.JSON(), nullable=True),
        sa.Column("conclusion", sa.String(500), nullable=True),
        sa.Column("winner", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_optimization_experiments_tenant_id",
        "optimization_experiments",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_experiments_domain",
        "optimization_experiments",
        ["domain"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("optimization_experiments")
    op.drop_table("optimization_recommendations")
    op.drop_table("fitted_models")
    op.drop_table("optimization_runs")
    op.drop_table("optimization_strategies")
    
    # Drop source column from recommendations
    op.drop_column("recommendations", "source")
