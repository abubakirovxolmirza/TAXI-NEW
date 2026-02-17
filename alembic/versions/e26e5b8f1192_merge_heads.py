"""merge heads

Revision ID: e26e5b8f1192
Revises: add_driver_media_fields, add_seat_visibility_timeout
Create Date: 2026-02-01 17:39:25.031298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e26e5b8f1192"
down_revision = ("add_driver_media_fields", "add_seat_visibility_timeout")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
