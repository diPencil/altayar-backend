"""add_offer_ratings_table

Revision ID: c4b3e9f6d1a2
Revises: a1689b82963d
Create Date: 2026-01-31 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4b3e9f6d1a2"
down_revision = "a1689b82963d"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists (for SQLite)
    from sqlalchemy import inspect
    from database.base import engine

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "offer_ratings" in existing_tables:
        print("Table 'offer_ratings' already exists. Skipping creation.")
        return

    op.create_table(
        "offer_ratings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "offer_id", name="uq_offer_rating_user_offer"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_offer_rating_range"),
    )
    op.create_index(op.f("ix_offer_ratings_user_id"), "offer_ratings", ["user_id"], unique=False)
    op.create_index(op.f("ix_offer_ratings_offer_id"), "offer_ratings", ["offer_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_offer_ratings_offer_id"), table_name="offer_ratings")
    op.drop_index(op.f("ix_offer_ratings_user_id"), table_name="offer_ratings")
    op.drop_table("offer_ratings")

