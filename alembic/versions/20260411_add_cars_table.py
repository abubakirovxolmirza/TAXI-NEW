"""add cars table

Revision ID: 20260411_add_cars_table
Revises: 20260402_driver_block_reason
Create Date: 2026-04-11 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260411_add_cars_table"
down_revision = "20260402_driver_block_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "cars" not in existing_tables:
        op.create_table(
            "cars",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("tariff", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_cars_id"), "cars", ["id"], unique=False)
        op.create_index(op.f("ix_cars_name"), "cars", ["name"], unique=False)
        op.create_index(op.f("ix_cars_tariff"), "cars", ["tariff"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "cars" in existing_tables:
        op.drop_index(op.f("ix_cars_tariff"), table_name="cars")
        op.drop_index(op.f("ix_cars_name"), table_name="cars")
        op.drop_index(op.f("ix_cars_id"), table_name="cars")
        op.drop_table("cars")
