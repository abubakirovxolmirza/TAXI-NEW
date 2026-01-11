"""add both to gender enum

Revision ID: add_both_gender_2025
Revises: add_new_features_2025
Create Date: 2025-12-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_both_gender_2025'
down_revision = 'add_new_features_2025'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'both' value to Gender enum
    op.execute("ALTER TYPE gender ADD VALUE IF NOT EXISTS 'both'")


def downgrade():
    # PostgreSQL doesn't support removing enum values directly
    # Would require recreating the enum type if rollback is needed
    pass
