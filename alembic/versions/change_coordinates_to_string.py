"""change coordinates to string

Revision ID: change_coordinates_to_string
Revises: add_system_settings
Create Date: 2025-11-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'change_coordinates_to_string'
down_revision = 'add_system_settings'
branch_label = None
depends_on = None


def upgrade():
    # Taxi Orders - Change latitude/longitude from Numeric to String
    op.alter_column('taxi_orders', 'pickup_latitude',
                    existing_type=sa.Numeric(precision=10, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='pickup_latitude::text')
    
    op.alter_column('taxi_orders', 'pickup_longitude',
                    existing_type=sa.Numeric(precision=11, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='pickup_longitude::text')
    
    # Delivery Orders - Change latitude/longitude from Numeric to String
    op.alter_column('delivery_orders', 'pickup_latitude',
                    existing_type=sa.Numeric(precision=10, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='pickup_latitude::text')
    
    op.alter_column('delivery_orders', 'pickup_longitude',
                    existing_type=sa.Numeric(precision=11, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='pickup_longitude::text')
    
    op.alter_column('delivery_orders', 'dropoff_latitude',
                    existing_type=sa.Numeric(precision=10, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='dropoff_latitude::text')
    
    op.alter_column('delivery_orders', 'dropoff_longitude',
                    existing_type=sa.Numeric(precision=11, scale=8),
                    type_=sa.String(length=50),
                    existing_nullable=True,
                    postgresql_using='dropoff_longitude::text')


def downgrade():
    # Revert to Numeric type
    op.alter_column('delivery_orders', 'dropoff_longitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=11, scale=8),
                    existing_nullable=True,
                    postgresql_using='dropoff_longitude::numeric')
    
    op.alter_column('delivery_orders', 'dropoff_latitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=10, scale=8),
                    existing_nullable=True,
                    postgresql_using='dropoff_latitude::numeric')
    
    op.alter_column('delivery_orders', 'pickup_longitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=11, scale=8),
                    existing_nullable=True,
                    postgresql_using='pickup_longitude::numeric')
    
    op.alter_column('delivery_orders', 'pickup_latitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=10, scale=8),
                    existing_nullable=True,
                    postgresql_using='pickup_latitude::numeric')
    
    op.alter_column('taxi_orders', 'pickup_longitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=11, scale=8),
                    existing_nullable=True,
                    postgresql_using='pickup_longitude::numeric')
    
    op.alter_column('taxi_orders', 'pickup_latitude',
                    existing_type=sa.String(length=50),
                    type_=sa.Numeric(precision=10, scale=8),
                    existing_nullable=True,
                    postgresql_using='pickup_latitude::numeric')
