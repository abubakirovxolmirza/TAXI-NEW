"""change delivery who_pay default to recipient

Revision ID: change_delivery_who_pay_default
Revises: add_delivery_who_pay
Create Date: 2026-02-26 15:30:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "change_delivery_who_pay_default"
down_revision = "add_delivery_who_pay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE delivery_orders ALTER COLUMN who_pay SET DEFAULT 'recipient'")


def downgrade() -> None:
    op.execute("ALTER TABLE delivery_orders ALTER COLUMN who_pay SET DEFAULT 'sender'")
