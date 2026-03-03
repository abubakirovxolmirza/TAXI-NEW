"""add rejection reason to driver photo controls

Revision ID: 20260302_add_rejection_reason
Revises: 20260302_driver_photocontrols
Create Date: 2026-03-02 20:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260302_add_rejection_reason"
down_revision = "20260302_driver_photocontrols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("driver_photocontrols")}
    if "rejection_reason" not in columns:
        op.add_column("driver_photocontrols", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("driver_photocontrols")}
    if "rejection_reason" in columns:
        op.drop_column("driver_photocontrols", "rejection_reason")
