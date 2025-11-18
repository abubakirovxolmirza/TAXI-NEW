"""add order confirmation fields

Revision ID: add_order_confirmation
Revises: add_system_settings
Create Date: 2024-11-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_order_confirmation'
down_revision = 'add_system_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Add confirmed_at and is_confirmed columns to taxi_orders table
    op.add_column('taxi_orders', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('taxi_orders', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add confirmed_at and is_confirmed columns to delivery_orders table
    op.add_column('delivery_orders', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('delivery_orders', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Remove confirmed_at and is_confirmed columns from delivery_orders table
    op.drop_column('delivery_orders', 'is_confirmed')
    op.drop_column('delivery_orders', 'confirmed_at')
    
    # Remove confirmed_at and is_confirmed columns from taxi_orders table
    op.drop_column('taxi_orders', 'is_confirmed')
    op.drop_column('taxi_orders', 'confirmed_at')
