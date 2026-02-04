from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class OrderType(str, enum.Enum):
    SERVICE = "SERVICE"
    MANUAL_INVOICE = "MANUAL_INVOICE"
    EXTRA = "EXTRA"
    CUSTOM_FEE = "CUSTOM_FEE"
    OTHER = "OTHER"


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"
    
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    created_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    order_type = Column(SQLEnum(OrderType), default=OrderType.MANUAL_INVOICE, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT, nullable=False, index=True)
    
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.00)
    discount_amount = Column(Float, default=0.00)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    notes_ar = Column(Text, nullable=True)
    notes_en = Column(Text, nullable=True)
    
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False, index=True)
    due_date = Column(Date, nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    is_free = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    user = relationship("User", backref="orders", foreign_keys=[user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    
    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "order_items"
    
    order_id = Column(UUID(), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    description_ar = Column(String(255), nullable=False)
    description_en = Column(String(255), nullable=False)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    item_metadata = Column(JSON, nullable=True)  # Renamed from metadata to avoid conflicts
    
    # Relationships
    order = relationship("Order", back_populates="items")
    
    def __repr__(self):
        return f"<OrderItem {self.description_en}>"
