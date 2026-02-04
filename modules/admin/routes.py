from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import uuid # Fixed: Import uuid for type casting
import json

from database.base import get_db
from modules.users.models import User, UserRole, UserStatus
from modules.orders.models import Order
from modules.bookings.models import Booking
from modules.payments.models import Payment, PaymentStatus
from modules.offers.models import Offer, OfferStatus
from modules.chat.models import Conversation, ConversationStatus
from modules.wallet.models import Wallet
from modules.wallet.service import WalletService
from modules.points.models import PointsBalance
from modules.points.service import PointsService
from modules.points.service import PointsService
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus
from shared.dependencies import require_admin, require_employee_or_admin
from shared.utils import hash_password

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats/overview")
def get_overview_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get overall platform statistics (admin only).
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    this_month = today.replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)
    
    # Users
    total_users = db.query(User).filter(User.role == UserRole.CUSTOMER).count()
    new_users_this_month = db.query(User).filter(
        User.role == UserRole.CUSTOMER,
        User.created_at >= this_month
    ).count()
    new_users_last_month = db.query(User).filter(
        User.role == UserRole.CUSTOMER,
        User.created_at >= last_month,
        User.created_at < this_month
    ).count()
    
    users_change = 0
    if new_users_last_month > 0:
        users_change = int(((new_users_this_month - new_users_last_month) / new_users_last_month) * 100)
    
    # Revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.PAID
    ).scalar() or 0
    
    revenue_this_month = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.PAID,
        Payment.created_at >= this_month
    ).scalar() or 0
    
    revenue_last_month = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.PAID,
        Payment.created_at >= last_month,
        Payment.created_at < this_month
    ).scalar() or 0
    
    revenue_change = 0
    if revenue_last_month > 0:
        revenue_change = int(((revenue_this_month - revenue_last_month) / revenue_last_month) * 100)
    
    # Bookings
    total_bookings = db.query(Booking).count()
    bookings_this_month = db.query(Booking).filter(
        Booking.created_at >= this_month
    ).count()
    bookings_last_month = db.query(Booking).filter(
        Booking.created_at >= last_month,
        Booking.created_at < this_month
    ).count()
    
    bookings_change = 0
    if bookings_last_month > 0:
        bookings_change = int(((bookings_this_month - bookings_last_month) / bookings_last_month) * 100)
    
    # Orders
    total_orders = db.query(Order).count()
    orders_this_month = db.query(Order).filter(
        Order.created_at >= this_month
    ).count()
    
    # Active Offers
    active_offers = db.query(Offer).filter(
        Offer.status == OfferStatus.ACTIVE,
        Offer.deleted_at.is_(None)
    ).count()
    
    # Open Chats
    open_chats = db.query(Conversation).filter(
        Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.ASSIGNED])
    ).count()
    
    return {
        "users": {
            "total": total_users,
            "this_month": new_users_this_month,
            "change_percent": users_change,
        },
        "revenue": {
            "total": float(total_revenue),
            "this_month": float(revenue_this_month),
            "change_percent": revenue_change,
        },
        "bookings": {
            "total": total_bookings,
            "this_month": bookings_this_month,
            "change_percent": bookings_change,
        },
        "orders": {
            "total": total_orders,
            "this_month": orders_this_month,
        },
        "offers": {
            "active": active_offers,
        },
        "chats": {
            "open": open_chats,
        }
    }


