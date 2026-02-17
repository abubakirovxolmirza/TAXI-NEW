"""Add phone OTP codes table

Revision ID: 20260207_sms_otp_login
Revises: 20260203_click_amount_decimal
Create Date: 2026-02-07

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260207_sms_otp_login"
down_revision = "20260203_click_amount_decimal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "phone_otps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_phone_otps_phone"), "phone_otps", ["phone"], unique=False)
    op.create_index(op.f("ix_phone_otps_expires_at"), "phone_otps", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_phone_otps_expires_at"), table_name="phone_otps")
    op.drop_index(op.f("ix_phone_otps_phone"), table_name="phone_otps")
    op.drop_table("phone_otps")
