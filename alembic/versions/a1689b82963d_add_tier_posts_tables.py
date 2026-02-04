"""Add tier posts tables

Revision ID: a1689b82963d
Revises: 6e22f269ae07
Create Date: 2026-01-13 18:19:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1689b82963d'
down_revision: Union[str, None] = '6e22f269ae07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tier_posts table
    op.create_table('tier_posts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier_code', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='poststatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tier_posts_id'), 'tier_posts', ['id'], unique=False)
    op.create_index(op.f('ix_tier_posts_user_id'), 'tier_posts', ['user_id'], unique=False)
    op.create_index(op.f('ix_tier_posts_tier_code'), 'tier_posts', ['tier_code'], unique=False)
    op.create_index(op.f('ix_tier_posts_status'), 'tier_posts', ['status'], unique=False)

    # Create post_likes table
    op.create_table('post_likes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['tier_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_likes_id'), 'post_likes', ['id'], unique=False)
    op.create_index(op.f('ix_post_likes_user_id'), 'post_likes', ['user_id'], unique=False)
    op.create_index(op.f('ix_post_likes_post_id'), 'post_likes', ['post_id'], unique=False)

    # Create post_comments table
    op.create_table('post_comments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='poststatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['tier_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_post_comments_id'), 'post_comments', ['id'], unique=False)
    op.create_index(op.f('ix_post_comments_user_id'), 'post_comments', ['user_id'], unique=False)
    op.create_index(op.f('ix_post_comments_post_id'), 'post_comments', ['post_id'], unique=False)
    op.create_index(op.f('ix_post_comments_status'), 'post_comments', ['status'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_post_comments_status'), table_name='post_comments')
    op.drop_index(op.f('ix_post_comments_post_id'), table_name='post_comments')
    op.drop_index(op.f('ix_post_comments_user_id'), table_name='post_comments')
    op.drop_index(op.f('ix_post_comments_id'), table_name='post_comments')
    op.drop_table('post_comments')

    op.drop_index(op.f('ix_post_likes_post_id'), table_name='post_likes')
    op.drop_index(op.f('ix_post_likes_user_id'), table_name='post_likes')
    op.drop_index(op.f('ix_post_likes_id'), table_name='post_likes')
    op.drop_table('post_likes')

    op.drop_index(op.f('ix_tier_posts_status'), table_name='tier_posts')
    op.drop_index(op.f('ix_tier_posts_tier_code'), table_name='tier_posts')
    op.drop_index(op.f('ix_tier_posts_user_id'), table_name='tier_posts')
    op.drop_index(op.f('ix_tier_posts_id'), table_name='tier_posts')
    op.drop_table('tier_posts')