@router.get("/stats/revenue-chart")
def get_revenue_chart(
    days: int = 7,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get revenue data for chart (last N days).
    """
    chart_data = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(days - 1, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        revenue = db.query(func.sum(Payment.amount)).filter(
            Payment.status == PaymentStatus.PAID,
            Payment.created_at >= day_start,
            Payment.created_at < day_end
        ).scalar() or 0
        
        chart_data.append({
            "date": day_start.strftime('%Y-%m-%d'),
            "day": day_start.strftime('%a'),
            "revenue": float(revenue),
        })
    
    return chart_data


@router.get("/stats/recent-activities")
def get_recent_activities(
    limit: int = 10,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent platform activities.
    """
    activities = []
    
    # Recent Users
    recent_users = db.query(User).filter(
        User.role == UserRole.CUSTOMER
    ).order_by(User.created_at.desc()).limit(limit).all()
    
    for user in recent_users:
        activities.append({
            "type": "user",
            "icon": "person-add",
            "title": "New User Registered",
            "description": f"{user.first_name} {user.last_name} joined",
            "time": user.created_at.isoformat(),
        })
    
    # Recent Payments
    recent_payments = db.query(Payment).filter(
        Payment.status == PaymentStatus.PAID
    ).order_by(Payment.created_at.desc()).limit(limit).all()
    
    for payment in recent_payments:
        activities.append({
            "type": "payment",
            "icon": "card",
            "title": "Payment Received",
            "description": f"{payment.amount} {payment.currency}",
            "time": payment.created_at.isoformat(),
        })
    
    # Recent Bookings
    recent_bookings = db.query(Booking).order_by(Booking.created_at.desc()).limit(limit).all()
    
    for booking in recent_bookings:
        activities.append({
            "type": "booking",
            "icon": "airplane",
            "title": "New Booking",
            "description": f"Booking #{booking.booking_number}",
            "time": booking.created_at.isoformat(),
        })

    # Recent Membership Plans
    recent_plans = db.query(MembershipPlan).order_by(MembershipPlan.created_at.desc()).limit(limit).all()
    
    for plan in recent_plans:
        activities.append({
            "type": "membership",
            "icon": "layers", 
            "title": "New Plan Created",
            "description": f"Plan: {plan.tier_name_en}",
            "time": plan.created_at.isoformat(),
        })
    
    # Sort by time and limit
    activities.sort(key=lambda x: x['time'], reverse=True)
    activities.sort(key=lambda x: x['time'], reverse=True)
    return activities[:limit]


@router.get("/stats/transactions")
def get_recent_transactions(
    limit: int = 10,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent transactions (payments) for admin dashboard.
    """
    # Fetch Payments
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()
    
    # Fetch Orders (Invoices)
    from modules.orders.models import Order
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()

    combined = []
    
    for tx in payments:
        user_name = "Unknown"
        if tx.user:
            user_name = f"{tx.user.first_name} {tx.user.last_name}"
            
        combined.append({
            "id": str(tx.id),
            "user": user_name,
            "amount": tx.amount,
            "currency": tx.currency,
            "status": tx.status.value if hasattr(tx.status, 'value') else str(tx.status),
            "created_at": tx.created_at.isoformat(),
            "type": "PAYMENT"
        })

    for order in orders:
        user_name = "Unknown"
        if order.user:
            user_name = f"{order.user.first_name} {order.user.last_name}"
            
        combined.append({
            "id": str(order.id),
            "user": user_name,
            "amount": order.total_amount,
            "currency": order.currency,
            "status": order.payment_status.value if hasattr(order.payment_status, 'value') else str(order.payment_status),
            "created_at": order.created_at.isoformat(),
            "type": "INVOICE"
        })

    # Sort by recent
    combined.sort(key=lambda x: x['created_at'], reverse=True)
    return combined[:limit]


@router.get("/users")
def get_all_users(
    search: str = None,
    role: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users (admin or employee).
    """
    query = db.query(User).options(joinedload(User.subscriptions).joinedload(MembershipSubscription.plan))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) | 
            (User.first_name.ilike(search_term)) | 
            (User.last_name.ilike(search_term)) |
            (User.phone.ilike(search_term))
        )

    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
        
    # Restrict Employees to see only their assigned users
    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(User.assigned_employee_id == str(current_user.id))
    
    total = query.count()
    # Include Membership details using outer join
    # We want the *latest* subscription status and plan
    # Subquery or join logic might be needed. For simplicity, we can fetch active subscription.
    
    # Let's perform a join with filtering
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    # We need to manually populate plan info if we don't want to complex join the query object directly 
    # (since query is on User model). 
    # Or strict Eager Loading if relationships are set up.
    # Assuming User has `subscriptions` relationship.
    
    result_users = []
    for u in users:
        # Find latest subscription (if any) or active one
        latest_sub = None
        if u.subscriptions:
            # Sort by created_at desc
            sorted_subs = sorted(u.subscriptions, key=lambda s: s.created_at, reverse=True)
            latest_sub = sorted_subs[0] if sorted_subs else None
            
        plan_info = None
        subscription_info = None
        
        # Get points balance for this user
        from modules.points.models import PointsBalance
        points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == str(u.id)).first()

        plan_info = None
        if latest_sub and latest_sub.plan:
            plan_info = {
                "name": latest_sub.plan.tier_name_en,
                "name_ar": latest_sub.plan.tier_name_ar,
                "code": latest_sub.plan.tier_code,
                "color": latest_sub.plan.color_hex,
                "status": latest_sub.status.value if hasattr(latest_sub.status, "value") else str(latest_sub.status),
                "membership_id": latest_sub.membership_number,
                "end_date": latest_sub.expiry_date.isoformat() if latest_sub.expiry_date else None
            }

        result_users.append({
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,  # Real username
            "avatar": u.avatar,  # User avatar
            "phone": u.phone,
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
            "status": u.status.value if hasattr(u.status, 'value') else str(u.status),
            "created_at": u.created_at.isoformat(),
            "plan": plan_info,
            "points": {
                "current_balance": points_balance.current_balance if points_balance else 0,
                "total_earned": points_balance.total_earned if points_balance else 0,
                "total_redeemed": points_balance.total_redeemed if points_balance else 0
            } if points_balance else None
        })
    
    return {
        "total": total,
        "users": result_users
    }


