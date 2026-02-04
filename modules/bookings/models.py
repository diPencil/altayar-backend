from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin, UUID


class BookingType(str, enum.Enum):
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


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    NO_SHOW = "NO_SHOW"


class BookingSource(str, enum.Enum):
    """Who created the booking"""
    SELF = "SELF"        # Customer booked themselves
    ADMIN = "ADMIN"      # Admin/employee created for customer
    AGENT = "AGENT"      # Agent created for their client


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Booking(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bookings"
    
    booking_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)  # The customer
    created_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)  # Who created it
    offer_id = Column(String(36), nullable=True, index=True)  # FK to offers.id (if booked from offer)
    
    booking_type = Column(SQLEnum(BookingType), nullable=False, index=True)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)
    
    # Dates
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Pricing
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.00)
    discount_amount = Column(Float, default=0.00)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Payment
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False, index=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Details
    title_ar = Column(String(255), nullable=True)
    title_en = Column(String(255), nullable=True)
    description_ar = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    booking_details = Column(JSON, nullable=True)  # Flexible storage for booking-specific data
    
    # Guest info
    guest_count = Column(Integer, default=1)
    guest_names = Column(JSON, nullable=True)  # List of guest names
    
    # Notes
    internal_notes = Column(Text, nullable=True)  # Admin notes
    customer_notes = Column(Text, nullable=True)  # Customer special requests
    
    # Confirmation
    confirmation_number = Column(String(100), nullable=True)  # External reference
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")
    status_history = relationship("BookingStatusHistory", back_populates="booking", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Booking {self.booking_number}>"
    
    @property
    def booking_source(self) -> str:
        """
        Compute booking source based on who created it.
        
        Logic:
        - If user_id == created_by_user_id: SELF (customer booked themselves)
        - If creator is ADMIN/EMPLOYEE: ADMIN
        - If creator is AGENT: AGENT
        """
        if str(self.user_id) == str(self.created_by_user_id):
            return BookingSource.SELF.value
        # The actual role check happens at the API level
        return BookingSource.ADMIN.value  # Default, will be computed properly in API


class BookingItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "booking_items"
    
    booking_id = Column(UUID(), ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)  # room, flight_segment, etc.
    description_ar = Column(String(255), nullable=False)
    description_en = Column(String(255), nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    item_details = Column(JSON, nullable=True)  # Room type, flight details, etc.
    
    # Relationships
    booking = relationship("Booking", back_populates="items")
    
    def __repr__(self):
        return f"<BookingItem {self.description_en}>"


class BookingStatusHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "booking_status_history"
    
    booking_id = Column(UUID(), ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    old_status = Column(SQLEnum(BookingStatus), nullable=True)
    new_status = Column(SQLEnum(BookingStatus), nullable=False)
    changed_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="status_history")
    
    def __repr__(self):
        return f"<BookingStatusHistory {self.old_status} -> {self.new_status}>"
