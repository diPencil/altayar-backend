from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from database.base import get_db
from shared.dependencies import get_current_user
from modules.users.models import User
from modules.referrals.models import ReferralCode, Referral
from modules.referrals.schemas import ReferralCodeResponse, ReferralStatsResponse, ReferralHistoryResponse

router = APIRouter()

@router.get("/code", response_model=ReferralCodeResponse)
def get_referral_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    referral_code = db.query(ReferralCode).filter(ReferralCode.user_id == current_user.id).first()
    
    if not referral_code:
        # Generate new code
        # Format: REF-XXXXXX (6 chars from UUID)
        # Ensure uniqueness loop
        while True:
            unique_suffix = uuid.uuid4().hex[:6].upper()
            new_code_str = f"REF-{unique_suffix}"
            if not db.query(ReferralCode).filter(ReferralCode.code == new_code_str).first():
                break
        
        referral_code = ReferralCode(
            user_id=current_user.id,
            code=new_code_str,
            usage_count=0
        )
        db.add(referral_code)
        db.commit()
        db.refresh(referral_code)
        
    return referral_code

@router.get("/stats", response_model=ReferralStatsResponse)
def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Total Referrals
    total_referrals = db.query(Referral).filter(Referral.referrer_id == current_user.id).count()
    
    # Points Earned
    total_points = db.query(func.sum(Referral.points_earned)).filter(
        Referral.referrer_id == current_user.id
    ).scalar() or 0
    
    # Pending Referrals
    pending_referrals = db.query(Referral).filter(
        Referral.referrer_id == current_user.id,
        Referral.status == 'PENDING'
    ).count()
    
    return {
        "total_referrals": total_referrals,
        "total_points": int(total_points),
        "pending_referrals": pending_referrals
    }

@router.get("/history", response_model=ReferralHistoryResponse)
def get_referral_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    referrals = db.query(Referral).filter(
        Referral.referrer_id == current_user.id
    ).order_by(Referral.created_at.desc()).all()
    
    history_items = []
    for referral in referrals:
        referred_name = "Unknown User"
        if referral.referred_user:
            referred_name = f"{referral.referred_user.first_name} {referral.referred_user.last_name}"
            
        history_items.append({
            "id": referral.id,
            "referred_user_name": referred_name,
            "referred_user_avatar": referral.referred_user.avatar if referral.referred_user else None,
            "status": referral.status,
            "points_earned": referral.points_earned,
            "created_at": referral.created_at
        })
        
    return {"referrals": history_items}


@router.post("/employee/create-referral")
def create_employee_referral(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allow employees to get/create their referral code.
    This code can be shared with potential customers during registration.
    
    Returns the employee's referral code that customers can use.
    """
    from shared.dependencies import require_employee_or_admin
    from modules.users.models import UserRole
    
    # Verify user is employee or admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role not in ["EMPLOYEE", "ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only employees and admins can create referral codes"
        )
    
    # Get or create employee's referral code
    referral_code = db.query(ReferralCode).filter(
        ReferralCode.user_id == current_user.id
    ).first()
    
    if not referral_code:
        # Generate new code for employee
        while True:
            unique_suffix = uuid.uuid4().hex[:6].upper()
            new_code_str = f"EMP-{unique_suffix}"  # EMP prefix for employee codes
            if not db.query(ReferralCode).filter(ReferralCode.code == new_code_str).first():
                break
        
        referral_code = ReferralCode(
            user_id=current_user.id,
            code=new_code_str,
            usage_count=0
        )
        db.add(referral_code)
        db.commit()
        db.refresh(referral_code)
    
    return {
        "referral_code": referral_code.code,
        "usage_count": referral_code.usage_count,
        "message": "Share this code with customers during registration. They will be automatically assigned to you."
    }
