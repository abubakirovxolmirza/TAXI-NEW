"""add is_new flag to taxi orders

Revision ID: 20260220_add_taxi_is_new
Revises: m20260217_legacy_heads
Create Date: 2026-02-20 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260220_add_taxi_is_new"
down_revision = "m20260217_legacy_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "taxi_orders",
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("taxi_orders", "is_new")
