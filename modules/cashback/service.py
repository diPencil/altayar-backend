from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from modules.cashback.models import ClubGiftRecord, ClubGiftStatus
from modules.wallet.service import WalletService
from shared.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)



from modules.notifications.service import NotificationService
from modules.users.models import User

class ClubGiftService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_club_gift(
        self,
        user_id: str,
        reference_type: str,
        reference_id: str,
        booking_amount: float,
        cashback_rate: float
    ) -> ClubGiftRecord:
        """
        Create a pending Club Gift record.
        Typically called after a booking is confirmed.
        """
        cashback_amount = round(booking_amount * (cashback_rate / 100), 2)
        
        record = ClubGiftRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            reference_type=reference_type,
            reference_id=reference_id,
            booking_amount=booking_amount,
            cashback_rate=cashback_rate,
            cashback_amount=cashback_amount,
            currency="USD",
            status=ClubGiftStatus.PENDING
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"✅ Club Gift record created: {cashback_amount} {record.currency} for user {user_id}")
        
        return record
    
    # Alias for backward compatibility
    def create_cashback(self, *args, **kwargs):
        return self.create_club_gift(*args, **kwargs)
    
    def approve_club_gift(
        self,
        club_gift_id: str,
        approved_by_user_id: str
    ) -> ClubGiftRecord:
        """
        Approve a pending Club Gift record.
        """
        record = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.id == club_gift_id).first()
        
        if not record:
            raise NotFoundException("Club Gift record not found")
        
        if record.status != ClubGiftStatus.PENDING:
            raise BadRequestException(f"Club Gift cannot be approved. Status: {record.status}")
        
        record.status = ClubGiftStatus.APPROVED
        record.approved_by_user_id = approved_by_user_id
        record.approved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"✅ Club Gift approved: {record.cashback_amount} {record.currency}")
        
        return record
    
    # Alias for backward compatibility
    def approve_cashback(self, cashback_id: str, approved_by_user_id: str):
        return self.approve_club_gift(cashback_id, approved_by_user_id)
    
    def credit_club_gift(
        self,
        club_gift_id: str
    ) -> ClubGiftRecord:
        """
        Credit approved Club Gift to user's wallet.
        """
        record = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.id == club_gift_id).first()
        
        if not record:
            raise NotFoundException("Club Gift record not found")
        
        if record.status != ClubGiftStatus.APPROVED:
            raise BadRequestException(f"Club Gift must be approved first. Status: {record.status}")
        
        record.status = ClubGiftStatus.CREDITED
        record.credited_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"✅ Club Gift credited: {record.cashback_amount} {record.currency}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(record.user_id)
            if user:
                notification_service.notify_cashback_change(
                    user=user,
                    amount=record.cashback_amount,
                    type="EARNED",
                    reason=f"Booking Club Gift: {record.reference_id}"
                )
        except Exception as e:
            logger.error(f"Failed to send club gift notification: {e}")
        
        return record
    
    # Alias for backward compatibility
    def credit_cashback(self, cashback_id: str):
        return self.credit_club_gift(cashback_id)
    
    def reject_club_gift(
        self,
        club_gift_id: str,
        reason: str,
        rejected_by_user_id: str
    ) -> ClubGiftRecord:
        """
        Reject a pending Club Gift record.
        """
        record = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.id == club_gift_id).first()
        
        if not record:
            raise NotFoundException("Club Gift record not found")
        
        if record.status not in [ClubGiftStatus.PENDING, ClubGiftStatus.APPROVED]:
            raise BadRequestException(f"Club Gift cannot be rejected. Status: {record.status}")
        
        record.status = ClubGiftStatus.REJECTED
        record.rejection_reason = reason
        record.approved_by_user_id = rejected_by_user_id
        
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"❌ Club Gift rejected: {reason}")
        
        return record
    
    # Alias for backward compatibility
    def reject_cashback(self, cashback_id: str, reason: str, rejected_by_user_id: str):
        return self.reject_club_gift(cashback_id, reason, rejected_by_user_id)
    
    def get_user_club_gifts(
        self,
        user_id: str,
        status: Optional[ClubGiftStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ClubGiftRecord]:
        """
        Get Club Gift records for a user.
        """
        query = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.user_id == user_id)

        if status:
            query = query.filter(ClubGiftRecord.status == status)

        return query.order_by(ClubGiftRecord.created_at.desc()).offset(offset).limit(limit).all()
    
    # Alias for backward compatibility
    def get_user_cashback(self, user_id: str, status=None, limit=50, offset=0):
        return self.get_user_club_gifts(user_id, status, limit, offset)

    @staticmethod
    def _get_club_gift_description_static(record) -> str:
        """Generate human-readable description for Club Gift record"""
        if record.reference_type == "BOOKING":
            return f"Club Gift {record.cashback_rate}% on booking"
        elif record.reference_type == "ORDER":
            return f"Club Gift {record.cashback_rate}% on order"
        elif record.reference_type == "ADMIN_BONUS":
            return "Admin Club Gift bonus"
        elif record.reference_type == "WITHDRAWAL_TO_WALLET":
            return "Club Gift withdrawn to wallet"
        elif record.reference_type == "CLUB_GIFT_WITHDRAWAL_REQUEST":
            return "Withdrawal Request"
        elif record.reference_type == "CLUB_GIFT_WITHDRAWAL":
            return "Club Gift withdrawal"
        elif record.reference_type == "CASHBACK_WITHDRAWAL":  # Legacy support
            return "Club Gift withdrawal"
        else:
            return f"Club Gift {record.cashback_rate}% on {record.reference_type}"
    
    # Alias for backward compatibility
    @staticmethod
    def _get_cashback_description_static(record) -> str:
        return ClubGiftService._get_club_gift_description_static(record)
    
    def get_pending_club_gifts(self, limit: int = 100) -> List[ClubGiftRecord]:
        """
        Get all pending Club Gift records (for admin review).
        """
        return self.db.query(ClubGiftRecord).filter(
            ClubGiftRecord.status == ClubGiftStatus.PENDING
        ).order_by(ClubGiftRecord.created_at.asc()).limit(limit).all()
    
    # Alias for backward compatibility
    def get_pending_cashback(self, limit: int = 100):
        return self.get_pending_club_gifts(limit)

    def admin_add_club_gift(
        self,
        user_id: str,
        amount: float,
        reason: str,
        admin_user_id: str
    ) -> ClubGiftRecord:
        """
        Admin: Directly add Club Gift to user.
        Creates a Club Gift record and credits it immediately.
        """
        if amount <= 0:
            raise BadRequestException("Amount must be positive")

        # Create Club Gift record
        record = ClubGiftRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            reference_type="ADMIN_BONUS",
            reference_id=str(uuid.uuid4()),  # Generate a reference ID
            booking_amount=amount,
            cashback_rate=100.0,  # 100% since it's direct gift
            cashback_amount=amount,
            currency="USD",
            status=ClubGiftStatus.APPROVED  # Skip pending for admin direct add
        )

        self.db.add(record)

        record.status = ClubGiftStatus.CREDITED
        record.credited_at = datetime.utcnow()
        record.approved_by_user_id = admin_user_id
        record.approved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(record)

        logger.info(f"✅ Admin Club Gift added: {amount} USD to user {user_id}")
        
        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_cashback_change(
                    user=user,
                    amount=amount,
                    type="EARNED",
                    reason=f"Admin Club Gift: {reason}"
                )
        except Exception as e:
            logger.error(f"Failed to send club gift notification: {e}")

        return record
    
    # Alias for backward compatibility
    def admin_add_cashback(self, user_id: str, amount: float, reason: str, admin_user_id: str):
        return self.admin_add_club_gift(user_id, amount, reason, admin_user_id)

    def admin_remove_club_gift(
        self,
        user_id: str,
        amount: float,
        reason: str,
        admin_user_id: str
    ) -> dict:
        """
        Admin: Directly deduct Club Gift from user.
        This creates a negative Club Gift record to reduce the balance.
        """
        if amount <= 0:
            raise BadRequestException("Amount must be positive")

        # Check current Club Gift balance
        all_records = self.get_user_club_gifts(user_id=user_id, limit=1000)
        total_credited = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.CREDITED)
        pending_withdrawals = sum(abs(r.cashback_amount) for r in all_records if r.status == ClubGiftStatus.PENDING_WITHDRAWAL)
        current_balance = total_credited - pending_withdrawals

        if current_balance < amount:
            raise BadRequestException(f"Insufficient Club Gift balance. Available: {current_balance}, Requested: {amount}")

        # Create a negative Club Gift record (deduction)
        deduction_record = ClubGiftRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            reference_type="ADMIN_DEDUCTION",
            reference_id=str(uuid.uuid4()),
            booking_amount=0,  # Not related to a booking
            cashback_rate=0,
            cashback_amount=-amount,  # Negative amount for deduction
            currency="USD",
            status=ClubGiftStatus.CREDITED,  # Immediately applied
            approved_by_user_id=admin_user_id,
            approved_at=datetime.utcnow(),
            credited_at=datetime.utcnow()
        )

        self.db.add(deduction_record)
        self.db.commit()
        self.db.refresh(deduction_record)

        logger.info(f"✅ Admin Club Gift deducted: {amount} USD from user {user_id}")

        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(user_id)
            if user:
                notification_service.notify_cashback_change(
                    user=user,
                    amount=amount,
                    type="REDEEMED",
                    reason=f"Admin Deduction: {reason}"
                )
        except Exception as e:
            logger.error(f"Failed to send club gift notification: {e}")
        
        return {
            "status": "deducted",
            "amount": amount,
            "club_gift_record_id": str(deduction_record.id),
            "remaining_balance": current_balance - amount
        }
    
    # Alias for backward compatibility
    def admin_remove_cashback(self, user_id: str, amount: float, reason: str, admin_user_id: str):
        return self.admin_remove_club_gift(user_id, amount, reason, admin_user_id)

    def withdraw_club_gift_to_wallet(
        self,
        user_id: str,
        amount: float
    ) -> dict:
        """
        User: Create a withdrawal request for Club Gift to wallet.
        Creates a PENDING_WITHDRAWAL record which locks the funds.
        """
        if amount <= 0:
            raise BadRequestException("Amount must be positive")

        # Check current available Club Gift balance
        # We need to calculate available balance logic here too to ensure consistency
        all_records = self.get_user_club_gifts(user_id=user_id, limit=1000)
        
        total_credited = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.CREDITED)
        pending_withdrawals = sum(abs(r.cashback_amount) for r in all_records if r.status == ClubGiftStatus.PENDING_WITHDRAWAL)
        available_club_gift = total_credited - pending_withdrawals

        if available_club_gift < amount:
            raise BadRequestException(f"Insufficient Club Gift balance. Available: {available_club_gift}, Requested: {amount}")

        # Create a PENDING_WITHDRAWAL record
        # This acts as a hold on the funds
        record = ClubGiftRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            reference_type="CLUB_GIFT_WITHDRAWAL_REQUEST",
            reference_id=str(uuid.uuid4()),
            booking_amount=0,
            cashback_rate=0,
            cashback_amount=-amount,  # Negative amount to represent deduction
            currency="USD",
            status=ClubGiftStatus.PENDING_WITHDRAWAL,
            created_at=datetime.utcnow()
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(f"✅ Club Gift withdrawal request: {amount} USD for user {user_id}")
        
        # Notify Admins (Optional: Implement if needed)

        return {
            "status": "pending_approval",
            "amount": amount,
            "club_gift_transaction_id": str(record.id),
            "remaining_available": available_club_gift - amount
        }
    
    def approve_withdrawal_request(
        self,
        request_id: str,
        admin_user_id: str
    ) -> dict:
        """
        Admin: Approve a withdrawal request.
        1. Find the PENDING_WITHDRAWAL record.
        2. Create Wallet Deposit transaction.
        3. Update record status to CREDITED (finalized deduction).
        """
        record = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.id == request_id).first()
        
        if not record:
            raise NotFoundException("Withdrawal request not found")
            
        if record.status != ClubGiftStatus.PENDING_WITHDRAWAL:
            raise BadRequestException(f"Cannot approve. Status is {record.status}")
            
        # Create Wallet Transaction
        wallet_service = WalletService(self.db)
        wallet_transaction = wallet_service.deposit(
            user_id=str(record.user_id),
            amount=abs(record.cashback_amount),
            description_en=f"Club Gift withdrawal approved: {abs(record.cashback_amount)} USD",
            description_ar=f"تمت الموافقة على سحب هدية النادي: {abs(record.cashback_amount)} دولار",
            reference_type="CLUB_GIFT_WITHDRAWAL",
            reference_id=str(record.id)
        )
        
        # Update Club Gift Record
        record.status = ClubGiftStatus.CREDITED
        record.approved_by_user_id = admin_user_id
        record.approved_at = datetime.utcnow()
        record.wallet_transaction_id = wallet_transaction.id
        
        self.db.commit()
        
        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(record.user_id)
            if user:
                notification_service.notify_cashback_change(
                    user=user,
                    amount=abs(record.cashback_amount),
                    type="REDEEMED",
                    reason="Withdrawal Approved"
                )
        except Exception:
            pass
            
        return {
            "status": "approved",
            "wallet_transaction_id": str(wallet_transaction.id)
        }

    def reject_withdrawal_request(
        self,
        request_id: str,
        reason: str,
        admin_user_id: str
    ) -> dict:
        """
        Admin: Reject a withdrawal request.
        Update record status to REJECTED.
        This releases the funds back to available balance (since REJECTED records aren't summed in pending_withdrawals).
        """
        record = self.db.query(ClubGiftRecord).filter(ClubGiftRecord.id == request_id).first()
        
        if not record:
            raise NotFoundException("Withdrawal request not found")
            
        if record.status != ClubGiftStatus.PENDING_WITHDRAWAL:
            raise BadRequestException(f"Cannot reject. Status is {record.status}")
            
        record.status = ClubGiftStatus.REJECTED
        record.rejection_reason = reason
        record.approved_by_user_id = admin_user_id
        record.approved_at = datetime.utcnow()
        
        self.db.commit()
        
        # Notify User
        try:
            notification_service = NotificationService(self.db)
            user = self.db.query(User).get(record.user_id)
            if user:
                notification_service.notify_cashback_change(
                    user=user,
                    amount=abs(record.cashback_amount),
                    type="INFO", # Not REDEEMED or EARNED strictly
                    reason=f"Withdrawal Rejected: {reason}"
                )
        except Exception:
            pass
            
        return {"status": "rejected"}
    
    def get_withdrawal_requests(self, status: Optional[str] = None, limit: int = 100) -> List[ClubGiftRecord]:
        """
        Admin: Get withdrawal requests.
        """
        query = self.db.query(ClubGiftRecord).filter(
            ClubGiftRecord.reference_type == "CLUB_GIFT_WITHDRAWAL_REQUEST"
        )

        if status:
            if status == "PROCESSED":
                query = query.filter(ClubGiftRecord.status.in_([ClubGiftStatus.CREDITED, ClubGiftStatus.REJECTED]))
            else:
                query = query.filter(ClubGiftRecord.status == status)
        else:
             query = query.filter(ClubGiftRecord.status == ClubGiftStatus.PENDING_WITHDRAWAL)

        return query.order_by(ClubGiftRecord.created_at.desc()).limit(limit).all()

    # Alias for backward compatibility
    def withdraw_cashback_to_wallet(self, user_id: str, amount: float):
        return self.withdraw_club_gift_to_wallet(user_id, amount)
