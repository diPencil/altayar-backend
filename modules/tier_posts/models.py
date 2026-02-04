from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class PostStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TierPost(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tier_posts"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    tier_code = Column(String(50), nullable=False, index=True)  # SILVER, GOLD, etc.
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    status = Column(SQLEnum(PostStatus), default=PostStatus.PENDING, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="tier_posts")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TierPost {self.id} by {self.user_id}>"


class PostLike(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "post_likes"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(UUID(), ForeignKey('tier_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Relationships
    user = relationship("User")
    post = relationship("TierPost", back_populates="likes")
    
    def __repr__(self):
        return f"<PostLike {self.user_id} -> {self.post_id}>"


class PostComment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "post_comments"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(UUID(), ForeignKey('tier_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(SQLEnum(PostStatus), default=PostStatus.PENDING, nullable=False, index=True)
    
    # Relationships
    user = relationship("User")
    post = relationship("TierPost", back_populates="comments")
    
    def __repr__(self):
        return f"<PostComment {self.id} on {self.post_id}>"