@router.get("/employees")
def get_employees(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all employees for chat assignment.
    """
    employees = db.query(User).filter(
        User.role.in_([UserRole.EMPLOYEE, UserRole.ADMIN, UserRole.SUPER_ADMIN]),
        User.status == UserStatus.ACTIVE
    ).all()
    
    return [
        {
            "id": str(e.id),
            "name": f"{e.first_name} {e.last_name}",
            "email": e.email,
            "role": e.role.value if hasattr(e.role, 'value') else str(e.role),
        }
        for e in employees
    ]


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    new_role: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user role (admin only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    valid_roles = ["CUSTOMER", "EMPLOYEE", "ADMIN"]
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    user.role = UserRole(new_role)
    db.commit()
    
    logger.info(f"✅ User {user.email} role changed to {new_role} by {current_user.email}")
    
    return {"success": True, "message": f"User role updated to {new_role}"}


@router.post("/users/{user_id}/send-payment-request")
def send_payment_request(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Send payment request to user for their pending subscription.
    This will notify the user to complete payment for their membership plan.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find pending subscription
    subscription = db.query(MembershipSubscription).filter(
        MembershipSubscription.user_id == user_id,
        MembershipSubscription.status == MembershipStatus.PENDING_PAYMENT
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=400, detail="No pending subscription found for this user")
    
    # Get plan details
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == subscription.plan_id).first()
    
    # TODO: Send actual notification (email/push)
    # For now, we'll just log and return success
    logger.info(f"📧 Payment request sent to {user.email} for plan: {plan.tier_name_en if plan else 'Unknown'}")
    
    return {
        "success": True,
        "message": f"Payment request sent to {user.email}",
        "subscription": {
            "id": str(subscription.id),
            "membership_number": subscription.membership_number,
            "plan_name": plan.tier_name_en if plan else "Unknown",
            "price": plan.price if plan else 0,
            "currency": plan.currency if plan else "USD",
            "status": subscription.status.value
        }
    }

@router.get("/users/{user_id}/details")
def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get full details for a specific user (admin only).
    Includes: Profile, Membership, Wallet, Points, Recent Payments.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Membership
    # Explicitly query for the latest subscription with plan eager loaded
    latest_sub = db.query(MembershipSubscription)\
        .options(joinedload(MembershipSubscription.plan))\
        .filter(MembershipSubscription.user_id == user_id)\
        .order_by(MembershipSubscription.created_at.desc())\
        .first()
        
    membership_data = None
    if latest_sub:
        plan_name = "Unknown Plan"
        plan_color = "#999"
        if latest_sub.plan:
            plan_name = latest_sub.plan.tier_name_en
            plan_color = latest_sub.plan.color_hex

        membership_data = {
            "plan_id": str(latest_sub.plan.id) if latest_sub.plan else None,
            "plan_name": plan_name,
            "plan_color": plan_color,
            "status": latest_sub.status.value if hasattr(latest_sub.status, "value") else str(latest_sub.status),
            "start_date": latest_sub.start_date.isoformat() if latest_sub.start_date else None,
            "end_date": latest_sub.expiry_date.isoformat() if latest_sub.expiry_date else None, # Fixed: expiry_date
            "progress": 0
        }

    # Wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    
    # Aggressive Fix: Ensure USD for empty wallets
    if wallet and wallet.balance == 0 and wallet.currency != "USD":
        wallet.currency = "USD"
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
        
    wallet_data = {
        "balance": wallet.balance if wallet else 0.0,
        "currency": "USD" if ((wallet and wallet.balance == 0) or (wallet and wallet.currency == "EGP")) else (wallet.currency if wallet else "USD")
    }

    # Points
    points = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
    points_data = {
        "current_balance": points.current_balance if points else 0,
        "total_earned": points.total_earned if points else 0
    }

    # Club Gifts (formerly Cashback)
    from modules.cashback.models import ClubGiftRecord, ClubGiftStatus
    club_gift_records = db.query(ClubGiftRecord).filter(
        ClubGiftRecord.user_id == user_id,
        ClubGiftRecord.status == ClubGiftStatus.CREDITED
    ).all()
    club_gift_balance = sum(record.cashback_amount for record in club_gift_records)

    # Payments (Recent 5)
    # Payments / Transactions (Recent 10)
    # Use WalletTransaction as the source of truth for financial activity
    from modules.wallet.models import WalletTransaction
    
    payments_data = []

    # 1. Fetch Wallet Transactions
    wallet_txs = db.query(WalletTransaction).filter(
        WalletTransaction.user_id == user_id
    ).order_by(WalletTransaction.created_at.desc()).limit(10).all()

    for tx in wallet_txs:
        # Determine display method/type
        method_display = tx.transaction_type.value
        # Use reference type for more context if available
        if tx.reference_type and tx.reference_type != "MANUAL":
            method_display = f"{tx.transaction_type.value} ({tx.reference_type})"
            
        payments_data.append({
            "id": str(tx.id),
            "amount": tx.amount,
            "currency": tx.currency,
            "status": tx.status.value if hasattr(tx.status, "value") else str(tx.status),
            "date": tx.created_at.isoformat(),
            "method": method_display,
            "source": "WALLET"
        })

    # 2. Fetch Direct Payments (Invoices)
    direct_payments = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(Payment.created_at.desc()).limit(10).all()

    for p in direct_payments:
        # Avoid duplicates if payment is also a wallet deposit (though unlikely to duplicate ID)
        # We just list them as "Direct Payment"
        payments_data.append({
            "id": str(p.id),
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "date": p.created_at.isoformat(),
            "method": f"Direct Payment ({p.payment_method.value if hasattr(p.payment_method, 'value') and p.payment_method else 'N/A'})",
            "source": "PAYMENT"
        })

    # 3. Fetch Orders (Invoices)
    from modules.orders.models import Order
    user_orders = db.query(Order).filter(
        Order.user_id == user_id
    ).order_by(Order.created_at.desc()).limit(10).all()

    for o in user_orders:
        payments_data.append({
            "id": str(o.id),
            "amount": o.total_amount,
            "currency": o.currency,
            "status": o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status),
            "date": o.created_at.isoformat(),
            "method": f"Invoice #{o.order_number}",
            "source": "INVOICE"
        })

    # 4. Sort and limit to top 10
    payments_data.sort(key=lambda x: x['date'], reverse=True)
    payments_data = payments_data[:10]

    # Referrals
    from modules.referrals.models import Referral
    referrals_query = db.query(Referral).filter(Referral.referrer_id == user_id)
    referral_count = referrals_query.count()
    referral_points = db.query(func.sum(Referral.points_earned)).filter(Referral.referrer_id == user_id).scalar() or 0

    # Fetch assigned employee details if exists
    assigned_employee_data = None
    if user.assigned_employee_id:
        assigned_emp = db.query(User).filter(User.id == user.assigned_employee_id).first()
        if assigned_emp:
            assigned_employee_data = {
                "id": str(assigned_emp.id),
                "name": f"{assigned_emp.first_name} {assigned_emp.last_name}",
                "email": assigned_emp.email
            }
    
    response = {
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": f"{user.first_name} {user.last_name}",
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "avatar": user.avatar,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "joined_at": user.created_at.isoformat(),
            "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
            "assigned_employee_id": user.assigned_employee_id
        },
        "assigned_employee": assigned_employee_data,
        "membership": membership_data,
        "points": points_data,
        "cashback_balance": club_gift_balance,
        "wallet": wallet_data,
        "referrals": {
            "count": referral_count,
            "points_earned": referral_points
        },
        "recent_payments": payments_data
    }
    
    return response


@router.get("/users/{user_id}/competition")
def get_user_competition(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: get competition stats (cards sold per tier) for a given user (employee).
    Same structure as employee competition endpoint but for any user_id.
    """
    from modules.referrals.models import Referral
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    plans = db.query(MembershipPlan).filter(
        MembershipPlan.is_active == True
    ).order_by(MembershipPlan.tier_order).all()
    counts_by_plan = (
        db.query(Referral.plan_id, func.count(Referral.id).label("cnt"))
        .filter(
            Referral.referrer_id == str(user_id),
            Referral.status == "ACTIVE",
            Referral.plan_id.isnot(None),
        )
        .group_by(Referral.plan_id)
        .all()
    )
    count_map = {str(plan_id): cnt for plan_id, cnt in counts_by_plan}
    return [
        {
            "plan_id": str(p.id),
            "tier_code": p.tier_code or "",
            "tier_name_en": p.tier_name_en or "",
            "tier_name_ar": p.tier_name_ar or "",
            "count": count_map.get(str(p.id), 0),
        }
        for p in plans
    ]


@router.post("/users")
def create_user(
    user_data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user with full details (Admin only).
    Handles: Profile, Role, Status, Membership Subscription, Points, and Wallet atomically.
    """
    logger.info(f"Creating user with integrated service: {user_data.get('email', 'unknown')}")

    try:
        from shared.user_integration_service import UserIntegrationService

        integration_service = UserIntegrationService(db)
        result = integration_service.create_user_with_membership(user_data, created_by_admin=True)

        logger.info(f"✅ User creation completed successfully: {result['user']['email']}")
        return result

    except Exception as e:
        logger.error(f"❌ User creation failed: {str(e)}")
        # Let the service handle transaction rollback
        if hasattr(e, 'detail'):
            raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    user_data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user with integrated membership, points, and wallet handling.
    """
    logger.info(f"Updating user {user_id} with integrated service")
    logger.info(f"Received data keys: {list(user_data.keys())}")
    logger.info(f"Avatar in data: {'Yes' if 'avatar' in user_data else 'No'}")
    if 'avatar' in user_data:
        avatar_value = user_data['avatar']
        if avatar_value:
            logger.info(f"Avatar length: {len(str(avatar_value))} chars, preview: {str(avatar_value)[:50]}...")
        else:
            logger.info(f"Avatar is None/empty")

    try:
        from shared.user_integration_service import UserIntegrationService

        integration_service = UserIntegrationService(db)
        result = integration_service.update_user_with_membership(user_id, user_data)

        logger.info(f"✅ User update completed successfully for user {user_id}")
        logger.info(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        return result

    except Exception as e:
        logger.error(f"❌ User update failed for {user_id}: {str(e)}")
        # Let the service handle transaction rollback
        if hasattr(e, 'detail'):
            raise HTTPException(status_code=400, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Hard delete a user (permanent removal from database) - Admin only.
    WARNING: This action cannot be undone!
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")
        
        # Store email for logging before deletion
        user_email = user.email
        
        # Hard delete - permanently remove from database
        # SQLAlchemy will handle cascade deletes for related records (subscriptions, etc.)
        db.delete(user)
        db.commit()
        
        logger.warning(f"User {user_email} (ID: {user_id}) permanently deleted by {current_user.email}")
        return {"success": True, "message": "User permanently deleted from database"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.put("/users/{user_id}/assign-employee")
def assign_employee(
    user_id: str,
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Assign an employee to a customer (Admin only).
    """
    employee_id = data.get("employee_id")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=400, detail="Can only assign employees to customers")

    if employee_id:
        employee = db.query(User).filter(User.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
            
        if employee.role not in [UserRole.EMPLOYEE, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
             raise HTTPException(status_code=400, detail="Selected user is not an employee")
             
        user.assigned_employee_id = employee_id
        logger.info(f"✅ Assigned employee {employee.email} to user {user.email}")
    else:
        # Unassign
        user.assigned_employee_id = None
        logger.info(f"✅ Unassigned employee from user {user.email}")
        
    db.commit()
    db.refresh(user)
    
    logger.info(f"📤 Returning assignment response for user {user.email}")
    
    return {
        "success": True, 
        "message": "Employee assignment updated successfully",
        "assigned_employee_id": user.assigned_employee_id
    }


@router.get("/users/{user_id}/assigned-customers")
def get_assigned_customers(
    user_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get all customers assigned to a specific employee.
    """
    customers = db.query(User).filter(
        User.assigned_employee_id == user_id,
        User.role == UserRole.CUSTOMER
    ).all()
    
    return [
        {
            "id": str(c.id),
            "name": f"{c.first_name} {c.last_name}",
            "email": c.email,
            "phone": c.phone,
            "avatar": c.avatar,
            "status": c.status.value,
        }
        for c in customers
    ]


# ============ Points Management ============

@router.post("/points/add")
def add_points_to_user(
    user_id: str,
    points: int,
    reason: str = "Admin adjustment",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Add points to a user's account.
    """
    from modules.points.service import PointsService
    
    points_service = PointsService(db)
    transaction = points_service.add_bonus_points(
        user_id=user_id,
        points=points,
        description_en=reason,
        created_by_user_id=str(current_user.id)
    )
    
    return {
        "status": "success",
        "message": f"Added {points} points to user",
        "transaction_id": str(transaction.id),
        "new_balance": transaction.balance_after
    }


@router.post("/points/remove")
def remove_points_from_user(
    user_id: str,
    points: int,
    reason: str = "Admin adjustment",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Remove points from a user's account.
    """
    from modules.points.service import PointsService
    from modules.points.models import PointsTransactionType
    
    points_service = PointsService(db)

    # Deduct points using the service method
    transaction = points_service.deduct_points(
        user_id=user_id,
        points=points,
        description_en=reason,
        created_by_user_id=str(current_user.id)
    )
    
    return {
        "status": "success",
        "message": f"Removed {points} points from user",
        "transaction_id": str(transaction.id),
        "new_balance": transaction.balance_after
    }


@router.get("/points/history/all")
def get_all_points_history(
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Get latest points transactions for ALL users.
    """
    from modules.points.models import PointsTransaction
    
    transactions = db.query(PointsTransaction)\
        .options(joinedload(PointsTransaction.user))\
        .order_by(PointsTransaction.created_at.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": str(t.id),
            "user_id": str(t.user_id),
            "user_name": f"{t.user.first_name} {t.user.last_name}" if t.user else "Unknown User",
            "user_avatar": t.user.avatar if t.user else None,
            "type": t.transaction_type,
            "points": t.points,
            "description": t.description_en,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in transactions
    ]
@router.get("/points/history/{user_id}")
def get_user_points_history(
    user_id: str,
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Get points transaction history for a user.
    """
    from modules.points.service import PointsService
    
    points_service = PointsService(db)
    transactions = points_service.get_transactions(user_id=user_id, limit=limit)
    
    return {
        "user_id": user_id,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.transaction_type,
                "points": t.points,
                "balance_before": t.balance_before,
                "balance_after": t.balance_after,
                "description": t.description_en,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ]
    }


# ============ Cashback Management ============

@router.post("/cashback/add")
def add_cashback_to_user(
    user_id: str,
    amount: float,
    reason: str = "Admin bonus",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Add cashback to a user's wallet (Cashback Balance).
    """
    from modules.cashback.service import CashbackService
    
    cashback_service = CashbackService(db)
    record = cashback_service.admin_add_cashback(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_user_id=str(current_user.id)
    )
    
    return {
        "status": "success",
        "message": f"Added {amount} USD cashback to user's balance",
        "cashback_id": str(record.id)
    }


@router.post("/cashback/remove")
def remove_cashback_from_user(
    user_id: str,
    amount: float,
    reason: str = "Admin adjustment",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Deduct amount from user's cashback balance.
    """
    from modules.cashback.service import CashbackService
    
    cashback_service = CashbackService(db)
    result = cashback_service.admin_remove_cashback(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_user_id=str(current_user.id)
    )
    
    return {
        "status": "success",
        "message": f"Removed {amount} USD from user's cashback balance",
        "details": result
    }


@router.get("/cashback/history/all")
def get_all_cashback_history(
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Get latest Club Gift records for ALL users (formerly Cashback).
    """
    from modules.cashback.models import ClubGiftRecord
    
    records = db.query(ClubGiftRecord)\
        .options(joinedload(ClubGiftRecord.user))\
        .order_by(ClubGiftRecord.created_at.desc())\
        .limit(limit)\
        .all()
    
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "user_name": f"{r.user.first_name} {r.user.last_name}" if r.user else "Unknown User",
            "user_avatar": r.user.avatar if r.user else None,
            "amount": r.cashback_amount,
            "status": r.status,
            "reference_type": r.reference_type,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
@router.get("/cashback/history/{user_id}")
def get_user_cashback_history(
    user_id: str,
    limit: int = 50,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Get cashback history for a user.
    """
    from modules.cashback.service import CashbackService
    
    cashback_service = CashbackService(db)
    records = cashback_service.get_user_cashback(user_id=user_id, limit=limit)
    
    return {
        "user_id": user_id,
        "records": [
            {
                "id": str(r.id),
                "amount": r.cashback_amount,
                "status": r.status,
                "reference_type": r.reference_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "credited_at": r.credited_at.isoformat() if r.credited_at else None
            }
            for r in records
        ]
    }


@router.get("/users/{user_id}/assigned-customers")
def get_assigned_customers(
    user_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get all customers assigned to a specific employee.
    Employees can only see their own assigned customers.
    Admins can see any employee's assigned customers.
    """
    # Authorization check
    current_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if current_role == "EMPLOYEE" and str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Employees can only view their own assigned customers")
    
    # Get assigned customers
    customers = db.query(User).filter(
        User.assigned_employee_id == user_id,
        User.role == UserRole.CUSTOMER,
        User.status == UserStatus.ACTIVE
    ).all()
    
    return {
        "employee_id": user_id,
        "total": len(customers),
        "customers": [
            {
                "id": str(c.id),
                "name": f"{c.first_name} {c.last_name}",
                "email": c.email,
                "phone": c.phone,
                "avatar": c.avatar
            }
            for c in customers
        ]
    }


# ============ Payments Management ============

@router.get("/payments")
def getAllPayments(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all payments (Admin only).
    Delegates to the payments module endpoint.
    """
    from modules.payments.routes import list_all_payments
    return list_all_payments(status=status, limit=limit, offset=offset, db=db, current_user=current_user)


@router.get("/payments/{payment_id}")
def getPaymentById(
    payment_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get payment details by ID (Admin only).
    Delegates to the payments module endpoint.
    """
    from modules.payments.routes import get_payment_details
    return get_payment_details(payment_id=payment_id, db=db, current_user=current_user)


@router.post("/users/{user_id}/attribute-referral")
def attribute_referral(
    user_id: str,
    data: dict = Body(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin: Manually attribute a membership sale to an employee.
    This creates or updates a Referral record to mark it as ACTIVE.
    """
    employee_id = data.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="Employee ID is required")

    # 1. Verify customer
    customer = db.query(User).filter(User.id == user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 2. Verify employee
    employee = db.query(User).filter(User.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.role not in [UserRole.EMPLOYEE, UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=400, detail="Target user is not an employee")

    # 3. Get customer's active subscription
    subscription = db.query(MembershipSubscription).filter(
        MembershipSubscription.user_id == user_id,
        MembershipSubscription.status == MembershipStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Customer does not have an active membership to attribute")

    # 4. Find or create Referral record
    from modules.referrals.models import Referral
    referral = db.query(Referral).filter(
        Referral.referred_user_id == user_id
    ).first()

    if referral:
        # Update existing referral (even if it was pending to someone else, 
        # admin manual action overrides it)
        referral.referrer_id = employee_id
        referral.status = "ACTIVE"
        referral.plan_id = str(subscription.plan_id)
    else:
        # Create new referral
        referral = Referral(
            id=str(uuid.uuid4()),
            referrer_id=employee_id,
            referred_user_id=user_id,
            status="ACTIVE",
            plan_id=str(subscription.plan_id),
            points_earned=0 
        )
        db.add(referral)

    db.commit()
    
    logger.info(f"✅ Manually attributed sale of {subscription.plan_id} to employee {employee.email} for customer {customer.email}")
    
    return {
        "success": True,
        "message": f"Sale attributed to {employee.first_name} {employee.last_name}",
        "referral_id": referral.id
    }

