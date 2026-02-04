from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database.base import get_db
from modules.users.models import User, UserRole
from modules.memberships.models import MembershipSubscription, MembershipStatus, MembershipPlan
from modules.points.models import PointsBalance
from modules.chat.models import Conversation, ConversationStatus, Message
from modules.referrals.models import Referral
from modules.orders.models import Order
from modules.orders.schemas import OrderListResponse, OrderResponse
from shared.dependencies import require_employee_or_admin, require_admin
from modules.employee.models import EmployeeAdminMessage
from modules.notifications.models import NotificationTargetRole, NotificationType
from modules.notifications.schemas import NotificationCreate
from modules.notifications.service import NotificationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class EmployeeAdminMessageCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    urgent: bool = False
    target_employee_id: Optional[str] = None


class EmployeeAdminMessageResponse(BaseModel):
    id: str
    title: str
    message: str
    priority: str
    is_active: bool
    target_employee_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_by_role: Optional[str] = None
    created_at: Optional[str] = None


class EmployeeListItem(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


@router.get("/employees/list", response_model=List[EmployeeListItem])
def list_employees(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List employees for admin selection (sending targeted messages).
    """
    q = db.query(User).filter(User.role == UserRole.EMPLOYEE)
    if search:
        s = f"%{search}%"
        q = q.filter(
            (User.email.ilike(s)) |
            (User.first_name.ilike(s)) |
            (User.last_name.ilike(s)) |
            (User.phone.ilike(s))
        )

    rows = q.order_by(User.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 200)).all()
    out: List[EmployeeListItem] = []
    for u in rows:
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or (u.email or "")
        out.append(EmployeeListItem(id=str(u.id), name=name, email=u.email))
    return out


@router.get("/employees/admin-messages", response_model=List[EmployeeAdminMessageResponse])
def list_employee_admin_messages(
    limit: int = 5,
    include_inactive: bool = False,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db),
):
    """
    List admin messages for employee dashboard.
    - EMPLOYEE: sees broadcast messages + messages targeted to them
    - ADMIN: sees all (for debugging)
    """
    query = db.query(EmployeeAdminMessage).order_by(EmployeeAdminMessage.created_at.desc())

    if not include_inactive:
        query = query.filter(EmployeeAdminMessage.is_active == True)

    # EMPLOYEE can only see broadcast or targeted to them
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(
            (EmployeeAdminMessage.target_employee_id.is_(None)) |
            (EmployeeAdminMessage.target_employee_id == str(current_user.id))
        )

    rows = query.limit(min(max(limit, 1), 50)).all()

    results: List[EmployeeAdminMessageResponse] = []
    for r in rows:
        created_at = None
        if getattr(r, "created_at", None) and hasattr(r.created_at, "isoformat"):
            created_at = r.created_at.isoformat()
            if "Z" not in created_at and "+" not in created_at[-6:]:
                created_at = created_at + "Z"

        results.append(EmployeeAdminMessageResponse(
            id=str(r.id),
            title=r.title,
            message=r.message,
            priority=r.priority or "NORMAL",
            is_active=bool(r.is_active),
            target_employee_id=r.target_employee_id,
            created_by_user_id=r.created_by_user_id,
            created_by_role=r.created_by_role,
            created_at=created_at,
        ))

    return results


@router.get("/employees/admin-messages/{message_id}", response_model=EmployeeAdminMessageResponse)
def get_employee_admin_message(
    message_id: str,
    include_inactive: bool = False,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db),
):
    """
    Get a single admin message (used by employee to open message details).
    """
    q = db.query(EmployeeAdminMessage).filter(EmployeeAdminMessage.id == message_id)
    if not include_inactive:
        q = q.filter(EmployeeAdminMessage.is_active == True)

    msg = q.first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # EMPLOYEE can only see broadcast or targeted to them
    if current_user.role == UserRole.EMPLOYEE:
        if msg.target_employee_id is not None and str(msg.target_employee_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

    created_at = None
    if getattr(msg, "created_at", None) and hasattr(msg.created_at, "isoformat"):
        created_at = msg.created_at.isoformat()
        if "Z" not in created_at and "+" not in created_at[-6:]:
            created_at = created_at + "Z"

    return EmployeeAdminMessageResponse(
        id=str(msg.id),
        title=msg.title,
        message=msg.message,
        priority=msg.priority or "NORMAL",
        is_active=bool(msg.is_active),
        target_employee_id=msg.target_employee_id,
        created_by_user_id=msg.created_by_user_id,
        created_by_role=msg.created_by_role,
        created_at=created_at,
    )


@router.post("/employees/admin-messages", response_model=EmployeeAdminMessageResponse)
def create_employee_admin_message(
    payload: EmployeeAdminMessageCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin sends a message to employees (broadcast by default).
    """
    # Optional: validate target employee exists and is employee
    if payload.target_employee_id:
        target = db.query(User).filter(User.id == payload.target_employee_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target employee not found")
        role_val = target.role.value if hasattr(target.role, "value") else str(target.role)
        if role_val not in ["EMPLOYEE", "ADMIN", "SUPER_ADMIN"]:
            raise HTTPException(status_code=400, detail="Target user is not an employee")

    import uuid
    msg = EmployeeAdminMessage(id=str(uuid.uuid4()))

    msg.title = payload.title.strip()
    msg.message = payload.message.strip()
    msg.priority = "HIGH" if payload.urgent else "NORMAL"
    msg.is_active = True
    msg.target_employee_id = payload.target_employee_id
    msg.created_by_user_id = str(current_user.id)
    msg.created_by_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Also create a real Notification (and send Push) so it appears in employee notifications screen.
    try:
        notification_service = NotificationService(db)
        notification_service.create_notification(
            NotificationCreate(
                target_role=NotificationTargetRole.EMPLOYEE,
                target_user_id=payload.target_employee_id,  # optional (when targeting one employee)
                type=NotificationType.ADMIN_MESSAGE,
                title=msg.title,
                message=msg.message,
                priority=msg.priority or "NORMAL",
                action_url=f"/(employee)/admin-messages/{msg.id}",
                triggered_by_id=str(current_user.id),
                triggered_by_role=msg.created_by_role,
                related_entity_id=str(msg.id),
            )
        )
    except Exception as e:
        # Don't block message creation if push/notification fails
        logger.error(f"[EmployeeAdminMessage] Failed to create notification/push: {e}", exc_info=True)

    created_at = msg.created_at.isoformat() + "Z" if getattr(msg, "created_at", None) else datetime.utcnow().isoformat() + "Z"

    return EmployeeAdminMessageResponse(
        id=str(msg.id),
        title=msg.title,
        message=msg.message,
        priority=msg.priority,
        is_active=bool(msg.is_active),
        target_employee_id=msg.target_employee_id,
        created_by_user_id=msg.created_by_user_id,
        created_by_role=msg.created_by_role,
        created_at=created_at,
    )


@router.get("/employees/my-customers")
def get_my_assigned_customers(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get customers assigned to the current employee.
    Employees can only see their assigned customers.
    Admins can see all customers (for compatibility).
    """
    logger.info(f"[EmployeeCustomers] User {current_user.email} (Role: {current_user.role}) fetching assigned customers")
    
    query = db.query(User).options(
        joinedload(User.subscriptions).joinedload(MembershipSubscription.plan)
    ).filter(User.role == UserRole.CUSTOMER)
    
    # Filter by assigned employee (only for EMPLOYEE role, not ADMIN)
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(User.assigned_employee_id == str(current_user.id))
        logger.info(f"[EmployeeCustomers] Filtering by assigned_employee_id: {current_user.id}")
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) | 
            (User.first_name.ilike(search_term)) | 
            (User.last_name.ilike(search_term)) |
            (User.phone.ilike(search_term))
        )
    
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    logger.info(f"[EmployeeCustomers] Returning {len(users)} customers (total: {total})")
    
    # Format response
    result = []
    for user in users:
        # Get active subscription
        active_sub = next((s for s in user.subscriptions if s.status == MembershipStatus.ACTIVE), None)
        
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "avatar": user.avatar,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "membership": None
        }
        
        if active_sub and active_sub.plan:
            user_data["membership"] = {
                "plan_name": active_sub.plan.tier_name_en,
                "plan_name_en": active_sub.plan.tier_name_en,
                "plan_name_ar": active_sub.plan.tier_name_ar,
                "tier_code": active_sub.plan.tier_code,
                "plan_color": active_sub.plan.color_hex,
                "expiry_date": active_sub.expiry_date.isoformat() if active_sub.expiry_date else None
            }
        
        result.append(user_data)
    
    return {
        "users": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/employees/stats")
def get_employee_stats(
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get statistics for the current employee.
    """
    logger.info(f"[EmployeeStats] User {current_user.email} fetching stats")
    
    # Assigned customers count
    assigned_customers = db.query(User).filter(
        User.assigned_employee_id == str(current_user.id),
        User.role == UserRole.CUSTOMER
    ).count()
    
    # Referrals stats
    total_referrals = db.query(Referral).filter(
        Referral.referrer_id == str(current_user.id)
    ).count()
    
    active_referrals = db.query(Referral).filter(
        Referral.referrer_id == str(current_user.id),
        Referral.status == 'ACTIVE'
    ).count()
    
    referral_points = db.query(func.sum(Referral.points_earned)).filter(
        Referral.referrer_id == str(current_user.id)
    ).scalar() or 0
    
    # Chats stats
    active_chats = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id),
        Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.ASSIGNED])
    ).count()
    
    total_chats = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id)
    ).count()

    # Response rate (real calculation, not placeholder):
    # % of assigned conversations where employee replied at least once.
    if total_chats > 0:
        responded_chats = db.query(func.count(func.distinct(Conversation.id))).join(
            Message, Message.conversation_id == Conversation.id
        ).filter(
            Conversation.assigned_to == str(current_user.id),
            Message.sender_role == "EMPLOYEE",
        ).scalar() or 0
        response_rate = int(round((responded_chats / total_chats) * 100))
    else:
        response_rate = 100
    
    return {
        "assigned_customers": assigned_customers,
        "referrals": {
            "total": total_referrals,
            "active": active_referrals,
            "points_earned": int(referral_points)
        },
        "chats": {
            "active": active_chats,
            "total": total_chats
        },
        "response_rate": response_rate
    }


