from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from database.base import get_db
from modules.chat.models import Conversation, Message, ConversationStatus, MessageType
from modules.chat.bot_service import BotService
from modules.chat.schemas import (
    SendMessageRequest, MessageResponse,
    StartConversationRequest, ConversationResponse, ConversationDetailResponse,
    AssignConversationRequest, CloseConversationRequest
)
from modules.users.models import User, UserRole
from modules.notifications.service import NotificationService
from modules.notifications.schemas import NotificationCreate
from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
from shared.dependencies import get_current_user, require_admin, require_employee_or_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Customer Endpoints ============

@router.post("/start", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def start_conversation(
    data: StartConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new conversation (customer).
    """
    # Check if customer has an open conversation
    existing = db.query(Conversation).filter(
        Conversation.customer_id == str(current_user.id),
        Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.ASSIGNED])
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already have an open conversation"
        )
    
    # Check for assigned employee
    assigned_employee_id = current_user.assigned_employee_id
    initial_status = ConversationStatus.OPEN
    
    if assigned_employee_id:
        initial_status = ConversationStatus.ASSIGNED
    
    # Create conversation
    conversation = Conversation(
        id=str(uuid.uuid4()),
        customer_id=str(current_user.id),
        subject=data.subject,
        status=initial_status,
        assigned_to=assigned_employee_id if assigned_employee_id else None,
        assigned_at=datetime.utcnow() if assigned_employee_id else None,
        last_message_at=datetime.utcnow(),
        last_message_preview=data.initial_message[:100],
        employee_unread_count=1,
    )
    db.add(conversation)
    db.flush()
    
    # Create initial message
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        sender_id=str(current_user.id),
        sender_role="CUSTOMER",
        message_type=MessageType.TEXT,
        content=data.initial_message,
    )
    db.add(message)
    db.commit()
    db.refresh(conversation)

    # Trigger Bot Welcome (contextual)
    try:
        BotService.send_welcome_message(db, conversation)
    except Exception as e:
        logger.error(f"Failed to send bot welcome: {e}")
    
    logger.info(f"✅ Conversation started by {current_user.email}")
    
    # Notify assigned employee if auto-assigned
    if conversation.assigned_to:
        try:
             notification_service = NotificationService(db)
             notification_data = NotificationCreate(
                type=NotificationType.CHAT_MESSAGE,
                title="New Chat Assigned",
                message=f"New chat from {current_user.first_name} {current_user.last_name}",
                related_entity_id=conversation.id,
                related_entity_type=NotificationEntityType.CONVERSATION,
                target_role=NotificationTargetRole.EMPLOYEE,
                target_user_id=conversation.assigned_to,
                priority="HIGH",
                action_url=f"/employee/chat/{conversation.id}"
             )
             notification_service.create_notification(notification_data)
        except Exception as e:
            logger.warning(f"Failed to notify employee of auto-assignment: {e}")
            
    # Always notify Admin about new conversation (start)
    try:
        notification_service = NotificationService(db)
        sender_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
        
        # Reuse notify_chat_message which handles Admin notification
        notification_service.notify_chat_message(
            conversation_id=conversation.id,
            sender_name=sender_name,
            message_preview=data.initial_message[:100],
            sender_role="CUSTOMER"
        )
    except Exception as e:
        logger.warning(f"Failed to notify admin of new conversation: {e}")
            
    return _conversation_to_response(conversation, db)


@router.get("/my", response_model=List[ConversationResponse])
def get_my_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get customer's conversations.
    """
    try:
        from sqlalchemy import desc, case
        
        # Order by last_message_at (nulls last), then by created_at
        conversations = db.query(Conversation).filter(
            Conversation.customer_id == str(current_user.id)
        ).order_by(
            case(
                (Conversation.last_message_at.is_(None), 1),
                else_=0
            ),
            desc(Conversation.last_message_at),
            desc(Conversation.created_at)
        ).all()
        
        return [_conversation_to_response(c, db) for c in conversations]
    except Exception as e:
        logger.error(f"Error getting conversations for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversations: {str(e)}")


@router.get("/my/active", response_model=Optional[ConversationDetailResponse])
def get_my_active_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get customer's active (open/assigned) conversation with messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.customer_id == str(current_user.id),
        Conversation.status.in_([ConversationStatus.OPEN, ConversationStatus.ASSIGNED])
    ).first()
    
    if not conversation:
        return None
    
    # Mark messages as read
    db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.sender_role != "CUSTOMER",
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    conversation.customer_unread_count = 0
    db.commit()
    
    return _conversation_to_detail_response(conversation, db)


@router.post("/{conversation_id}/message", response_model=MessageResponse)
def send_message(
    conversation_id: str,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check permission
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_customer = str(current_user.id) == conversation.customer_id
    is_assigned_employee = str(current_user.id) == conversation.assigned_to
    is_admin = user_role in ["ADMIN", "SUPER_ADMIN"]
    
    # If customer tries to send message to closed/resolved conversation, block it
    if is_customer and conversation.status in [ConversationStatus.CLOSED, ConversationStatus.RESOLVED]:
        raise HTTPException(
            status_code=403,
            detail="This conversation is closed. Please start a new conversation."
        )
    
    if not (is_customer or is_assigned_employee or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Determine sender role
    if is_customer:
        sender_role = "CUSTOMER"
    elif is_admin:
        sender_role = "ADMIN"
    else:
        sender_role = "EMPLOYEE"
    
    # Create message
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=str(current_user.id),
        sender_role=sender_role,
        message_type=data.message_type,
        content=data.content,
        offer_id=data.offer_id,
    )
    db.add(message)
    
    # Update conversation
    conversation.last_message_at = datetime.utcnow()
    conversation.last_message_preview = data.content[:100]
    
    # Update unread counts
    if is_customer:
        conversation.employee_unread_count = (conversation.employee_unread_count or 0) + 1
    else:
        conversation.customer_unread_count = (conversation.customer_unread_count or 0) + 1
    
    db.commit()
    db.refresh(message)

    # Process with Bot if active and sender is customer
    if is_customer and conversation.is_bot_active:
        try:
             # Refresh conversation to get latest state
             db.refresh(conversation)
             BotService.process_message(db, conversation, data.content)
        except Exception as e:
             logger.error(f"Bot processing error: {e}")

    # Create notification for new chat message
    # Notify admin when customer sends message OR when employee/admin replies
    try:
        sender_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
        notification_service = NotificationService(db)
        
        if is_customer:
            # Customer sent message - notify admin and assigned employee
            notification_service.notify_chat_message(
                conversation_id=conversation_id,
                sender_name=sender_name,
                message_preview=data.content[:100],
                sender_role="CUSTOMER"
            )
        elif is_assigned_employee or is_admin:
            # Employee/Admin replied - notify admin about the reply
            notification_service.notify_chat_message(
                conversation_id=conversation_id,
                sender_name=sender_name,
                message_preview=data.content[:100],
                sender_role=sender_role
            )
    except Exception as e:
        logger.warning(f"Failed to create chat message notification: {e}")

    return _message_to_response(message, db)


# ============ Admin Endpoints ============
# IMPORTANT: Admin endpoints must come BEFORE dynamic routes like /{conversation_id}
# to avoid route conflicts

@router.get("/admin/all", response_model=List[ConversationResponse])
def get_all_conversations(
    status_filter: Optional[str] = None,
    unassigned_only: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all conversations (admin only).
    """
    query = db.query(Conversation)
    
    if status_filter:
        query = query.filter(Conversation.status == status_filter)
    if unassigned_only:
        query = query.filter(Conversation.assigned_to.is_(None))
    
    conversations = query.order_by(Conversation.last_message_at.desc()).offset(offset).limit(limit).all()
    
    return [_conversation_to_response(c, db) for c in conversations]


@router.get("/stats/admin")
def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get overall chat statistics (admin only).
    """
    total_open = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.OPEN
    ).count()
    
    total_assigned = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.ASSIGNED
    ).count()
    
    unassigned = db.query(Conversation).filter(
        Conversation.assigned_to.is_(None),
        Conversation.status == ConversationStatus.OPEN
    ).count()
    
    resolved_today = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.RESOLVED,
        Conversation.closed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    return {
        "total_open": total_open,
        "total_assigned": total_assigned,
        "unassigned": unassigned,
        "resolved_today": resolved_today,
    }


# ============ Employee Endpoints ============

@router.get("/assigned", response_model=List[ConversationResponse])
def get_assigned_conversations(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get conversations assigned to current employee.
    """
    query = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id)
    )
    
    if status_filter:
        query = query.filter(Conversation.status == status_filter)
    
    conversations = query.order_by(Conversation.last_message_at.desc()).all()
    
    return [_conversation_to_response(c, db) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get conversation details with messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check permission
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_customer = str(current_user.id) == conversation.customer_id
    is_assigned_employee = str(current_user.id) == conversation.assigned_to
    is_admin = user_role in ["ADMIN", "SUPER_ADMIN"]
    
    if not (is_customer or is_assigned_employee or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Mark messages as read
    if is_customer:
        db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.sender_role != "CUSTOMER",
            Message.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        conversation.customer_unread_count = 0
    else:
        db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.sender_role == "CUSTOMER",
            Message.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        conversation.employee_unread_count = 0
    
    db.commit()
    
    return _conversation_to_detail_response(conversation, db)


@router.post("/{conversation_id}/assign")
def assign_conversation(
    conversation_id: str,
    data: AssignConversationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Assign conversation to employee (admin only).
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify employee exists
    employee = db.query(User).filter(
        User.id == data.employee_id,
        User.role.in_([UserRole.EMPLOYEE, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    conversation.assigned_to = data.employee_id
    conversation.assigned_at = datetime.utcnow()
    conversation.assigned_by = str(current_user.id)
    conversation.status = ConversationStatus.ASSIGNED
    
    # Add system message
    system_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=str(current_user.id),
        sender_role="SYSTEM",
        message_type=MessageType.SYSTEM,
        content=f"تم تعيين المحادثة إلى {employee.first_name} {employee.last_name}",
    )
    db.add(system_message)
    db.commit()
    
    logger.info(f"✅ Conversation {conversation_id} assigned to {employee.email}")
    
    # Notify employee
    try:
         notification_service = NotificationService(db)
         notification_data = NotificationCreate(
            type=NotificationType.CHAT_MESSAGE,
            title="New Conversation Assigned",
            message=f"You have been assigned to conversation",
            related_entity_id=conversation_id,
            related_entity_type=NotificationEntityType.CONVERSATION,
            target_role=NotificationTargetRole.EMPLOYEE,
            target_user_id=data.employee_id,
            priority="HIGH",
            action_url=f"/employee/chat/{conversation_id}"
         )
         notification_service.create_notification(notification_data)
    except Exception as e:
        logger.warning(f"Failed to notify employee of assignment: {e}")

    return {"success": True, "message": "Conversation assigned"}


@router.post("/{conversation_id}/close")
def close_conversation(
    conversation_id: str,
    data: CloseConversationRequest,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Close a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.status = ConversationStatus.RESOLVED
    conversation.closed_at = datetime.utcnow()
    conversation.closed_by = str(current_user.id)
    conversation.resolution_notes = data.resolution_notes
    
    # Add system message
    system_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=str(current_user.id),
        sender_role="SYSTEM",
        message_type=MessageType.SYSTEM,
        content="تم إغلاق المحادثة",
    )
    db.add(system_message)
    db.commit()
    
    return {"success": True, "message": "Conversation closed"}


# ============ Stats ============

@router.get("/stats/employee")
def get_employee_stats(
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get chat statistics for current employee.
    """
    assigned = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id),
        Conversation.status == ConversationStatus.ASSIGNED
    ).count()
    
    resolved_today = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id),
        Conversation.status == ConversationStatus.RESOLVED,
        Conversation.closed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    total_unread = db.query(Conversation).filter(
        Conversation.assigned_to == str(current_user.id),
        Conversation.employee_unread_count > 0
    ).count()
    
    return {
        "assigned_conversations": assigned,
        "resolved_today": resolved_today,
        "unread_conversations": total_unread,
    }


