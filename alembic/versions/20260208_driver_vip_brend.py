"""Add vip and brend flags to drivers

Revision ID: 20260208_driver_vip_brend
Revises: 20260207_sms_otp_login
Create Date: 2026-02-08

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260208_driver_vip_brend"
down_revision = "20260207_sms_otp_login"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("drivers") as batch_op:
        batch_op.add_column(sa.Column("vip", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("brend", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("drivers") as batch_op:
        batch_op.drop_column("brend")
        batch_op.drop_column("vip")
