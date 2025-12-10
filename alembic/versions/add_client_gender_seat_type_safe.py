"""add client_gender and seat_type to taxi_orders safely

Revision ID: add_client_gender_seat_type_safe
Revises: add_order_confirmation
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_client_gender_seat_type_safe'
down_revision = 'add_order_confirmation'
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


def downgrade():
    # Remove columns if they exist
    if column_exists('taxi_orders', 'seat_type'):
        op.drop_column('taxi_orders', 'seat_type')
    
    if column_exists('taxi_orders', 'client_gender'):
        op.drop_column('taxi_orders', 'client_gender')
    
    # Note: We don't drop the enum types here as they might be used elsewhere
    # If you need to drop them, uncomment the following lines:
    # if enum_exists('seattype'):
    #     op.execute("DROP TYPE IF EXISTS seattype")
    # if enum_exists('gender'):
    #     op.execute("DROP TYPE IF EXISTS gender")

