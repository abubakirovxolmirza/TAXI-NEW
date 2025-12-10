"""merge gender and seat type branches

Revision ID: merge_gender_branches
Revises: ('add_gender_seat_type_pricing', 'add_order_confirmation')
Create Date: 2025-01-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'merge_gender_branches'
down_revision = ('add_gender_seat_type_pricing', 'add_order_confirmation')
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def enum_exists(enum_name):
    """Check if an enum type exists"""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name)"
    ), {"enum_name": enum_name})
    return result.scalar()


def upgrade():
    # This merge migration ensures both branches are applied
    # If coming from add_gender_seat_type_pricing branch, columns might already exist
    # If coming from add_order_confirmation branch, we need to add them
    
    # Check and create gender enum if it doesn't exist
    if not enum_exists('gender'):
        gender_enum = sa.Enum('male', 'female', 'other', name='gender', create_type=True)
        gender_enum.create(op.get_bind())
    
    # Check and create seattype enum if it doesn't exist
    if not enum_exists('seattype'):
        seattype_enum = sa.Enum('front', 'back', name='seattype', create_type=True)
        seattype_enum.create(op.get_bind())
    
    # Add client_gender column if it doesn't exist
    if not column_exists('taxi_orders', 'client_gender'):
        op.add_column('taxi_orders', sa.Column('client_gender', sa.Enum('male', 'female', 'other', name='gender'), nullable=True))
    
    # Add seat_type column if it doesn't exist
    if not column_exists('taxi_orders', 'seat_type'):
        op.add_column('taxi_orders', sa.Column('seat_type', sa.Enum('front', 'back', name='seattype'), nullable=True))
    
    # Ensure front_seat_price and back_seat_price exist in pricing table
    if not column_exists('pricing', 'front_seat_price'):
        op.add_column('pricing', sa.Column('front_seat_price', sa.Numeric(10, 2), nullable=True))
    
    if not column_exists('pricing', 'back_seat_price'):
        op.add_column('pricing', sa.Column('back_seat_price', sa.Numeric(10, 2), nullable=True))


def downgrade():
    # Note: This is a merge point, downgrade would need to handle both branches
    # For safety, we'll leave the columns in place
    pass

