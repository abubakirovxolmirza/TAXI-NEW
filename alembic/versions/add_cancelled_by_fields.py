"""add cancelled by fields to orders

Revision ID: add_cancelled_by_fields
Revises: 20260225_add_delivery_is_new
Create Date: 2026-02-26 10:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_cancelled_by_fields"
down_revision = "20260225_add_delivery_is_new"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("taxi_orders", sa.Column("cancelled_by_user_id", sa.Integer(), nullable=True))
    op.add_column("taxi_orders", sa.Column("cancelled_by_role", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_taxi_orders_cancelled_by_user_id_users",
        "taxi_orders",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
    )

    op.add_column("delivery_orders", sa.Column("cancelled_by_user_id", sa.Integer(), nullable=True))
    op.add_column("delivery_orders", sa.Column("cancelled_by_role", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_delivery_orders_cancelled_by_user_id_users",
        "delivery_orders",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
    )

    # Backfill old cancelled orders: if actor is unknown, assume order owner.
    op.execute(
        """
        UPDATE taxi_orders
        SET cancelled_by_user_id = user_id,
            cancelled_by_role = 'user'
        WHERE status = 'cancelled'
          AND cancelled_by_user_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE delivery_orders
        SET cancelled_by_user_id = user_id,
            cancelled_by_role = 'user'
        WHERE status = 'cancelled'
          AND cancelled_by_user_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_delivery_orders_cancelled_by_user_id_users", "delivery_orders", type_="foreignkey")
    op.drop_column("delivery_orders", "cancelled_by_role")
    op.drop_column("delivery_orders", "cancelled_by_user_id")

    op.drop_constraint("fk_taxi_orders_cancelled_by_user_id_users", "taxi_orders", type_="foreignkey")
    op.drop_column("taxi_orders", "cancelled_by_role")
    op.drop_column("taxi_orders", "cancelled_by_user_id")
