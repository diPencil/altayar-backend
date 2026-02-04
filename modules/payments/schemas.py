from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CreatePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="EGP")
    customer_first_name: str
    customer_last_name: Optional[str] = None
    customer_email: str
    customer_phone: Optional[str] = None
    description: str
    booking_id: Optional[str] = None
    order_id: Optional[str] = None
    payment_method_id: int = Field(default=1, description="1=Card, 2=Fawry, 3=Wallet, 4=Vodafone Cash")
    save_card: bool = Field(default=False, description="Whether to save the card for future use")


class CreatePaymentResponse(BaseModel):
    payment_id: str
    payment_number: str
    amount: float
    currency: str
    status: str
    payment_url: str
    invoice_id: Optional[str] = None
    invoice_key: Optional[str] = None
    fawry_code: Optional[str] = None
    qr_code_url: Optional[str] = None
    expires_at: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    payment_id: str
    payment_number: str
    status: str
    amount: float
    currency: str
    paid_at: Optional[datetime] = None

class UserCardResponse(BaseModel):
    id: str
    last4: str
    brand: Optional[str] = None
    expiry_month: Optional[str] = None
    expiry_year: Optional[str] = None
    holder_name: Optional[str] = None
    is_default: bool
    created_at: Optional[datetime] = None


class InitCardTokenResponse(BaseModel):
    url: str
    invoice_key: Optional[str] = None
