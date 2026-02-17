"""Adjust Click topups for phone-based account

Revision ID: 20260203_click_phone_account
Revises: 20260202_click_topups
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260203_click_phone_account"
down_revision = "20260202_click_topups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.drop_constraint("uq_topup_merchant_trans_id", type_="unique")
        batch_op.add_column(sa.Column("account_phone", sa.String(length=20), nullable=True))
        batch_op.alter_column("raw_prepare", new_column_name="raw_prepare_payload")
        batch_op.alter_column("raw_complete", new_column_name="raw_complete_payload")
    op.create_index("ix_topup_account_phone", "topup_transactions", ["account_phone"])


def downgrade() -> None:
    op.drop_index("ix_topup_account_phone", table_name="topup_transactions")
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.alter_column("raw_prepare_payload", new_column_name="raw_prepare")
        batch_op.alter_column("raw_complete_payload", new_column_name="raw_complete")
        batch_op.drop_column("account_phone")
        batch_op.create_unique_constraint("uq_topup_merchant_trans_id", ["merchant_trans_id"])
