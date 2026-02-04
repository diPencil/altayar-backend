from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ClubGiftStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CREDITED = "CREDITED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PENDING_WITHDRAWAL = "PENDING_WITHDRAWAL" # Added missing status

# Alias for backward compatibility
CashbackStatus = ClubGiftStatus


class ClubGiftRecordResponse(BaseModel):
    id: str
    user_id: str
    reference_type: str
    reference_id: str
    booking_amount: float
    cashback_rate: float
    cashback_amount: float
    currency: str
    status: ClubGiftStatus
    approved_at: Optional[datetime]
    credited_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    description: Optional[str] = None  # Computed field for frontend display

    class Config:
        from_attributes = True

# Alias for backward compatibility
CashbackRecordResponse = ClubGiftRecordResponse


class CreateClubGiftRequest(BaseModel):
    user_id: str
    reference_type: str  # BOOKING, ORDER
    reference_id: str
    booking_amount: float = Field(..., gt=0)
    cashback_rate: float = Field(..., ge=0, le=100)

# Alias for backward compatibility
CreateCashbackRequest = CreateClubGiftRequest


class WithdrawalRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw")
