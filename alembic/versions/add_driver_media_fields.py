"""add driver media fields

Revision ID: add_driver_media_fields
Revises: add_telegram_message_id_fields
Create Date: 2025-12-20 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_driver_media_fields"
down_revision = "add_telegram_message_id_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These fields exist in SQLAlchemy models but were missing from earlier schema
    # revisions. Use IF NOT EXISTS to stay safe on already-patched databases.
    op.execute("ALTER TABLE drivers ADD COLUMN IF NOT EXISTS car_photo VARCHAR(255)")
    op.execute("ALTER TABLE drivers ADD COLUMN IF NOT EXISTS tex_pas VARCHAR(255)")
    op.execute(
        "ALTER TABLE driver_applications ADD COLUMN IF NOT EXISTS car_photo VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE driver_applications ADD COLUMN IF NOT EXISTS tex_pas VARCHAR(255)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE driver_applications DROP COLUMN IF EXISTS tex_pas")
    op.execute("ALTER TABLE driver_applications DROP COLUMN IF EXISTS car_photo")
    op.execute("ALTER TABLE drivers DROP COLUMN IF EXISTS tex_pas")
    op.execute("ALTER TABLE drivers DROP COLUMN IF EXISTS car_photo")

