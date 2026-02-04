from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OfferType(str, Enum):
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


class OfferStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"


# ============ Category Schemas ============

class CategoryBase(BaseModel):
    name_ar: str = Field(..., min_length=2, max_length=100)
    name_en: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    icon: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    slug: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Create ============
class OfferCreate(BaseModel):
    title_ar: str = Field(..., min_length=3, max_length=255)
    title_en: str = Field(..., min_length=3, max_length=255)
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    image_url: Optional[str] = None
    offer_type: OfferType = OfferType.PACKAGE
    category: Optional[str] = None
    category_id: Optional[str] = None
    destination: Optional[str] = None
    original_price: float = Field(..., gt=0)
    discounted_price: Optional[float] = None
    currency: str = "USD"
    discount_percentage: Optional[int] = Field(None, ge=0, le=100)
    duration_days: Optional[int] = None
    duration_nights: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: OfferStatus = OfferStatus.DRAFT
    is_featured: bool = False
    is_hot: bool = False
    display_order: int = 0
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    terms: Optional[str] = None
    # Targeting
    created_by_user_id: Optional[str] = None
    target_audience: Optional[str] = "ALL"
    target_user_ids: Optional[List[str]] = None
    offer_source: str = "ADMIN"


# ============ Update ============
class OfferUpdate(BaseModel):
    title_ar: Optional[str] = None
    title_en: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    image_url: Optional[str] = None
    offer_type: Optional[OfferType] = None
    category: Optional[str] = None
    category_id: Optional[str] = None
    destination: Optional[str] = None
    original_price: Optional[float] = None
    discounted_price: Optional[float] = None
    currency: Optional[str] = None
    discount_percentage: Optional[int] = None
    duration_days: Optional[int] = None
    duration_nights: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: Optional[OfferStatus] = None
    is_featured: Optional[bool] = None
    is_hot: Optional[bool] = None
    display_order: Optional[int] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    terms: Optional[str] = None
    target_audience: Optional[str] = None
    target_user_ids: Optional[List[str]] = None
    offer_source: Optional[str] = None


# ============ Response ============
class OfferResponse(BaseModel):
    id: str
    title_ar: str
    title_en: str
    description_ar: Optional[str]
    description_en: Optional[str]
    image_url: Optional[str]
    offer_type: str
    category: Optional[str]
    category_id: Optional[str]
    category_details: Optional[CategoryResponse] = Field(None, alias="category_rel")
    destination: Optional[str]
    original_price: float
    discounted_price: Optional[float]
    currency: str
    discount_percentage: Optional[int]
    duration_days: Optional[int]
    duration_nights: Optional[int]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    status: str
    is_featured: bool
    is_hot: bool
    display_order: int
    view_count: int
    booking_count: int
    includes: Optional[List[str]]
    excludes: Optional[List[str]]
    terms: Optional[str]
    # Targeting
    created_by_user_id: Optional[str]
    target_audience: Optional[str]
    target_user_ids: Optional[List[str]]
    offer_source: str
    is_favorited: bool = False
    # Ratings
    rating_count: int = 0
    average_rating: float = 0.0
    my_rating: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfferListResponse(BaseModel):
    id: str
    title_ar: str
    title_en: str
    image_url: Optional[str]
    offer_type: str
    category: Optional[str]
    category_id: Optional[str]
    destination: Optional[str]
    original_price: float
    discounted_price: Optional[float]
    currency: str
    discount_percentage: Optional[int]
    duration_days: Optional[int]
    duration_nights: Optional[int]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    status: str
    is_featured: bool
    is_hot: bool
    display_order: int = 0
    offer_source: str = "ADMIN"
    is_favorited: bool = False
    # Ratings
    rating_count: int = 0
    average_rating: float = 0.0
    my_rating: Optional[int] = None

    class Config:
        from_attributes = True


# ============ Admin/Employee (internal) List Response ============
class OfferAdminListResponse(OfferListResponse):
    """
    Internal listing schema (admin/employee) that includes creator info and timestamps.
    This should NOT be used for public endpoints to avoid leaking internal user details.
    """

    created_at: datetime
    updated_at: datetime

    # Creator (display)
    created_by_user_id: Optional[str] = None
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None
    created_by_role: Optional[str] = None


class OfferBookRequest(BaseModel):
    save_card: bool = Field(default=False)


class OfferRateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class OfferRatingSummaryResponse(BaseModel):
    rating_count: int
    average_rating: float
    my_rating: int
