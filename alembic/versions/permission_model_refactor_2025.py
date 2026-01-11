"""Permission model refactor

Revision ID: permission_model_refactor_2025
Revises: merge_heads_2025
Create Date: 2024-12-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'permission_model_refactor_2025'
down_revision = 'merge_heads_2025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new permission columns first
    op.add_column('permissions', sa.Column('orders_update', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('orders_cancel', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('create_order', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('drivers_applications', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('drivers_block', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('drivers_delete', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('drivers_balance', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('users_role', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('users_reset_password', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('users_bonus', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('pricing_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('pricing_edit', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('pricing_fee', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('stats_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('region_stats_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('admin_report_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('messages_feedback', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('broadcast_send', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('profile', sa.Boolean(), nullable=False, server_default='false'))
    
    # Migrate data from old columns to new ones
    op.execute("""
        UPDATE permissions 
        SET pricing_view = COALESCE(pricing_manage, false),
            messages_feedback = COALESCE(feedback_view, false),
            broadcast_send = COALESCE(notifications_send, false)
    """)
    
    # Remove old permission columns
    op.drop_column('permissions', 'orders_manage')
    op.drop_column('permissions', 'drivers_manage')
    op.drop_column('permissions', 'users_manage')
    op.drop_column('permissions', 'transactions_view')
    op.drop_column('permissions', 'settings_edit')
    op.drop_column('permissions', 'support_chat_access')
    op.drop_column('permissions', 'pricing_manage')
    op.drop_column('permissions', 'regions_manage')
    op.drop_column('permissions', 'bonuses_manage')
    op.drop_column('permissions', 'feedback_view')
    op.drop_column('permissions', 'notifications_send')
    op.drop_column('permissions', 'permissions_manage')


def downgrade() -> None:
    # Remove new columns
    op.drop_column('permissions', 'orders_update')
    op.drop_column('permissions', 'orders_cancel')
    op.drop_column('permissions', 'create_order')
    op.drop_column('permissions', 'drivers_applications')
    op.drop_column('permissions', 'drivers_block')
    op.drop_column('permissions', 'drivers_delete')
    op.drop_column('permissions', 'drivers_balance')
    op.drop_column('permissions', 'users_role')
    op.drop_column('permissions', 'users_reset_password')
    op.drop_column('permissions', 'users_bonus')
    op.drop_column('permissions', 'pricing_view')
    op.drop_column('permissions', 'pricing_edit')
    op.drop_column('permissions', 'pricing_fee')
    op.drop_column('permissions', 'stats_view')
    op.drop_column('permissions', 'region_stats_view')
    op.drop_column('permissions', 'admin_report_view')
    op.drop_column('permissions', 'messages_feedback')
    op.drop_column('permissions', 'broadcast_send')
    op.drop_column('permissions', 'profile')
    
    # Add back old columns
    op.add_column('permissions', sa.Column('orders_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('drivers_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('users_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('transactions_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('settings_edit', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('support_chat_access', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('pricing_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('regions_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('bonuses_manage', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('feedback_view', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('notifications_send', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('permissions', sa.Column('permissions_manage', sa.Boolean(), nullable=False, server_default='false'))