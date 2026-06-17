"""FR-044 / T-071: Custom segments defined by Retention Manager.

Revision ID: 20260610_0046
Revises: 20260610_0045
Create Date: 2026-06-10 10:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260610_0046"
down_revision = "20260610_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom_segments table
    op.create_table(
        "custom_segments",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("definition", postgresql.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_user_id", postgresql.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_custom_segment_per_tenant_name"),
    )
    # Index on tenant_id for fast lookup
    op.create_index(
        "ix_custom_segments_tenant_id",
        "custom_segments",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_custom_segments_tenant_id")
    op.drop_table("custom_segments")
