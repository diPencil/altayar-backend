from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_

from database.base import get_db
from shared.dependencies import get_current_user
from modules.users.models import User
from modules.notifications.models import Notification, NotificationTargetRole
from modules.notifications.schemas import NotificationListResponse, NotificationStats, NotificationResponse, NotificationSettingsResponse, NotificationSettingsUpdate, PushTokenUpdate
from modules.notifications.service import NotificationService

def _get_target_role(current_user) -> NotificationTargetRole | None:
    """Convert user role to notification target role"""
    try:
        if hasattr(current_user, 'role') and current_user.role:
            role_value = current_user.role.value.upper() if hasattr(current_user.role, 'value') else str(current_user.role).upper()
            
            # Map user roles to notification target roles
            role_mapping = {
                'CUSTOMER': NotificationTargetRole.CUSTOMER,
                'EMPLOYEE': NotificationTargetRole.EMPLOYEE,
                'AGENT': NotificationTargetRole.AGENT,
                'ADMIN': NotificationTargetRole.ADMIN,
                'SUPER_ADMIN': NotificationTargetRole.ADMIN,  # Super admins use ADMIN role for notifications
            }
            
            if role_value in role_mapping:
                return role_mapping[role_value]
            
            # Fallback: try direct enum conversion
            if role_value in NotificationTargetRole._member_names_:
                return NotificationTargetRole(role_value)
    except (ValueError, AttributeError, KeyError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error converting user role to notification target role: {e}")
    return None

router = APIRouter()

@router.get("/", response_model=NotificationListResponse)
def get_notifications(
    skip: int = 0,
    offset: int = None,  # Support both 'skip' and 'offset' for compatibility
    limit: int = 50,
    include_read: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Use offset if provided, otherwise use skip
    if offset is not None:
        skip = offset
    """
    Get user's notifications.
    """
    # Determine target role safely
    target_role = _get_target_role(current_user)
    
    # Check if user is admin - admins see all notifications
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    # Filter notifications for current user or their role
    if is_admin:
        # Admins see all notifications - no filtering
        query = db.query(Notification)
    else:
        # Non-admin users see:
        # 1) Notifications targeted to them specifically (target_user_id == current_user.id)
        # 2) Broadcast notifications (target_user_id IS NULL AND target_role == ALL)
        # 3) Role-based notifications (target_user_id IS NULL AND target_role == their role)
        # NOTE: This prevents targeted notifications from leaking to other users via role matches.
        user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        role_targets: List[NotificationTargetRole] = []
        if target_role:
            role_targets.append(target_role)
        if user_role_str == 'EMPLOYEE' and NotificationTargetRole.EMPLOYEE not in role_targets:
            role_targets.append(NotificationTargetRole.EMPLOYEE)
        if user_role_str == 'AGENT' and NotificationTargetRole.AGENT not in role_targets:
            role_targets.append(NotificationTargetRole.AGENT)

        role_filters = [
            and_(Notification.target_user_id.is_(None), Notification.target_role == r)
            for r in role_targets
        ]

        query = db.query(Notification).filter(or_(
            Notification.target_user_id == current_user.id,
            and_(Notification.target_user_id.is_(None), Notification.target_role == NotificationTargetRole.ALL),
            *role_filters
        ))

    if not include_read:
        query = query.filter(Notification.is_read == False)

    # Query with raw SQL to avoid enum conversion issues
    from sqlalchemy import text, select
    try:
        notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    except (LookupError, KeyError, ValueError) as e:
        # If enum conversion fails, query raw data
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Enum conversion failed, querying raw data: {e}")
        # Fallback: query all columns as strings
        role_str = None
        try:
            role_str = target_role.value if hasattr(target_role, "value") else str(target_role) if target_role else None
        except Exception:
            role_str = None

        raw_query = text("""
            SELECT id, target_role, target_user_id, type, title, message, 
                   related_entity_id, related_entity_type, is_read, read_at, 
                   priority, action_url, triggered_by_id, triggered_by_role, 
                   created_at, updated_at
            FROM notifications
            WHERE (
              target_user_id = :user_id
              OR (target_user_id IS NULL AND target_role = 'ALL')
              OR (target_user_id IS NULL AND (:role IS NOT NULL) AND target_role = :role)
            )
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = db.execute(raw_query, {
            "user_id": current_user.id,
            "role": role_str,
            "limit": limit,
            "offset": skip
        })
        # Convert to Notification-like objects
        notifications = []
        for row in result:
            notif = type('Notification', (), {
                'id': row[0],
                'target_role': row[1],  # This will be a string from raw SQL
                'target_user_id': row[2],
                'type': row[3],  # Raw string
                'title': row[4],
                'message': row[5],
                'related_entity_id': row[6],
                'related_entity_type': row[7],  # Raw string
                'is_read': bool(row[8]),
                'read_at': row[9],
                'priority': row[10],
                'action_url': row[11],
                'triggered_by_id': row[12],
                'triggered_by_role': row[13],
                'created_at': row[14],
                'updated_at': row[15],  # This is now included
                'triggered_by': None  # Will be loaded separately if needed
            })()
            notifications.append(notif)

    # Get total and unread counts
    if is_admin:
        # Admins see all notifications
        total_query = db.query(Notification)
    else:
        user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)

        role_targets: List[NotificationTargetRole] = []
        if target_role:
            role_targets.append(target_role)
        if user_role_str == 'EMPLOYEE' and NotificationTargetRole.EMPLOYEE not in role_targets:
            role_targets.append(NotificationTargetRole.EMPLOYEE)
        if user_role_str == 'AGENT' and NotificationTargetRole.AGENT not in role_targets:
            role_targets.append(NotificationTargetRole.AGENT)

        role_filters = [
            and_(Notification.target_user_id.is_(None), Notification.target_role == r)
            for r in role_targets
        ]

        total_query = db.query(Notification).filter(or_(
            Notification.target_user_id == current_user.id,
            and_(Notification.target_user_id.is_(None), Notification.target_role == NotificationTargetRole.ALL),
            *role_filters
        ))

    total_count = total_query.count()
    unread_count = total_query.filter(Notification.is_read == False).count()

    results = []
    for notif in notifications:
        try:
            # Handle enum types safely - get raw value if enum conversion fails
            try:
                notif_type = notif.type.value if hasattr(notif.type, 'value') else str(notif.type)
            except (AttributeError, ValueError, KeyError, LookupError):
                # If enum conversion fails, get the raw string value
                notif_type = str(getattr(notif, 'type', 'UNKNOWN'))
            
            related_type = None
            if hasattr(notif, 'related_entity_type') and notif.related_entity_type:
                try:
                    related_type = notif.related_entity_type.value if hasattr(notif.related_entity_type, 'value') else str(notif.related_entity_type)
                except (AttributeError, ValueError, KeyError, LookupError):
                    related_type = str(notif.related_entity_type)
            
            # Handle datetime safely - ensure UTC timezone is included
            created_at_val = getattr(notif, 'created_at', None)
            if created_at_val:
                if hasattr(created_at_val, 'isoformat'):
                    # Ensure UTC timezone is included (add Z if missing)
                    created_at_str = created_at_val.isoformat()
                    if 'Z' not in created_at_str and '+' not in created_at_str[-6:]:
                        # Add Z for UTC if timezone is missing
                        created_at_str = created_at_str + 'Z'
                else:
                    created_at_str = str(created_at_val)
            else:
                created_at_str = datetime.utcnow().isoformat() + 'Z'
            
            # Get updated_at safely - ensure UTC timezone is included
            updated_at_val = getattr(notif, 'updated_at', None)
            if updated_at_val and hasattr(updated_at_val, 'isoformat'):
                updated_at_str = updated_at_val.isoformat()
                # Ensure UTC timezone is included (add Z if missing)
                if 'Z' not in updated_at_str and '+' not in updated_at_str[-6:]:
                    updated_at_str = updated_at_str + 'Z'
            elif updated_at_val:
                updated_at_str = str(updated_at_val)
            else:
                updated_at_str = None
            
            # Get target_role and target_user_id
            target_role_val = getattr(notif, 'target_role', None)
            target_role_str = target_role_val.value if hasattr(target_role_val, 'value') else str(target_role_val) if target_role_val else None
            
            notif_response = {
                "id": str(getattr(notif, 'id', '')),
                "type": notif_type,
                "title": getattr(notif, 'title', ''),
                "message": getattr(notif, 'message', ''),
                "related_entity_id": getattr(notif, 'related_entity_id', None),
                "related_entity_type": related_type,
                "action_url": getattr(notif, 'action_url', None),
                "is_read": bool(getattr(notif, 'is_read', False)),
                "created_at": created_at_str,
                "read_at": getattr(notif, 'read_at', None),
                "priority": getattr(notif, 'priority', 'NORMAL') or "NORMAL",
                "target_role": target_role_str,
                "target_user_id": getattr(notif, 'target_user_id', None),
                "updated_at": updated_at_str,
                "triggered_by_id": getattr(notif, 'triggered_by_id', None),
                "triggered_by_role": getattr(notif, 'triggered_by_role', None)
            }

            # Add actor info if available (use getattr to avoid lazy loading issues)
            try:
                triggered_by = getattr(notif, 'triggered_by', None)
                if triggered_by:
                    notif_response["actor_name"] = f"{getattr(triggered_by, 'first_name', '')} {getattr(triggered_by, 'last_name', '')}"
                    notif_response["actor_avatar"] = getattr(triggered_by, 'avatar', None)
            except Exception:
                pass  # Skip if relationship fails

            # Debug: Print what we're adding
            # print(f"DEBUG: Adding notification with fields: {list(notif_response.keys())}")
            # print(f"DEBUG: target_role={notif_response.get('target_role')}, target_user_id={notif_response.get('target_user_id')}, updated_at={notif_response.get('updated_at')}")
            
            # Ensure fields are present in notif_response before adding to results
            if 'target_role' not in notif_response:
                notif_response['target_role'] = target_role_str  # Re-add if missing
            if 'target_user_id' not in notif_response:
                notif_response['target_user_id'] = getattr(notif, 'target_user_id', None)  # Re-add if missing
            if 'updated_at' not in notif_response:
                notif_response['updated_at'] = updated_at_str  # Re-add if missing
            
            # Debug: Verify all fields are present
            required_fields = ['target_role', 'target_user_id', 'updated_at']
            missing_in_response = [f for f in required_fields if f not in notif_response]
            if missing_in_response:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Fields missing in notif_response: {missing_in_response} for notification {notif_response.get('id')}")
            
            results.append(notif_response)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing notification {getattr(notif, 'id', 'unknown')}: {e}", exc_info=True)
            continue

    # Debug: Check what's in results
    if results:
        first_result = results[0]
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: First result keys: {list(first_result.keys())}")
        logger.info(f"DEBUG: target_role in first_result: {'target_role' in first_result}, value: {first_result.get('target_role')}")
        logger.info(f"DEBUG: target_user_id in first_result: {'target_user_id' in first_result}, value: {first_result.get('target_user_id')}")
        logger.info(f"DEBUG: updated_at in first_result: {'updated_at' in first_result}, value: {first_result.get('updated_at')}")
    
    # Create NotificationResponse objects to ensure all fields are included
    notification_responses = []
    for result in results:
        # Convert datetime strings back to datetime objects if needed for Pydantic
        created_at_val = result.get('created_at')
        if isinstance(created_at_val, str):
            try:
                created_at_val = datetime.fromisoformat(created_at_val.replace('Z', '+00:00'))
            except:
                created_at_val = datetime.utcnow()
        elif not created_at_val:
            created_at_val = datetime.utcnow()
        
        updated_at_val = result.get('updated_at')
        if isinstance(updated_at_val, str):
            try:
                updated_at_val = datetime.fromisoformat(updated_at_val.replace('Z', '+00:00'))
            except:
                updated_at_val = None
        
        read_at_val = result.get('read_at')
        if isinstance(read_at_val, str):
            try:
                read_at_val = datetime.fromisoformat(read_at_val.replace('Z', '+00:00'))
            except:
                read_at_val = None
        
        # The result dictionary IS the notif_response with all fields already included
        # We just need to convert datetime strings to datetime objects for Pydantic
        # Don't recreate the dict - use result directly and just fix datetimes
        if isinstance(result.get('created_at'), str):
            result['created_at'] = created_at_val
        if isinstance(result.get('updated_at'), str) and updated_at_val:
            result['updated_at'] = updated_at_val
        if isinstance(result.get('read_at'), str) and read_at_val:
            result['read_at'] = read_at_val
        
        # Verify critical fields are present
        if 'target_role' not in result:
            result['target_role'] = None
        if 'target_user_id' not in result:
            result['target_user_id'] = None
        if 'updated_at' not in result:
            result['updated_at'] = None
        
        notification_responses.append(result)  # Use result directly - it already has all fields
    
    # Debug: Check what's in results before processing
    if results:
        first_result = results[0]
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: First result in results has keys: {list(first_result.keys())}")
        logger.info(f"DEBUG: target_role in first_result: {'target_role' in first_result}, value: {first_result.get('target_role')}")
        logger.info(f"DEBUG: target_user_id in first_result: {'target_user_id' in first_result}, value: {first_result.get('target_user_id')}")
        logger.info(f"DEBUG: updated_at in first_result: {'updated_at' in first_result}, value: {first_result.get('updated_at')}")
    
    # notification_responses contains dictionaries with all fields already
    # Convert datetime strings to datetime objects and create NotificationResponse objects
    from modules.notifications.schemas import NotificationResponse
    
    final_notification_objects = []
    for notif_dict in notification_responses:
        try:
            # Make a copy to avoid modifying original
            notif_data = notif_dict.copy()
            
            # Convert datetime strings to datetime objects if needed
            if isinstance(notif_data.get('created_at'), str):
                try:
                    notif_data['created_at'] = datetime.fromisoformat(notif_data['created_at'].replace('Z', '+00:00'))
                except:
                    notif_data['created_at'] = datetime.utcnow()
            
            if isinstance(notif_data.get('updated_at'), str) and notif_data.get('updated_at'):
                try:
                    notif_data['updated_at'] = datetime.fromisoformat(notif_data['updated_at'].replace('Z', '+00:00'))
                except:
                    notif_data['updated_at'] = None
            
            if isinstance(notif_data.get('read_at'), str) and notif_data.get('read_at'):
                try:
                    notif_data['read_at'] = datetime.fromisoformat(notif_data['read_at'].replace('Z', '+00:00'))
                except:
                    notif_data['read_at'] = None
            
            # CRITICAL: Ensure these fields are explicitly included even if None
            if 'target_role' not in notif_data:
                notif_data['target_role'] = None
            if 'target_user_id' not in notif_data:
                notif_data['target_user_id'] = None
            if 'updated_at' not in notif_data:
                notif_data['updated_at'] = None
            
            # Create NotificationResponse object - this validates the data
            notification_obj = NotificationResponse(**notif_data)
            final_notification_objects.append(notification_obj)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating NotificationResponse for notification {notif_dict.get('id')}: {e}", exc_info=True)
            # Fallback: skip this notification if we can't create the object
            continue
    
    # Return NotificationListResponse - FastAPI will serialize according to response_model
    return NotificationListResponse(
        notifications=final_notification_objects,
        total=total_count,
        unread_count=unread_count
    )

@router.get("/stats", response_model=NotificationStats)
def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get notification statistics.
    """
    target_role = _get_target_role(current_user)
    
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    if is_admin:
        # Admins see all notifications
        query = db.query(Notification)
    else:
        filter_conditions = [
            Notification.target_user_id == current_user.id,
            Notification.target_role == NotificationTargetRole.ALL
        ]
        
        if target_role:
            filter_conditions.append(Notification.target_role == target_role)
        
        query = db.query(Notification).filter(or_(*filter_conditions))

    total = query.count()
    unread = query.filter(Notification.is_read == False).count()

    return NotificationStats(total=total, unread=unread)

@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a notification as read.
    """
    target_role = _get_target_role(current_user)
    
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    if is_admin:
        # Admins can mark any notification as read
        notif = db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
    else:
        filter_conditions = [
            Notification.target_user_id == current_user.id,
            Notification.target_role == NotificationTargetRole.ALL
        ]
        
        if target_role:
            filter_conditions.append(Notification.target_role == target_role)
        
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(*filter_conditions)
        ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    from datetime import datetime
    notif.read_at = datetime.utcnow().isoformat()
    db.commit()

    return {"message": "Marked as read"}

@router.post("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications as read.
    """
    from datetime import datetime
    target_role = _get_target_role(current_user)
    
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    if is_admin:
        # Admins can mark all notifications as read
        db.query(Notification).filter(
            Notification.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow().isoformat()})
    else:
        filter_conditions = [
            Notification.target_user_id == current_user.id,
            Notification.target_role == NotificationTargetRole.ALL
        ]
        
        if target_role:
            filter_conditions.append(Notification.target_role == target_role)
        
        db.query(Notification).filter(
            or_(*filter_conditions),
            Notification.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow().isoformat()})

    db.commit()

    return {"message": "All notifications marked as read"}

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get unread notification count.
    """
    target_role = _get_target_role(current_user)
    
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    if is_admin:
        # Admins see all unread notifications
        query = db.query(Notification).filter(Notification.is_read == False)
    else:
        filter_conditions = [
            Notification.target_user_id == current_user.id,
            Notification.target_role == NotificationTargetRole.ALL
        ]
        
        if target_role:
            filter_conditions.append(Notification.target_role == target_role)
        
        query = db.query(Notification).filter(
            or_(*filter_conditions),
            Notification.is_read == False
        )
    
    unread_count = query.count()
    
    return {"unread_count": unread_count}

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a notification.
    """
    target_role = _get_target_role(current_user)
    
    # Check if user is admin
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin = user_role in ['ADMIN', 'SUPER_ADMIN']
    
    if is_admin:
        # Admins can access any notification
        notif = db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
    else:
        filter_conditions = [
            Notification.target_user_id == current_user.id,
            Notification.target_role == NotificationTargetRole.ALL
        ]
        
        if target_role:
            filter_conditions.append(Notification.target_role == target_role)
        
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            or_(*filter_conditions)
        ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notif)
    db.commit()

    return {"message": "Notification deleted"}

@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification settings"""
    service = NotificationService(db)
    return service.get_settings(current_user.id)

@router.put("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    settings: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update notification settings"""
    service = NotificationService(db)
    return service.update_settings(current_user.id, settings)

@router.post("/token")
def update_push_token(
    token_data: PushTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's Expo push token"""
    current_user.expo_push_token = token_data.token
    db.commit()
    return {"message": "Push token updated"}
