import os
import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.base import get_db
from shared.dependencies import get_current_user, get_current_user_optional, get_admin_user
from modules.users.models import User
from modules.reels.models import Reel, ReelInteraction, ReelStatus, InteractionType, ReelFavorite
from modules.reels.schemas import ReelCreate, ReelUpdate, ReelResponse, InteractionCreate, InteractionResponse
from modules.reels.utils import validate_video_url, get_youtube_thumbnail_url
from modules.notifications.utils import notify_comment_like, notify_comment_reply, notify_new_reel
from config.settings import settings

logger = logging.getLogger(__name__)

# Storage directory for uploaded videos
REELS_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'storage', 'reels')
os.makedirs(REELS_STORAGE_DIR, exist_ok=True)

router = APIRouter()

# --- Public / User Endpoints ---

@router.get("/", response_model=List[ReelResponse])
def get_reels(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional) # Optional for Guest view
):
    """
    Get active reels for the public feed.
    Only returns reels with status ACTIVE and valid video_url.
    """
    query = db.query(Reel).filter(
        Reel.status == ReelStatus.ACTIVE,
        Reel.video_url.isnot(None)  # Only reels with video URLs
    )
    
    # Sort by creation date desc for now, later can be algo based
    reels = query.order_by(desc(Reel.created_at)).offset(skip).limit(limit).all()
    
    # Safely serialize reels to response format
    results = []
    for reel in reels:
        try:
            # Auto-generate thumbnail for YouTube videos if not present
            thumbnail_url = reel.thumbnail_url
            if not thumbnail_url and reel.video_type == 'YOUTUBE':
                thumbnail_url = get_youtube_thumbnail_url(reel.video_url)
            
            reel_response = ReelResponse(
                id=str(reel.id),
                title=reel.title,
                description=reel.description,
                video_url=reel.video_url,
                video_type=reel.video_type or 'URL',
                thumbnail_url=thumbnail_url,
                status=reel.status,
                views_count=int(reel.views_count) if reel.views_count is not None else 0,
                likes_count=int(reel.likes_count) if reel.likes_count is not None else 0,
                comments_count=int(reel.comments_count) if reel.comments_count is not None else 0,
                shares_count=int(reel.shares_count) if reel.shares_count is not None else 0,
                created_at=reel.created_at,
                updated_at=reel.updated_at,
                is_liked=False
            )

            # Get creator user info
            if reel.creator:
                from modules.reels.schemas import UserInfo
                reel_response.user = UserInfo(
                    id=str(reel.creator.id),
                    name=f"{reel.creator.first_name} {reel.creator.last_name}".strip() or reel.creator.username,
                    avatar_url=reel.creator.avatar,
                    is_following=False  # TODO: Check if current_user follows this user
                )

            # Check if liked by current user
            if current_user:
                liked = db.query(ReelInteraction).filter(
                    ReelInteraction.reel_id == reel.id,
                    ReelInteraction.user_id == current_user.id,
                    ReelInteraction.type == InteractionType.LIKE
                ).first()
                reel_response.is_liked = bool(liked)

            results.append(reel_response)
        except Exception as e:
            logger.warning(f"Failed to serialize reel {reel.id} for user feed: {e}")
            continue

    return results

# --- Favorites Endpoints (MUST come before dynamic routes) ---

