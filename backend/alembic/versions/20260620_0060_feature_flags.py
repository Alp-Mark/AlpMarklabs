"""feature_flags

Revision ID: 20260620_0060
Revises: 20260620_0059
Create Date: 2026-06-20
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260620_0060"
down_revision = "20260620_0059"
branch_label = None
depends_on = None


def upgrade() -> None:
    # Create feature_flags table
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("default_enabled", sa.Boolean(), nullable=False),
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

    # Create tenant_feature_flags table
    op.create_table(
        "tenant_feature_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("feature_flag_slug", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["feature_flag_slug"],
            ["feature_flags.slug"],
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "feature_flag_slug", name="uq_tenant_feature_flag"
        ),
    )

    # Create indexes
    op.create_index(
        "ix_tenant_feature_flags_tenant_id",
        "tenant_feature_flags",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_feature_flags_feature_flag_slug",
        "tenant_feature_flags",
        ["feature_flag_slug"],
        unique=False,
    )

    # Seed default feature flags
    op.execute(
        """
        INSERT INTO feature_flags (id, slug, name, description, category, is_available, default_enabled)
        VALUES
        -- Analytics features
        (
            gen_random_uuid(),
            'dashboards',
            'Dashboards',
            'Access to executive, growth, retention, finance, and operations dashboards',
            'analytics',
            true,
            true
        ),
        (
            gen_random_uuid(),
            'basic_recommendations',
            'Basic Recommendations',
            'Automated recommendations for common optimization opportunities',
            'analytics',
            true,
            true
        ),
        (
            gen_random_uuid(),
            'advanced_recommendations',
            'Advanced Recommendations',
            'ML-powered recommendations with confidence scoring and advanced insights',
            'analytics',
            true,
            false
        ),
        (
            gen_random_uuid(),
            'simulations',
            'Simulations',
            'What-if scenario planning and simulation engine',
            'analytics',
            true,
            false
        ),
        (
            gen_random_uuid(),
            'custom_segments',
            'Custom Segments',
            'Create and analyze custom customer segments',
            'analytics',
            true,
            false
        ),
        -- Alert features
        (
            gen_random_uuid(),
            'email_alerts',
            'Email Alerts',
            'Receive alerts via email',
            'notifications',
            true,
            true
        ),
        (
            gen_random_uuid(),
            'slack_alerts',
            'Slack Alerts',
            'Receive alerts in Slack channels',
            'notifications',
            true,
            false
        ),
        -- Integration features
        (
            gen_random_uuid(),
            'api_access',
            'API Access',
            'Programmatic access to AlpMark data and functionality',
            'integrations',
            true,
            false
        ),
        (
            gen_random_uuid(),
            'custom_integrations',
            'Custom Integrations',
            'Build custom integrations with AlpMark platform',
            'integrations',
            true,
            false
        ),
        (
            gen_random_uuid(),
            'sso',
            'Single Sign-On (SSO)',
            'SAML-based single sign-on for enterprise authentication',
            'platform',
            true,
            false
        ),
        (
            gen_random_uuid(),
            'white_label',
            'White Label',
            'Customize AlpMark branding to match your company',
            'platform',
            true,
            false
        )
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_feature_flags_feature_flag_slug", table_name="tenant_feature_flags"
    )
    op.drop_index("ix_tenant_feature_flags_tenant_id", table_name="tenant_feature_flags")
    op.drop_table("tenant_feature_flags")
    op.drop_table("feature_flags")
