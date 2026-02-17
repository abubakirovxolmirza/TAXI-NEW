"""Change click topup amount to numeric

Revision ID: 20260203_click_amount_decimal
Revises: 20260203_click_phone_account
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260203_click_amount_decimal"
down_revision = "20260203_click_phone_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.alter_column(
            "amount",
            type_=sa.Numeric(12, 2),
            existing_type=sa.BigInteger(),
            postgresql_using="amount::numeric(12,2)",
        )


def downgrade() -> None:
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.alter_column(
            "amount",
            type_=sa.BigInteger(),
            existing_type=sa.Numeric(12, 2),
            postgresql_using="amount::bigint",
        )
