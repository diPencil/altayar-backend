from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class PaymentType(str, enum.Enum):
    BOOKING = "BOOKING"
    MEMBERSHIP_PURCHASE = "MEMBERSHIP_PURCHASE"
    MEMBERSHIP_RENEWAL = "MEMBERSHIP_RENEWAL"
    WALLET_DEPOSIT = "WALLET_DEPOSIT"
    ORDER = "ORDER"
    MANUAL = "MANUAL"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    WALLET = "WALLET"
    BANK_TRANSFER = "BANK_TRANSFER"
    CASH = "CASH"
    FAWRY = "FAWRY"
    MEEZA = "MEEZA"
    VODAFONE_CASH = "VODAFONE_CASH"
    MIXED = "MIXED"
    OTHER = "OTHER"


class PaymentProvider(str, enum.Enum):
    FAWATERK = "FAWATERK"
    STRIPE = "STRIPE"
    MANUAL = "MANUAL"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"
    
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    
    # Link to different entities
    booking_id = Column(UUID(), ForeignKey('bookings.id'), nullable=True, index=True)
    order_id = Column(UUID(), ForeignKey('orders.id'), nullable=True, index=True)
    subscription_id = Column(UUID(), nullable=True, index=True)
    
    payment_type = Column(SQLEnum(PaymentType), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    
    provider = Column(SQLEnum(PaymentProvider), default=PaymentProvider.FAWATERK, nullable=False, index=True)
    provider_transaction_id = Column(String(255), nullable=True, index=True)
    provider_invoice_id = Column(String(255), nullable=True, index=True)
    provider_reference_id = Column(String(255), nullable=True, index=True)
    
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    payment_details = Column(JSON, nullable=True)
    webhook_payload = Column(JSON, nullable=True)
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)
    webhook_event_id = Column(String(255), nullable=True, index=True)
    
    # Idempotency
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    
    # Refund tracking
    refund_amount = Column(Float, default=0.00)
    refund_reason = Column(Text, nullable=True)
    refund_requested_at = Column(DateTime(timezone=True), nullable=True)
    refund_processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    error_message = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    user = relationship("User", foreign_keys=[user_id])
    booking = relationship("Booking", foreign_keys=[booking_id])
    
    def __repr__(self):
        return f"<Payment {self.payment_number} {self.status}>"


class PaymentWebhookLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payment_webhook_logs"
    
    provider = Column(String(50), default="FAWATERK", nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # PAID, FAILED, EXPIRED
    
    # Fawaterk specific fields
    invoice_id = Column(String(255), nullable=True, index=True)
    invoice_key = Column(String(255), nullable=True)
    reference_id = Column(String(255), nullable=True, index=True)
    
    # Payload and validation
    raw_payload = Column(JSON, nullable=False)
    hash_received = Column(String(255), nullable=True)
    hash_computed = Column(String(255), nullable=True)
    is_valid = Column(Boolean, default=False, nullable=False)
    
    # Processing
    payment_id = Column(UUID(), ForeignKey('payments.id'), nullable=True, index=True)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<PaymentWebhookLog {self.provider} {self.event_type} processed={self.processed}>"


class UserCard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_cards"
    
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    
    # Tokenization details
    provider = Column(String(50), default="FAWATERK", nullable=False)
    provider_token = Column(String(255), nullable=False, index=True) # The secure token
    card_mask = Column(String(255), nullable=False) # e.g. "xxxx-xxxx-xxxx-1234"
    
    # Display details
    last4 = Column(String(4), nullable=False)
    brand = Column(String(50), nullable=True) # visa, mastercard
    expiry_month = Column(String(2), nullable=True)
    expiry_year = Column(String(4), nullable=True)
    holder_name = Column(String(255), nullable=True)
    
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", backref="saved_cards")

    def __repr__(self):
        return f"<UserCard {self.last4} {self.provider}>"
