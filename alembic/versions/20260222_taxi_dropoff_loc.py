"""add dropoff location fields to taxi orders

Revision ID: 20260222_taxi_dropoff_loc
Revises: 20260221_add_driver_is_worked
Create Date: 2026-02-22 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260222_taxi_dropoff_loc"
down_revision = "20260221_add_driver_is_worked"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("taxi_orders", sa.Column("dropoff_latitude", sa.String(length=50), nullable=True))
    op.add_column("taxi_orders", sa.Column("dropoff_longitude", sa.String(length=50), nullable=True))
    op.add_column("taxi_orders", sa.Column("dropoff_address", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("taxi_orders", "dropoff_address")
    op.drop_column("taxi_orders", "dropoff_longitude")
    op.drop_column("taxi_orders", "dropoff_latitude")
