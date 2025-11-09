"""add system settings table

Revision ID: add_system_settings
Revises: add_scheduled_datetime
Create Date: 2025-11-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_system_settings'
down_revision = 'add_scheduled_datetime'
branch_label = None
depends_on = None


def upgrade():
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('setting_value', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_setting_key'), 'system_settings', ['setting_key'], unique=True)
    
    # Insert default service fee percentage (10%)
    op.execute("""
        INSERT INTO system_settings (setting_key, setting_value, description)
        VALUES ('service_fee_percentage', '10.00', 'Platform service fee percentage')
    """)


def downgrade():
    op.drop_index(op.f('ix_system_settings_setting_key'), table_name='system_settings')
    op.drop_table('system_settings')
