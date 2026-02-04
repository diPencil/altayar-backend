from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, String, update
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import datetime, timedelta

from database.base import get_db
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus, MembershipBenefits
from modules.memberships.schemas import (
    MembershipPlanCreate, MembershipPlanUpdate, MembershipPlanResponse, SubscriptionCreate,
    MembershipBenefitsCreate, MembershipBenefitsUpdate, MembershipBenefitsResponse
)
from modules.users.models import User
from modules.notifications.service import NotificationService
from shared.dependencies import get_current_user, require_admin
from modules.referrals.models import Referral
from modules.points.models import PointsBalance, PointsTransaction

logger = logging.getLogger(__name__)
router = APIRouter()

# ============ Admin: Plan Management ============

@router.post("/plans", response_model=MembershipPlanResponse)
def create_plan(
    plan: MembershipPlanCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Check if tier code exists
    existing = db.query(MembershipPlan).filter(MembershipPlan.tier_code == plan.tier_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plan with this code already exists")

    new_plan = MembershipPlan(
        id=str(uuid.uuid4()),
        tier_code=plan.tier_code,
        tier_name_ar=plan.tier_name_ar,
        tier_name_en=plan.tier_name_en,
        tier_order=plan.tier_order,
        description_ar=plan.description_ar,
        description_en=plan.description_en,
        price=plan.price,
        currency=plan.currency,
        # plan_type=plan.plan_type, # ensure model has this field or map appropriately
        cashback_rate=plan.cashback_rate,
        points_multiplier=plan.points_multiplier,
        perks=plan.perks,
        color_hex=plan.color_hex,
        icon_url=plan.icon_url,
        is_active=plan.is_active,
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan

from sqlalchemy import func
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus

@router.get("/plans", response_model=List[MembershipPlanResponse])
def get_plans(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(
        MembershipPlan, 
        func.count(MembershipSubscription.id).label('members_count')
    ).outerjoin(
        MembershipSubscription, 
        (MembershipSubscription.plan_id == MembershipPlan.id) & 
        (MembershipSubscription.status == MembershipStatus.ACTIVE)
    ).group_by(MembershipPlan.id)

    if active_only:
        query = query.filter(MembershipPlan.is_active == True)
    
    results = query.order_by(MembershipPlan.tier_order).all()
    
    # Transform result to match Pydantic model
    response = []
    for plan, count in results:
        # Use Pydantic model_validate to ensure all fields are correctly serialized
        plan_response = MembershipPlanResponse.model_validate(plan)
        plan_response.members_count = count
        response.append(plan_response)
        
    return response

@router.get("/plans/{plan_id}", response_model=MembershipPlanResponse)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):
    try:
        # Convert plan_id to UUID if it's a string
        try:
            plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid plan ID format")
        
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Calculate active members count
        sub_count = db.query(MembershipSubscription).filter(
            MembershipSubscription.plan_id == plan_uuid,
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).count()
        
        # Convert ORM model to Pydantic model using model_validate (Pydantic v2)
        # This ensures all fields defined in schema are correctly extracted from the ORM object
        try:
            response = MembershipPlanResponse.model_validate(plan)
        except Exception as e:
            # Fallback: manually construct response if model_validate fails
            logger.error(f"Error validating plan model: {e}")
            response = MembershipPlanResponse(
                id=plan.id,
                tier_code=plan.tier_code,
                tier_name_en=plan.tier_name_en,
                tier_name_ar=plan.tier_name_ar,
                tier_order=plan.tier_order,
                description_en=plan.description_en,
                description_ar=plan.description_ar,
                price=plan.price,
                currency=plan.currency,
                plan_type=plan.plan_type,
                duration_days=plan.duration_days,
                purchase_limit=plan.purchase_limit,
                cashback_rate=plan.cashback_rate,
                points_multiplier=plan.points_multiplier,
                perks=plan.perks,
                color_hex=plan.color_hex,
                icon_url=plan.icon_url,
                is_active=plan.is_active,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
                members_count=0
            )
        
        # Manually set the computed field
        response.members_count = sub_count
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/plans/{plan_id}/members")
def get_plan_members(
    plan_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all members subscribed to a specific membership plan
    """
    try:
        # Convert plan_id to UUID if it's a string
        try:
            plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid plan ID format")

        # Verify plan exists
        plan_uuid_str = str(plan_uuid)
        plan_uuid_hex = plan_uuid.hex

        plan = db.query(MembershipPlan).filter(
            (MembershipPlan.id == plan_uuid_str) |
            (MembershipPlan.id == plan_uuid_hex) |
            (MembershipPlan.id == plan_uuid)
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Get all active subscriptions for this plan with user details
        from sqlalchemy.orm import joinedload

        # Convert UUID to string formats for comparison
        plan_uuid_str = str(plan_uuid)
        plan_uuid_hex = plan_uuid.hex

        subscriptions = db.query(MembershipSubscription).options(
            joinedload(MembershipSubscription.user)
        ).filter(
            (MembershipSubscription.plan_id == plan_uuid_str) |
            (MembershipSubscription.plan_id == plan_uuid_hex) |
            (MembershipSubscription.plan_id == plan_uuid),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).all()

        # Build members response
        members = []
        for sub in subscriptions:
            if sub.user:
                user = sub.user
                member_data = {
                    "id": str(user.id),
                    "name": f"{user.first_name} {user.last_name}",
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "avatar": user.avatar,
                    "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                    "status": user.status.value if hasattr(user.status, "value") else str(user.status),
                    "joined_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                    "membership": {
                        "status": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
                        "start_date": sub.start_date.isoformat() if sub.start_date else None,
                        "end_date": sub.expiry_date.isoformat() if sub.expiry_date else None,
                        "membership_id": sub.user.membership_id_display or sub.membership_number
                    }
                }
                members.append(member_data)

        return {
            "plan": {
                "id": str(plan.id),
                "tier_name_en": plan.tier_name_en,
                "tier_name_ar": plan.tier_name_ar,
                "tier_code": plan.tier_code,
                "color_hex": plan.color_hex
            },
            "members": members,
            "total_members": len(members)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan members for {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/plans/{plan_id}", response_model=MembershipPlanResponse)
def update_plan(
    plan_id: str,
    update_data: MembershipPlanUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        # Convert plan_id to UUID if it's a string
        try:
            plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid plan ID format")
        
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Log the update data for debugging
        update_dict = update_data.model_dump(exclude_unset=True)
        logger.info(f"Updating plan {plan_id} with fields: {list(update_dict.keys())}")
        if 'perks' in update_dict:
            logger.info(f"Perks update value: {update_dict['perks']}")
        
        # Check if tier_code is being changed and if it conflicts
        if 'tier_code' in update_dict and update_dict['tier_code'] != plan.tier_code:
            existing_plan = db.query(MembershipPlan).filter(
                MembershipPlan.tier_code == update_dict['tier_code'],
                MembershipPlan.id != plan_uuid
            ).first()
            if existing_plan:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Plan with tier code '{update_dict['tier_code']}' already exists"
                )
            
        for field, value in update_dict.items():
            setattr(plan, field, value)
            # For JSON columns, we need to flag them as modified so SQLAlchemy detects the change
            if field == 'perks' and value is not None:
                flag_modified(plan, 'perks')
            
        db.commit()
        db.refresh(plan)
        
        # Log the updated perks to verify
        logger.info(f"Plan {plan_id} updated. Current perks: {plan.perks}")
        
        # Calculate members count
        sub_count = db.query(MembershipSubscription).filter(
            MembershipSubscription.plan_id == plan_uuid,
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).count()
        
        # Convert to response model
        try:
            response = MembershipPlanResponse.model_validate(plan)
        except Exception as e:
            logger.error(f"Error validating plan model: {e}")
            response = MembershipPlanResponse(
                id=plan.id,
                tier_code=plan.tier_code,
                tier_name_en=plan.tier_name_en,
                tier_name_ar=plan.tier_name_ar,
                tier_order=plan.tier_order,
                description_en=plan.description_en,
                description_ar=plan.description_ar,
                price=plan.price,
                currency=plan.currency,
                plan_type=plan.plan_type,
                duration_days=plan.duration_days,
                purchase_limit=plan.purchase_limit,
                cashback_rate=plan.cashback_rate,
                points_multiplier=plan.points_multiplier,
                perks=plan.perks,
                color_hex=plan.color_hex,
                icon_url=plan.icon_url,
                is_active=plan.is_active,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
                members_count=0
            )
        
        response.members_count = sub_count
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")

@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a membership plan (Admin only).
    """
    try:
        # Convert plan_id to UUID if it's a string
        try:
            plan_uuid = uuid.UUID(plan_id) if isinstance(plan_id, str) else plan_id
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid plan ID format")
        
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_uuid).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        # Check if any subscriptions are using this plan
        subs_count = db.query(MembershipSubscription).filter(MembershipSubscription.plan_id == plan_uuid).count()
        if subs_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete plan with {subs_count} active subscription(s). Please deactivate the plan instead."
            )

        # Delete the plan using SQLAlchemy delete
        db.query(MembershipPlan).filter(MembershipPlan.id == plan_uuid).delete()
        db.commit()
        
        logger.info(f"Plan {plan_uuid} deleted successfully by admin {current_user.id}")
        return {"success": True, "message": "Plan deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete plan: {str(e)}")


# ============ User: Subscriptions ============

@router.post("/subscribe")
def subscribe_to_plan(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == subscription.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if not plan.is_active:
        raise HTTPException(status_code=400, detail="This plan is no longer active")

    # Business Logic for Payment would go here (Check wallet balance, etc.)
    # For now, we assume successful "PAID_INFINITE" subscription via Admin or Wallet deduction
    
    # Check existing
    existing_sub = db.query(MembershipSubscription).filter(MembershipSubscription.user_id == current_user.id).first()
    if existing_sub:
        # Here we would handle upgrade/downgrade logic
        # For now, simplistic replacement or error
        existing_sub.status = MembershipStatus.CANCELLED
    
    new_sub = MembershipSubscription(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        plan_id=plan.id,
        membership_number=f"MEM-{uuid.uuid4().hex[:8].upper()}",
        start_date=datetime.utcnow().date(),
        status=MembershipStatus.ACTIVE,
        # Infinite => no expiry, or far future
        expiry_date=None 
    )
    
    db.add(new_sub)
    db.commit()

    # Check for pending referral and award points
    try:
        pending_referral = db.query(Referral).filter(
            Referral.referred_user_id == current_user.id,
            Referral.status == "PENDING"
        ).first()

        if pending_referral:
            # Calculate Reward (10% of plan price)
            # Assuming price is float or decimal
            reward_points = int(float(plan.price) * 0.10) if plan.price else 0

            if reward_points > 0:
                # Award points to referrer
                referrer_balance = db.query(PointsBalance).filter(PointsBalance.user_id == pending_referral.referrer_id).first()
                if not referrer_balance:
                    referrer_balance = PointsBalance(
                        id=str(uuid.uuid4()),
                        user_id=pending_referral.referrer_id,
                        current_balance=0,
                        lifetime_earned=0,
                        lifetime_spent=0
                    )
                    db.add(referrer_balance)
                
                referrer_balance.current_balance += reward_points
                referrer_balance.lifetime_earned += reward_points

                transaction = PointsTransaction(
                    id=str(uuid.uuid4()),
                    user_id=pending_referral.referrer_id,
                    amount=reward_points,
                    transaction_type="EARN", # Make sure this matches Enum if used
                    description=f"Referral Bonus: {current_user.first_name} subscribed to {plan.tier_name_en}",
                    reference_id=pending_referral.id,
                    created_at=datetime.utcnow()
                )
                db.add(transaction)
                
                pending_referral.points_earned = reward_points
                logger.info(f"✅ Awarded {reward_points} points to referrer {pending_referral.referrer_id}")

            pending_referral.status = "ACTIVE"
            pending_referral.plan_id = str(plan.id)  # for competition: which tier was sold
            pending_referral.updated_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"❌ Error processing referral reward: {e}")
        # Don't fail the subscription if referral fails

    # Create notification for membership change
    try:
        notification_service = NotificationService(db)
        change_type = "subscribed" if not existing_sub else "upgraded"
        notification_service.notify_membership_changed(current_user, change_type)
    except Exception as e:
        logger.warning(f"Failed to create membership change notification: {e}")

    return {"message": "Subscribed successfully", "membership_number": new_sub.membership_number}

# ============ Admin: Subscriptions Management ============

from modules.memberships.schemas import SubscriptionResponse

@router.get("/subscriptions", response_model=Dict[str, Any])
def get_subscriptions(
    search: str = None,
    search_field: str = None, # 'username', 'email', 'user_id', 'membership_id'
    plan_filter: str = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(MembershipSubscription)\
        .join(MembershipSubscription.user)\
        .join(MembershipSubscription.plan)
        
    # Search Filter
    if search:
        search_term = f"%{search}%"
        if search_field == 'email':
            query = query.filter(User.email.ilike(search_term))
        elif search_field == 'username':
            # Assuming username is first_name + last_name for now or add username field
             query = query.filter(
                (User.first_name.ilike(search_term)) | 
                (User.last_name.ilike(search_term))
            )
        elif search_field == 'user_id':
            # Cast UUID to string for search if needed, or exact match
            # query = query.filter(User.id == search) 
             # For partial match on ID string:
             query = query.filter(func.cast(User.id, String).ilike(search_term))
        elif search_field == 'membership_id':
             query = query.filter(MembershipSubscription.membership_number.ilike(search_term))
        else:
            # Global search
            query = query.filter(
                (User.email.ilike(search_term)) | 
                (User.first_name.ilike(search_term)) | 
                (User.last_name.ilike(search_term)) |
                (MembershipSubscription.membership_number.ilike(search_term))
            )

    # Plan Filter
    if plan_filter:
        # plan_filter could be 'Silver', 'Gold' or literal plan ID
        # Let's assume passed as Plan ID or plan tier name
        # If it's a UUID:
        # query = query.filter(MembershipSubscription.plan_id == plan_filter)
        # If it's a name:
        query = query.filter(MembershipPlan.tier_name_en.ilike(f"%{plan_filter}%"))

    # Status Filter
    if status_filter:
        query = query.filter(MembershipSubscription.status == status_filter)

    total = query.count()
    users = query.order_by(MembershipSubscription.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
        
    print(f"DEBUG: get_subscriptions called. Found {len(users)} raw items.")
    serialized_items = []
    for u in users:
        try:
            serialized_items.append(SubscriptionResponse.model_validate(u))
        except Exception as e:
            print(f"DEBUG: Serialization Error for sub {u.id}: {e}")

    print(f"DEBUG: Returning {len(serialized_items)} serialized items.")
    return {
        "total": total,
        "items": serialized_items
    }

class BulkActionRequest(BaseModel):
    action: str # 'ACTIVATE', 'SUSPEND', 'DELETE', 'ASSIGN_PLAN'
    subscription_ids: List[str]
    target_plan_id: Optional[str] = None

@router.post("/subscriptions/bulk", response_model=Dict[str, Any])
def bulk_subscription_actions(
    req: BulkActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    valid_ids = []
    
    if req.action == 'DELETE':
        # Delete subscriptions
        db.query(MembershipSubscription).filter(
            MembershipSubscription.id.in_(req.subscription_ids)
        ).delete(synchronize_session=False)
        db.commit()
        return {"success": True, "message": f"Deleted {len(req.subscription_ids)} records"}
        
    elif req.action in ['ACTIVATE', 'SUSPEND']:
        new_status = MembershipStatus.ACTIVE if req.action == 'ACTIVATE' else MembershipStatus.CANCELLED 
        # Note: CANCELLED or EXPIRED for 'Suspend'? Let's use CANCELLED as 'Inactive' equivalent for now
        # Or if we have a SUSPENDED status. Let's stick to existing enums: ACTIVE, CANCELLED, EXPIRED
        if req.action == 'SUSPEND':
             new_status = MembershipStatus.CANCELLED
             
        stmt = update(MembershipSubscription).where(
            MembershipSubscription.id.in_(req.subscription_ids)
        ).values(status=new_status)
        
        db.execute(stmt)
        db.commit()
        return {"success": True, "message": f"Updated {len(req.subscription_ids)} records to {new_status}"}
        
    return {"success": False, "message": "Invalid action"}

@router.get("/stats", response_model=Dict[str, Any])
def get_membership_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get comprehensive membership statistics with accurate user counts per plan.
    """
    from shared.user_integration_service import UserIntegrationService

    integration_service = UserIntegrationService(db)
    stats = integration_service.get_membership_stats()

    # Add revenue calculation (estimation from active subscriptions)
    revenue_query = db.query(func.sum(MembershipPlan.price)).join(
        MembershipSubscription, MembershipSubscription.plan_id == MembershipPlan.id
    ).filter(MembershipSubscription.status == MembershipStatus.ACTIVE)
    total_revenue = revenue_query.scalar() or 0.0

    stats["total_revenue"] = float(total_revenue)

    # --- 1. Top Plan Calculation ---
    # Find plan with max user_count from stats['plans']
    top_plan = None
    max_users = -1
    for p in stats.get("plans", []):
        if p["user_count"] > max_users:
            max_users = p["user_count"]
            top_plan = p
    
    if top_plan:
        stats["top_plan"] = {
            "name_en": top_plan["name"],
            # We don't have ar name in stats['plans'] currently, query it or fetch all plans with details
            # Optimally we should have fetched it in integration_service, but for now let's query or use en
             "name_ar": top_plan["name"] # Placeholder if we don't have AR
        }
        # Fetch AR name from DB to be correct
        tp_db = db.query(MembershipPlan).filter(MembershipPlan.id == top_plan["id"]).first()
        if tp_db:
            stats["top_plan"]["name_ar"] = tp_db.tier_name_ar
    else:
        stats["top_plan"] = None

    # --- 2. Monthly Growth Calculation ---
    now = datetime.utcnow()
    start_of_this_month = datetime(now.year, now.month, 1)
    
    if now.month == 1:
        start_of_last_month = datetime(now.year - 1, 12, 1)
    else:
        start_of_last_month = datetime(now.year, now.month - 1, 1)
        
    # Count new active subscriptions this month
    new_this_month = db.query(MembershipSubscription).filter(
        MembershipSubscription.start_date >= start_of_this_month.date(),
        MembershipSubscription.status == MembershipStatus.ACTIVE
    ).count()
    
    # Count new active subscriptions last month (up to start of this month)
    new_last_month = db.query(MembershipSubscription).filter(
        MembershipSubscription.start_date >= start_of_last_month.date(),
        MembershipSubscription.start_date < start_of_this_month.date(),
        MembershipSubscription.status == MembershipStatus.ACTIVE
    ).count()
    
    growth_percent = 0.0
    if new_last_month > 0:
        growth_percent = ((new_this_month - new_last_month) / new_last_month) * 100
    elif new_this_month > 0:
        growth_percent = 100.0 # From 0 to something is 100% growth effectively (or infinite)
        
    stats["monthly_growth"] = round(growth_percent, 1)

    # --- 3. Recent Activity ---
    # Get last 5 actions (New Subscription or Upgrades)
    # We use created_at for new subs, need to tracking upgrades better if we want that
    # For now, let's list recent subscriptions by created_at (or start_date logic if available)
    # There is no 'created_at' on MembershipSubscription in the code I saw earlier? 
    # Wait, check models.py for MembershipSubscription fields. 
    # user_integration_service used created_at? No, I don't see created_at in the CREATE statement.
    # Ah, I need to check models.py. 
    # If no created_at, I will use start_date (which is a date, not datetime, so order might be loose).
    # Assuming standard fields exist via Base model or mixins?
    # Checking models.py is safer.
    
    recent_subs = db.query(MembershipSubscription).options(
        joinedload(MembershipSubscription.user),
        joinedload(MembershipSubscription.plan)
    ).order_by(MembershipSubscription.start_date.desc()).limit(5).all()
    
    activities = []
    for sub in recent_subs:
        if not sub.user or not sub.plan:
            continue
            
        # Determine strict "Ago" string
        # Since start_date is DATE, we fake the time or assume midnight
        # Ideally schema should have created_at DATETIME
        date_obj = sub.start_date
        if isinstance(date_obj, datetime):
            delta = now - date_obj
        else:
            delta = now.date() - date_obj
            
        days = delta.days
        time_str = "Today"
        if days == 0:
             time_str = "Today"
        elif days == 1:
             time_str = "Yesterday"
        elif days < 30:
             time_str = f"{days}d ago"
        else:
             time_str = f"{days // 30}mo ago"
             
        activities.append({
            "id": str(sub.id),
            "user": f"{sub.user.first_name} {sub.user.last_name}",
            "action_en": "Subscribed to",
            "action_ar": "اشترك في",
            "plan_en": sub.plan.tier_name_en,
            "plan_ar": sub.plan.tier_name_ar,
            "date": time_str
        })
        
    stats["recent_activity"] = activities

    return stats


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
        benefits_data = benefits.model_dump(exclude_unset=True)
        # Convert upgrade_to_plan_id string to UUID if provided
        if 'upgrade_to_plan_id' in benefits_data:
            if benefits_data['upgrade_to_plan_id']:
                try:
                    if isinstance(benefits_data['upgrade_to_plan_id'], str):
                        benefits_data['upgrade_to_plan_id'] = uuid.UUID(benefits_data['upgrade_to_plan_id'])
                except (ValueError, TypeError):
                    benefits_data['upgrade_to_plan_id'] = None
            else:
                benefits_data['upgrade_to_plan_id'] = None
        
        for key, value in benefits_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        benefits_data = benefits.model_dump(exclude_unset=True)
        # Convert upgrade_to_plan_id string to UUID if provided
        if 'upgrade_to_plan_id' in benefits_data and benefits_data['upgrade_to_plan_id']:
            try:
                if isinstance(benefits_data['upgrade_to_plan_id'], str):
                    benefits_data['upgrade_to_plan_id'] = uuid.UUID(benefits_data['upgrade_to_plan_id'])
            except (ValueError, TypeError):
                benefits_data['upgrade_to_plan_id'] = None
        
        new_benefits = MembershipBenefits(
            id=str(uuid.uuid4()),
            plan_id=plan_uuid,
            **benefits_data
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
