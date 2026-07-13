"""create_marketing_channel_spends_table

Revision ID: dfea8b94212e
Revises: ad8caf696011
Create Date: 2026-07-08 18:20:16.874537

This migration was removed and replaced with the Steps 4-10 multi-channel allocator.
Stub migration kept to maintain alembic history chain.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = 'dfea8b94212e'
down_revision = 'ad8caf696011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op upgrade. This migration was removed during refactoring."""
    pass


def downgrade() -> None:
    """No-op downgrade. This migration was removed during refactoring."""
    pass
