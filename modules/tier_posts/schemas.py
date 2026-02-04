from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TierPostCreate(BaseModel):
    tier_code: str
    content: str
    image_url: Optional[str] = None


class TierPostResponse(BaseModel):
    id: str
    user_id: str
    tier_code: str
    content: str
    image_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    # User info
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_avatar: Optional[str] = None
    
    # Counts
    likes_count: int = 0
    comments_count: int = 0
    is_liked_by_current_user: bool = False
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    user_id: str
    post_id: str
    content: str
    status: str
    created_at: datetime
    
    # User info
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_avatar: Optional[str] = None
    
    class Config:
        from_attributes = True
