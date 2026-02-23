"""add device tokens and rich notification payload

Revision ID: 20260223_push_notifications
Revises: 20260222_taxi_dropoff_loc
Create Date: 2026-02-23 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260223_push_notifications"
down_revision = "20260222_taxi_dropoff_loc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    device_platform = postgresql.ENUM("android", "ios", "web", name="deviceplatform", create_type=False)
    device_platform.create(bind, checkfirst=True)

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", device_platform, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_device_tokens_id"), "device_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_device_tokens_is_active"), "device_tokens", ["is_active"], unique=False)
    op.create_index(op.f("ix_device_tokens_token"), "device_tokens", ["token"], unique=True)
    op.create_index(op.f("ix_device_tokens_user_id"), "device_tokens", ["user_id"], unique=False)

    op.add_column("notifications", sa.Column("body", sa.Text(), nullable=True))
    op.add_column("notifications", sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute("UPDATE notifications SET body = message WHERE body IS NULL")
    op.alter_column("notifications", "body", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.drop_column("notifications", "data")
    op.drop_column("notifications", "body")

    op.drop_index(op.f("ix_device_tokens_user_id"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_token"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_is_active"), table_name="device_tokens")
    op.drop_index(op.f("ix_device_tokens_id"), table_name="device_tokens")
    op.drop_table("device_tokens")

    bind = op.get_bind()
    device_platform = postgresql.ENUM("android", "ios", "web", name="deviceplatform", create_type=False)
    device_platform.drop(bind, checkfirst=True)
