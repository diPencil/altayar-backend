from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.base import Base

class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    usage_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="referral_code_obj")

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = Column(String, ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, ACTIVE
    points_earned = Column(Integer, default=0)
    plan_id = Column(String, ForeignKey("membership_plans.id"), nullable=True)  # plan they subscribed to when referral completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], backref="referrals_made")
    referred_user = relationship("User", foreign_keys=[referred_user_id], backref="referred_by")
    plan = relationship("MembershipPlan", foreign_keys=[plan_id])
