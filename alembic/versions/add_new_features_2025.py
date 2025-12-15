"""Add new features: bonus system, order acceptance history, public orders, pending time

Revision ID: add_new_features_2025
Revises: merge_heads_2025
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_new_features_2025'
down_revision = 'merge_heads_2025'
branch_labels = None
depends_on = None


def upgrade():
    # Add bonus_ball to users table
    op.add_column('users', sa.Column('bonus_ball', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
    
    # Add new columns to taxi_orders table
    op.add_column('taxi_orders', sa.Column('pending_time', sa.Integer(), nullable=True))
    op.add_column('taxi_orders', sa.Column('bonus_user_id', sa.Integer(), nullable=True))
    op.add_column('taxi_orders', sa.Column('public_order', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('taxi_orders', sa.Column('public_order_activated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key for bonus_user_id in taxi_orders
    op.create_foreign_key('fk_taxi_orders_bonus_user_id', 'taxi_orders', 'users', ['bonus_user_id'], ['id'])
    
    # Add new columns to delivery_orders table
    op.add_column('delivery_orders', sa.Column('pending_time', sa.Integer(), nullable=True))
    op.add_column('delivery_orders', sa.Column('bonus_user_id', sa.Integer(), nullable=True))
    op.add_column('delivery_orders', sa.Column('public_order', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('delivery_orders', sa.Column('public_order_activated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key for bonus_user_id in delivery_orders
    op.create_foreign_key('fk_delivery_orders_bonus_user_id', 'delivery_orders', 'users', ['bonus_user_id'], ['id'])
    
    # Create bonus table
    op.create_table('bonus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bonus_percent', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create order_acceptance_history table
    op.create_table('order_acceptance_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('taxi_order_id', sa.Integer(), nullable=True),
        sa.Column('delivery_order_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['taxi_order_id'], ['taxi_orders.id'], ),
        sa.ForeignKeyConstraint(['delivery_order_id'], ['delivery_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on order_acceptance_history
    op.create_index('ix_order_acceptance_history_driver_id', 'order_acceptance_history', ['driver_id'])
    op.create_index('ix_order_acceptance_history_taxi_order_id', 'order_acceptance_history', ['taxi_order_id'])
    op.create_index('ix_order_acceptance_history_delivery_order_id', 'order_acceptance_history', ['delivery_order_id'])
    
    # Update Gender enum to remove 'other' option
    # Note: This is database-specific. For PostgreSQL:
    op.execute("ALTER TYPE gender DROP VALUE IF EXISTS 'other'")


def downgrade():
    # Drop indexes
    op.drop_index('ix_order_acceptance_history_delivery_order_id', table_name='order_acceptance_history')
    op.drop_index('ix_order_acceptance_history_taxi_order_id', table_name='order_acceptance_history')
    op.drop_index('ix_order_acceptance_history_driver_id', table_name='order_acceptance_history')
    
    # Drop order_acceptance_history table
    op.drop_table('order_acceptance_history')
    
    # Drop bonus table
    op.drop_table('bonus')
    
    # Remove foreign keys from delivery_orders
    op.drop_constraint('fk_delivery_orders_bonus_user_id', 'delivery_orders', type_='foreignkey')
    
    # Remove columns from delivery_orders
    op.drop_column('delivery_orders', 'public_order_activated_at')
    op.drop_column('delivery_orders', 'public_order')
    op.drop_column('delivery_orders', 'bonus_user_id')
    op.drop_column('delivery_orders', 'pending_time')
    
    # Remove foreign keys from taxi_orders
    op.drop_constraint('fk_taxi_orders_bonus_user_id', 'taxi_orders', type_='foreignkey')
    
    # Remove columns from taxi_orders
    op.drop_column('taxi_orders', 'public_order_activated_at')
    op.drop_column('taxi_orders', 'public_order')
    op.drop_column('taxi_orders', 'bonus_user_id')
    op.drop_column('taxi_orders', 'pending_time')
    
    # Remove bonus_ball from users
    op.drop_column('users', 'bonus_ball')
    
    # Note: Cannot easily re-add 'other' to Gender enum in downgrade
    # This would require more complex SQL operations
