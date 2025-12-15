"""add new features 2025

Revision ID: add_new_features_2025
Revises: merge_heads_2025
Create Date: 2025-12-16 00:00:00.000000

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
    
    # Add bonus_user_id, public_order, and pending_time to taxi_orders
    op.add_column('taxi_orders', sa.Column('bonus_user_id', sa.Integer(), nullable=True))
    op.add_column('taxi_orders', sa.Column('public_order', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('taxi_orders', sa.Column('pending_time', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_taxi_orders_bonus_user_id', 'taxi_orders', 'users', ['bonus_user_id'], ['id'])
    
    # Add bonus_user_id, public_order, and pending_time to delivery_orders
    op.add_column('delivery_orders', sa.Column('bonus_user_id', sa.Integer(), nullable=True))
    op.add_column('delivery_orders', sa.Column('public_order', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('delivery_orders', sa.Column('pending_time', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_delivery_orders_bonus_user_id', 'delivery_orders', 'users', ['bonus_user_id'], ['id'])
    
    # Create bonuses table
    op.create_table('bonuses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bonus_percent', sa.Numeric(precision=5, scale=2), nullable=False, server_default='5.00'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bonuses_id'), 'bonuses', ['id'], unique=False)
    
    # Create order_acceptance_history table
    op.create_table('order_acceptance_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('taxi_order_id', sa.Integer(), nullable=True),
        sa.Column('delivery_order_id', sa.Integer(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.ForeignKeyConstraint(['taxi_order_id'], ['taxi_orders.id'], ),
        sa.ForeignKeyConstraint(['delivery_order_id'], ['delivery_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_acceptance_history_id'), 'order_acceptance_history', ['id'], unique=False)
    
    # Update Gender enum - remove 'other' option
    # Note: This requires a more complex migration for PostgreSQL
    # First, create a new enum type without 'other'
    op.execute("CREATE TYPE gender_new AS ENUM ('male', 'female')")
    
    # Update any 'other' values to NULL in all tables that use gender
    op.execute("UPDATE taxi_orders SET client_gender = NULL WHERE client_gender = 'other'")
    
    # Check if users table has gender column and update it
    op.execute("""
        DO $$ 
        BEGIN 
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'gender'
            ) THEN
                UPDATE users SET gender = NULL WHERE gender = 'other';
                ALTER TABLE users ALTER COLUMN gender TYPE gender_new USING gender::text::gender_new;
            END IF;
        END $$;
    """)
    
    # Alter taxi_orders column to use new enum
    op.execute("ALTER TABLE taxi_orders ALTER COLUMN client_gender TYPE gender_new USING client_gender::text::gender_new")
    
    # Drop old enum with CASCADE and rename new one
    op.execute("DROP TYPE gender CASCADE")
    op.execute("ALTER TYPE gender_new RENAME TO gender")
    
    # Insert default bonus configuration
    op.execute("INSERT INTO bonuses (bonus_percent, description, is_active) VALUES (5.00, 'Default bonus percentage', true)")
    
    # Insert default pending time system setting (15 seconds)
    op.execute("INSERT INTO system_settings (setting_key, setting_value, description) VALUES ('public_order_pending_time', '15', 'Time in seconds before order becomes public') ON CONFLICT (setting_key) DO NOTHING")


def downgrade():
    # Remove system setting
    op.execute("DELETE FROM system_settings WHERE setting_key = 'public_order_pending_time'")
    
    # Recreate old Gender enum with 'other'
    op.execute("CREATE TYPE gender_new AS ENUM ('male', 'female', 'other')")
    
    # Update taxi_orders to use new enum
    op.execute("ALTER TABLE taxi_orders ALTER COLUMN client_gender TYPE gender_new USING client_gender::text::gender_new")
    
    # Update users table if it has gender column
    op.execute("""
        DO $$ 
        BEGIN 
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'gender'
            ) THEN
                ALTER TABLE users ALTER COLUMN gender TYPE gender_new USING gender::text::gender_new;
            END IF;
        END $$;
    """)
    
    # Drop old enum and rename new one
    op.execute("DROP TYPE gender CASCADE")
    op.execute("ALTER TYPE gender_new RENAME TO gender")
    
    # Drop order_acceptance_history table
    op.drop_index(op.f('ix_order_acceptance_history_id'), table_name='order_acceptance_history')
    op.drop_table('order_acceptance_history')
    
    # Drop bonuses table
    op.drop_index(op.f('ix_bonuses_id'), table_name='bonuses')
    op.drop_table('bonuses')
    
    # Remove columns from delivery_orders
    op.drop_constraint('fk_delivery_orders_bonus_user_id', 'delivery_orders', type_='foreignkey')
    op.drop_column('delivery_orders', 'pending_time')
    op.drop_column('delivery_orders', 'public_order')
    op.drop_column('delivery_orders', 'bonus_user_id')
    
    # Remove columns from taxi_orders
    op.drop_constraint('fk_taxi_orders_bonus_user_id', 'taxi_orders', type_='foreignkey')
    op.drop_column('taxi_orders', 'pending_time')
    op.drop_column('taxi_orders', 'public_order')
    op.drop_column('taxi_orders', 'bonus_user_id')
    
    # Remove bonus_ball from users
    op.drop_column('users', 'bonus_ball')
