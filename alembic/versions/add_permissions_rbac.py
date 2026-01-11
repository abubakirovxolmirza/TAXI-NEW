"""add permissions rbac

Revision ID: add_permissions_rbac
Revises: add_new_features_2025
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_permissions_rbac"
down_revision = "add_new_features_2025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("orders_view", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("orders_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("drivers_list", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("drivers_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("users_view", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("users_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("transactions_view", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("settings_edit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("support_chat_access", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("pricing_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("regions_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("bonuses_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("feedback_view", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notifications_send", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("permissions_manage", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_permissions_id"), table_name="permissions")
    op.drop_table("permissions")
