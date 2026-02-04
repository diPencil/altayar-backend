from sqlalchemy import Column, String, Boolean, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin

class NotificationType(str, enum.Enum):
    NEW_REEL = "NEW_REEL"  # Admin posted new reel
    COMMENT_REPLY = "COMMENT_REPLY"  # Someone replied to user's comment
    COMMENT_LIKE = "COMMENT_LIKE"  # Someone liked user's comment
    REEL_LIKE = "REEL_LIKE"  # Someone liked user's reel
    REEL_COMMENT = "REEL_COMMENT"  # Someone commented on user's reel (if user is creator)
    BOOKING_CREATED = "BOOKING_CREATED"  # Booking was created
    BOOKING_UPDATED = "BOOKING_UPDATED"  # Booking was updated
    ORDER_CREATED = "ORDER_CREATED"  # Order was created
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"  # Payment was received
    MEMBERSHIP_CHANGED = "MEMBERSHIP_CHANGED"  # Membership changed
    POINTS_EARNED = "POINTS_EARNED"  # Points earned
    USER_POINTS_EARNED = "USER_POINTS_EARNED"  # User points earned (legacy)
    POINTS_REDEEMED = "POINTS_REDEEMED"  # Points redeemed
    CASHBACK_EARNED = "CASHBACK_EARNED"  # Cashback earned
    CASHBACK_REDEEMED = "CASHBACK_REDEEMED"  # Cashback redeemed
    WALLET_DEPOSIT = "WALLET_DEPOSIT"  # Wallet deposit
    WALLET_WITHDRAWAL = "WALLET_WITHDRAWAL"  # Wallet withdrawal
    INVOICE_CREATED = "INVOICE_CREATED"  # Invoice created
    OFFER_CREATED = "OFFER_CREATED"  # New offer created
    CHAT_MESSAGE = "CHAT_MESSAGE"  # New chat message
    USER_LOGIN = "USER_LOGIN"  # User logged in
    USER_LOGOUT = "USER_LOGOUT"  # User logged out
    USER_REGISTERED = "USER_REGISTERED"  # User registered
    TIER_POST_CREATED = "TIER_POST_CREATED"  # User created tier post
    NEW_COMMENT = "NEW_COMMENT"  # User commented on a post
    ADMIN_MESSAGE = "ADMIN_MESSAGE"  # Admin -> Employee message/announcement

class NotificationTargetRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"
    ADMIN = "ADMIN"  # Admin-specific notifications
    ALL = "ALL"

class NotificationEntityType(str, enum.Enum):
    CONVERSATION = "CONVERSATION"
    REEL = "REEL"
    BOOKING = "BOOKING"
    ORDER = "ORDER"
    USER = "USER"  # User-related notifications
    MEMBERSHIP = "MEMBERSHIP"  # Membership-related notifications
    PAYMENT = "PAYMENT"  # Payment-related notifications
    OFFER = "OFFER"  # Offer-related notifications
    TIER_POST = "TIER_POST"  # Tier post-related notifications
    TIER_COMMENT = "TIER_COMMENT"  # Tier comment-related notifications

class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    # Target audience
    target_role = Column(SQLEnum(NotificationTargetRole), nullable=False, index=True)
    target_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Notification content
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entity
    related_entity_id = Column(String(36), nullable=True, index=True)
    related_entity_type = Column(SQLEnum(NotificationEntityType), nullable=True)

    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(String, nullable=True)

    # Additional metadata
    priority = Column(String(20), default="NORMAL")
    action_url = Column(String(500), nullable=True)

    # Trigger info
    triggered_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    triggered_by_role = Column(String(20), nullable=True)

    # Legacy fields removed - they don't exist in the database
    # These were replaced by target_user_id, related_entity_id, and triggered_by_id
    # If you need to migrate, add these columns via Alembic migration first
    
    # Relationships
    target_user = relationship("User", foreign_keys=[target_user_id])
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])

    def __repr__(self):
        return f"<Notification {self.type} for role {self.target_role}>"

class NotificationSettings(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_settings"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Channels
    push_notifications = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)

    # Activity
    booking_updates = Column(Boolean, default=True)
    payment_alerts = Column(Boolean, default=True)
    chat_messages = Column(Boolean, default=True)

    # Marketing
    promotions = Column(Boolean, default=True)
    new_offers = Column(Boolean, default=True)
    price_drops = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<NotificationSettings user_id={self.user_id}>"
