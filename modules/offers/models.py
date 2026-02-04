from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, Enum as SQLEnum, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin


class OfferType(str, enum.Enum):
    HOTEL = "HOTEL"
    FLIGHT = "FLIGHT"
    PACKAGE = "PACKAGE"
    ACTIVITY = "ACTIVITY"
    TRANSFER = "TRANSFER"
    CRUISE = "CRUISE"
    DISCOUNT = "DISCOUNT"
    VOUCHER = "VOUCHER"
    BROADCAST = "BROADCAST"
    OTHER = "OTHER"


class OfferStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"


class TargetAudience(str, enum.Enum):
    ALL = "ALL"              # All users
    ASSIGNED = "ASSIGNED"    # Only assigned users of the creator employee
    SPECIFIC = "SPECIFIC"    # Specific user IDs


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"
    
    # Multilingual Names
    name_ar = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=False)
    
    # Slug for URL-friendly identifier
    slug = Column(String(100), nullable=False, unique=True, index=True)
    
    # Optional icon name (e.g., "hotel", "flight", "package")
    icon = Column(String(50), nullable=True)
    
    # Display order for sorting
    sort_order = Column(Integer, default=0, index=True)
    
    # Active status
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationship to offers
    offers = relationship("Offer", back_populates="category_rel")
    
    def __repr__(self):
        return f"<Category {self.name_en}>"



class Offer(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "offers"
    
    # Basic Info
    title_ar = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=False)
    description_ar = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    # Media
    image_url = Column(String(500), nullable=True)
    images = Column(Text, nullable=True)  # JSON array of image URLs
    
    # Type & Category
    offer_type = Column(SQLEnum(OfferType), nullable=False, default=OfferType.PACKAGE)
    category = Column(String(100), nullable=True)  # Legacy field - kept for backward compatibility
    category_id = Column(String(36), ForeignKey('categories.id'), nullable=True, index=True)  # Foreign key to categories
    destination = Column(String(200), nullable=True)  # e.g., "Sharm El Sheikh"
    
    # Relationship to Category
    category_rel = relationship("Category", back_populates="offers", foreign_keys=[category_id])

    
    # Pricing
    original_price = Column(Float, nullable=False, default=0)
    discounted_price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    discount_percentage = Column(Integer, nullable=True)  # e.g., 50 for 50%
    
    # Duration
    duration_days = Column(Integer, nullable=True)
    duration_nights = Column(Integer, nullable=True)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Status & Display
    status = Column(SQLEnum(OfferStatus), nullable=False, default=OfferStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)  # Show in carousel
    is_hot = Column(Boolean, default=False)  # Hot deal badge
    display_order = Column(Integer, default=0)  # For ordering in carousel
    
    # Stats
    view_count = Column(Integer, default=0)
    booking_count = Column(Integer, default=0)
    
    # Additional Details (JSON)
    includes = Column(Text, nullable=True)  # JSON array of what's included
    excludes = Column(Text, nullable=True)  # JSON array of what's not included
    terms = Column(Text, nullable=True)  # Terms and conditions
    
    # Creator & Targeting
    created_by_user_id = Column(String(36), nullable=True, index=True)  # FK to users.id
    target_audience = Column(String(20), nullable=False, default="ALL")  # ALL, ASSIGNED, SPECIFIC
    target_user_ids = Column(Text, nullable=True)  # JSON array of user IDs for SPECIFIC targeting
    
    # Separation
    offer_source = Column(String(20), nullable=False, default="ADMIN")  # ADMIN, MARKETING
    
    def __repr__(self):
        return f"<Offer {self.title_en}>"


# Favorites table (many-to-many)
class OfferFavorite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offer_favorites"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    offer_id = Column(String(36), ForeignKey("offers.id"), nullable=False, index=True)

    # Relationships
    user = relationship("User")
    offer = relationship("Offer")

    def __repr__(self):
        return f"<OfferFavorite user={self.user_id} offer={self.offer_id}>"


class OfferRating(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offer_ratings"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    offer_id = Column(String(36), ForeignKey("offers.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "offer_id", name="uq_offer_rating_user_offer"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_offer_rating_range"),
    )

    # Relationships
    user = relationship("User")
    offer = relationship("Offer")

    def __repr__(self):
        return f"<OfferRating user={self.user_id} offer={self.offer_id} rating={self.rating}>"
