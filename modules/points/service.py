from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date, timedelta
import uuid
import logging

from modules.points.models import PointsBalance, PointsTransaction, PointsTransactionType
from shared.exceptions import BadRequestException

logger = logging.getLogger(__name__)

from modules.notifications.service import NotificationService
from modules.users.models import User


class PointsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_balance(self, user_id: str) -> PointsBalance:
        """Get points balance for user, create if not exists"""
        balance = self.db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
        
        if not balance:
            balance = PointsBalance(
                id=str(uuid.uuid4()),
                user_id=user_id,
                total_earned=0,
                total_redeemed=0,
                total_expired=0,
                current_balance=0
            )
            self.db.add(balance)
            self.db.commit()
            self.db.refresh(balance)
            logger.info(f"✅ Points balance created for user {user_id}")
        
        return balance
    
    def get_balance(self, user_id: str) -> int:
        """Get current points balance"""
        balance = self.get_or_create_balance(user_id)
        return balance.current_balance
    
    def earn_points(
        self,
        user_id: str,
        points: int,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None,
        multiplier: float = 1.0,
        expires_in_days: int = 365
    ) -> PointsTransaction:
        """Add points to user's balance"""
        if points <= 0:
            raise BadRequestException("Points must be positive")
        
        # Apply multiplier
        actual_points = int(points * multiplier)
        
        balance = self.get_or_create_balance(user_id)
        balance_before = balance.current_balance
        balance_after = balance_before + actual_points
        
        # Update balance
        balance.current_balance = balance_after
        balance.total_earned += actual_points
        
        # Create transaction
        transaction = PointsTransaction(
            id=str(uuid.uuid4()),
            balance_id=balance.id,
            user_id=user_id,
            transaction_type=PointsTransactionType.EARNED,
            points=actual_points,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or f"Earned {actual_points} points",
            description_ar=description_ar or f"تم كسب {actual_points} نقطة",
            multiplier_applied=multiplier,
            expires_at=date.today() + timedelta(days=expires_in_days)
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ User {user_id} earned {actual_points} points (x{multiplier})")
        
        logger.info(f"✅ User {user_id} earned {actual_points} points (x{multiplier})")
        
        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_points_change(
                    user=user, 
                    points=actual_points, 
                    type="EARNED",
                    reason=description_en
                )
        except Exception as e:
            logger.error(f"Failed to send points notification: {e}")

        return transaction
    
    def redeem_points(
        self,
        user_id: str,
        points: int,
        reference_type: str,
        reference_id: str,
        description_en: str = None,
        description_ar: str = None
    ) -> PointsTransaction:
        """Redeem points from user's balance"""
        if points <= 0:
            raise BadRequestException("Points must be positive")
        
        balance = self.get_or_create_balance(user_id)
        
        if balance.current_balance < points:
            raise BadRequestException(
                f"Insufficient points. Current: {balance.current_balance}, Required: {points}"
            )
        
        balance_before = balance.current_balance
        balance_after = balance_before - points
        
        # Update balance
        balance.current_balance = balance_after
        balance.total_redeemed += points
        
        # Create transaction
        transaction = PointsTransaction(
            id=str(uuid.uuid4()),
            balance_id=balance.id,
            user_id=user_id,
            transaction_type=PointsTransactionType.REDEEMED,
            points=-points,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            description_en=description_en or f"Redeemed {points} points",
            description_ar=description_ar or f"تم استبدال {points} نقطة",
            multiplier_applied=1.0
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ User {user_id} redeemed {points} points")
        
        logger.info(f"✅ User {user_id} redeemed {points} points")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_points_change(
                    user=user, 
                    points=points, 
                    type="REDEEMED",
                    reason=description_en
                )
        except Exception as e:
            logger.error(f"Failed to send points notification: {e}")
        
        return transaction
    
    def add_bonus_points(
        self,
        user_id: str,
        points: int,
        description_en: str = None,
        description_ar: str = None,
        created_by_user_id: str = None
    ) -> PointsTransaction:
        """Add bonus points (admin)"""
        balance = self.get_or_create_balance(user_id)
        balance_before = balance.current_balance
        balance_after = balance_before + points
        
        balance.current_balance = balance_after
        balance.total_earned += points
        
        transaction = PointsTransaction(
            id=str(uuid.uuid4()),
            balance_id=balance.id,
            user_id=user_id,
            transaction_type=PointsTransactionType.BONUS,
            points=points,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type="BONUS",
            description_en=description_en or "Bonus points",
            description_ar=description_ar or "نقاط مكافأة",
            multiplier_applied=1.0,
            expires_at=date.today() + timedelta(days=365),
            created_by_user_id=created_by_user_id
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"✅ User {user_id} received {points} bonus points")
        
        logger.info(f"✅ User {user_id} received {points} bonus points")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_points_change(
                    user=user, 
                    points=points, 
                    type="EARNED",
                    reason=description_en or "Bonus Points"
                )
        except Exception as e:
            logger.error(f"Failed to send points notification: {e}")
        
        return transaction
    
    def deduct_points(
        self,
        user_id: str,
        points: int,
        description_en: str = None,
        description_ar: str = None,
        created_by_user_id: str = None
    ) -> PointsTransaction:
        """Deduct points from user's balance (admin adjustment)"""
        if points <= 0:
            raise BadRequestException("Points to deduct must be positive")

        balance = self.get_or_create_balance(user_id)

        if balance.current_balance < points:
            raise BadRequestException(
                f"Insufficient points. Current: {balance.current_balance}, Required: {points}"
            )

        balance_before = balance.current_balance
        balance_after = balance_before - points

        # Update balance
        balance.current_balance = balance_after
        balance.total_redeemed += points

        # Create transaction
        transaction = PointsTransaction(
            id=str(uuid.uuid4()),
            balance_id=balance.id,
            user_id=user_id,
            transaction_type=PointsTransactionType.ADJUSTED,
            points=-points,  # Negative for deduction
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type="ADMIN_ADJUSTMENT",
            description_en=description_en or f"Points deducted: {points}",
            description_ar=description_ar or f"تم خصم النقاط: {points}",
            multiplier_applied=1.0,
            created_by_user_id=created_by_user_id
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        logger.info(f"✅ User {user_id} had {points} points deducted by admin {created_by_user_id}")

        logger.info(f"✅ User {user_id} had {points} points deducted by admin {created_by_user_id}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_points_change(
                    user=user, 
                    points=points, 
                    type="REDEEMED", # Treated as removal/redemption logic
                    reason=description_en or "Admin Deduction"
                )
        except Exception as e:
            logger.error(f"Failed to send points notification: {e}")

        return transaction

    def get_transactions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[PointsTransaction]:
        """Get points transactions for user"""
        balance = self.get_or_create_balance(user_id)

        transactions = self.db.query(PointsTransaction).filter(
            PointsTransaction.balance_id == balance.id
        ).order_by(PointsTransaction.created_at.desc()).offset(offset).limit(limit).all()

        return transactions
