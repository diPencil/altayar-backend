from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class ClubGiftStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CREDITED = "CREDITED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PENDING_WITHDRAWAL = "PENDING_WITHDRAWAL"


class ClubGiftRecord(Base, UUIDMixin, TimestampMixin):
    """Club Gift record for bookings/orders"""
    __tablename__ = "cashback_records"  # Keep table name for backward compatibility
    
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    reference_type = Column(String(50), nullable=False, index=True)  # BOOKING, ORDER
    reference_id = Column(UUID(), nullable=False, index=True)
    booking_amount = Column(Float, nullable=False)
    cashback_rate = Column(Float, nullable=False)  # Percentage (e.g., 5.0 for 5%)
    cashback_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(SQLEnum(ClubGiftStatus), default=ClubGiftStatus.PENDING, index=True)
    approved_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    credited_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    wallet_transaction_id = Column(UUID(), nullable=True, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ClubGiftRecord {self.cashback_amount} {self.status}>"
