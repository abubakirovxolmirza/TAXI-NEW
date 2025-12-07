"""add gender to users, seat_type to taxi_orders, and seat pricing to pricing

Revision ID: add_gender_seat_type_pricing
Revises: add_system_settings
Create Date: 2025-12-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_gender_seat_type_pricing'
down_revision = 'add_system_settings'
branch_labels = None
depends_on = None


def upgrade():
    # Add gender column to users table
    op.add_column('users', sa.Column('gender', sa.Enum('male', 'female', 'other', name='gender'), nullable=True))
    
    # Add seat_type column to taxi_orders table
    op.add_column('taxi_orders', sa.Column('seat_type', sa.Enum('front', 'back', name='seattype'), nullable=True))
    
    # Add front_seat_price and back_seat_price columns to pricing table
    op.add_column('pricing', sa.Column('front_seat_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('pricing', sa.Column('back_seat_price', sa.Numeric(10, 2), nullable=True))


def downgrade():
    # Remove back_seat_price and front_seat_price columns from pricing table
    op.drop_column('pricing', 'back_seat_price')
    op.drop_column('pricing', 'front_seat_price')
    
    # Remove seat_type column from taxi_orders table
    op.drop_column('taxi_orders', 'seat_type')
    
    # Remove gender column from users table
    op.drop_column('users', 'gender')
