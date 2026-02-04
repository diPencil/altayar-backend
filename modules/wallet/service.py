from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from datetime import datetime
import uuid
import logging

from modules.wallet.models import Wallet, WalletTransaction, TransactionType, TransactionStatus
from modules.users.models import User
from shared.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)

from modules.notifications.service import NotificationService


class WalletService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_wallet(self, user_id: str) -> Wallet:
        """Get wallet for user, create if not exists"""
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if wallet:
            # Lazy migration: If wallet exists but is EGP and empty, move to USD
            if wallet.currency != "USD" and wallet.balance == 0:
                wallet.currency = "USD"
                self.db.add(wallet)
                self.db.commit()
                self.db.refresh(wallet)
        
        if not wallet:
            wallet = Wallet(
                id=str(uuid.uuid4()),
                user_id=user_id,
                balance=0.00,
                currency="USD",
                is_active="Y"
            )
            self.db.add(wallet)
            self.db.commit()
            self.db.refresh(wallet)
            logger.info(f"✅ Wallet created for user {user_id}")
        
        return wallet
    
    def get_balance(self, user_id: str) -> float:
        """Get wallet balance for user"""
        wallet = self.get_or_create_wallet(user_id)
        return wallet.balance
    
    def deposit(
        self,
        user_id: str,
        amount: float,
        description_en: str = None,
        description_ar: str = None,
        reference_type: str = None,
        reference_id: str = None,
        created_by_user_id: str = None
    ) -> WalletTransaction:
        """Add funds to wallet"""
        if amount <= 0:
            raise BadRequestException("Amount must be positive")
        
        wallet = self.get_or_create_wallet(user_id)
        balance_before = wallet.balance
        balance_after = balance_before + amount
        
        # Update wallet balance
        wallet.balance = balance_after
        
        # Create transaction record
        transaction = WalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or "Wallet deposit",
            description_ar=description_ar or "إيداع في المحفظة",
            status=TransactionStatus.COMPLETED,
            created_by_user_id=created_by_user_id
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ Deposit {amount} to wallet for user {user_id}. New balance: {balance_after}")
        
        logger.info(f"✅ Deposit {amount} to wallet for user {user_id}. New balance: {balance_after}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_wallet_change(
                    user=user,
                    amount=amount,
                    type="DEPOSIT",
                    currency=wallet.currency
                )
        except Exception as e:
            logger.error(f"Failed to send wallet notification: {e}")
        
        return transaction
    
    def withdraw(
        self,
        user_id: str,
        amount: float,
        description_en: str = None,
        description_ar: str = None,
        reference_type: str = None,
        reference_id: str = None,
        created_by_user_id: str = None
    ) -> WalletTransaction:
        """Withdraw funds from wallet"""
        if amount <= 0:
            raise BadRequestException("Amount must be positive")
        
        wallet = self.get_or_create_wallet(user_id)
        
        if wallet.balance < amount:
            raise BadRequestException(f"Insufficient balance. Current: {wallet.balance}, Required: {amount}")
        
        balance_before = wallet.balance
        balance_after = balance_before - amount
        
        # Update wallet balance
        wallet.balance = balance_after
        
        # Create transaction record
        transaction = WalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=-amount,  # Negative for withdrawals
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or "Wallet withdrawal",
            description_ar=description_ar or "سحب من المحفظة",
            status=TransactionStatus.COMPLETED,
            created_by_user_id=created_by_user_id
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ Withdrawal {amount} from wallet for user {user_id}. New balance: {balance_after}")

        logger.info(f"✅ Withdrawal {amount} from wallet for user {user_id}. New balance: {balance_after}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_wallet_change(
                    user=user,
                    amount=amount,
                    type="WITHDRAWAL",
                    currency=wallet.currency
                )
        except Exception as e:
            logger.error(f"Failed to send wallet notification: {e}")

        return transaction

    def deduct_funds(
        self,
        user_id: str,
        amount: float,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None,
        created_by_user_id: str = None
    ) -> WalletTransaction:
        """Deduct funds from wallet (for admin actions, penalties, etc.)"""
        if amount <= 0:
            raise BadRequestException("Amount must be positive")

        wallet = self.get_or_create_wallet(user_id)

        if wallet.balance < amount:
            raise BadRequestException(f"Insufficient balance. Current: {wallet.balance}, Required: {amount}")

        balance_before = wallet.balance
        balance_after = balance_before - amount

        # Update wallet balance
        wallet.balance = balance_after

        # Create transaction record
        transaction = WalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=TransactionType.DEDUCTION,  # Assuming this exists
            amount=-amount,  # Negative for deductions
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or "Funds deduction",
            description_ar=description_ar or "خصم من المحفظة",
            status=TransactionStatus.COMPLETED,
            created_by_user_id=created_by_user_id
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        logger.info(f"✅ Deducted {amount} from wallet for user {user_id}. New balance: {balance_after}")

        logger.info(f"✅ Deducted {amount} from wallet for user {user_id}. New balance: {balance_after}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_wallet_change(
                    user=user,
                    amount=amount,
                    type="WITHDRAWAL", # Treated as withdrawal/deduction
                    currency=wallet.currency
                )
        except Exception as e:
            logger.error(f"Failed to send wallet notification: {e}")

        return transaction
    
    def pay_from_wallet(
        self,
        user_id: str,
        amount: float,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None
    ) -> WalletTransaction:
        """Pay for booking/order from wallet"""
        return self.withdraw(
            user_id=user_id,
            amount=amount,
            description_en=description_en or f"Payment for {reference_type}",
            description_ar=description_ar or f"دفع لـ {reference_type}",
            reference_type=reference_type,
            reference_id=reference_id
        )
    
    def add_cashback(
        self,
        user_id: str,
        amount: float,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None
    ) -> WalletTransaction:
        """Add cashback to wallet"""
        wallet = self.get_or_create_wallet(user_id)
        balance_before = wallet.balance
        balance_after = balance_before + amount
        
        wallet.balance = balance_after
        
        transaction = WalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=TransactionType.CASHBACK,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or "Cashback reward",
            description_ar=description_ar or "مكافأة كاش باك",
            status=TransactionStatus.COMPLETED
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ Cashback {amount} added to wallet for user {user_id}")
        
        return transaction
    
    def refund_to_wallet(
        self,
        user_id: str,
        amount: float,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None
    ) -> WalletTransaction:
        """Refund amount to wallet"""
        wallet = self.get_or_create_wallet(user_id)
        balance_before = wallet.balance
        balance_after = balance_before + amount
        
        wallet.balance = balance_after
        
        transaction = WalletTransaction(
            id=str(uuid.uuid4()),
            wallet_id=wallet.id,
            user_id=user_id,
            transaction_type=TransactionType.REFUND,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or "Refund",
            description_ar=description_ar or "استرداد",
            status=TransactionStatus.COMPLETED
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ Refund {amount} to wallet for user {user_id}")
        
        return transaction
    
    def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[WalletTransaction]:
        """Get wallet transactions for user"""
        wallet = self.get_or_create_wallet(user_id)
        
        transactions = self.db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == wallet.id
        ).order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit).all()
        
        return transactions
