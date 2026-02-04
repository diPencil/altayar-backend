from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class PointsTransactionType(str, Enum):
    EARNED = "EARNED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"
    BONUS = "BONUS"
    ADJUSTED = "ADJUSTED"


class PointsBalanceResponse(BaseModel):
    id: str
    user_id: str
    total_earned: int
    total_redeemed: int
    total_expired: int
    current_balance: int

    class Config:
        from_attributes = True


class PointsTransactionResponse(BaseModel):
    id: str
    transaction_type: PointsTransactionType
    points: int
    balance_before: int
    balance_after: int
    reference_type: Optional[str]
    reference_id: Optional[str]
    description_en: Optional[str]
    description_ar: Optional[str]
    multiplier_applied: float
    expires_at: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


class EarnPointsRequest(BaseModel):
    points: int = Field(..., gt=0)
    reference_type: str
    reference_id: str
    description_en: Optional[str] = None
    multiplier: float = Field(default=1.0, ge=1.0)


class RedeemPointsRequest(BaseModel):
    points: int = Field(..., gt=0)
    reference_type: str
    reference_id: str
    description_en: Optional[str] = None
