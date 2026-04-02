"""add block reason to drivers

Revision ID: 20260402_driver_block_reason
Revises: 20260302_add_rejection_reason
Create Date: 2026-04-02 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260402_driver_block_reason"
down_revision = "20260302_add_rejection_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("drivers")}
    if "block_reason" not in columns:
        op.add_column("drivers", sa.Column("block_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("drivers")}
    if "block_reason" in columns:
        op.drop_column("drivers", "block_reason")
