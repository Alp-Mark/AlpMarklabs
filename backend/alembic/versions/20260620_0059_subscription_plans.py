"""subscription_plans

Revision ID: 20260620_0059
Revises: 20260620_0058
Create Date: 2026-06-20
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260620_0059"
down_revision = "20260620_0058"
branch_label = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("price_monthly", sa.Float(), nullable=False),
        sa.Column("price_annual", sa.Float(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # Seed standard plans
    op.execute(
        """
        INSERT INTO subscription_plans (id, slug, name, description, price_monthly, price_annual, features, limits, is_active, sort_order)
        VALUES
        (
            gen_random_uuid(),
            'starter',
            'Starter',
            'Perfect for small teams getting started with data-driven decisions',
            49.00,
            490.00,
            '["dashboards", "basic_recommendations", "email_alerts"]'::jsonb,
            '{"seat_limit": 5, "connector_limit": 3, "recommendation_limit": 50}'::jsonb,
            true,
            1
        ),
        (
            gen_random_uuid(),
            'professional',
            'Professional',
            'Advanced analytics and simulations for growing D2C brands',
            149.00,
            1490.00,
            '["dashboards", "basic_recommendations", "advanced_recommendations", "simulations", "email_alerts", "slack_alerts", "custom_segments"]'::jsonb,
            '{"seat_limit": 15, "connector_limit": 10, "recommendation_limit": 200}'::jsonb,
            true,
            2
        ),
        (
            gen_random_uuid(),
            'enterprise',
            'Enterprise',
            'Full platform access with dedicated support and custom integrations',
            499.00,
            4990.00,
            '["dashboards", "basic_recommendations", "advanced_recommendations", "simulations", "email_alerts", "slack_alerts", "custom_segments", "api_access", "white_label", "custom_integrations", "sso"]'::jsonb,
            '{"seat_limit": 50, "connector_limit": 999, "recommendation_limit": 999}'::jsonb,
            true,
            3
        )
        """
    )


def downgrade() -> None:
    op.drop_table("subscription_plans")
