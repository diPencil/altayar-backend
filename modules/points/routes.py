from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from database.base import get_db
from modules.points.service import PointsService
from modules.points.schemas import (
    PointsBalanceResponse,
    PointsTransactionResponse,
    EarnPointsRequest,
    RedeemPointsRequest
)
from modules.users.models import User
from shared.dependencies import get_current_user, get_admin_user, require_active_membership

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=PointsBalanceResponse)
def get_my_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's points balance.
    """
    points_service = PointsService(db)
    balance = points_service.get_or_create_balance(str(current_user.id))
    return balance


@router.get("/me/balance")
def get_my_points_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's points balance (simple).
    """
    points_service = PointsService(db)
    balance = points_service.get_balance(str(current_user.id))
    return {"points": balance}


@router.get("/me/transactions", response_model=List[PointsTransactionResponse])
def get_my_points_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's points transactions.
    """
    points_service = PointsService(db)
    transactions = points_service.get_transactions(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset
    )
    return transactions


@router.post("/me/redeem")
def redeem_points(
    request: RedeemPointsRequest,
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    Redeem points for booking/order.
    """
    points_service = PointsService(db)
    transaction = points_service.redeem_points(
        user_id=str(current_user.id),
        points=request.points,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        description_en=request.description_en
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "points_redeemed": request.points,
        "new_balance": transaction.balance_after
    }


# ============ Admin Endpoints ============

@router.post("/earn")
def admin_earn_points(
    user_id: str,
    request: EarnPointsRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Award points to user.
    """
    points_service = PointsService(db)
    transaction = points_service.earn_points(
        user_id=user_id,
        points=request.points,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        description_en=request.description_en,
        multiplier=request.multiplier
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "points_earned": transaction.points,
        "new_balance": transaction.balance_after
    }


@router.post("/bonus")
def admin_bonus_points(
    user_id: str,
    points: int,
    description_en: str = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Give bonus points to user.
    """
    points_service = PointsService(db)
    transaction = points_service.add_bonus_points(
        user_id=user_id,
        points=points,
        description_en=description_en,
        created_by_user_id=str(current_user.id)
    )
    return {
        "status": "success",
        "transaction_id": str(transaction.id),
        "bonus_points": points,
        "new_balance": transaction.balance_after
    }


@router.get("/{user_id}")
def get_user_points(
    user_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Admin: Get any user's points balance.
    """
    points_service = PointsService(db)
    balance = points_service.get_or_create_balance(user_id)
    return {
        "user_id": user_id,
        "current_balance": balance.current_balance,
        "total_earned": balance.total_earned,
        "total_redeemed": balance.total_redeemed,
        "total_expired": balance.total_expired
    }
