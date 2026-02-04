"""
Notification utility functions (production-safe).

IMPORTANT:
The Notification model was refactored and no longer supports legacy fields like
`user_id`, `reel_id`, `comment_id`, `actor_id` on the Notification table.

All notification creation should go through NotificationService which:
- stores notifications using the current schema
- sends Expo push notifications when possible
"""

from sqlalchemy.orm import Session

from modules.notifications.schemas import NotificationCreate
from modules.notifications.service import NotificationService
from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
from modules.users.models import User, UserRole

def notify_new_reel(db: Session, reel_id: str, admin_id: str):
    """
    Notify all users about a new reel.
    """
    service = NotificationService(db)

    # Notify customers (fan-out by role is not supported for CUSTOMER to avoid mass push).
    # We still create per-user notifications so they appear in-app, and push will send if token exists.
    users = db.query(User).filter(User.role == UserRole.CUSTOMER).limit(2000).all()
    for user in users:
        if str(user.id) == str(admin_id):
            continue
        service.create_notification(
            NotificationCreate(
                target_role=NotificationTargetRole.CUSTOMER,
                target_user_id=str(user.id),
                type=NotificationType.NEW_REEL,
                title="New Reel Available!",
                message="Check out the latest reel from Altayar",
                related_entity_id=str(reel_id),
                related_entity_type=NotificationEntityType.REEL,
                action_url=f"/(user)/reels",
                triggered_by_id=str(admin_id),
                triggered_by_role="ADMIN",
            )
        )

def notify_comment_reply(db: Session, parent_comment, reply_comment, actor_id: str):
    """
    Notify user when someone replies to their comment.
    """
    if parent_comment.user_id == actor_id:
        return  # Don't notify if replying to own comment
    
    service = NotificationService(db)
    service.create_notification(
        NotificationCreate(
            target_role=NotificationTargetRole.CUSTOMER,
            target_user_id=str(parent_comment.user_id),
            type=NotificationType.COMMENT_REPLY,
            title="New Reply",
            message="Someone replied to your comment",
            related_entity_id=str(parent_comment.reel_id),
            related_entity_type=NotificationEntityType.REEL,
            action_url=f"/(user)/reels",
            triggered_by_id=str(actor_id),
            triggered_by_role="CUSTOMER",
        )
    )

def notify_comment_like(db: Session, comment, actor_id: str):
    """
    Notify user when someone likes their comment.
    """
    if comment.user_id == actor_id:
        return  # Don't notify if liking own comment
    
    service = NotificationService(db)
    service.create_notification(
        NotificationCreate(
            target_role=NotificationTargetRole.CUSTOMER,
            target_user_id=str(comment.user_id),
            type=NotificationType.COMMENT_LIKE,
            title="Comment Liked",
            message="Someone liked your comment",
            related_entity_id=str(comment.reel_id),
            related_entity_type=NotificationEntityType.REEL,
            action_url=f"/(user)/reels",
            triggered_by_id=str(actor_id),
            triggered_by_role="CUSTOMER",
        )
    )


def notify_reel_like(db: Session, reel, actor_id: str):
    """
    Notify admin when someone likes a reel.
    """
    # Notify admins (fan-out by role is supported in NotificationService now).
    service = NotificationService(db)
    service.create_notification(
        NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,
            target_user_id=None,
            type=NotificationType.REEL_LIKE,
            title="Reel Liked",
            message="Someone liked a reel",
            related_entity_id=str(getattr(reel, "id", "")),
            related_entity_type=NotificationEntityType.REEL,
            action_url="/(admin)/reels",
            triggered_by_id=str(actor_id),
            triggered_by_role="CUSTOMER",
        )
    )
