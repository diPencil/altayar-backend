from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ConversationStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"


class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    OFFER = "OFFER"
    SYSTEM = "SYSTEM"


# ============ Messages ============
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = MessageType.TEXT
    offer_id: Optional[str] = None  # For sending offers


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    sender_role: str
    message_type: str
    content: str
    file_url: Optional[str]
    file_name: Optional[str]
    offer_id: Optional[str]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Conversations ============
class StartConversationRequest(BaseModel):
    subject: Optional[str] = None
    initial_message: str = Field(..., min_length=1, max_length=5000)


class ConversationResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    customer_avatar: Optional[str] = None
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    status: str
    subject: Optional[str]
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    customer_unread_count: int
    employee_unread_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse]


# ============ Admin Actions ============
class AssignConversationRequest(BaseModel):
    employee_id: str


class CloseConversationRequest(BaseModel):
    resolution_notes: Optional[str] = None
