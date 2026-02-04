from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ReferralCodeResponse(BaseModel):
    code: str
    usage_count: int

    class Config:
        from_attributes = True

class ReferralStatsResponse(BaseModel):
    total_referrals: int
    total_points: int
    pending_referrals: int

class ReferralHistoryItem(BaseModel):
    id: str
    referred_user_name: str
    referred_user_avatar: Optional[str] = None
    status: str
    points_earned: int
    created_at: datetime

class ReferralHistoryResponse(BaseModel):
    referrals: List[ReferralHistoryItem]
