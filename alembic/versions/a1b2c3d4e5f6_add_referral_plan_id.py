"""add referral plan_id for competition

Revision ID: a1b2c3d4e5f6
Revises: c4b3e9f6d1a2
Create Date: 2026-02-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "c4b3e9f6d1a2"
branch_labels = None
depends_on = None


def upgrade():
    # Add plan_id to referrals (which plan the referred user subscribed to)
    try:
        op.add_column("referrals", sa.Column("plan_id", sa.String(36), nullable=True))
    except Exception:
        pass  # column may already exist


def downgrade():
    try:
        op.drop_column("referrals", "plan_id")
    except Exception:
        pass