@router.get("/favorites", response_model=List[ReelResponse])
def get_user_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all favorite reels for the current user.
    """
    favorites = db.query(ReelFavorite).filter(
        ReelFavorite.user_id == current_user.id
    ).all()
    
    if not favorites:
        return []
    
    reel_ids = [f.reel_id for f in favorites]
    reels = db.query(Reel).filter(
        Reel.id.in_(reel_ids),
        Reel.status == ReelStatus.ACTIVE
    ).all()
    
    results = []
    for reel in reels:
        if not reel.video_url:
            continue
        
        # Check if user liked this reel
        is_liked = db.query(ReelInteraction).filter(
            ReelInteraction.reel_id == reel.id,
            ReelInteraction.user_id == current_user.id,
            ReelInteraction.type == InteractionType.LIKE
        ).first() is not None
        
        # Auto-generate thumbnail for YouTube videos if not present
        thumbnail_url = reel.thumbnail_url
        if not thumbnail_url and reel.video_type == 'YOUTUBE':
            thumbnail_url = get_youtube_thumbnail_url(reel.video_url)
        
        reel_response = ReelResponse(
            id=str(reel.id),
            title=reel.title,
            description=reel.description,
            video_url=reel.video_url,
            video_type=reel.video_type or 'URL',
            thumbnail_url=thumbnail_url,
            status=reel.status,
            views_count=int(reel.views_count) if reel.views_count is not None else 0,
            likes_count=int(reel.likes_count) if reel.likes_count is not None else 0,
            comments_count=int(reel.comments_count) if reel.comments_count is not None else 0,
            shares_count=int(reel.shares_count) if reel.shares_count is not None else 0,
            created_at=reel.created_at,
            updated_at=reel.updated_at,
            is_liked=is_liked
        )
        results.append(reel_response)
    
    return results

@router.get("/{reel_id}", response_model=ReelResponse)
def get_reel(
    reel_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel or not reel.video_url:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Auto-generate thumbnail for YouTube videos if not present
    thumbnail_url = reel.thumbnail_url
    if not thumbnail_url and reel.video_type == 'YOUTUBE':
        thumbnail_url = get_youtube_thumbnail_url(reel.video_url)
        
    reel_response = ReelResponse.from_orm(reel)
    reel_response.video_url = reel.video_url  # Ensure it's set
    reel_response.video_type = reel.video_type or 'URL'  # Ensure it's set
    reel_response.thumbnail_url = thumbnail_url  # Set thumbnail (auto-generated if needed)
    if current_user:
        liked = db.query(ReelInteraction).filter(
            ReelInteraction.reel_id == reel.id,
            ReelInteraction.user_id == current_user.id,
            ReelInteraction.type == InteractionType.LIKE
        ).first()
        reel_response.is_liked = bool(liked)
        
    return reel_response

@router.post("/{reel_id}/interaction", response_model=InteractionResponse)
def interact_with_reel(
    reel_id: str,
    interaction: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handle Like, View, Share, Comment.
    Updates counters on Reel model atomically.
    """
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    # Prevent duplicate Views/Likes if logic requires (e.g. 1 view per session? 1 like per user)
    # For Likes: Toggle
    if interaction.type == InteractionType.LIKE:
        existing_like = db.query(ReelInteraction).filter(
            ReelInteraction.reel_id == reel_id,
            ReelInteraction.user_id == current_user.id,
            ReelInteraction.type == InteractionType.LIKE
        ).first()
        
        if existing_like:
            # Unlike
            db.delete(existing_like)
            reel.likes_count = max(0, reel.likes_count - 1)
            db.commit()
            return InteractionResponse(
                id=existing_like.id, 
                reel_id=reel_id, 
                user_id=current_user.id, 
                type=InteractionType.LIKE, 
                created_at=existing_like.created_at
            ) # Return deleted interaction effectively
        else:
            # Like
            new_interaction = ReelInteraction(
                reel_id=reel_id,
                user_id=current_user.id,
                type=InteractionType.LIKE
            )
            db.add(new_interaction)
            reel.likes_count += 1
            db.commit()
            db.refresh(new_interaction)
            
            # Send notification to admin about new like
            try:
                from modules.notifications.service import NotificationService
                from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
                from modules.notifications.schemas import NotificationCreate
                
                notification_service = NotificationService(db)
                user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
                reel_title = reel.title[:50] if reel.title else f"Reel {reel_id[:8]}"
                
                notification_data = NotificationCreate(
                    target_role=NotificationTargetRole.ADMIN,
                    target_user_id=None,
                    type=NotificationType.REEL_LIKE,
                    title=f"New Like on Reel",
                    message=f"{user_name} liked reel: {reel_title}",
                    related_entity_id=reel_id,
                    related_entity_type=NotificationEntityType.REEL,
                    action_url=f"altayar://reels/{reel_id}",
                    triggered_by_id=current_user.id,
                    triggered_by_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
                )
                notification_service.create_notification(notification_data)
            except Exception as e:
                logger.warning(f"Failed to send like notification to admin: {e}")

            return new_interaction

    # For Views
    elif interaction.type == InteractionType.VIEW:
        # Simple view count increment
        # To prevent spam, could check if viewed in last X mins, but for now allow
        new_interaction = ReelInteraction(
            reel_id=reel_id,
            user_id=current_user.id,
            type=InteractionType.VIEW
        )
        db.add(new_interaction)
        reel.views_count += 1
        db.commit()
        db.refresh(new_interaction)
        return new_interaction

    # For Comments
    elif interaction.type == InteractionType.COMMENT:
        if not interaction.content:
             raise HTTPException(status_code=400, detail="Comment content required")
             
        new_interaction = ReelInteraction(
            reel_id=reel_id,
            user_id=current_user.id,
            type=InteractionType.COMMENT,
            content=interaction.content
        )
        db.add(new_interaction)
        reel.comments_count += 1
        db.commit()
        db.refresh(new_interaction)
        
        # Send notification to admin about new comment
        try:
            from modules.notifications.service import NotificationService
            from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
            from modules.notifications.schemas import NotificationCreate
            
            notification_service = NotificationService(db)
            user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
            reel_title = reel.title[:50] if reel.title else f"Reel {reel_id[:8]}"
            
            notification_data = NotificationCreate(
                target_role=NotificationTargetRole.ADMIN,  # Notify admin
                target_user_id=None,  # All admins see this
                type=NotificationType.REEL_COMMENT,
                title=f"New Comment on Reel / تعليق جديد على الريل",
                message=f"{user_name} commented on reel: {reel_title}",
                related_entity_id=reel_id,
                related_entity_type=NotificationEntityType.REEL,
                action_url=f"altayar://reels/{reel_id}",
                triggered_by_id=current_user.id,
                triggered_by_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            )
            notification_service.create_notification(notification_data)
        except Exception as e:
            logger.warning(f"Failed to send comment notification to admin: {e}")
        
        # Populate user info for response
        resp = InteractionResponse.from_orm(new_interaction)
        resp.user_name = f"{current_user.first_name} {current_user.last_name}"
        resp.user_avatar = current_user.avatar
        return resp

    # For Shares
    elif interaction.type == InteractionType.SHARE:
        new_interaction = ReelInteraction(
            reel_id=reel_id,
            user_id=current_user.id,
            type=InteractionType.SHARE
        )
        db.add(new_interaction)
        reel.shares_count += 1
        db.commit()
        db.refresh(new_interaction)
        return new_interaction

    raise HTTPException(status_code=400, detail="Invalid interaction type")

