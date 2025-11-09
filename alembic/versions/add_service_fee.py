"""add service fee to orders

Revision ID: add_service_fee
Revises: add_scheduled_datetime
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = 'add_service_fee'
down_revision = '6d35d36c72cc'  # Points to the merge revision
branch_labels = None
depends_on = None


def upgrade():
    # Add service_fee and driver_earnings columns to taxi_orders
    op.add_column('taxi_orders', sa.Column('service_fee', sa.Numeric(10, 2), nullable=False, server_default='0.00'))
    op.add_column('taxi_orders', sa.Column('driver_earnings', sa.Numeric(10, 2), nullable=False, server_default='0.00'))
    
    # Add service_fee and driver_earnings columns to delivery_orders
    op.add_column('delivery_orders', sa.Column('service_fee', sa.Numeric(10, 2), nullable=False, server_default='0.00'))
    op.add_column('delivery_orders', sa.Column('driver_earnings', sa.Numeric(10, 2), nullable=False, server_default='0.00'))
    
    # Update existing orders to calculate service fee (8%) and driver earnings
    op.execute("""
        UPDATE taxi_orders 
        SET service_fee = price * 0.08,
            driver_earnings = price * 0.92
        WHERE service_fee = 0.00
    """)
    
    op.execute("""
        UPDATE delivery_orders 
        SET service_fee = price * 0.08,
            driver_earnings = price * 0.92
        WHERE service_fee = 0.00
    """)


def downgrade():
    # Remove service_fee and driver_earnings columns from taxi_orders
    op.drop_column('taxi_orders', 'driver_earnings')
    op.drop_column('taxi_orders', 'service_fee')
    
    # Remove service_fee and driver_earnings columns from delivery_orders
    op.drop_column('delivery_orders', 'driver_earnings')
    op.drop_column('delivery_orders', 'service_fee')
