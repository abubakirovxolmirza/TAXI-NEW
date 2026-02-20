"""normalize legacy start tariff values to standard

Revision ID: 20260220_normalize_start_tariff
Revises: 20260220_add_taxi_is_new
Create Date: 2026-02-20 13:10:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260220_normalize_start_tariff"
down_revision = "20260220_add_taxi_is_new"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize any legacy "start" tariff values to "standard".
    op.execute("UPDATE drivers SET tariff = 'standard' WHERE tariff::text = 'start'")
    op.execute("UPDATE taxi_orders SET tariff = 'standard' WHERE tariff::text = 'start'")
    op.execute("UPDATE pricing SET tariff = 'standard' WHERE tariff::text = 'start'")
    op.execute("UPDATE district_pricing SET tariff = 'standard' WHERE tariff::text = 'start'")


def downgrade() -> None:
    # Irreversible data normalization.
    pass
