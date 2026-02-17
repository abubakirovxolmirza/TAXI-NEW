"""Add vip expiration datetime for drivers

Revision ID: 20260208_driver_vip_expiry
Revises: 20260208_driver_vip_brend
Create Date: 2026-02-08

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260208_driver_vip_expiry"
down_revision = "20260208_driver_vip_brend"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("drivers") as batch_op:
        batch_op.add_column(sa.Column("vip_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("drivers") as batch_op:
        batch_op.drop_column("vip_expires_at")
