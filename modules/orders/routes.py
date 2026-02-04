from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
import uuid

from database.base import get_db
from modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus as OrderPaymentStatus, OrderType as ModelOrderType
from modules.orders.schemas import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    OrderItemResponse,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    OrderUpdate
)
from modules.payments.service import PaymentService
from modules.points.service import PointsService
from modules.wallet.service import WalletService
from modules.cashback.service import ClubGiftService
from modules.notifications.service import NotificationService
from modules.users.models import User
from shared.utils import generate_unique_number
from shared.exceptions import NotFoundException, BadRequestException
from shared.dependencies import get_current_user, get_admin_user, require_active_membership
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Customer Endpoints ============

@router.get("/me", response_model=List[OrderListResponse])
def get_my_orders(
    payment_status: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current customer's orders.
    Optionally filter by payment_status (e.g. UNPAID, PENDING, PAID).
    
    Requires: Bearer token (any authenticated user)
    """
    query = db.query(Order).filter(Order.user_id == str(current_user.id))
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
        
    orders = query.options(joinedload(Order.user)).order_by(Order.created_at.desc()).all()
    
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get order details.
    
    Requires: Bearer token
    - Customers can only see their own orders
    - Admins can see any order
    """
    order = db.query(Order).options(joinedload(Order.user)).filter(Order.id == order_id).first()
    
    if not order:
        raise NotFoundException("Order not found")
    
    # Check access: customer can only see their own orders
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "CUSTOMER" and str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders"
        )
    
    return order


