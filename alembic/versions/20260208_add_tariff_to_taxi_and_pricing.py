"""Add tariff to taxi orders and pricing tables

Revision ID: 20260208_add_tariff
Revises: 20260208_phone_otp_query_indexes
Create Date: 2026-02-08

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260208_add_tariff"
down_revision = "20260208_phone_otp_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tariff_enum = sa.Enum("standard", "comfort", "comfort_plus", "business", name="tariff")
    tariff_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("pricing") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tariff",
                tariff_enum,
                nullable=False,
                server_default="standard",
            )
        )

    with op.batch_alter_table("district_pricing") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tariff",
                tariff_enum,
                nullable=False,
                server_default="standard",
            )
        )

    with op.batch_alter_table("taxi_orders") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tariff",
                tariff_enum,
                nullable=False,
                server_default="standard",
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    tariff_enum = sa.Enum("standard", "comfort", "comfort_plus", "business", name="tariff")

    with op.batch_alter_table("taxi_orders") as batch_op:
        batch_op.drop_column("tariff")

    with op.batch_alter_table("district_pricing") as batch_op:
        batch_op.drop_column("tariff")

    with op.batch_alter_table("pricing") as batch_op:
        batch_op.drop_column("tariff")

    tariff_enum.drop(bind, checkfirst=True)
