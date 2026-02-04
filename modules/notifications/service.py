from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import logging
import requests
import json

from .models import Notification, NotificationType, NotificationTargetRole, NotificationSettings
from .schemas import NotificationCreate, NotificationUpdate, NotificationStats, NotificationSettingsUpdate
from modules.users.models import User, UserRole
from modules.users.models import User, UserRole

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self, user_id: str) -> NotificationSettings:
        """Get notification settings for user, create if not exist"""
        settings = self.db.query(NotificationSettings).filter(
            NotificationSettings.user_id == user_id
        ).first()

        if not settings:
            # Create default settings
            settings = NotificationSettings(user_id=user_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        
        return settings

    def update_settings(self, user_id: str, update_data: NotificationSettingsUpdate) -> NotificationSettings:
        """Update notification settings"""
        settings = self.get_settings(user_id)
        
        # Update attributes
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(settings, key, value)
            
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification"""
        notification = Notification(**notification_data.model_dump())
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        logger.info(f"Created notification: {notification.type} - {notification.title}")
        # Push delivery:
        # - If target_user_id is set, send to that user's device token.
        # - If target_role is ADMIN/EMPLOYEE/AGENT with no target_user_id, fan out to that role.
        try:
            recipients: List[User] = []
            if notification.target_user_id:
                user = self.db.query(User).filter(User.id == notification.target_user_id).first()
                if user:
                    recipients = [user]
            else:
                # Fan-out only for staff roles to avoid mass send to ALL/CUSTOMER.
                if notification.target_role == NotificationTargetRole.ADMIN:
                    recipients = self.db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])).all()
                elif notification.target_role == NotificationTargetRole.EMPLOYEE:
                    recipients = self.db.query(User).filter(User.role == UserRole.EMPLOYEE).all()
                elif notification.target_role == NotificationTargetRole.AGENT:
                    recipients = self.db.query(User).filter(User.role == UserRole.AGENT).all()

            # Filter users with push enabled + token present
            tokens: List[str] = []
            for u in recipients:
                if not getattr(u, "expo_push_token", None):
                    continue
                try:
                    settings = self.get_settings(str(u.id))
                    if settings and not settings.push_notifications:
                        continue
                except Exception:
                    # If settings retrieval fails, fall back to sending (don't break notification creation).
                    pass
                tokens.append(u.expo_push_token)

            if tokens:
                self.send_push_notification(
                    to=tokens,
                    title=notification.title,
                    body=notification.message,
                    data={
                        "url": notification.action_url,
                        "action_url": notification.action_url,
                        "id": str(notification.id),
                        "notification_id": str(notification.id),
                        "type": str(notification.type.value) if hasattr(notification.type, "value") else str(notification.type),
                        "related_entity_id": notification.related_entity_id,
                        "related_entity_type": str(notification.related_entity_type.value)
                        if hasattr(notification.related_entity_type, "value")
                        else (str(notification.related_entity_type) if notification.related_entity_type else None),
                    },
                )
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}", exc_info=True)
        
        return notification

    def _is_valid_expo_push_token(self, token: str) -> bool:
        if not token:
            return False
        # Expo tokens are typically "ExponentPushToken[...]" or "ExpoPushToken[...]"
        return token.startswith("ExponentPushToken") or token.startswith("ExpoPushToken")

    def send_push_notification(self, to: Union[str, List[str]], title: str, body: str, data: dict = None):
        """Send Expo Push Notification"""
        try:
            tokens = [to] if isinstance(to, str) else list(to or [])
            tokens = [t for t in tokens if self._is_valid_expo_push_token(t)]
            if not tokens:
                logger.warning("No valid Expo push tokens to send.")
                return

            # Expo accepts an array of messages; batch to avoid large payloads.
            messages: List[Dict[str, Any]] = []
            for token in tokens:
                messages.append(
                    {
                        "to": token,
                        "sound": "default",
                        "title": title,
                        "body": body,
                        "data": data or {},
                        "priority": "high",
                        "channelId": "default",
                    }
                )

            headers = {
                "Accept": "application/json",
                "Accept-encoding": "gzip, deflate",
                "Content-Type": "application/json",
            }

            # Expo recommends sending up to 100 messages per request.
            for i in range(0, len(messages), 100):
                batch = messages[i : i + 100]
                response = requests.post(
                    "https://exp.host/--/api/v2/push/send",
                    headers=headers,
                    data=json.dumps(batch),
                    timeout=10,
                )
                if response.status_code >= 400:
                    logger.warning(f"Expo push send failed: {response.status_code} {response.text}")
            
            # log response if needed
            # logger.info(f"Push response: {response.text}")
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")

    def get_notifications_for_user(
        self,
        user_id: str,
        user_role: UserRole,
        limit: int = 50,
        offset: int = 0,
        include_read: bool = True
    ) -> List[Notification]:
        """Get notifications for a specific user based on their role"""
        query = self.db.query(Notification)

        # Role-based filtering
        if user_role == UserRole.CUSTOMER:
            # Customers see only their personal notifications
            query = query.filter(
                and_(
                    Notification.target_role.in_([NotificationTargetRole.CUSTOMER, NotificationTargetRole.ALL]),
                    or_(
                        Notification.target_user_id == user_id,
                        Notification.target_user_id.is_(None)
                    )
                )
            )
        elif user_role in [UserRole.EMPLOYEE, UserRole.AGENT]:
            # Employees see employee-level and system notifications
            query = query.filter(
                Notification.target_role.in_([
                    NotificationTargetRole.EMPLOYEE,
                    NotificationTargetRole.AGENT,
                    NotificationTargetRole.ALL
                ])
            )
        elif user_role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            # Admins see all notifications
            pass  # No filtering needed

        if not include_read:
            query = query.filter(Notification.is_read == False)

        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

    def get_unread_count(self, user_id: str, user_role: UserRole) -> int:
        """Get unread notification count for user"""
        query = self.db.query(func.count(Notification.id)).filter(
            Notification.is_read == False
        )

        # Apply same role-based filtering as get_notifications_for_user
        if user_role == UserRole.CUSTOMER:
            query = query.filter(
                and_(
                    Notification.target_role.in_([NotificationTargetRole.CUSTOMER, NotificationTargetRole.ALL]),
                    or_(
                        Notification.target_user_id == user_id,
                        Notification.target_user_id.is_(None)
                    )
                )
            )
        elif user_role in [UserRole.EMPLOYEE, UserRole.AGENT]:
            query = query.filter(
                Notification.target_role.in_([
                    NotificationTargetRole.EMPLOYEE,
                    NotificationTargetRole.AGENT,
                    NotificationTargetRole.ALL
                ])
            )
        # Admins see all

        return query.scalar() or 0

    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if not notification:
            return False

        # Check if user has permission to mark this notification as read
        if notification.target_user_id and notification.target_user_id != user_id:
            return False

        notification.is_read = True
        notification.read_at = datetime.utcnow().isoformat()
        self.db.commit()
        return True

    def mark_all_as_read(self, user_id: str, user_role: UserRole) -> int:
        """Mark all notifications as read for user"""
        query = self.db.query(Notification).filter(
            Notification.is_read == False
        )

        # Apply same role-based filtering
        if user_role == UserRole.CUSTOMER:
            query = query.filter(
                and_(
                    Notification.target_role.in_([NotificationTargetRole.CUSTOMER, NotificationTargetRole.ALL]),
                    or_(
                        Notification.target_user_id == user_id,
                        Notification.target_user_id.is_(None)
                    )
                )
            )
        elif user_role in [UserRole.EMPLOYEE, UserRole.AGENT]:
            query = query.filter(
                Notification.target_role.in_([
                    NotificationTargetRole.EMPLOYEE,
                    NotificationTargetRole.AGENT,
                    NotificationTargetRole.ALL
                ])
            )

        notifications = query.all()
        count = len(notifications)

        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow().isoformat()

        self.db.commit()
        return count

    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if not notification:
            return False

        # Check permissions
        if notification.target_user_id and notification.target_user_id != user_id:
            return False

        self.db.delete(notification)
        self.db.commit()
        return True

    def get_notification_stats(self, user_id: str, user_role: UserRole) -> NotificationStats:
        """Get notification statistics for user"""
        # Get total and unread counts
        total_query = self.db.query(func.count(Notification.id))
        unread_query = self.db.query(func.count(Notification.id)).filter(
            Notification.is_read == False
        )

        # Apply role-based filtering
        if user_role == UserRole.CUSTOMER:
            filter_condition = and_(
                Notification.target_role.in_([NotificationTargetRole.CUSTOMER, NotificationTargetRole.ALL]),
                or_(
                    Notification.target_user_id == user_id,
                    Notification.target_user_id.is_(None)
                )
            )
        elif user_role in [UserRole.EMPLOYEE, UserRole.AGENT]:
            filter_condition = Notification.target_role.in_([
                NotificationTargetRole.EMPLOYEE,
                NotificationTargetRole.AGENT,
                NotificationTargetRole.ALL
            ])
        else:
            filter_condition = None

        if filter_condition is not None:
            total_query = total_query.filter(filter_condition)
            unread_query = unread_query.filter(filter_condition)

        total = total_query.scalar() or 0
        unread = unread_query.scalar() or 0

        # Get counts by type
        type_stats = {}
        for notification_type in NotificationType:
            count = self.db.query(func.count(Notification.id)).filter(
                Notification.type == notification_type
            )
            if filter_condition is not None:
                count = count.filter(filter_condition)
            type_stats[notification_type.value] = count.scalar() or 0

        return NotificationStats(
            total=total,
            unread=unread,
            by_type=type_stats,
            by_priority={"NORMAL": total}  # Simplified for now
        )

    # Event-driven notification creation methods
    def notify_user_login(self, user: User):
        """Create notification when user logs in - notify admin"""
        from .schemas import NotificationCreate
        from .models import NotificationType, NotificationTargetRole, NotificationEntityType
        
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        
        notification_data = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,  # Notify admin
            target_user_id=None,  # All admins see this
            type=NotificationType.USER_LOGIN,
            title=f"User Login / تسجيل دخول مستخدم",
            message=f"User {user_name} ({user.role.value}) logged in",
            related_entity_id=user.id,
            related_entity_type=NotificationEntityType.USER,
            triggered_by_id=user.id,
            triggered_by_role=user.role.value
        )
        return self.create_notification(notification_data)

    def notify_user_logout(self, user: User):
        """Create notification when user logs out - notify admin"""
        from .schemas import NotificationCreate
        from .models import NotificationType, NotificationTargetRole, NotificationEntityType
        
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        
        notification_data = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,  # Notify admin
            target_user_id=None,  # All admins see this
            type=NotificationType.USER_LOGOUT,
            title=f"User Logout / تسجيل خروج مستخدم",
            message=f"User {user_name} ({user.role.value}) logged out",
            related_entity_id=user.id,
            related_entity_type=NotificationEntityType.USER,
            triggered_by_id=user.id,
            triggered_by_role=user.role.value
        )
        return self.create_notification(notification_data)

    def notify_user_registered(self, user: User):
        """Create notification when user registers"""
        from .schemas import NotificationTemplate
        notification_data = NotificationTemplate.user_registered(
            user_name=user.first_name + " " + user.last_name,
            user_id=user.id
        )
        return self.create_notification(notification_data)

    def notify_chat_message(self, conversation_id: str, sender_name: str, message_preview: str, sender_role: str = "CUSTOMER"):
        """Create notification for new chat message - notify admin and assigned employee"""
        from .schemas import NotificationCreate
        from .models import NotificationType, NotificationTargetRole, NotificationEntityType
        
        # Notify admin about new chat message
        admin_notification = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,  # Notify admin
            target_user_id=None,  # All admins see this
            type=NotificationType.CHAT_MESSAGE,
            title=f"New Chat Message / رسالة شات جديدة",
            message=f"{sender_name}: {message_preview[:100]}",
            related_entity_id=conversation_id,
            related_entity_type=NotificationEntityType.CONVERSATION,
            priority="HIGH",
            triggered_by_role=sender_role
        )
        self.create_notification(admin_notification)
        
        # Also notify assigned employee if message is from customer
        if sender_role == "CUSTOMER":
            # Get conversation to find assigned employee
            from modules.chat.models import Conversation
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation and conversation.assigned_to:
                employee_notification = NotificationCreate(
                    target_role=NotificationTargetRole.EMPLOYEE,
                    target_user_id=conversation.assigned_to,
                    type=NotificationType.CHAT_MESSAGE,
                    title=f"New Message from {sender_name}",
                    message=message_preview[:100],
                    related_entity_id=conversation_id,
                    related_entity_type=NotificationEntityType.CONVERSATION,
                    priority="HIGH",
                    action_url=f"/employee/chat/{conversation_id}",
                    triggered_by_role=sender_role
                )
                self.create_notification(employee_notification)
        
        return admin_notification

    def notify_membership_changed(self, user: User, change_type: str):
        """Create notification for membership changes"""
        from .schemas import NotificationTemplate
        notification_data = NotificationTemplate.membership_changed(
            user_name=user.first_name + " " + user.last_name,
            user_id=user.id,
            change_type=change_type
        )
        return self.create_notification(notification_data)

    def notify_offer_created(self, offer: Any):
        """
        Create notification for new offer.
        Handles both Global (ALL) and Targeted (ASSIGNED/SPECIFIC) offers.
        """
        from modules.offers.models import Offer
        import json
        
        # Determine Target
        target_role = NotificationTargetRole.CUSTOMER
        
        if offer.target_audience == 'ALL':
            # Global Broadcast to all Customers
            # We create ONE notification with target_role=CUSTOMER (or ALL)
            # This is efficient and avoids creating thousands of rows.
            notification_data = NotificationCreate(
                type=NotificationType.OFFER_CREATED,
                title=f"New Offer: {offer.title_en}",
                message=f"Check out our new offer: {offer.title_en}",
                target_role=target_role,
                target_user_id=None,
                related_entity_type="OFFER",
                related_entity_id=str(offer.id),
                triggered_by_id=None,
                triggered_by_role=None
            )
            self.create_notification(notification_data)
            
            # TODO: FCM Push Notification for Topic 'all_customers'
            logger.info(f"PUSH NOTIFICATION [MOCK]: Sent to topic 'all_customers' for offer {offer.title_en}")
            
        elif offer.target_audience == 'SPECIFIC' and offer.target_user_ids:
            # Notify specific users
            try:
                target_ids = json.loads(offer.target_user_ids) if isinstance(offer.target_user_ids, str) else offer.target_user_ids
                for user_id in target_ids:
                    notification_data = NotificationCreate(
                        type=NotificationType.OFFER_CREATED,
                        title=f"New Offer: {offer.title_en}",
                        message=f"Check out our new offer: {offer.title_en}",
                        target_role=target_role,
                        target_user_id=str(user_id),
                        related_entity_type="OFFER",
                        related_entity_id=str(offer.id),
                        triggered_by_id=None,
                        triggered_by_role=None
                    )
                    self.create_notification(notification_data)
            except Exception as e:
                logger.error(f"Error parsing target_user_ids for offer {offer.id}: {e}")
        
        elif offer.target_audience == 'ASSIGNED':
            # Notify assigned users - handled by querying users with assigned_employee_id
            # This is done at query time, not here
            logger.info(f"ASSIGNED offer created: {offer.title_en} - notifications will be shown to assigned users")

    def notify_cashback_change(self, user: User, amount: float, type: str, reason: str = None):
        """Notify user of cashback change (EARNED/REDEEMED)"""
        from .schemas import NotificationTemplate
        if type == "EARNED":
            data = NotificationTemplate.cashback_earned(
                user_name=f"{user.first_name} {user.last_name}",
                amount=amount,
                reason=reason
            )
        else:
            data = NotificationTemplate.cashback_redeemed(
                user_name=f"{user.first_name} {user.last_name}",
                amount=amount,
                reason=reason
            )
        data.target_user_id = user.id
        return self.create_notification(data)

    def notify_wallet_change(self, user: User, amount: float, type: str, currency: str = "USD"):
        """Notify user of wallet change (DEPOSIT/WITHDRAWAL)"""
        from .schemas import NotificationTemplate
        if type == "DEPOSIT":
            data = NotificationTemplate.wallet_deposit(
                user_name=f"{user.first_name} {user.last_name}",
                amount=amount,
                currency=currency
            )
        else:
            data = NotificationTemplate.wallet_withdrawal(
                user_name=f"{user.first_name} {user.last_name}",
                amount=amount,
                currency=currency
            )
        data.target_user_id = user.id
        return self.create_notification(data)

    def notify_invoice_created(self, user: User, invoice: Any):
        """Notify user of new invoice"""
        from .schemas import NotificationTemplate
        data = NotificationTemplate.invoice_created(
            user_name=f"{user.first_name} {user.last_name}",
            invoice_number=invoice.order_number,
            amount=invoice.total_amount,
            invoice_id=str(invoice.id)
        )
        data.target_user_id = user.id
        return self.create_notification(data)

    def notify_points_change(self, user: User, points: int, type: str, reason: str = None):
        """Notify user of points change (EARNED/REDEEMED)"""
        from .schemas import NotificationTemplate
        if type == "EARNED":
            data = NotificationTemplate.points_earned(
                user_name=f"{user.first_name} {user.last_name}",
                points=points,
                reason=reason
            )
        else:
            data = NotificationTemplate.points_redeemed(
                user_name=f"{user.first_name} {user.last_name}",
                points=points,
                reason=reason
            )
        data.target_user_id = user.id
        return self.create_notification(data)

    def notify_tier_post_created(self, post: Any, user: User):
        """Notify admin when user creates tier post"""
        from .schemas import NotificationCreate
        from .models import NotificationType, NotificationTargetRole, NotificationEntityType
        
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        tier_name = post.tier_code.upper()
        
        notification_data = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,
            target_user_id=None,  # All admins
            type=NotificationType.TIER_POST_CREATED,
            title=f"New Tier Post / منشور جديد",
            message=f"{user_name} created a post in {tier_name} tier",
            related_entity_id=str(post.id),
            related_entity_type=NotificationEntityType.TIER_POST,
            triggered_by_id=str(user.id),
            triggered_by_role=user.role.value,
            priority="NORMAL"
        )
        return self.create_notification(notification_data)

    def notify_tier_comment_created(self, comment: Any, post: Any, user: User):
        """Notify admin when user comments on a tier post"""
        from .schemas import NotificationCreate
        from .models import NotificationType, NotificationTargetRole, NotificationEntityType
        
        user_name = f"{user.first_name} {user.last_name}".strip() or user.email
        tier_name = post.tier_code.upper()
        
        notification_data = NotificationCreate(
            type=NotificationType.NEW_COMMENT,
            title=f"New Comment in {tier_name}",
            message=f"{user_name} commented: {comment.content[:50]}...",
            target_role=NotificationTargetRole.ADMIN,
            entity_type=NotificationEntityType.TIER_COMMENT,
            entity_id=str(comment.id),
            metadata={
                "post_id": str(post.id),
                "tier_code": post.tier_code,
                "user_id": str(user.id),
                "user_name": user_name
            }
        )
        return self.create_notification(notification_data)
