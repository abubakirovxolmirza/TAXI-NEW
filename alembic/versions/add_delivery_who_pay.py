"""add who_pay to delivery orders

Revision ID: add_delivery_who_pay
Revises: add_device_token_app_version
Create Date: 2026-02-26 15:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_delivery_who_pay"
down_revision = "add_device_token_app_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_orders",
        sa.Column("who_pay", sa.String(length=20), nullable=False, server_default="recipient"),
    )


def downgrade() -> None:
    op.drop_column("delivery_orders", "who_pay")
