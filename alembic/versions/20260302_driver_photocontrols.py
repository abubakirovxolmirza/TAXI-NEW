"""add driver photo controls

Revision ID: 20260302_driver_photocontrols
Revises: change_delivery_who_pay_default
Create Date: 2026-03-02 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260302_driver_photocontrols"
down_revision = "change_delivery_who_pay_default"
branch_labels = None
depends_on = None


driver_photo_control_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="driver_photo_control_status",
)

driver_photo_control_status_nocreate = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    name="driver_photo_control_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    driver_columns = {column["name"] for column in inspector.get_columns("drivers")}
    if "control" not in driver_columns:
        op.add_column(
            "drivers",
            sa.Column("control", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.alter_column("drivers", "control", server_default=None)

    # Create enum type in an idempotent way.
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE driver_photo_control_status AS ENUM ('pending', 'approved', 'rejected');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    existing_tables = set(inspector.get_table_names())
    if "driver_photocontrols" not in existing_tables:
        op.create_table(
            "driver_photocontrols",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("driver_id", sa.Integer(), nullable=False),
            sa.Column("front_image", sa.String(length=255), nullable=False),
            sa.Column("back_image", sa.String(length=255), nullable=False),
            sa.Column("front_salon", sa.String(length=255), nullable=False),
            sa.Column("back_salon", sa.String(length=255), nullable=False),
            sa.Column("trunk_image", sa.String(length=255), nullable=False),
            sa.Column("status", driver_photo_control_status_nocreate, nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_driver_photocontrols_driver_id"), "driver_photocontrols", ["driver_id"], unique=False)
        op.create_index(op.f("ix_driver_photocontrols_id"), "driver_photocontrols", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "driver_photocontrols" in existing_tables:
        op.drop_index(op.f("ix_driver_photocontrols_id"), table_name="driver_photocontrols")
        op.drop_index(op.f("ix_driver_photocontrols_driver_id"), table_name="driver_photocontrols")
        op.drop_table("driver_photocontrols")
    driver_photo_control_status.drop(bind, checkfirst=True)

    driver_columns = {column["name"] for column in inspector.get_columns("drivers")}
    if "control" in driver_columns:
        op.drop_column("drivers", "control")
