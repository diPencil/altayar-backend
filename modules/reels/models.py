from sqlalchemy import Column, String, Integer, Enum as SQLEnum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

class ReelStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"

class InteractionType(str, enum.Enum):
    VIEW = "VIEW"
    LIKE = "LIKE"
    COMMENT = "COMMENT"
    SHARE = "SHARE"

class Reel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "reels"

    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)  # Made optional - can be URL or file path
    video_type = Column(String(50), nullable=False, default='URL')  # 'URL', 'UPLOAD', 'YOUTUBE'
    thumbnail_url = Column(String, nullable=True)
    status = Column(SQLEnum(ReelStatus), default=ReelStatus.DRAFT, nullable=False, index=True)
    
    # Creator/Owner
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    
    # Analytics Counters (denormalized for performance)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    
    # Relationships
    interactions = relationship("ReelInteraction", back_populates="reel", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f"<Reel {self.id} - {self.title}>"

class ReelInteraction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reel_interactions"

    reel_id = Column(String(36), ForeignKey("reels.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True) # Nullable for guest views if needed, generally should be logged in
    type = Column(SQLEnum(InteractionType), nullable=False, index=True)
    content = Column(Text, nullable=True) # For comments
    parent_id = Column(String(36), ForeignKey("reel_interactions.id"), nullable=True, index=True) # For replies to comments
    likes_count = Column(Integer, default=0) # For comment likes
    
    # Relationships
    reel = relationship("Reel", back_populates="interactions")
    user = relationship("User") # Assuming User model is in database.base or we import it if needed for backref, but usually lazy is fine.
    parent = relationship("ReelInteraction", remote_side="ReelInteraction.id", foreign_keys=[parent_id]) # Self-referencing for replies

    def __repr__(self):
        return f"<ReelInteraction {self.type} on {self.reel_id} by {self.user_id}>"

# Favorites table (many-to-many)
class ReelFavorite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reel_favorites"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    reel_id = Column(String(36), ForeignKey("reels.id"), nullable=False, index=True)
    
    # Relationships
    user = relationship("User")
    reel = relationship("Reel")
    
    def __repr__(self):
        return f"<ReelFavorite user={self.user_id} reel={self.reel_id}>"
