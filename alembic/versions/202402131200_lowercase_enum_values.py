"""normalize enum values to lowercase to match SQLAlchemy models

Revision ID: 202402131200_lowercase_enum_values
Revises: change_coordinates_to_string
Create Date: 2024-02-13 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202402131200_lowercase_enum_values"
down_revision = "change_coordinates_to_string"
branch_labels = None
depends_on = None


def _swap_enum(enum_name, table_columns, target_values, source_values, transform_sql):
    """
    Replace an enum type with a new set of values while transforming existing data.

    Args:
        enum_name: Name of the enum type in Postgres.
        table_columns: Iterable of (table_name, column_name) tuples that use the enum.
        target_values: Iterable of the desired enum values.
        source_values: Iterable of the current enum values.
        transform_sql: SQL fragment with `{column}` placeholder to project column values
                       into the new enum (e.g. 'lower({column}::text)').
    """
    bind = op.get_bind()

    op.execute(sa.text(f"ALTER TYPE {enum_name} RENAME TO {enum_name}_old"))

    target_enum = sa.Enum(*target_values, name=enum_name)
    target_enum.create(bind, checkfirst=False)

    source_enum = sa.Enum(*source_values, name=f"{enum_name}_old")

    for table_name, column_name in table_columns:
        op.alter_column(
            table_name,
            column_name,
            type_=target_enum,
            existing_type=source_enum,
            postgresql_using=f"{transform_sql.format(column=column_name)}::{enum_name}",
        )

    op.execute(sa.text(f"DROP TYPE {enum_name}_old"))


def upgrade():
    _swap_enum(
        "userrole",
        [("users", "role")],
        ("user", "driver", "admin", "superadmin"),
        ("USER", "DRIVER", "ADMIN", "SUPERADMIN"),
        "lower({column}::text)",
    )
    _swap_enum(
        "language",
        [("users", "language")],
        ("uz_latin", "uz_cyrillic", "russian"),
        ("UZ_LATIN", "UZ_CYRILLIC", "RUSSIAN"),
        "lower({column}::text)",
    )
    _swap_enum(
        "applicationstatus",
        [("driver_applications", "status")],
        ("pending", "approved", "rejected"),
        ("PENDING", "APPROVED", "REJECTED"),
        "lower({column}::text)",
    )
    _swap_enum(
        "itemtype",
        [("delivery_orders", "item_type")],
        ("document", "box", "luggage", "valuable", "other"),
        ("DOCUMENT", "BOX", "LUGGAGE", "VALUABLE", "OTHER"),
        "lower({column}::text)",
    )
    _swap_enum(
        "orderstatus",
        [("delivery_orders", "status"), ("taxi_orders", "status")],
        ("pending", "accepted", "completed", "cancelled"),
        ("PENDING", "ACCEPTED", "COMPLETED", "CANCELLED"),
        "lower({column}::text)",
    )


def downgrade():
    _swap_enum(
        "orderstatus",
        [("delivery_orders", "status"), ("taxi_orders", "status")],
        ("PENDING", "ACCEPTED", "COMPLETED", "CANCELLED"),
        ("pending", "accepted", "completed", "cancelled"),
        "upper({column}::text)",
    )
    _swap_enum(
        "itemtype",
        [("delivery_orders", "item_type")],
        ("DOCUMENT", "BOX", "LUGGAGE", "VALUABLE", "OTHER"),
        ("document", "box", "luggage", "valuable", "other"),
        "upper({column}::text)",
    )
    _swap_enum(
        "applicationstatus",
        [("driver_applications", "status")],
        ("PENDING", "APPROVED", "REJECTED"),
        ("pending", "approved", "rejected"),
        "upper({column}::text)",
    )
    _swap_enum(
        "language",
        [("users", "language")],
        ("UZ_LATIN", "UZ_CYRILLIC", "RUSSIAN"),
        ("uz_latin", "uz_cyrillic", "russian"),
        "upper({column}::text)",
    )
    _swap_enum(
        "userrole",
        [("users", "role")],
        ("USER", "DRIVER", "ADMIN", "SUPERADMIN"),
        ("user", "driver", "admin", "superadmin"),
        "upper({column}::text)",
    )
