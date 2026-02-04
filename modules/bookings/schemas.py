from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class BookingType(str, Enum):
    HOTEL = "HOTEL"
    FLIGHT = "FLIGHT"
    PACKAGE = "PACKAGE"
    ACTIVITY = "ACTIVITY"
    TRANSFER = "TRANSFER"
    VISA = "VISA"
    INSURANCE = "INSURANCE"
    TRIP = "TRIP"
    CUSTOM = "CUSTOM"
    OTHER = "OTHER"


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    NO_SHOW = "NO_SHOW"


class BookingSource(str, Enum):
    SELF = "SELF"
    ADMIN = "ADMIN"
    AGENT = "AGENT"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


# ============ Booking Item Schemas ============
class BookingItemCreate(BaseModel):
    item_type: str = Field(default="service", max_length=50)
    description_ar: str = Field(..., min_length=1, max_length=255)
    description_en: str = Field(..., min_length=1, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(..., ge=0)
    item_details: Optional[Dict[str, Any]] = None


class BookingItemResponse(BaseModel):
    id: str
    item_type: str
    description_ar: str
    description_en: str
    quantity: float
    unit_price: float
    total_price: float
    currency: str
    item_details: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ============ Booking Schemas ============
class BookingCreate(BaseModel):
    user_id: str  # Customer ID (for admin/agent creating bookings)
    booking_type: BookingType
    title_ar: Optional[str] = None
    title_en: Optional[str] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    guest_count: int = Field(default=1, ge=1)
    guest_names: Optional[List[str]] = None
    items: List[BookingItemCreate]
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    booking_details: Optional[Dict[str, Any]] = None
    tax_rate: Optional[float] = Field(default=14.0, ge=0, le=100)
    discount_amount: Optional[float] = Field(default=0, ge=0)


class BookingResponse(BaseModel):
    id: str
    booking_number: str
    user_id: str
    created_by_user_id: str
    booking_type: BookingType
    status: BookingStatus
    booking_source: str  # Computed field: SELF, ADMIN, AGENT
    creator_name: str    # Computed field: Name of who created it
    customer_name: Optional[str] = None  # Computed field: Name of the customer
    start_date: Optional[date]
    end_date: Optional[date]
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    payment_status: PaymentStatus
    membership_id: Optional[str] = None
    title_ar: Optional[str]
    title_en: Optional[str]
    guest_count: int
    guest_names: Optional[List[str]]
    customer_notes: Optional[str]
    confirmation_number: Optional[str]
    items: List[BookingItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    id: str
    booking_number: str
    booking_type: BookingType
    status: BookingStatus
    booking_source: str  # SELF, ADMIN, AGENT
    creator_name: str
    customer_name: Optional[str] = None
    title_en: Optional[str]
    title_ar: Optional[str]
    total_amount: float
    currency: str
    payment_status: PaymentStatus
    membership_id: Optional[str] = None  # User's friendly ID (ALT-...)
    start_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    reason: Optional[str] = None


# ============ Query Filters ============
class BookingSourceFilter(str, Enum):
    ALL = "all"
    SELF = "self"
    ADMIN = "admin"
    AGENT = "agent"


# ============ Manual Booking Creation (Simplified) ============
class ManualBookingCreate(BaseModel):
    """Simplified schema for manual booking creation from admin/employee dashboard"""
    user_id: str
    booking_type: str  # TRIP, HOTEL, OFFER, CUSTOM
    destination: str  # Destination or service name
    start_date: date
    end_date: date
    num_persons: int = Field(default=1, ge=1)
    notes: Optional[str] = None
    original_price: float = Field(..., gt=0)
    discount: float = Field(default=0, ge=0)
    payment_status: str = "UNPAID"  # PAID, UNPAID, PARTIAL
    payment_method: str = "CASH"  # CASH, CARD, WALLET (NOT POINTS)
    currency: str = "USD"  # USD, EUR, SAR, EGP
    wallet_to_use: float = Field(default=0, ge=0)
    
    # Points as separate admin action (NOT payment)
    points_reason: Optional[str] = None


class InitiatePaymentRequest(BaseModel):
    payment_method_id: int = 1

