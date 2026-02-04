"""add_membership_benefits_table

Revision ID: 6e22f269ae07
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6e22f269ae07'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (for SQLite)
    from sqlalchemy import inspect
    from database.base import engine
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if 'membership_benefits' not in existing_tables:
        op.create_table(
            'membership_benefits',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('plan_id', sa.String(), nullable=False),
            sa.Column('image_url', sa.String(), nullable=True),
            sa.Column('welcome_message_en', sa.String(), nullable=True),
            sa.Column('welcome_message_ar', sa.String(), nullable=True),
            sa.Column('hotel_discounts_en', sa.JSON(), nullable=True),
            sa.Column('hotel_discounts_ar', sa.JSON(), nullable=True),
            sa.Column('membership_benefits_en', sa.JSON(), nullable=True),
            sa.Column('membership_benefits_ar', sa.JSON(), nullable=True),
            sa.Column('flight_coupons_en', sa.JSON(), nullable=True),
            sa.Column('flight_coupons_ar', sa.JSON(), nullable=True),
            sa.Column('free_flight_terms_en', sa.String(), nullable=True),
            sa.Column('free_flight_terms_ar', sa.String(), nullable=True),
            sa.Column('car_rental_services_en', sa.JSON(), nullable=True),
            sa.Column('car_rental_services_ar', sa.JSON(), nullable=True),
            sa.Column('restaurant_benefits_en', sa.JSON(), nullable=True),
            sa.Column('restaurant_benefits_ar', sa.JSON(), nullable=True),
            sa.Column('immediate_coupons_en', sa.JSON(), nullable=True),
            sa.Column('immediate_coupons_ar', sa.JSON(), nullable=True),
            sa.Column('tourism_services_en', sa.JSON(), nullable=True),
            sa.Column('tourism_services_ar', sa.JSON(), nullable=True),
            sa.Column('terms_conditions_en', sa.String(), nullable=True),
            sa.Column('terms_conditions_ar', sa.String(), nullable=True),
            sa.Column('comparison_guarantee_en', sa.String(), nullable=True),
            sa.Column('comparison_guarantee_ar', sa.String(), nullable=True),
            sa.Column('availability_terms_en', sa.String(), nullable=True),
            sa.Column('availability_terms_ar', sa.String(), nullable=True),
            sa.Column('coupon_usage_terms_en', sa.String(), nullable=True),
            sa.Column('coupon_usage_terms_ar', sa.String(), nullable=True),
            sa.Column('upgrade_to_plan_id', sa.String(), nullable=True),
            sa.Column('upgrade_info_en', sa.String(), nullable=True),
            sa.Column('upgrade_info_ar', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['plan_id'], ['membership_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['upgrade_to_plan_id'], ['membership_plans.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_membership_benefits_plan_id'), 'membership_benefits', ['plan_id'], unique=False)
    else:
        print("Table 'membership_benefits' already exists. Skipping creation.")


def downgrade():
    op.drop_index(op.f('ix_membership_benefits_plan_id'), table_name='membership_benefits')
    op.drop_table('membership_benefits')
