"""add telegram message id fields

Revision ID: add_telegram_message_id_fields
Revises: add_both_gender_2025
Create Date: 2025-12-19 02:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_telegram_message_id_fields"
down_revision = "add_both_gender_2025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("taxi_orders", sa.Column("telegram_message_id", sa.Integer(), nullable=True))
    op.add_column("delivery_orders", sa.Column("telegram_message_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("delivery_orders", "telegram_message_id")
    op.drop_column("taxi_orders", "telegram_message_id")
