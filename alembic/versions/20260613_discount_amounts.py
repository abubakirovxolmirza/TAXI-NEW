"""Change passenger discounts to fixed amounts

Revision ID: 20260613_discount_amounts
Revises: 20260413_add_driver_region
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260613_discount_amounts"
down_revision = "20260413_add_driver_region"
branch_labels = None
depends_on = None


DISCOUNT_COLUMNS = (
    "discount_1_passenger",
    "discount_2_passengers",
    "discount_3_passengers",
    "discount_full_car",
)


def upgrade():
    for table_name in ("pricing", "district_pricing"):
        for column_name in DISCOUNT_COLUMNS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.Numeric(precision=5, scale=2),
                type_=sa.Numeric(precision=10, scale=2),
                existing_nullable=True,
            )


def downgrade():
    for table_name in ("pricing", "district_pricing"):
        for column_name in DISCOUNT_COLUMNS:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.Numeric(precision=10, scale=2),
                type_=sa.Numeric(precision=5, scale=2),
                existing_nullable=True,
            )
