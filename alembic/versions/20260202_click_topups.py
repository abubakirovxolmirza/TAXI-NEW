"""Add Click topup tables

Revision ID: 20260202_click_topups
Revises: e26e5b8f1192
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260202_click_topups"
down_revision = "e26e5b8f1192"
branch_labels = None
depends_on = None


def upgrade() -> None:
    topup_status = sa.Enum(
        "CREATED",
        "PREPARED",
        "PAID",
        "FAILED",
        "CANCELED",
        name="topup_status",
    )
    topup_status.create(op.get_bind(), checkfirst=True)

    topup_status_col = postgresql.ENUM(
        "CREATED",
        "PREPARED",
        "PAID",
        "FAILED",
        "CANCELED",
        name="topup_status",
        create_type=False,
    )

    op.create_table(
        "topup_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("merchant_trans_id", sa.String(length=64), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("status", topup_status_col, nullable=False),
        sa.Column("click_trans_id", sa.String(length=64), nullable=True),
        sa.Column("merchant_prepare_id", sa.String(length=64), nullable=True),
        sa.Column("merchant_confirm_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("raw_prepare", postgresql.JSONB(), nullable=True),
        sa.Column("raw_complete", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("merchant_trans_id", name="uq_topup_merchant_trans_id"),
        sa.UniqueConstraint("click_trans_id", name="uq_topup_click_trans_id"),
        sa.UniqueConstraint("merchant_prepare_id", name="uq_topup_merchant_prepare_id"),
        sa.UniqueConstraint("merchant_confirm_id", name="uq_topup_merchant_confirm_id"),
    )
    op.create_index(
        "ix_topup_driver_created_at",
        "topup_transactions",
        ["driver_id", "created_at"],
    )

    op.create_table(
        "payment_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("merchant_trans_id", sa.String(length=64), nullable=False),
        sa.Column("click_trans_id", sa.String(length=64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("payment_logs")
    op.drop_index("ix_topup_driver_created_at", table_name="topup_transactions")
    op.drop_table("topup_transactions")
    op.execute("DROP TYPE IF EXISTS topup_status")
