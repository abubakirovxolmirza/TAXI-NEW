"""add app version to device tokens

Revision ID: add_device_token_app_version
Revises: add_cancelled_by_fields
Create Date: 2026-02-26 14:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_device_token_app_version"
down_revision = "add_cancelled_by_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("device_tokens", sa.Column("app_version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("device_tokens", "app_version")
