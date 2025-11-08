"""add scheduled_datetime to orders

Revision ID: add_scheduled_datetime
Revises: 
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_scheduled_datetime'
down_revision = None  # Update this with your latest revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Add scheduled_datetime column to taxi_orders
    op.add_column('taxi_orders', sa.Column('scheduled_datetime', sa.DateTime(timezone=True), nullable=True))
    
    # Add scheduled_datetime column to delivery_orders
    op.add_column('delivery_orders', sa.Column('scheduled_datetime', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove scheduled_datetime column from taxi_orders
    op.drop_column('taxi_orders', 'scheduled_datetime')
    
    # Remove scheduled_datetime column from delivery_orders
    op.drop_column('delivery_orders', 'scheduled_datetime')
