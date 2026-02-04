from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from database.base import get_db
from modules.wallet.service import WalletService
from modules.wallet.schemas import (
    WalletResponse,
    WalletTransactionResponse,
    DepositRequest,
    WithdrawRequest,
    PayFromWalletRequest
)
from modules.users.models import User
from shared.dependencies import get_current_user, get_admin_user, require_active_membership

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=WalletResponse)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's wallet.
    Creates wallet if not exists.
    """
    wallet_service = WalletService(db)
    wallet = wallet_service.get_or_create_wallet(str(current_user.id))
    # Force currency display to USD for frontend consistency, even if DB update is pending
    if wallet.currency != "USD" and wallet.balance == 0:
        wallet.currency = "USD"
    return wallet


@router.get("/me/balance")
def get_my_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's wallet balance.
    """
    wallet_service = WalletService(db)
    balance = wallet_service.get_balance(str(current_user.id))
    return {"balance": balance, "currency": "USD"}


@router.get("/me/transactions", response_model=List[WalletTransactionResponse])
def get_my_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's wallet transactions.
    """
    wallet_service = WalletService(db)
    transactions = wallet_service.get_transactions(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset
    )
    return transactions


@router.post("/me/pay")
def pay_from_wallet(
    request: PayFromWalletRequest,
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    Pay for booking/order from wallet.
    """
    wallet_service = WalletService(db)
    transaction = wallet_service.pay_from_wallet(
        user_id=str(current_user.id),
        amount=request.amount,
        reference_type=request.reference_type,
        reference_id=request.reference_id
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "new_balance": transaction.balance_after
    }


# ============ Admin Endpoints ============

@router.post("/deposit")
def admin_deposit(
    user_id: str,
    request: DepositRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Deposit funds to user's wallet.
    """
    wallet_service = WalletService(db)
    transaction = wallet_service.deposit(
        user_id=user_id,
        amount=request.amount,
        description_en=request.description_en,
        description_ar=request.description_ar,
        created_by_user_id=str(current_user.id)
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "new_balance": transaction.balance_after
    }


@router.post("/withdraw")
def admin_withdraw(
    user_id: str,
    request: WithdrawRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Withdraw funds from user's wallet.
    """
    wallet_service = WalletService(db)
    transaction = wallet_service.withdraw(
        user_id=user_id,
        amount=request.amount,
        description_en=request.description_en,
        description_ar=request.description_ar,
        created_by_user_id=str(current_user.id)
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "new_balance": transaction.balance_after
    }


@router.get("/{user_id}")
def get_user_wallet(
    user_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get any user's wallet.
    """
    wallet_service = WalletService(db)
    wallet = wallet_service.get_or_create_wallet(user_id)
    return {
        "id": str(wallet.id),
        "user_id": str(wallet.user_id),
        "balance": wallet.balance,
        "currency": wallet.currency
    }


@router.get("/", response_model=Dict[str, Any])
def list_all_wallets(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Admin: List all wallets.
    """
    from modules.wallet.models import Wallet
    from modules.users.models import User as UserModel
    
    # Query wallets with user data using proper join
    # Use explicit join condition - returns (Wallet, User) tuples
    query = db.query(Wallet, UserModel).join(UserModel, Wallet.user_id == UserModel.id)
    total = query.count()
    results = query.offset(offset).limit(limit).all()
    
    # Build response items
    items = []
    for wallet, user in results:
        items.append({
            "id": str(wallet.id),
            "user_id": str(wallet.user_id),
            "balance": wallet.balance,
            "currency": wallet.currency or "USD",
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "user_email": user.email if user else "Unknown"
        })
    
    return {
        "total": total,
        "items": items
    }


@router.get("/transactions/all")
def get_all_wallet_transactions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Admin: Get latest wallet transactions for ALL users (for Recent Activity).
    """
    from modules.wallet.models import WalletTransaction
    from modules.users.models import User as UserModel
    from sqlalchemy.orm import joinedload
    
    # Query recent transactions with user data
    transactions = db.query(WalletTransaction, UserModel)\
        .join(UserModel, WalletTransaction.user_id == UserModel.id)\
        .order_by(WalletTransaction.created_at.desc())\
        .limit(limit)\
        .all()
    
    result = []
    for tx, user in transactions:
        # Determine if it's add or deduct
        is_add = tx.transaction_type.value in ['DEPOSIT', 'REFUND', 'CASHBACK', 'BONUS', 'TRANSFER_IN']
        # For display: positive amount = deposit/add, negative = withdraw/deduct
        amount_display = abs(tx.amount) if is_add else -abs(tx.amount)
        
        result.append({
            "id": str(tx.id),
            "user_id": str(tx.user_id),
            "user_name": f"{user.first_name} {user.last_name}" if user else "Unknown User",
            "user_avatar": user.avatar if user else None,
            "amount": amount_display,  # Positive for deposits, negative for withdrawals
            "currency": tx.currency or "USD",
            "type": tx.transaction_type.value,
            "description": tx.description_en or tx.description_ar or tx.reference_type or "Wallet Transaction",
            "reference_type": tx.reference_type,
            "created_at": tx.created_at.isoformat() if tx.created_at else None
        })
    
    return result


@router.get("/transactions/{user_id}")
def get_user_wallet_transactions(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Admin: Get wallet transaction history for a specific user.
    """
    from modules.wallet.service import WalletService
    
    wallet_service = WalletService(db)
    transactions = wallet_service.get_transactions(
        user_id=user_id,
        limit=limit,
        offset=0
    )
    
    return {
        "user_id": user_id,
        "transactions": [
            {
                "id": str(tx.id),
                "amount": tx.amount,
                "currency": tx.currency or "USD",
                "type": tx.transaction_type.value,
                "description": tx.description_en or tx.description_ar or tx.reference_type or "Wallet Transaction",
                "reference_type": tx.reference_type,
                "balance_before": tx.balance_before,
                "balance_after": tx.balance_after,
                "status": tx.status.value if hasattr(tx.status, "value") else str(tx.status),
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
                "created_by_user_id": str(tx.created_by_user_id) if tx.created_by_user_id else None
            }
            for tx in transactions
        ]
    }