@router.get("/stats/admin")
def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get overall chat statistics (admin only).
    """
    total_open = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.OPEN
    ).count()
    
    total_assigned = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.ASSIGNED
    ).count()
    
    unassigned = db.query(Conversation).filter(
        Conversation.assigned_to.is_(None),
        Conversation.status == ConversationStatus.OPEN
    ).count()
    
    resolved_today = db.query(Conversation).filter(
        Conversation.status == ConversationStatus.RESOLVED,
        Conversation.closed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    return {
        "total_open": total_open,
        "total_assigned": total_assigned,
        "unassigned": unassigned,
        "resolved_today": resolved_today,
    }


# ============ Helper Functions ============

def _conversation_to_response(conv: Conversation, db: Session) -> ConversationResponse:
    customer = db.query(User).filter(User.id == conv.customer_id).first()
    assigned_user = db.query(User).filter(User.id == conv.assigned_to).first() if conv.assigned_to else None
    
    return ConversationResponse(
        id=str(conv.id),
        customer_id=conv.customer_id,
        customer_name=f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
        customer_avatar=customer.avatar if customer and customer.avatar else None,
        assigned_to=conv.assigned_to,
        assigned_to_name=f"{assigned_user.first_name} {assigned_user.last_name}" if assigned_user else None,
        status=conv.status.value if hasattr(conv.status, 'value') else str(conv.status),
        subject=conv.subject,
        last_message_at=conv.last_message_at,
        last_message_preview=conv.last_message_preview,
        customer_unread_count=conv.customer_unread_count or 0,
        employee_unread_count=conv.employee_unread_count or 0,
        created_at=conv.created_at,
    )


def _conversation_to_detail_response(conv: Conversation, db: Session) -> ConversationDetailResponse:
    base = _conversation_to_response(conv, db)
    messages = db.query(Message).filter(
        Message.conversation_id == conv.id
    ).order_by(Message.created_at.asc()).all()
    
    return ConversationDetailResponse(
        **base.model_dump(),
        messages=[_message_to_response(m, db) for m in messages]
    )


def _message_to_response(msg: Message, db: Session) -> MessageResponse:
    sender = db.query(User).filter(User.id == msg.sender_id).first()
    
    if msg.sender_role == "BOT":
        sender_name = "المساعد الآلي 🤖"
    elif msg.sender_role == "SYSTEM":
        sender_name = "System"
    else:
        sender_name = f"{sender.first_name} {sender.last_name}" if sender else "Unknown"

    return MessageResponse(
        id=str(msg.id),
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        sender_name=sender_name,
        sender_role=msg.sender_role,
        message_type=msg.message_type.value if hasattr(msg.message_type, 'value') else str(msg.message_type),
        content=msg.content,
        file_url=msg.file_url,
        file_name=msg.file_name,
        offer_id=msg.offer_id,
        is_read=msg.is_read or False,
        created_at=msg.created_at,
    )
