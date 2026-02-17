"""Add query indexes for phone otps

Revision ID: 20260208_phone_otp_query_indexes
Revises: 20260208_driver_vip_expiry
Create Date: 2026-02-08

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260208_phone_otp_query_indexes"
down_revision = "20260208_driver_vip_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_phone_otps_phone_created_at",
        "phone_otps",
        ["phone", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_phone_otps_phone_is_used_expires_at",
        "phone_otps",
        ["phone", "is_used", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_phone_otps_phone_is_used_expires_at", table_name="phone_otps")
    op.drop_index("ix_phone_otps_phone_created_at", table_name="phone_otps")
