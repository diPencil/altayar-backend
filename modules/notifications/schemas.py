from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType

class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    reel_id: Optional[str] = None
    comment_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_avatar: Optional[str] = None
    is_read: bool
    created_at: datetime
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[NotificationEntityType] = None
    action_url: Optional[str] = None
    read_at: Optional[datetime] = None
    priority: Optional[str] = "NORMAL"
    target_role: Optional[str] = None
    target_user_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    triggered_by_id: Optional[str] = None
    triggered_by_role: Optional[str] = None
    
    class Config:
        from_attributes = True
        # Include None values in serialization
        exclude_none = False

class NotificationCreate(BaseModel):
    target_role: NotificationTargetRole
    target_user_id: Optional[str] = None
    type: NotificationType
    title: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[NotificationEntityType] = None
    priority: Optional[str] = "NORMAL"
    action_url: Optional[str] = None
    triggered_by_id: Optional[str] = None
    triggered_by_role: Optional[str] = None

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class NotificationStats(BaseModel):
    total: int
    unread: int

class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]  # Changed from 'items' to 'notifications'
    total: int  # Changed from 'total_count' to 'total'
    unread_count: int

class NotificationSettingsBase(BaseModel):
    push_notifications: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    booking_updates: bool = True
    payment_alerts: bool = True
    chat_messages: bool = True
    promotions: bool = True
    new_offers: bool = True
    price_drops: bool = False

class NotificationSettingsUpdate(NotificationSettingsBase):
    pass

class NotificationSettingsResponse(NotificationSettingsBase):
    id: str
    user_id: str
    
    class Config:
        from_attributes = True

class PushTokenUpdate(BaseModel):
    token: str
