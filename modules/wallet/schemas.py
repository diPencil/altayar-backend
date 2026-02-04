from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    CASHBACK = "CASHBACK"
    BONUS = "BONUS"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class WalletResponse(BaseModel):
    id: str
    user_id: str
    balance: float
    currency: str
    is_active: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    id: str
    transaction_type: TransactionType
    amount: float
    balance_before: float
    balance_after: float
    currency: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    description_en: Optional[str]
    description_ar: Optional[str]
    status: TransactionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description_en: Optional[str] = None
    description_ar: Optional[str] = None


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description_en: Optional[str] = None
    description_ar: Optional[str] = None


class PayFromWalletRequest(BaseModel):
    amount: float = Field(..., gt=0)
    reference_type: str  # BOOKING, ORDER
    reference_id: str
