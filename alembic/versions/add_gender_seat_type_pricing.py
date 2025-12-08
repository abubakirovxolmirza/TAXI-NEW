"""add gender to users, client_gender to taxi_orders, seat_type to taxi_orders, and seat pricing to pricing

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
    # Create gender enum type
    gender_enum = sa.Enum('male', 'female', 'other', name='gender', create_type=True)
    gender_enum.create(op.get_bind())
    
    # Create seattype enum type
    seattype_enum = sa.Enum('front', 'back', name='seattype', create_type=True)
    seattype_enum.create(op.get_bind())
    
    # Add gender column to users table
    op.add_column('users', sa.Column('gender', gender_enum, nullable=True))
    
    # Add client_gender and seat_type columns to taxi_orders table
    op.add_column('taxi_orders', sa.Column('client_gender', gender_enum, nullable=True))
    op.add_column('taxi_orders', sa.Column('seat_type', seattype_enum, nullable=True))
    
    # Add front_seat_price and back_seat_price columns to pricing table
    op.add_column('pricing', sa.Column('front_seat_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('pricing', sa.Column('back_seat_price', sa.Numeric(10, 2), nullable=True))


def downgrade():
    # Remove back_seat_price and front_seat_price columns from pricing table
    op.drop_column('pricing', 'back_seat_price')
    op.drop_column('pricing', 'front_seat_price')
    
    # Remove client_gender and seat_type columns from taxi_orders table
    op.drop_column('taxi_orders', 'seat_type')
    op.drop_column('taxi_orders', 'client_gender')
    
    # Remove gender column from users table
    op.drop_column('users', 'gender')
    
    # Drop enum types
    sa.Enum('front', 'back', name='seattype').drop(op.get_bind())
    sa.Enum('male', 'female', 'other', name='gender').drop(op.get_bind())
