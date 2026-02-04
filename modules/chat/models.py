from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin


class ConversationStatus(str, enum.Enum):
    OPEN = "OPEN"
    WAITING = "WAITING"
    ASSIGNED = "ASSIGNED"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"


class MessageType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    OFFER = "OFFER"  # Special message type for offers
    SYSTEM = "SYSTEM"  # System messages like assignment notifications


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"
    
    # Customer
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Assigned Employee (Sales)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)  # Admin who assigned
    
    # Status
    status = Column(SQLEnum(ConversationStatus), nullable=False, default=ConversationStatus.OPEN, index=True)
    is_bot_active = Column(Boolean, default=True)
    
    # Subject/Topic
    subject = Column(String(255), nullable=True)
    
    # Last message tracking
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_preview = Column(String(100), nullable=True)
    
    # Unread counts
    customer_unread_count = Column(Integer, default=0)
    employee_unread_count = Column(Integer, default=0)
    
    # Closed info
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by = Column(String(36), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    
    def __repr__(self):
        return f"<Conversation {self.id}>"


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"
    
    # Conversation
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    
    # Sender
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # CUSTOMER, EMPLOYEE, ADMIN, SYSTEM
    
    # Content
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    content = Column(Text, nullable=False)
    
    # For file/image messages
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # For offer messages
    offer_id = Column(String(36), ForeignKey("offers.id"), nullable=True)
    
    # Read status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.id}>"