@router.get("/{reel_id}/comments", response_model=List[InteractionResponse])
def get_reel_comments(
    reel_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    from sqlalchemy.orm import joinedload
    
    comments = db.query(ReelInteraction)\
        .options(joinedload(ReelInteraction.user))\
        .filter(
            ReelInteraction.reel_id == reel_id,
            ReelInteraction.type == InteractionType.COMMENT
        ).order_by(desc(ReelInteraction.created_at)).offset(skip).limit(limit).all()
    
    results = []
    for c in comments:
        # Build response manually to ensure all fields are included
        resp_dict = {
            "id": str(c.id),
            "reel_id": str(c.reel_id),
            "user_id": str(c.user_id) if c.user_id else None,
            "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "content": c.content,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "likes_count": c.likes_count if hasattr(c, 'likes_count') else 0,
            "created_at": c.created_at,
            "user_name": None,
            "user_avatar": None,
        }
        
        # Add user info if available
        if c.user:
            resp_dict["user_name"] = f"{c.user.first_name} {c.user.last_name}".strip() or c.user.username or "Anonymous"
            resp_dict["user_avatar"] = c.user.avatar
        
        resp = InteractionResponse(**resp_dict)
        results.append(resp)
    return results

@router.post("/comments/{comment_id}/like", response_model=InteractionResponse)
def like_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Like or unlike a comment.
    """
    comment = db.query(ReelInteraction).filter(
        ReelInteraction.id == comment_id,
        ReelInteraction.type == InteractionType.COMMENT
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check if already liked
    existing_like = db.query(ReelInteraction).filter(
        ReelInteraction.parent_id == comment_id,
        ReelInteraction.user_id == current_user.id,
        ReelInteraction.type == InteractionType.LIKE
    ).first()
    
    if existing_like:
        # Unlike
        db.delete(existing_like)
        comment.likes_count = max(0, comment.likes_count - 1)
        db.commit()
        return InteractionResponse(
            id=existing_like.id,
            reel_id=comment.reel_id,
            user_id=current_user.id,
            type=InteractionType.LIKE,
            created_at=existing_like.created_at
        )
    else:
        # Like
        new_like = ReelInteraction(
            reel_id=comment.reel_id,
            user_id=current_user.id,
            type=InteractionType.LIKE,
            parent_id=comment_id
        )
        db.add(new_like)
        comment.likes_count += 1
        db.commit()
        db.refresh(new_like)
        
        # Send notification
        try:
            notify_comment_like(db, comment, current_user.id)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
        
        return new_like

@router.post("/comments/{comment_id}/reply", response_model=InteractionResponse)
def reply_to_comment(
    comment_id: str,
    interaction: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reply to a comment.
    """
    parent_comment = db.query(ReelInteraction).filter(
        ReelInteraction.id == comment_id,
        ReelInteraction.type == InteractionType.COMMENT
    ).first()
    
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if not interaction.content:
        raise HTTPException(status_code=400, detail="Reply content required")
    
    # Create reply
    new_reply = ReelInteraction(
        reel_id=parent_comment.reel_id,
        user_id=current_user.id,
        type=InteractionType.COMMENT,
        content=interaction.content,
        parent_id=comment_id
    )
    db.add(new_reply)
    # Don't increment reel comments_count for replies, only for top-level comments
    db.commit()
    db.refresh(new_reply)
    
    # Send notification
    try:
        notify_comment_reply(db, parent_comment, new_reply, current_user.id)
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
    
    # Populate user info
    resp = InteractionResponse.from_orm(new_reply)
    resp.user_name = f"{current_user.first_name} {current_user.last_name}"
    resp.user_avatar = current_user.avatar
    return resp

# --- Admin Endpoints ---

@router.get("/admin/comments", response_model=List[InteractionResponse])
def get_all_comments_admin(
    skip: int = 0,
    limit: int = 50,
    reel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Get all comments for admin with optional reel filter.
    """
    query = db.query(ReelInteraction).filter(
        ReelInteraction.type == InteractionType.COMMENT
    )
    
    if reel_id:
        query = query.filter(ReelInteraction.reel_id == reel_id)
    
    comments = query.order_by(desc(ReelInteraction.created_at)).offset(skip).limit(limit).all()
    
    results = []
    for c in comments:
        resp = InteractionResponse.from_orm(c)
        if c.user:
            resp.user_name = f"{c.user.first_name} {c.user.last_name}"
            resp.user_avatar = c.user.avatar
        # Add reel info
        if c.reel:
            resp.reel_title = c.reel.title
        results.append(resp)
    return results

@router.put("/admin/comments/{comment_id}", response_model=InteractionResponse)
def update_comment_admin(
    comment_id: str,
    content: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Edit a comment (admin only).
    """
    comment = db.query(ReelInteraction).filter(
        ReelInteraction.id == comment_id,
        ReelInteraction.type == InteractionType.COMMENT
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.content = content
    db.commit()
    db.refresh(comment)
    
    resp = InteractionResponse.from_orm(comment)
    if comment.user:
        resp.user_name = f"{comment.user.first_name} {comment.user.last_name}"
        resp.user_avatar = comment.user.avatar
    return resp

@router.delete("/admin/comments/{comment_id}")
def delete_comment_admin(
    comment_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Delete a comment (admin only).
    """
    comment = db.query(ReelInteraction).filter(
        ReelInteraction.id == comment_id,
        ReelInteraction.type == InteractionType.COMMENT
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Get reel to update counter
    reel = db.query(Reel).filter(Reel.id == comment.reel_id).first()
    if reel:
        reel.comments_count = max(0, reel.comments_count - 1)
    
    # Delete all replies to this comment
    replies = db.query(ReelInteraction).filter(
        ReelInteraction.parent_id == comment_id
    ).all()
    for reply in replies:
        db.delete(reply)
    
    db.delete(comment)
    db.commit()
    
    return {"message": "Comment deleted successfully"}

@router.post("/upload", response_model=ReelResponse)
async def upload_reel_video(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: ReelStatus = Form(ReelStatus.DRAFT),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Upload a video file for a reel.
    Accepts MP4, MOV, AVI, MKV, WEBM, M4V, 3GP files.
    """
    file_path = None
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Validate file type - check both filename extension and content type
        allowed_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp']
        allowed_mime_types = [
            'video/mp4', 'video/quicktime', 'video/x-msvideo', 
            'video/x-matroska', 'video/webm', 'video/mp4v-es', 'video/3gpp'
        ]
        
        # Get file extension
        original_filename = file.filename or ''
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # If no extension, try to detect from content type
        if not file_ext and file.content_type:
            content_type_map = {
                'video/mp4': '.mp4',
                'video/quicktime': '.mov',
                'video/x-msvideo': '.avi',
                'video/x-matroska': '.mkv',
                'video/webm': '.webm',
                'video/mp4v-es': '.m4v',
                'video/3gpp': '.3gp'
            }
            file_ext = content_type_map.get(file.content_type.lower(), '.mp4')  # Default to mp4
            logger.info(f"No extension found, using content type: {file.content_type} -> {file_ext}")
        
        # Validate extension
        if file_ext not in allowed_extensions:
            # If still no valid extension, default to .mp4 for uploaded files
            logger.warning(f"Invalid or missing extension '{file_ext}', defaulting to .mp4")
            file_ext = '.mp4'
        
        # Validate content type if provided
        if file.content_type and not any(mime in file.content_type.lower() for mime in allowed_mime_types):
            logger.warning(f"Unexpected content type: {file.content_type}, but allowing upload")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(REELS_STORAGE_DIR, filename)
        
        # Save file
        logger.info(f"Uploading file: {original_filename} ({file.content_type}) -> {filename}")
        with open(file_path, 'wb') as f:
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty file uploaded"
                )
            f.write(content)
        
        logger.info(f"✅ File saved: {filename} ({len(content)} bytes)")
        
        # Generate absolute URL for accessing the file
        video_url = f"{settings.APP_BASE_URL}/api/reels/video/{filename}"
        
        # Create reel record
        new_reel = Reel(
            title=title or "Untitled Reel",
            description=description,
            video_url=video_url,
            video_type='UPLOAD',
            status=status,
            created_by_user_id=current_admin.id
        )
        db.add(new_reel)
        db.commit()
        db.refresh(new_reel)
        
        # Send notifications if status is ACTIVE
        if status == ReelStatus.ACTIVE:
            try:
                notify_new_reel(db, new_reel.id, current_admin.id)
            except Exception as e:
                logger.warning(f"Failed to send notifications: {e}")
        
        logger.info(f"✅ Video uploaded successfully: {filename} (Reel ID: {new_reel.id})")
        return new_reel
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error uploading video: {str(e)}", exc_info=True)
        # Clean up file if database operation fails
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )

@router.get("/video/{filename}")
def get_reel_video(
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Serve uploaded video files.
    """
    # Security: Prevent path traversal
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(REELS_STORAGE_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',  # Default, could be determined from extension
        filename=filename
    )

@router.post("/", response_model=ReelResponse)
def create_reel(
    reel: ReelCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Create a reel with a video URL (YouTube or direct link).
    """
    try:
        logger.info(f"Creating reel with video_url: {reel.video_url}, title: {reel.title}")
        
        # Validate that video_url is provided
        if not reel.video_url:
            logger.warning("Reel creation failed: video_url is required")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="video_url is required when not uploading a file"
            )
        
        # Validate URL
        is_valid, video_type, error_msg = validate_video_url(reel.video_url)
        if not is_valid:
            logger.warning(f"Reel creation failed: Invalid video URL - {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Invalid video URL"
            )
        
        # Determine video_type
        final_video_type = reel.video_type if reel.video_type else (video_type or 'URL')
        logger.info(f"Video type determined: {final_video_type}")
        
        # Auto-generate thumbnail for YouTube videos if not provided
        thumbnail_url = reel.thumbnail_url
        if not thumbnail_url and final_video_type == 'YOUTUBE':
            thumbnail_url = get_youtube_thumbnail_url(reel.video_url)
            logger.info(f"Auto-generated YouTube thumbnail: {thumbnail_url}")
        
        # Ensure status is a ReelStatus enum (Pydantic should handle this, but be safe)
        reel_status = reel.status
        if isinstance(reel_status, str):
            try:
                reel_status = ReelStatus(reel_status.upper())
            except (ValueError, AttributeError):
                logger.warning(f"Invalid status '{reel_status}', defaulting to DRAFT")
                reel_status = ReelStatus.DRAFT
        
        # Create reel with explicit field mapping
        logger.info(f"Creating Reel object with status: {reel_status}")
        new_reel = Reel(
            title=reel.title,
            description=reel.description,
            video_url=reel.video_url,
            video_type=final_video_type,
            thumbnail_url=thumbnail_url,
            status=reel_status,
            created_by_user_id=current_admin.id
        )
        
        db.add(new_reel)
        db.commit()
        db.refresh(new_reel)
        logger.info(f"Reel created successfully with ID: {new_reel.id}")
        
        # Send notifications if status is ACTIVE
        if reel_status == ReelStatus.ACTIVE:
            try:
                notify_new_reel(db, new_reel.id, current_admin.id)
            except Exception as e:
                logger.warning(f"Failed to send notifications: {e}")
        
        # Return properly serialized response
        response = ReelResponse(
            id=str(new_reel.id),
            title=new_reel.title,
            description=new_reel.description,
            video_url=new_reel.video_url,
            video_type=new_reel.video_type or 'URL',
            thumbnail_url=new_reel.thumbnail_url,
            status=new_reel.status,
            views_count=int(new_reel.views_count) if new_reel.views_count is not None else 0,
            likes_count=int(new_reel.likes_count) if new_reel.likes_count is not None else 0,
            comments_count=int(new_reel.comments_count) if new_reel.comments_count is not None else 0,
            shares_count=int(new_reel.shares_count) if new_reel.shares_count is not None else 0,
            created_at=new_reel.created_at,
            updated_at=new_reel.updated_at,
            is_liked=False
        )
        logger.info(f"Returning response for reel {response.id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors) - these already have proper status codes
        raise
    except Exception as e:
        logger.error(f"Error creating reel: {e}", exc_info=True)
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create reel: {str(e)}"
        )

@router.delete("/{reel_id}")
def delete_reel(
    reel_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Soft delete
    reel.delete(db) 
    return {"message": "Reel deleted successfully"}

@router.post("/{reel_id}/favorite")
def add_to_favorites(
    reel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a reel to user's favorites.
    """
    # Check if reel exists
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Check if already favorited
    existing = db.query(ReelFavorite).filter(
        ReelFavorite.user_id == current_user.id,
        ReelFavorite.reel_id == reel_id
    ).first()
    
    if existing:
        return {"message": "Already in favorites"}
    
    # Add to favorites
    favorite = ReelFavorite(
        user_id=current_user.id,
        reel_id=reel_id
    )
    db.add(favorite)
    db.commit()
    
    return {"message": "Added to favorites"}

@router.delete("/{reel_id}/favorite")
def remove_from_favorites(
    reel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a reel from user's favorites.
    """
    favorite = db.query(ReelFavorite).filter(
        ReelFavorite.user_id == current_user.id,
        ReelFavorite.reel_id == reel_id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Not in favorites")
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Removed from favorites"}

@router.patch("/{reel_id}", response_model=ReelResponse)
@router.put("/{reel_id}", response_model=ReelResponse)
def update_reel(
    reel_id: str,
    reel_update: ReelUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Update a reel (admin only). Supports both PATCH and PUT.
    """
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Update only provided fields
    update_data = reel_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(reel, key, value)
    
    db.commit()
    db.refresh(reel)
    
    # Return properly formatted response
    return ReelResponse(
        id=str(reel.id),
        title=reel.title,
        description=reel.description,
        video_url=reel.video_url,
        video_type=reel.video_type or 'URL',
        thumbnail_url=reel.thumbnail_url,
        status=reel.status,
        views_count=int(reel.views_count) if reel.views_count is not None else 0,
        likes_count=int(reel.likes_count) if reel.likes_count is not None else 0,
        comments_count=int(reel.comments_count) if reel.comments_count is not None else 0,
        shares_count=int(reel.shares_count) if reel.shares_count is not None else 0,
        created_at=reel.created_at,
        updated_at=reel.updated_at,
        is_liked=False
    )

@router.get("/admin/all", response_model=List[ReelResponse])
def get_all_reels_admin(
    skip: int = 0,
    limit: int = 20,
    status: Optional[ReelStatus] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Get all reels for admin (with pagination).
    Admin sees all reels regardless of status.
    """
    try:
        query = db.query(Reel)
        if status:
            query = query.filter(Reel.status == status)
        
        reels = query.order_by(desc(Reel.created_at)).offset(skip).limit(limit).all()
        
        # Safely serialize reels to response format
        results = []
        for reel in reels:
            # Skip reels without video_url (required field)
            if not reel.video_url:
                continue
            
            try:
                # Manually construct response to ensure all required fields are set
                reel_response = ReelResponse(
                    id=str(reel.id),
                    title=reel.title,
                    description=reel.description,
                    video_url=reel.video_url,  # Already checked above
                    video_type=reel.video_type if reel.video_type else 'URL',
                    thumbnail_url=reel.thumbnail_url,
                    status=reel.status,
                    views_count=int(reel.views_count) if reel.views_count is not None else 0,
                    likes_count=int(reel.likes_count) if reel.likes_count is not None else 0,
                    comments_count=int(reel.comments_count) if reel.comments_count is not None else 0,
                    shares_count=int(reel.shares_count) if reel.shares_count is not None else 0,
                    created_at=reel.created_at,
                    updated_at=reel.updated_at,
                    is_liked=False  # Admin view doesn't need this
                )
                results.append(reel_response)
            except Exception as e:
                logger.warning(f"Failed to serialize reel {reel.id}: {e}", exc_info=True)
                continue  # Skip this reel if serialization fails
        
        return results
        
    except Exception as e:
        logger.error(f"Error fetching admin reels: {e}", exc_info=True)
        # Return empty list instead of crashing
        return []

@router.get("/admin/analytics")
def get_global_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user)
):
    """
    Get global analytics for reels.
    Returns safe default values if no reels exist.
    """
    try:
        # Safe aggregation with defaults
        total_reels = db.query(Reel).count() or 0
        
        # Use COALESCE or handle None values safely
        total_views_result = db.query(func.sum(Reel.views_count)).scalar()
        total_views = int(total_views_result) if total_views_result is not None else 0
        
        total_likes_result = db.query(func.sum(Reel.likes_count)).scalar()
        total_likes = int(total_likes_result) if total_likes_result is not None else 0
        
        total_comments_result = db.query(func.sum(Reel.comments_count)).scalar()
        total_comments = int(total_comments_result) if total_comments_result is not None else 0
        
        # Safe queries for most viewed/liked - handle empty results
        most_viewed_query = db.query(Reel.title, Reel.views_count).filter(
            Reel.views_count > 0
        ).order_by(desc(Reel.views_count)).limit(5).all()
        
        most_liked_query = db.query(Reel.title, Reel.likes_count).filter(
            Reel.likes_count > 0
        ).order_by(desc(Reel.likes_count)).limit(5).all()
        
        # Safely format results
        most_viewed = []
        for result in most_viewed_query:
            # Handle both tuple and object results
            if isinstance(result, tuple):
                title, count = result
            else:
                title = result.title if hasattr(result, 'title') else None
                count = result.views_count if hasattr(result, 'views_count') else 0
            most_viewed.append({
                "title": title or "(No Title)",
                "count": int(count) if count is not None else 0
            })
        
        most_liked = []
        for result in most_liked_query:
            # Handle both tuple and object results
            if isinstance(result, tuple):
                title, count = result
            else:
                title = result.title if hasattr(result, 'title') else None
                count = result.likes_count if hasattr(result, 'likes_count') else 0
            most_liked.append({
                "title": title or "(No Title)",
                "count": int(count) if count is not None else 0
            })
        
        return {
            "total_reels": total_reels,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "most_viewed": most_viewed,
            "most_liked": most_liked
        }
    except Exception as e:
        logger.error(f"Error fetching reels analytics: {e}", exc_info=True)
        # Return safe defaults instead of crashing
        return {
            "total_reels": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "most_viewed": [],
            "most_liked": []
        }
