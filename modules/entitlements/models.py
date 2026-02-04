from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin


class EntitlementType(str, enum.Enum):
    BOOLEAN = "BOOLEAN"
    QUOTA = "QUOTA"
    DISCOUNT = "DISCOUNT"
    ACCESS = "ACCESS"
    SERVICE = "SERVICE"


class ResetPeriod(str, enum.Enum):
    NEVER = "NEVER"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class MembershipEntitlement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_entitlements"
    
    plan_id = Column(UUID(as_uuid=True), ForeignKey('membership_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    entitlement_code = Column(String(100), unique=True, nullable=False, index=True)
    title_ar = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=False)
    description_ar = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    entitlement_type = Column(SQLEnum(EntitlementType), nullable=False, index=True)
    quota_limit = Column(Integer, nullable=True)
    reset_period = Column(SQLEnum(ResetPeriod), default=ResetPeriod.NEVER)
    discount_percentage = Column(Float, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    icon_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    # Relationships
    plan = relationship("MembershipPlan", back_populates="entitlements")
    user_entitlements = relationship("UserEntitlement", back_populates="entitlement")
    
    def __repr__(self):
        return f"<MembershipEntitlement {self.entitlement_code}>"


class UserEntitlement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_entitlements"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('membership_subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    entitlement_id = Column(UUID(as_uuid=True), ForeignKey('membership_entitlements.id', ondelete='CASCADE'), nullable=False, index=True)
    quota_used = Column(Integer, default=0)
    quota_remaining = Column(Integer, nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    subscription = relationship("MembershipSubscription", back_populates="user_entitlements")
    entitlement = relationship("MembershipEntitlement", back_populates="user_entitlements")
    usage_logs = relationship("EntitlementUsageLog", back_populates="user_entitlement")
    
    def __repr__(self):
        return f"<UserEntitlement user={self.user_id} entitlement={self.entitlement_id}>"


class EntitlementUsageLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "entitlement_usage_log"
    
    user_entitlement_id = Column(UUID(as_uuid=True), ForeignKey('user_entitlements.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    entitlement_code = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    reference_type = Column(String(50), nullable=True, index=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    quantity_used = Column(Integer, default=1)
    notes = Column(String, nullable=True)
    
    # Relationships
    user_entitlement = relationship("UserEntitlement", back_populates="usage_logs")
    
    def __repr__(self):
        return f"<EntitlementUsageLog {self.action}>"