@router.post("/{order_id}/pay", response_model=InitiatePaymentResponse)
def initiate_order_payment(
    order_id: str,
    request: InitiatePaymentRequest,
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    Initiate payment for an order.
    
    Requires: Bearer token
    Returns: payment_url to be opened in mobile WebView
    """
    payment_service = PaymentService(db)
    
    result = payment_service.initiate_order_payment(
        order_id=order_id,
        user_id=str(current_user.id),
        payment_method_id=request.payment_method_id
    )
    
    return result


# ============ Admin Endpoints ============

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Create a new order (admin creates for customer).
    
    Requires: Bearer token with ADMIN or SUPER_ADMIN role
    
    This is for the 'My Orders' feature where admin issues manual invoices.
    """
    # Services
    points_service = PointsService(db)
    wallet_service = WalletService(db)
    club_gift_service = ClubGiftService(db)
    
    # Generate unique order number
    # Find the maximum sequence number for current year to avoid duplicates
    from sqlalchemy import func, extract
    current_year = datetime.now().year
    prefix = f"ORD-{current_year}-"
    
    # Get the highest sequence number for this year
    max_order = db.query(Order).filter(
        Order.order_number.like(f"{prefix}%")
    ).order_by(Order.order_number.desc()).first()
    
    if max_order:
        # Extract sequence from existing order number (e.g., "ORD-2026-000004" -> 4)
        try:
            existing_seq = int(max_order.order_number.split('-')[-1])
            sequence = existing_seq + 1
        except (ValueError, IndexError):
            # Fallback if parsing fails
            sequence = db.query(Order).filter(
                Order.order_number.like(f"{prefix}%")
            ).count() + 1
    else:
        sequence = 1
    
    # Generate order number and ensure uniqueness (retry if collision)
    max_retries = 10
    for attempt in range(max_retries):
        order_number = generate_unique_number("ORD", sequence)
        
        # Check if this order number already exists
        existing = db.query(Order).filter(Order.order_number == order_number).first()
        if not existing:
            break
        
        # If exists, increment sequence and try again
        sequence += 1
        if attempt == max_retries - 1:
            # Last attempt failed, use timestamp-based fallback
            import time
            order_number = f"ORD-{current_year}-{int(time.time()) % 1000000:06d}"
            logger.warning(f"Order number collision, using timestamp-based number: {order_number}")
    
    # Calculate totals
    subtotal = sum(item.quantity * item.unit_price for item in order_data.items)
    
    # Handle Free Orders
    if order_data.is_free:
        # Import validator
        from shared.validators import validate_currency
        
        # Free orders: zero out all amounts and mark as paid
        tax_amount = 0
        discount_amount = 0
        total_amount = 0
        currency = validate_currency(order_data.currency)
        currency = validate_currency(order_data.currency)
        order_id = str(uuid.uuid4())
        
        try:
            # Create order
            order = Order(
                id=uuid.UUID(order_id),  # Fixed: Convert to UUID object
                order_number=order_number,
                user_id=uuid.UUID(order_data.user_id), # Fixed: Convert to UUID object
                created_by_user_id=current_user.id, # id is already UUID
                order_type=ModelOrderType(order_data.order_type.value),
                status=OrderStatus.DRAFT,
                subtotal=0,
                tax_amount=0,
                discount_amount=0,
                total_amount=0,
                currency=currency,
                notes_ar=order_data.notes_ar,
                notes_en=order_data.notes_en,
                payment_status=OrderPaymentStatus.PAID,
                paid_at=datetime.utcnow(),
                due_date=order_data.due_date,
                is_free=True
            )
            
            db.add(order)
            db.flush()
            
            # Create order items
            for item_data in order_data.items:
                item = OrderItem(
                    id=uuid.uuid4(), # Fixed: Convert to UUID object (uuid4 returns UUID object)
                    order_id=order.id, # order.id is UUID
                    description_ar=item_data.description_ar,
                    description_en=item_data.description_en,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    total_price=round(item_data.quantity * item_data.unit_price, 2),
                    currency=currency
                )
                db.add(item)
            
            db.commit()
            db.refresh(order)
            
            logger.info(f"✅ Free order created by admin {current_user.email}: {order_number}")
            
            # Notify User
            try:
                notification_service = NotificationService(db)
                target_user = db.query(User).get(order.user_id)
                if target_user:
                    notification_service.notify_invoice_created(
                        user=target_user,
                        invoice=order
                    )
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {e}")

            return order
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create free order: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create free order: {str(e)}")
    
    # Normal (Paid) Order Flow
    tax_rate = order_data.tax_rate if order_data.tax_rate is not None else 14.0
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    
    # Get and validate currency
    from shared.validators import validate_currency
    currency = validate_currency(order_data.currency)
    
    # Initial discount (manual + others)
    discount_amount = order_data.discount_amount or 0
    
    # Create preliminary order object to get ID (needed for transaction references)
    order_id = str(uuid.uuid4())
    
    # Process Points Redemption
    points_redeemed_value = 0
    if order_data.points_to_use and order_data.points_to_use > 0:
        # Get user's membership to calculate points value
        from modules.memberships.models import MembershipSubscription, MembershipPlan
        
        user_subscription = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == order_data.user_id
        ).first()
        
        # Calculate points rate based on membership plan
        if user_subscription and user_subscription.plan:
            plan = user_subscription.plan
            # Calculate rate: price / initial_points
            # Example: Silver = 2000 USD / 1500 points = 1.33 USD per point
            if plan.initial_points and plan.initial_points > 0:
                POINTS_RATE = plan.price / plan.initial_points
                logger.info(f"Using membership-based points rate: 1 point = {POINTS_RATE:.2f} {plan.currency} (Plan: {plan.tier_name_en})")
            else:
                # Fallback to 1:1 if plan has no initial_points
                POINTS_RATE = 1.0
                logger.warning(f"Plan {plan.tier_name_en} has no initial_points, using default rate 1:1")
        else:
            # Fallback to 1:1 if user has no membership
            POINTS_RATE = 1.0
            logger.warning(f"User {order_data.user_id} has no membership, using default points rate 1:1")
        
        points_redeemed_value = order_data.points_to_use * POINTS_RATE
        
        logger.info(f"Processing points redemption: {order_data.points_to_use} points for user {order_data.user_id}")
        
        try:
            points_service.redeem_points(
                user_id=order_data.user_id,
                points=order_data.points_to_use,
                reference_type="ORDER_PAYMENT",
                reference_id=order_id,
                description_en=f"Payment for Order {order_number}",
                description_ar=f"دفع للفاتورة {order_number}"
            )
            discount_amount += points_redeemed_value
            logger.info(f"✅ Successfully redeemed {order_data.points_to_use} points (value: {points_redeemed_value:.2f} {currency})")
        except Exception as e:
            logger.error(f"❌ Failed to redeem points: {e}", exc_info=True)
            raise BadRequestException(f"Failed to redeem points: {str(e)}")

    # Process Wallet Usage (Real Money)
    wallet_used_amount = 0
    if order_data.wallet_to_use and order_data.wallet_to_use > 0:
        logger.info(f"Processing wallet withdrawal: {order_data.wallet_to_use} {currency} for user {order_data.user_id}")
        
        try:
            wallet_service.withdraw(
                user_id=order_data.user_id,
                amount=order_data.wallet_to_use,
                reference_type="ORDER_PAYMENT",
                reference_id=order_id,
                description_en=f"Payment for Order {order_number}",
                description_ar=f"دفع للفاتورة {order_number}"
            )
            discount_amount += order_data.wallet_to_use
            wallet_used_amount = order_data.wallet_to_use
            logger.info(f"✅ Successfully withdrew {order_data.wallet_to_use} from wallet")
        except Exception as e:
            logger.error(f"❌ Failed to deduct wallet balance: {e}", exc_info=True)
            raise BadRequestException(f"Failed to deduct wallet balance: {str(e)}")

    # Process Club Gift Usage (formerly Cashback)
    club_gift_used_amount = 0
    if order_data.cashback_to_use and order_data.cashback_to_use > 0:
        logger.info(f"Processing Club Gift deduction: {order_data.cashback_to_use} {currency} for user {order_data.user_id}")
        
        try:
            # Use admin_remove_club_gift logic to deduct from Club Gift balance
            club_gift_service.admin_remove_club_gift(
                user_id=order_data.user_id,
                amount=order_data.cashback_to_use,
                reason=f"Payment for Order {order_number}",
                admin_user_id=str(current_user.id)
            )
            discount_amount += order_data.cashback_to_use
            club_gift_used_amount = order_data.cashback_to_use
            logger.info(f"✅ Successfully deducted {order_data.cashback_to_use} from Club Gift")
        except Exception as e:
            logger.error(f"❌ Failed to deduct Club Gift balance: {e}", exc_info=True)
            raise BadRequestException(f"Failed to deduct Club Gift balance: {str(e)}")
            
    # Legacy Support: If frontend still sends 'cashback_to_use' but meant Wallet (from old code)
    # The new schema has 'wallet_to_use'. If frontend sends old payload, it might be ambiguous.
    # But since we just added 'wallet_to_use', old clients sending 'cashback_to_use' will now hit the Cashback block above.
    # This might be a BREAKING CHANGE if 'cashback_to_use' was previously withdrawing from Wallet.
    # The previous code was:
    # if order_data.cashback_to_use > 0: wallet_service.withdraw(...)
    # So yes, 'cashback_to_use' WAS treating it as Wallet.
    # User Request: "Use Wallet" and "Use Cashback" separate buttons.
    # To correspond to typical naming: 
    # 'wallet_to_use' -> Wallet Service
    # 'cashback_to_use' -> Cashback Service
    # If I deploy this, the "Use Wallet/Cashback" toggle in current UI (mapped to cashback_to_use) will now deduct form CASHBACK instead of WALLET.
    # This is acceptable since I am updating the frontend immediately in the next step to separate them.

    total_amount = round(subtotal + tax_amount - discount_amount, 2)
    
    # Determine payment status
    if order_data.payment_status:
        # Use explicit payment status from request
        payment_status = OrderPaymentStatus(order_data.payment_status.value)
    elif total_amount <= 0:
        # Fully paid via points/wallet
        payment_status = OrderPaymentStatus.PAID
    elif points_redeemed_value > 0 or wallet_used_amount > 0 or club_gift_used_amount > 0:
        # Partially paid
        payment_status = OrderPaymentStatus.PARTIALLY_PAID
    else:
        # Not paid
        payment_status = OrderPaymentStatus.UNPAID
    
    # Create order
    # Create order
    try:
        order = Order(
            id=uuid.UUID(order_id),  # Fixed: Convert to UUID object
            order_number=order_number,
            user_id=uuid.UUID(order_data.user_id), # Fixed: Convert to UUID object
            created_by_user_id=current_user.id, # id is UUID
            order_type=ModelOrderType(order_data.order_type.value),
            status=OrderStatus.DRAFT,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            currency=currency,
            notes_ar=order_data.notes_ar,
            notes_en=order_data.notes_en,
            payment_status=payment_status,
            due_date=order_data.due_date,
            is_free=False
        )
        
        # Set paid_at if fully paid
        if payment_status == OrderPaymentStatus.PAID:
            order.payment_status = OrderPaymentStatus.PAID
            order.paid_at = datetime.utcnow()
        
        db.add(order)
        db.flush()
        
        # Create order items
        for item_data in order_data.items:
            item = OrderItem(
                id=uuid.uuid4(), # Fixed: Convert to UUID object
                order_id=order.id,
                description_ar=item_data.description_ar,
                description_en=item_data.description_en,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=round(item_data.quantity * item_data.unit_price, 2),
                currency=currency  # Use order currency instead of hardcoded "EGP"
            )
            db.add(item)
        
        db.commit()
        db.refresh(order)
        
        logger.info(f"✅ Order created by admin {current_user.email}: {order_number}")
        
        # Notify User
        try:
            notification_service = NotificationService(db)
            target_user = db.query(User).get(order.user_id)
            if target_user:
                notification_service.notify_invoice_created(
                    user=target_user,
                    invoice=order
                )
        except Exception as e:
            logger.error(f"Failed to send invoice notification: {e}")

        return order

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create order: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.post("/{order_id}/issue", response_model=OrderResponse)
def issue_order(
    order_id: str,
    current_user: User = Depends(get_admin_user),  # Admin only
    db: Session = Depends(get_db)
):
    """
    Issue order (change from DRAFT to ISSUED).
    
    Requires: Bearer token with ADMIN or SUPER_ADMIN role
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise NotFoundException("Order not found")
    
    if order.status != OrderStatus.DRAFT:
        raise BadRequestException(f"Order cannot be issued. Current status: {order.status}")
    
    order.status = OrderStatus.ISSUED
    order.issued_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    logger.info(f"✅ Order issued by admin {current_user.email}: {order.order_number}")
    
    return order


@router.get("", response_model=List[OrderListResponse])
def list_all_orders(
    current_user: User = Depends(get_admin_user),  # Admin only
    db: Session = Depends(get_db),
    status: str = None,
    payment_status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all orders (admin view).
    
    Requires: Bearer token with ADMIN or SUPER_ADMIN role
    """
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    
    orders = query.options(joinedload(Order.user)).order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    
    
    return orders


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: str,
    order_data: OrderUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing order.
    
    Requires: Bearer token with ADMIN or SUPER_ADMIN role
    """
    # Fetch existing order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")

    # Update basic fields if provided
    if order_data.notes_ar is not None:
        order.notes_ar = order_data.notes_ar
    if order_data.notes_en is not None:
        order.notes_en = order_data.notes_en
    if order_data.due_date is not None:
        order.due_date = order_data.due_date
    if order_data.currency is not None:
        order.currency = order_data.currency
    
    # Update payment status if explicitly provided
    if order_data.payment_status is not None:
        order.payment_status = order_data.payment_status
        if order.payment_status == OrderPaymentStatus.PAID and not order.paid_at:
            order.paid_at = datetime.utcnow()
            
    # Update Free Status
    if order_data.is_free is not None:
        order.is_free = order_data.is_free
        if order.is_free:
             pass

    # If items are provided, replace them
    if order_data.items is not None:
        # 1. Delete existing items
        db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
        
        # 2. Add new items
        new_subtotal = 0
        for item_data in order_data.items:
            total_price = round(item_data.quantity * item_data.unit_price, 2)
            new_subtotal += total_price
            
            new_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order.id,
                description_ar=item_data.description_ar,
                description_en=item_data.description_en,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=total_price,
                currency=order.currency
            )
            db.add(new_item)
            
        # 3. Recalculate totals
        order.subtotal = new_subtotal
        
        tax_rate = order_data.tax_rate if order_data.tax_rate is not None else (14.0) 
        
        if order.is_free:
            order.tax_amount = 0
            order.total_amount = 0
            order.discount_amount = 0
        else:
            order.tax_amount = round(order.subtotal * (tax_rate / 100), 2)
            discount_val = order_data.discount_amount if order_data.discount_amount is not None else 0
            order.discount_amount = discount_val
            order.total_amount = round(order.subtotal + order.tax_amount - order.discount_amount, 2)

    db.commit()
    db.refresh(order)
    logger.info(f"✅ Order {order.order_number} updated by admin {current_user.email}")
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: str,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete an order.
    
    Requires: Bearer token with ADMIN or SUPER_ADMIN role
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order not found")
        
    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
    
    db.delete(order)
    db.commit()
    
    logger.info(f"🗑️ Order {order.order_number} deleted by admin {current_user.email}")
    return None
