"""Merge permission refactor with existing head

Revision ID: merge_permission_refactor_2025
Revises: permission_model_refactor_2025, 3914e013be7d
Create Date: 2024-12-23 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_permission_refactor_2025'
down_revision = ('permission_model_refactor_2025', '3914e013be7d')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No changes needed for merge
    pass


def downgrade() -> None:
    # No changes needed for merge
    pass