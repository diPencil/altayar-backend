from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class OrderType(str, Enum):
    SERVICE = "SERVICE"
    MANUAL_INVOICE = "MANUAL_INVOICE"
    EXTRA = "EXTRA"
    CUSTOM_FEE = "CUSTOM_FEE"
    OTHER = "OTHER"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"



# User Summary Schema
class OrderUserSummary(BaseModel):
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


# Order Item Schemas
class OrderItemCreate(BaseModel):
    description_ar: str = Field(..., min_length=1, max_length=255)
    description_en: str = Field(..., min_length=1, max_length=255)
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(..., ge=0)


class OrderItemResponse(BaseModel):
    id: str
    description_ar: str
    description_en: str
    quantity: float
    unit_price: float
    total_price: float
    currency: str

    class Config:
        from_attributes = True


# Order Schemas
class OrderCreate(BaseModel):
    user_id: str  # Customer ID (for admin creating orders for customers)
    order_type: OrderType = OrderType.MANUAL_INVOICE
    items: List[OrderItemCreate]
    notes_ar: Optional[str] = None
    notes_en: Optional[str] = None
    due_date: Optional[date] = None
    tax_rate: Optional[float] = Field(default=14.0, ge=0, le=100)
    discount_amount: Optional[float] = Field(default=0, ge=0)
    points_to_use: Optional[int] = Field(default=0, ge=0, description="Points to redeem for discount")
    points_to_use: Optional[int] = Field(default=0, ge=0, description="Points to redeem for discount")
    cashback_to_use: Optional[float] = Field(default=0, ge=0, description="Cashback balance to use")
    wallet_to_use: Optional[float] = Field(default=0, ge=0, description="Wallet balance to use")
    currency: Optional[str] = Field(default="USD", description="Currency code (USD, EGP, SAR, EUR)")
    is_free: Optional[bool] = Field(default=False, description="Mark order as free (no payment required)")
    payment_status: Optional[PaymentStatus] = Field(default=None, description="Explicit payment status (PAID/UNPAID)")


class OrderUpdate(BaseModel):
    user_id: Optional[str] = None
    order_type: Optional[OrderType] = None
    items: Optional[List[OrderItemCreate]] = None
    notes_ar: Optional[str] = None
    notes_en: Optional[str] = None
    due_date: Optional[date] = None
    tax_rate: Optional[float] = Field(default=None, ge=0, le=100)
    discount_amount: Optional[float] = Field(default=None, ge=0)
    points_to_use: Optional[int] = Field(default=0, ge=0)
    wallet_to_use: Optional[float] = Field(default=0, ge=0)
    cashback_to_use: Optional[float] = Field(default=0, ge=0)
    currency: Optional[str] = None
    is_free: Optional[bool] = None
    payment_status: Optional[PaymentStatus] = None



class OrderResponse(BaseModel):
    id: str
    order_number: str
    user_id: str
    created_by_user_id: str
    order_type: OrderType
    status: OrderStatus
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    notes_ar: Optional[str]
    notes_en: Optional[str]
    payment_status: PaymentStatus
    is_free: bool = False
    due_date: Optional[date]
    issued_at: Optional[datetime]
    paid_at: Optional[datetime]
    items: List[OrderItemResponse] = []
    user: Optional[OrderUserSummary] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    id: str
    order_number: str
    order_type: OrderType
    status: OrderStatus
    total_amount: float
    currency: str
    payment_status: PaymentStatus
    is_free: bool = False
    due_date: Optional[date]
    created_at: datetime
    user: Optional[OrderUserSummary] = None

    class Config:
        from_attributes = True


# Payment Initiation
class InitiatePaymentRequest(BaseModel):
    payment_method_id: int = Field(default=1, description="1=Card, 2=Fawry, etc.")


class InitiatePaymentResponse(BaseModel):
    payment_id: str
    payment_number: str
    order_number: str
    amount: float
    currency: str
    status: str
    payment_url: str
    fawry_code: Optional[str] = None
    expires_at: Optional[str] = None
