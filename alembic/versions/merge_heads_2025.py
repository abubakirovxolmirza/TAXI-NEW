"""Merge multiple heads

Revision ID: merge_heads_2025
Revises: 79e33bf1283d, add_district_pricing
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_2025'
down_revision = ('79e33bf1283d', 'add_district_pricing')
branch_labels = None
depends_on = None


def upgrade():
    # No changes needed, just merging branches
    pass


def downgrade():
    # No changes needed, just merging branches
    pass
