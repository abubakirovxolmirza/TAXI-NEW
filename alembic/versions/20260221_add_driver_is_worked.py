"""add is_worked flag to drivers

Revision ID: 20260221_add_driver_is_worked
Revises: 20260220_normalize_start_tariff
Create Date: 2026-02-21 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260221_add_driver_is_worked"
down_revision = "20260220_normalize_start_tariff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "drivers",
        sa.Column("is_worked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("drivers", "is_worked")
