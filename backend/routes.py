
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from database.base import get_db
from modules.memberships.models import MembershipPlan, MembershipBenefits
from modules.memberships.schemas import MembershipBenefitsResponse, MembershipBenefitsUpdate
from modules.users.models import User
from shared.dependencies import require_admin

router = APIRouter()

# ============ Membership Benefits Management ============

@router.post("/plans/{plan_id}/benefits", response_model=MembershipBenefitsResponse)
def create_or_update_benefits(
    plan_id: str,
    benefits: MembershipBenefitsUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create or update membership benefits for a plan"""
    try:
        plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID format")
    
    # Check if plan exists
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if benefits already exist
    existing = db.query(MembershipBenefits).filter(MembershipBenefits.plan_id == plan_uuid).first()
    
    if existing:
        # Update existing
        for key, value in benefits.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        new_benefits = MembershipBenefits(
            id=str(uuid.uuid4()),
            plan_id=plan_uuid,
            **benefits.model_dump(exclude_unset=True)
        )
        db.add(new_benefits)
        db.commit()
        db.refresh(new_benefits)
        return new_benefits


@router.get("/plans/{plan_id}/benefits", response_model=MembershipBenefitsResponse)
def get_plan_benefits(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """Get membership benefits for a plan"""
    try:
        plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID format")
    
    benefits = db.query(MembershipBenefits).filter(MembershipBenefits.plan_id == plan_uuid).first()
    if not benefits:
        raise HTTPException(status_code=404, detail="Benefits not found for this plan")
    
    return benefits


@router.get("/benefits/by-plan-code/{tier_code}", response_model=MembershipBenefitsResponse)
def get_benefits_by_tier_code(
    tier_code: str,
    db: Session = Depends(get_db)
):
    """Get membership benefits by tier code (for user-facing API)"""
    plan = db.query(MembershipPlan).filter(MembershipPlan.tier_code == tier_code.upper()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    benefits = db.query(MembershipBenefits).filter(MembershipBenefits.plan_id == plan.id).first()
    if not benefits:
        raise HTTPException(status_code=404, detail="Benefits not found for this plan")
    
    return benefits

