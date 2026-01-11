"""Add default seat visibility timeout setting

Revision ID: add_seat_visibility_timeout
Revises: merge_permission_refactor_2025
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision = 'add_seat_visibility_timeout'
down_revision = 'merge_permission_refactor_2025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert default seat visibility timeout setting if it doesn't exist
    op.execute("""
        INSERT INTO system_settings (setting_key, setting_value, description, created_at)
        SELECT 'seat_visibility_timeout_minutes', '15', 
               'Time in minutes before order becomes visible to all drivers (default: 15 minutes)', 
               NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM system_settings WHERE setting_key = 'seat_visibility_timeout_minutes'
        )
    """)


def downgrade() -> None:
    # Remove the seat visibility timeout setting
    op.execute("""
        DELETE FROM system_settings WHERE setting_key = 'seat_visibility_timeout_minutes'
    """)
