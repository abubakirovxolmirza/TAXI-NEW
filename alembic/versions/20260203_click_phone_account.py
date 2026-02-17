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


"""def upgrade() -> None:
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.drop_constraint("uq_topup_merchant_trans_id", type_="unique")
        batch_op.add_column(sa.Column("account_phone", sa.String(length=20), nullable=True))
        batch_op.alter_column("raw_prepare", new_column_name="raw_prepare_payload")
        batch_op.alter_column("raw_complete", new_column_name="raw_complete_payload")
    op.create_index("ix_topup_account_phone", "topup_transactions", ["account_phone"])
"""
def upgrade() -> None:
    # 1) constraint bo'lsa o'chir, bo'lmasa skip
    op.execute("ALTER TABLE topup_transactions DROP CONSTRAINT IF EXISTS uq_topup_merchant_trans_id")

    # 2) account_phone bor-yo'qligini tekshir
    conn = op.get_bind()
    cols = {row["name"] for row in sa.inspect(conn).get_columns("topup_transactions")}

    with op.batch_alter_table("topup_transactions") as batch_op:
        if "account_phone" not in cols:
            batch_op.add_column(sa.Column("account_phone", sa.String(length=20), nullable=True))

        # bu 2 ustun eski DBda raw_prepare/raw_complete bo'lsa rename qiladi,
        # agar allaqachon rename bo'lgan bo'lsa, xatoga tushmasligi uchun tekshirib o'tamiz
        if "raw_prepare" in cols and "raw_prepare_payload" not in cols:
            batch_op.alter_column("raw_prepare", new_column_name="raw_prepare_payload")

        if "raw_complete" in cols and "raw_complete_payload" not in cols:
            batch_op.alter_column("raw_complete", new_column_name="raw_complete_payload")

    # index ham bor bo'lsa qayta yaratmasin
    op.execute("CREATE INDEX IF NOT EXISTS ix_topup_account_phone ON topup_transactions (account_phone)")
    
def downgrade() -> None:
    op.drop_index("ix_topup_account_phone", table_name="topup_transactions")
    with op.batch_alter_table("topup_transactions") as batch_op:
        batch_op.alter_column("raw_prepare_payload", new_column_name="raw_prepare")
        batch_op.alter_column("raw_complete_payload", new_column_name="raw_complete")
        batch_op.drop_column("account_phone")
        batch_op.create_unique_constraint("uq_topup_merchant_trans_id", ["merchant_trans_id"])
