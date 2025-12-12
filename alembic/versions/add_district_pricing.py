"""Add district pricing table

Revision ID: add_district_pricing
Revises: merge_gender_branches
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_district_pricing'
down_revision = 'merge_gender_branches'
branch_labels = None
depends_on = None


def upgrade():
    # Create district_pricing table
    op.create_table(
        'district_pricing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_district_id', sa.Integer(), nullable=False),
        sa.Column('to_district_id', sa.Integer(), nullable=False),
        sa.Column('service_type', sa.String(length=20), nullable=False),
        sa.Column('base_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('front_seat_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('back_seat_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('discount_1_passenger', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=True),
        sa.Column('discount_2_passengers', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=True),
        sa.Column('discount_3_passengers', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=True),
        sa.Column('discount_full_car', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['from_district_id'], ['districts.id'], ),
        sa.ForeignKeyConstraint(['to_district_id'], ['districts.id'], )
    )
    op.create_index(op.f('ix_district_pricing_id'), 'district_pricing', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_district_pricing_id'), table_name='district_pricing')
    op.drop_table('district_pricing')