class CompetitionTierStat(BaseModel):
    plan_id: str
    tier_code: str
    tier_name_en: str
    tier_name_ar: str
    count: int

class CompetitionChartPoint(BaseModel):
    label: str
    count: int

class CompetitionStatsResponse(BaseModel):
    tiers: List[CompetitionTierStat]
    monthly_total: int
    yearly_total: int
    chart_data: List[CompetitionChartPoint]


class CompetitionCustomerItem(BaseModel):
    customer_name: str
    membership_number: str
    customer_avatar: Optional[str] = None
    start_date: Optional[str] = None
    referred_at: Optional[str] = None


@router.get("/employees/competition", response_model=CompetitionStatsResponse)
def get_competition_stats(
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Competition: for current employee, count of completed referrals (cards sold).
    Returns yearly count per tier and monthly total count.
    """
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    plans = db.query(MembershipPlan).filter(
        MembershipPlan.is_active == True
    ).order_by(MembershipPlan.tier_order).all()

    # Yearly counts per plan
    yearly_counts_by_plan = (
        db.query(Referral.plan_id, func.count(Referral.id).label("cnt"))
        .filter(
            Referral.referrer_id == str(current_user.id),
            Referral.status == "ACTIVE",
            Referral.plan_id.isnot(None),
            Referral.created_at >= start_of_year
        )
        .group_by(Referral.plan_id)
        .all()
    )
    yearly_map = {str(plan_id): cnt for plan_id, cnt in yearly_counts_by_plan}

    # Monthly total count
    monthly_total = db.query(func.count(Referral.id)).filter(
        Referral.referrer_id == str(current_user.id),
        Referral.status == "ACTIVE",
        Referral.created_at >= start_of_month
    ).scalar() or 0

    yearly_total = sum(yearly_map.values())

    # Chart Data: last 6 months
    chart_data = []
    for i in range(5, -1, -1):
        # Subtract months
        m = (now.month - i - 1) % 12 + 1
        y = now.year + (now.month - i - 1) // 12
        
        m_start = datetime(y, m, 1)
        if m == 12:
            m_end = datetime(y + 1, 1, 1)
        else:
            m_end = datetime(y, m + 1, 1)
            
        c = db.query(func.count(Referral.id)).filter(
            Referral.referrer_id == str(current_user.id),
            Referral.status == "ACTIVE",
            Referral.created_at >= m_start,
            Referral.created_at < m_end
        ).scalar() or 0
        
        month_label = m_start.strftime("%b")
        chart_data.append(CompetitionChartPoint(label=month_label, count=c))

    tiers_out = [
        CompetitionTierStat(
            plan_id=str(p.id),
            tier_code=p.tier_code or "",
            tier_name_en=p.tier_name_en or "",
            tier_name_ar=p.tier_name_ar or "",
            count=yearly_map.get(str(p.id), 0),
        )
        for p in plans
    ]

    return CompetitionStatsResponse(
        tiers=tiers_out,
        monthly_total=monthly_total,
        yearly_total=yearly_total,
        chart_data=chart_data
    )


@router.get("/employees/competition/plans/{plan_id}", response_model=List[CompetitionCustomerItem])
def get_competition_plan_customers(
    plan_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    List of customers (referred by this employee) who subscribed to this plan.
    Shows customer name, membership number, start date.
    """
    now = datetime.now()
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    referrals = (
        db.query(Referral)
        .options(joinedload(Referral.referred_user))
        .filter(
            Referral.referrer_id == str(current_user.id),
            Referral.status == "ACTIVE",
            Referral.plan_id == plan_id,
            Referral.created_at >= start_of_year
        )
        .order_by(Referral.created_at.desc())
        .all()
    )

    out: List[CompetitionCustomerItem] = []
    for r in referrals:
        name = "Unknown"
        if r.referred_user:
            name = f"{r.referred_user.first_name or ''} {r.referred_user.last_name or ''}".strip() or r.referred_user.email or name
        sub = (
            db.query(MembershipSubscription)
            .filter(
                MembershipSubscription.user_id == r.referred_user_id,
                MembershipSubscription.plan_id == plan_id,
            )
            .order_by(MembershipSubscription.start_date.desc())
            .first()
        )
        membership_number = ""
        if r.referred_user and r.referred_user.membership_id_display:
            membership_number = r.referred_user.membership_id_display
        elif sub:
            membership_number = sub.membership_number

        start_date = sub.start_date.isoformat() if sub and sub.start_date else None
        referred_at = r.created_at.isoformat() if r.created_at else None
        out.append(
            CompetitionCustomerItem(
                customer_name=name,
                membership_number=membership_number,
                customer_avatar=r.referred_user.avatar if r.referred_user else None,
                start_date=start_date,
                referred_at=referred_at,
            )
        )
    return out


@router.get("/employees/customers/{user_id}/details")
def get_customer_details(
    user_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific customer.
    Employees can only view details of their assigned customers.
    Admins can view any customer.
    """
    logger.info(f"[EmployeeCustomerDetails] User {current_user.email} requesting details for customer {user_id}")
    
    # Get the customer
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check permission: employee can only view assigned customers
    if current_user.role == UserRole.EMPLOYEE:
        if str(user.assigned_employee_id) != str(current_user.id):
            logger.warning(f"[EmployeeCustomerDetails] Employee {current_user.email} tried to access unassigned customer {user_id}")
            raise HTTPException(
                status_code=403,
                detail="You can only view details of customers assigned to you"
            )
    
    # Get membership
    from modules.memberships.models import MembershipSubscription, MembershipPlan
    subscription = db.query(MembershipSubscription).filter(
        MembershipSubscription.user_id == user_id
    ).order_by(MembershipSubscription.created_at.desc()).first()
    
    membership_data = None
    if subscription:
        plan = db.query(MembershipPlan).filter(
            MembershipPlan.id == subscription.plan_id
        ).first()
        
        if plan:
            membership_data = {
                "membership_number": subscription.membership_number,
                "plan_name": plan.tier_name_en,
                "plan_color": plan.color_hex,
                "tier_code": plan.tier_code,
                "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
                "end_date": subscription.expiry_date.isoformat() if subscription.expiry_date else None,
                "status": subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status)
            }
    
    # Get wallet balance
    from modules.wallet.models import Wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    wallet_data = {
        "balance": wallet.balance if wallet else 0.0,
        "currency": wallet.currency if wallet else "USD"
    }
    
    # Get points balance
    points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
    points_data = {
        "current_balance": points_balance.current_balance if points_balance else 0,
        "total_earned": points_balance.total_earned if points_balance else 0,
        "total_redeemed": points_balance.total_redeemed if points_balance else 0
    }
    
    # Get recent payments
    from modules.payments.models import Payment
    recent_payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    payments_data = [{
        "id": str(p.id),
        "amount": p.amount,
        "currency": p.currency,
        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in recent_payments]
    
    # Get referrals
    referrals = db.query(Referral).filter(
        Referral.referrer_id == user_id
    ).all()
    
    referral_count = len(referrals)
    referral_points = sum(r.points_earned for r in referrals if r.points_earned)
    
    # Club Gifts Balance
    from modules.cashback.models import ClubGiftRecord, ClubGiftStatus
    club_gift_records = db.query(ClubGiftRecord).filter(
        ClubGiftRecord.user_id == user_id,
        ClubGiftRecord.status == ClubGiftStatus.CREDITED
    ).all()
    cashback_balance = sum(record.cashback_amount for record in club_gift_records)
    
    response = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "avatar": user.avatar,
            "created_at": user.created_at.isoformat() if user.created_at else None
        },
        "membership": membership_data,
        "wallet": wallet_data,
        "points": points_data,
        "referrals": {
            "count": referral_count,
            "points": int(referral_points)
        },
        "recent_payments": payments_data,
        "cashback_balance": cashback_balance
    }
    
    logger.info(f"[EmployeeCustomerDetails] Successfully returned details for customer {user_id}")
    return response


@router.get("/employees/orders", response_model=List[OrderListResponse])
def get_employee_orders(
    search: Optional[str] = None,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get orders from assigned customers (employee) or all orders (admin).
    """
    logger.info(f"[EmployeeOrders] User {current_user.email} (Role: {current_user.role}) fetching orders")
    
    # Start with base query
    query = db.query(Order).options(joinedload(Order.user))
    
    # Filter by assigned customers (only for EMPLOYEE role)
    if current_user.role == UserRole.EMPLOYEE:
        # Get assigned customer IDs
        assigned_customer_ids = db.query(User.id).filter(
            User.assigned_employee_id == str(current_user.id),
            User.role == UserRole.CUSTOMER
        ).all()
        
        customer_ids = [str(cid[0]) for cid in assigned_customer_ids]
        
        if not customer_ids:
            # No assigned customers = no orders
            return []
        
        query = query.filter(Order.user_id.in_(customer_ids))
        logger.info(f"[EmployeeOrders] Filtering by {len(customer_ids)} assigned customers")
    
    # Apply filters
    if status:
        query = query.filter(Order.status == status)
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    
    if search:
        search_term = f"%{search}%"
        query = query.join(User, Order.user_id == User.id).filter(
            (Order.order_number.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.first_name.ilike(search_term)) |
            (User.last_name.ilike(search_term))
        )
    
    # Get results
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    logger.info(f"[EmployeeOrders] Returning {len(orders)} orders")
    
    return orders


@router.get("/employees/orders/{order_id}", response_model=OrderResponse)
def get_employee_order_details(
    order_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db),
):
    """
    Get order details for employee/admin.
    - EMPLOYEE: can only access orders belonging to customers assigned to them
    - ADMIN: can access all
    """
    order = db.query(Order).options(
        joinedload(Order.user),
        joinedload(Order.items),
    ).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.EMPLOYEE:
        if not order.user or str(order.user.assigned_employee_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="You can only view orders for customers assigned to you")

    return order
