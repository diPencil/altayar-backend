from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from database.base import get_db
from modules.cashback.service import ClubGiftService
from modules.cashback.schemas import (
    CashbackRecordResponse,  # Keep for backward compatibility
    CreateCashbackRequest,
    CashbackStatus,  # Keep for backward compatibility
    WithdrawalRequest
)
from modules.users.models import User
from shared.dependencies import get_current_user, get_admin_user, require_active_membership

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=List[CashbackRecordResponse])
def get_my_club_gifts(
    status: Optional[CashbackStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Club Gift records.
    """
    club_gift_service = ClubGiftService(db)
    records = club_gift_service.get_user_club_gifts(
        user_id=str(current_user.id),
        status=status,
        limit=limit,
        offset=offset
    )
    return records

# Alias for backward compatibility
get_my_cashback = get_my_club_gifts


@router.get("/me/balance", response_model=dict)
def get_my_club_gift_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Club Gift balance summary.
    Returns total credited Club Gift and available balance.
    """
    from modules.cashback.models import ClubGiftStatus
    club_gift_service = ClubGiftService(db)
    all_records = club_gift_service.get_user_club_gifts(
        user_id=str(current_user.id),
        limit=1000
    )

    # Calculate totals
    total = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.CREDITED)
    
    # Calculate pending withdrawals
    pending_withdrawals = sum(abs(r.cashback_amount) for r in all_records if r.status == ClubGiftStatus.PENDING_WITHDRAWAL)
    
    available = total - pending_withdrawals

    return {
        "total": total,
        "available": available,
        "currency": "USD"
    }

# Alias for backward compatibility
get_my_cashback_balance = get_my_club_gift_balance


@router.get("/me/records")
def get_my_club_gift_records(
    status: Optional[CashbackStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Club Gift records with descriptions.
    """
    club_gift_service = ClubGiftService(db)
    records = club_gift_service.get_user_club_gifts(
        user_id=str(current_user.id),
        status=status,
        limit=limit,
        offset=offset
    )

    # Transform records to include description and amount fields for frontend
    result = []
    for record in records:
        description = ClubGiftService._get_club_gift_description_static(record)
        record_dict = {
            'id': record.id,
            'user_id': record.user_id,
            'reference_type': record.reference_type,
            'reference_id': record.reference_id,
            'booking_amount': record.booking_amount,
            'cashback_rate': record.cashback_rate,
            'cashback_amount': record.cashback_amount,
            'currency': record.currency,
            'status': record.status.value,
            'approved_at': record.approved_at,
            'credited_at': record.credited_at,
            'rejection_reason': record.rejection_reason,
            'created_at': record.created_at,
            'description': description,
            'amount': record.cashback_amount  # For frontend compatibility
        }
        result.append(record_dict)

    return result

# Alias for backward compatibility
get_my_cashback_records = get_my_club_gift_records


@router.get("/me/summary")
def get_my_club_gift_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's Club Gift summary.
    """
    from modules.cashback.models import ClubGiftStatus
    club_gift_service = ClubGiftService(db)
    all_records = club_gift_service.get_user_club_gifts(
        user_id=str(current_user.id),
        limit=1000
    )

    pending = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.PENDING)
    approved = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.APPROVED)
    credited = sum(r.cashback_amount for r in all_records if r.status == ClubGiftStatus.CREDITED)

    return {
        "pending": pending,
        "approved": approved,
        "credited": credited,
        "currency": "USD"
    }

# Alias for backward compatibility
get_my_cashback_summary = get_my_club_gift_summary


# ============ Admin Endpoints ============

@router.post("", response_model=CashbackRecordResponse)
def create_club_gift(
    request: CreateCashbackRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Create a Club Gift record.
    """
    club_gift_service = ClubGiftService(db)
    record = club_gift_service.create_club_gift(
        user_id=request.user_id,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        booking_amount=request.booking_amount,
        cashback_rate=request.cashback_rate
    )
    return record

# Alias for backward compatibility
create_cashback = create_club_gift


@router.get("/pending", response_model=List[CashbackRecordResponse])
def get_pending_club_gifts(
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get all pending Club Gift records.
    """
    club_gift_service = ClubGiftService(db)
    return club_gift_service.get_pending_club_gifts(limit=limit)

# Alias for backward compatibility
get_pending_cashback = get_pending_club_gifts


@router.post("/{cashback_id}/approve")
def approve_club_gift(
    cashback_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Approve a pending Club Gift.
    """
    club_gift_service = ClubGiftService(db)
    record = club_gift_service.approve_club_gift(
        club_gift_id=cashback_id,
        approved_by_user_id=str(current_user.id)
    )
    return {"status": "approved", "cashback_id": str(record.id), "club_gift_id": str(record.id)}

# Alias for backward compatibility
approve_cashback = approve_club_gift


@router.post("/{cashback_id}/credit")
def credit_club_gift(
    cashback_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Credit approved Club Gift to user's wallet.
    """
    club_gift_service = ClubGiftService(db)
    record = club_gift_service.credit_club_gift(club_gift_id=cashback_id)
    return {
        "status": "credited",
        "cashback_id": str(record.id),
        "club_gift_id": str(record.id),
        "amount": record.cashback_amount,
        "wallet_transaction_id": str(record.wallet_transaction_id) if record.wallet_transaction_id else None
    }

# Alias for backward compatibility
credit_cashback = credit_club_gift


@router.post("/{cashback_id}/reject")
def reject_club_gift(
    cashback_id: str,
    reason: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Reject a Club Gift.
    """
    club_gift_service = ClubGiftService(db)
    record = club_gift_service.reject_club_gift(
        club_gift_id=cashback_id,
        reason=reason,
        rejected_by_user_id=str(current_user.id)
    )
    return {"status": "rejected", "cashback_id": str(record.id), "club_gift_id": str(record.id), "reason": reason}

# Alias for backward compatibility
reject_cashback = reject_club_gift


# ============ Admin Direct Cashback Management ============

@router.post("/admin/add")
def admin_add_club_gift(
    user_id: str,
    amount: float,
    reason: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Directly add Club Gift to user (creates credited Club Gift record).
    """
    club_gift_service = ClubGiftService(db)
    record = club_gift_service.admin_add_club_gift(
        user_id=user_id,
        amount=amount,
        reason=reason or "Admin Club Gift",
        admin_user_id=str(current_user.id)
    )
    return {
        "status": "added",
        "club_gift_id": str(record.id),
        "cashback_id": str(record.id),  # Backward compatibility
        "amount": record.cashback_amount,
        "wallet_transaction_id": str(record.wallet_transaction_id) if record.wallet_transaction_id else None
    }

# Alias for backward compatibility
admin_add_cashback = admin_add_club_gift


@router.post("/admin/remove")
def admin_remove_club_gift(
    user_id: str,
    amount: float,
    reason: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Directly deduct Club Gift from user.
    """
    club_gift_service = ClubGiftService(db)
    result = club_gift_service.admin_remove_club_gift(
        user_id=user_id,
        amount=amount,
        reason=reason or "Admin adjustment",
        admin_user_id=str(current_user.id)
    )
    return result

# Alias for backward compatibility
admin_remove_cashback = admin_remove_club_gift


@router.get("/admin/history/{user_id}")
def admin_get_club_gift_history(
    user_id: str,
    limit: int = 50,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get Club Gift history for a user.
    """
    club_gift_service = ClubGiftService(db)
    records = club_gift_service.get_user_club_gifts(
        user_id=user_id,
        limit=limit
    )

    # Transform records for frontend
    result = []
    for record in records:
        description = ClubGiftService._get_club_gift_description_static(record)
        record_dict = {
            'id': record.id,
            'user_id': record.user_id,
            'reference_type': record.reference_type,
            'reference_id': record.reference_id,
            'booking_amount': record.booking_amount,
            'cashback_rate': record.cashback_rate,
            'cashback_amount': record.cashback_amount,
            'currency': record.currency,
            'status': record.status.value,
            'approved_at': record.approved_at,
            'credited_at': record.credited_at,
            'rejection_reason': record.rejection_reason,
            'created_at': record.created_at,
            'description': description,
            'points': record.cashback_amount,  # For backward compatibility with points.tsx
            'description_en': description,
            'reason': description
        }
        result.append(record_dict)

    return {"records": result}

# Alias for backward compatibility
admin_get_cashback_history = admin_get_club_gift_history


# ============ User Cashback Withdrawal ============

@router.post("/withdraw")
def withdraw_club_gift_to_wallet(
    request: WithdrawalRequest,
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    User: Request to withdraw Club Gift to wallet.
    Creates a pending withdrawal request that requires admin approval.
    """
    club_gift_service = ClubGiftService(db)
    result = club_gift_service.withdraw_club_gift_to_wallet(
        user_id=str(current_user.id),
        amount=request.amount
    )
    return result

# Alias for backward compatibility
withdraw_cashback_to_wallet = withdraw_club_gift_to_wallet


# ============ Admin Withdrawal Management ============

@router.get("/admin/withdrawal-requests")
def get_withdrawal_requests(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get withdrawal requests.
    Status can be 'PENDING_WITHDRAWAL' (default), 'CREDITED', 'REJECTED' or 'PROCESSED' (both).
    """
    club_gift_service = ClubGiftService(db)
    # Get requests and enhance with User info
    requests = club_gift_service.get_withdrawal_requests(status=status, limit=limit)
    
    # We might want to return User details with the request
    # ideally we should join with User table, but for now we iterate
    result = []
    for req in requests:
        user = db.query(User).get(req.user_id)
        result.append({
            "id": str(req.id),
            "user_id": str(req.user_id),
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown User",
            "amount": abs(req.cashback_amount),
            "created_at": req.created_at,
            "status": req.status
        })
        
    return result


@router.post("/admin/requests/{request_id}/approve")
def approve_withdrawal_request(
    request_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Approve withdrawal request.
    """
    club_gift_service = ClubGiftService(db)
    return club_gift_service.approve_withdrawal_request(
        request_id=request_id,
        admin_user_id=str(current_user.id)
    )


@router.post("/admin/requests/{request_id}/reject")
def reject_withdrawal_request(
    request_id: str,
    reason: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Reject withdrawal request.
    """
    club_gift_service = ClubGiftService(db)
    return club_gift_service.reject_withdrawal_request(
        request_id=request_id,
        reason=reason,
        admin_user_id=str(current_user.id)
    )
