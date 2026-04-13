"""add region_id to drivers and driver_applications

Revision ID: 20260413_add_driver_region
Revises: 20260411_add_cars_table
Create Date: 2026-04-13 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260413_add_driver_region"
down_revision = "20260411_add_cars_table"
branch_labels = None
depends_on = None


DRIVERS_FK_NAME = "fk_drivers_region_id_regions"
APPLICATIONS_FK_NAME = "fk_driver_applications_region_id_regions"


def _resolve_default_region_id(bind) -> int | None:
    """Prefer Farg'ona; fallback to first active region, then first region."""
    fargona_region_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM regions
            WHERE is_active = true
              AND (
                lower(name_uz_latin) LIKE '%farg%'
                OR lower(name_uz_cyrillic) LIKE '%фар%'
                OR lower(name_russian) LIKE '%fergan%'
              )
            ORDER BY id
            LIMIT 1
            """
        )
    ).scalar()
    if fargona_region_id is not None:
        return int(fargona_region_id)

    active_region_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM regions
            WHERE is_active = true
            ORDER BY id
            LIMIT 1
            """
        )
    ).scalar()
    if active_region_id is not None:
        return int(active_region_id)

    any_region_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM regions
            ORDER BY id
            LIMIT 1
            """
        )
    ).scalar()
    return int(any_region_id) if any_region_id is not None else None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    drivers_columns = {column["name"] for column in inspector.get_columns("drivers")}
    if "region_id" not in drivers_columns:
        op.add_column("drivers", sa.Column("region_id", sa.Integer(), nullable=True))

    applications_columns = {column["name"] for column in inspector.get_columns("driver_applications")}
    if "region_id" not in applications_columns:
        op.add_column("driver_applications", sa.Column("region_id", sa.Integer(), nullable=True))

    default_region_id = _resolve_default_region_id(bind)
    if default_region_id is not None:
        op.execute(
            sa.text(
                """
                UPDATE drivers
                SET region_id = :region_id
                WHERE region_id IS NULL
                """
            ).bindparams(region_id=default_region_id)
        )
        op.execute(
            sa.text(
                """
                UPDATE driver_applications
                SET region_id = :region_id
                WHERE region_id IS NULL
                """
            ).bindparams(region_id=default_region_id)
        )

    inspector = sa.inspect(bind)
    drivers_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("drivers")}
    if DRIVERS_FK_NAME not in drivers_fk_names:
        with op.batch_alter_table("drivers") as batch_op:
            batch_op.create_foreign_key(
                DRIVERS_FK_NAME,
                "regions",
                ["region_id"],
                ["id"],
            )

    applications_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("driver_applications")}
    if APPLICATIONS_FK_NAME not in applications_fk_names:
        with op.batch_alter_table("driver_applications") as batch_op:
            batch_op.create_foreign_key(
                APPLICATIONS_FK_NAME,
                "regions",
                ["region_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    drivers_columns = {column["name"] for column in inspector.get_columns("drivers")}
    drivers_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("drivers")}
    if DRIVERS_FK_NAME in drivers_fk_names:
        with op.batch_alter_table("drivers") as batch_op:
            batch_op.drop_constraint(DRIVERS_FK_NAME, type_="foreignkey")
    if "region_id" in drivers_columns:
        op.drop_column("drivers", "region_id")

    applications_columns = {column["name"] for column in inspector.get_columns("driver_applications")}
    applications_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("driver_applications")}
    if APPLICATIONS_FK_NAME in applications_fk_names:
        with op.batch_alter_table("driver_applications") as batch_op:
            batch_op.drop_constraint(APPLICATIONS_FK_NAME, type_="foreignkey")
    if "region_id" in applications_columns:
        op.drop_column("driver_applications", "region_id")
