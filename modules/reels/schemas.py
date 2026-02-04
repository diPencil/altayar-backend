from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from modules.reels.models import ReelStatus, InteractionType

# Reel Schemas
class ReelBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None  # Optional - can be URL or will be set after file upload
    video_type: Optional[str] = 'URL'  # 'URL', 'UPLOAD', 'YOUTUBE'
    thumbnail_url: Optional[str] = None
    status: ReelStatus = ReelStatus.DRAFT

class ReelCreate(ReelBase):
    pass

class ReelUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    video_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[ReelStatus] = None

class UserInfo(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None
    is_following: bool = False

class ReelResponse(ReelBase):
    id: str
    video_url: str  # Required in response - always has a value
    video_type: str
    views_count: int
    likes_count: int
    comments_count: int
    shares_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # User specific fields (to be populated manually)
    is_liked: bool = False
    user: Optional[UserInfo] = None  # User who created the reel

    class Config:
        from_attributes = True

# Interaction Schemas
class InteractionCreate(BaseModel):
    type: InteractionType
    content: Optional[str] = None # For comments

class InteractionResponse(BaseModel):
    id: str
    reel_id: str
    user_id: Optional[str]
    type: InteractionType
    content: Optional[str]
    parent_id: Optional[str] = None  # For replies
    likes_count: int = 0  # For comment likes
    created_at: datetime
    
    # User details for comments
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    reel_title: Optional[str] = None  # For admin comment management

    class Config:
        from_attributes = True
