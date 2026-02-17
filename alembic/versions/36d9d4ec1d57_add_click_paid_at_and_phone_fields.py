"""add click paid_at and phone fields

Revision ID: 36d9d4ec1d57
Revises: add_seat_visibility_timeout
Create Date: 2026-02-03 07:31:54.578750

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '36d9d4ec1d57'
down_revision = 'add_seat_visibility_timeout'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    topup_columns = {column["name"]: column for column in inspector.get_columns("topup_transactions")}

    if "account_phone" not in topup_columns:
        op.add_column("topup_transactions", sa.Column("account_phone", sa.String(length=20), nullable=True))

    if "raw_prepare_payload" not in topup_columns:
        op.add_column(
            "topup_transactions",
            sa.Column("raw_prepare_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    if "raw_complete_payload" not in topup_columns:
        op.add_column(
            "topup_transactions",
            sa.Column("raw_complete_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    amount_type = str(topup_columns.get("amount", {}).get("type", "")).lower()
    if amount_type.startswith("bigint"):
        op.alter_column(
            "topup_transactions",
            "amount",
            existing_type=sa.BIGINT(),
            type_=sa.Numeric(precision=12, scale=2),
            existing_nullable=False,
        )

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("topup_transactions")
        if constraint.get("name")
    }
    if "uq_topup_merchant_trans_id" in unique_constraints:
        op.drop_constraint("uq_topup_merchant_trans_id", "topup_transactions", type_="unique")

    indexes = {index["name"] for index in inspector.get_indexes("topup_transactions")}
    if "ix_topup_account_phone" not in indexes:
        op.create_index("ix_topup_account_phone", "topup_transactions", ["account_phone"], unique=False)

    if "raw_prepare" in topup_columns:
        op.drop_column("topup_transactions", "raw_prepare")

    if "raw_complete" in topup_columns:
        op.drop_column("topup_transactions", "raw_complete")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "gender" in user_columns:
        op.drop_column("users", "gender")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "gender" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "gender",
                postgresql.ENUM("male", "female", "both", name="gender"),
                autoincrement=False,
                nullable=True,
            ),
        )

    topup_columns = {column["name"]: column for column in inspector.get_columns("topup_transactions")}
    if "raw_complete" not in topup_columns:
        op.add_column(
            "topup_transactions",
            sa.Column("raw_complete", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        )

    if "raw_prepare" not in topup_columns:
        op.add_column(
            "topup_transactions",
            sa.Column("raw_prepare", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
        )

    indexes = {index["name"] for index in inspector.get_indexes("topup_transactions")}
    if "ix_topup_account_phone" in indexes:
        op.drop_index("ix_topup_account_phone", table_name="topup_transactions")

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("topup_transactions")
        if constraint.get("name")
    }
    if "uq_topup_merchant_trans_id" not in unique_constraints:
        op.create_unique_constraint("uq_topup_merchant_trans_id", "topup_transactions", ["merchant_trans_id"])

    amount_type = str(topup_columns.get("amount", {}).get("type", "")).lower()
    if amount_type.startswith("numeric"):
        op.alter_column(
            "topup_transactions",
            "amount",
            existing_type=sa.Numeric(precision=12, scale=2),
            type_=sa.BIGINT(),
            existing_nullable=False,
        )

    if "raw_complete_payload" in topup_columns:
        op.drop_column("topup_transactions", "raw_complete_payload")

    if "raw_prepare_payload" in topup_columns:
        op.drop_column("topup_transactions", "raw_prepare_payload")

    if "account_phone" in topup_columns:
        op.drop_column("topup_transactions", "account_phone")
