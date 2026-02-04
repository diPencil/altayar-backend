from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    CASHBACK = "CASHBACK"
    BONUS = "BONUS"
    COMMISSION = "COMMISSION"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    DEDUCTION = "DEDUCTION"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class Wallet(Base, UUIDMixin, TimestampMixin):
    """User wallet - one per user"""
    __tablename__ = "wallets"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    balance = Column(Float, default=0.00, nullable=False)
    currency = Column(String(3), default="USD")
    is_active = Column(String(1), default="Y")
    
    # Relationships
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Wallet user={self.user_id} balance={self.balance}>"


class WalletTransaction(Base, UUIDMixin, TimestampMixin):
    """Wallet transaction ledger"""
    __tablename__ = "wallet_transactions"
    
    wallet_id = Column(UUID(), ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey('users.id'), nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    reference_type = Column(String(50), nullable=True, index=True)  # BOOKING, ORDER, CASHBACK, etc.
    reference_id = Column(UUID(), nullable=True, index=True)
    description_ar = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    transaction_metadata = Column(JSON, nullable=True)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.COMPLETED, index=True)
    created_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=True)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    
    def __repr__(self):
        return f"<WalletTransaction {self.transaction_type} {self.amount}>"
