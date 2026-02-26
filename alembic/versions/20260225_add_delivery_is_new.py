"""add is_new flag to delivery orders

Revision ID: 20260225_add_delivery_is_new
Revises: 20260223_push_notifications
Create Date: 2026-02-25 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260225_add_delivery_is_new"
down_revision = "20260223_push_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_orders",
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("delivery_orders", "is_new")
