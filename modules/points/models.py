from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class PointsTransactionType(str, enum.Enum):
    EARNED = "EARNED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"
    BONUS = "BONUS"
    ADJUSTED = "ADJUSTED"
    TRANSFERRED = "TRANSFERRED"


class PointsBalance(Base, UUIDMixin, TimestampMixin):
    """User's points balance - one per user"""
    __tablename__ = "points_balances"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    total_earned = Column(Integer, default=0)
    total_redeemed = Column(Integer, default=0)
    total_expired = Column(Integer, default=0)
    current_balance = Column(Integer, default=0)
    
    # Relationships
    transactions = relationship("PointsTransaction", back_populates="balance_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PointsBalance user={self.user_id} balance={self.current_balance}>"


class PointsTransaction(Base, UUIDMixin, TimestampMixin):
    """Points transaction ledger"""
    __tablename__ = "points_transactions"
    
    balance_id = Column(UUID(), ForeignKey('points_balances.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    transaction_type = Column(SQLEnum(PointsTransactionType), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reference_type = Column(String(50), nullable=True, index=True)  # BOOKING, ORDER, BONUS
    reference_id = Column(UUID(), nullable=True, index=True)
    description_ar = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    multiplier_applied = Column(Float, default=1.00)
    expires_at = Column(Date, nullable=True, index=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=True)
    
    # Relationships
    balance_record = relationship("PointsBalance", back_populates="transactions")
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<PointsTransaction {self.transaction_type} {self.points}>"
