from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
import uuid
import logging

from database.base import get_db
from modules.tier_posts.models import TierPost, PostLike, PostComment, PostStatus
from modules.tier_posts.schemas import (
    TierPostCreate, TierPostResponse, CommentCreate, CommentResponse
)
from modules.users.models import User
from shared.dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ User Routes ============

@router.post("", response_model=TierPostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: TierPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tier post (status=PENDING by default)"""
    new_post = TierPost(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        tier_code=post_data.tier_code.upper(),
        content=post_data.content,
        image_url=post_data.image_url,
        status=PostStatus.PENDING
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # Notify admin about new post
    try:
        from modules.notifications.service import NotificationService
        notification_service = NotificationService(db)
        notification_service.notify_tier_post_created(new_post, current_user)
    except Exception as e:
        logger.error(f"Failed to send notification for new tier post: {e}")
    
    # Build response
    response = TierPostResponse(
        id=str(new_post.id),
        user_id=str(new_post.user_id),
        tier_code=new_post.tier_code,
        content=new_post.content,
        image_url=new_post.image_url,
        status=new_post.status.value,
        created_at=new_post.created_at,
        updated_at=new_post.updated_at,
        user_first_name=current_user.first_name,
        user_last_name=current_user.last_name,
        user_avatar=current_user.avatar,
        likes_count=0,
        comments_count=0,
        is_liked_by_current_user=False
    )
    
    return response


@router.get("", response_model=List[TierPostResponse])
def get_tier_posts(
    tier: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get APPROVED posts for a tier (or all tiers if not specified)"""
    query = db.query(TierPost).options(joinedload(TierPost.user))
    
    # Filter by tier if specified
    if tier:
        query = query.filter(TierPost.tier_code == tier.upper())
    
    # Only show APPROVED posts to regular users
    query = query.filter(TierPost.status == PostStatus.APPROVED)
    
    posts = query.order_by(TierPost.created_at.desc()).all()
    
    # Build responses with counts
    responses = []
    for post in posts:
        likes_count = db.query(PostLike).filter(PostLike.post_id == post.id).count()
        comments_count = db.query(PostComment).filter(
            PostComment.post_id == post.id,
            PostComment.status == PostStatus.APPROVED
        ).count()
        is_liked = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id
        ).first() is not None
        
        responses.append(TierPostResponse(
            id=str(post.id),
            user_id=str(post.user_id),
            tier_code=post.tier_code,
            content=post.content,
            image_url=post.image_url,
            status=post.status.value,
            created_at=post.created_at,
            updated_at=post.updated_at,
            user_first_name=post.user.first_name if post.user else None,
            user_last_name=post.user.last_name if post.user else None,
            user_avatar=post.user.avatar if post.user else None,
            likes_count=likes_count,
            comments_count=comments_count,
            is_liked_by_current_user=is_liked
        ))
    
    return responses


@router.post("/{post_id}/like")
def toggle_like(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle like on a post"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    # Check if post exists
    post = db.query(TierPost).filter(TierPost.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if already liked
    existing_like = db.query(PostLike).filter(
        PostLike.post_id == post_uuid,
        PostLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        # Unlike
        db.delete(existing_like)
        db.commit()
        return {"liked": False, "message": "Post unliked"}
    else:
        # Like
        new_like = PostLike(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            post_id=post_uuid
        )
        db.add(new_like)
        db.commit()
        return {"liked": True, "message": "Post liked"}


@router.post("/{post_id}/comments", response_model=CommentResponse)
def add_comment(
    post_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a post (status=PENDING by default)"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    # Check if post exists
    post = db.query(TierPost).filter(TierPost.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    new_comment = PostComment(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        post_id=post_uuid,
        content=comment_data.content,
        status=PostStatus.PENDING
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    # Notify admin about new comment
    try:
        from modules.notifications.service import NotificationService
        notification_service = NotificationService(db)
        notification_service.notify_tier_comment_created(new_comment, post, current_user)
    except Exception as e:
        logger.error(f"Failed to send notification for new tier comment: {e}")
    
    return CommentResponse(
        id=str(new_comment.id),
        user_id=str(new_comment.user_id),
        post_id=str(new_comment.post_id),
        content=new_comment.content,
        status=new_comment.status.value,
        created_at=new_comment.created_at,
        user_first_name=current_user.first_name,
        user_last_name=current_user.last_name,
        user_avatar=current_user.avatar
    )


# ============ Admin Routes (must come before dynamic routes) ============

@router.get("/admin/comments", response_model=List[CommentResponse])
def get_all_comments_admin(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all comments for admin moderation"""
    query = db.query(PostComment).options(joinedload(PostComment.user))
    
    if status_filter:
        query = query.filter(PostComment.status == status_filter.upper())
    
    comments = query.order_by(PostComment.created_at.desc()).all()
    
    return [
        CommentResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            post_id=str(c.post_id),
            content=c.content,
            status=c.status.value,
            created_at=c.created_at,
            user_first_name=c.user.first_name if c.user else None,
            user_last_name=c.user.last_name if c.user else None,
            user_avatar=c.user.avatar if c.user else None
        )
        for c in comments
    ]


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get APPROVED comments for a post"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    comments = db.query(PostComment).options(joinedload(PostComment.user)).filter(
        PostComment.post_id == post_uuid,
        or_(
            PostComment.status == PostStatus.APPROVED,
            and_(
                PostComment.status == PostStatus.PENDING,
                PostComment.user_id == current_user.id
            )
        )
    ).order_by(PostComment.created_at.asc()).all()
    
    return [
        CommentResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            post_id=str(c.post_id),
            content=c.content,
            status=c.status.value,
            created_at=c.created_at,
            user_first_name=c.user.first_name if c.user else None,
            user_last_name=c.user.last_name if c.user else None,
            user_avatar=c.user.avatar if c.user else None
        )
        for c in comments
    ]


# ============ Admin Routes ============

@router.get("/admin/all", response_model=List[TierPostResponse])
def get_all_posts_admin(
    tier: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all posts (any status) for admin moderation"""
    query = db.query(TierPost).options(joinedload(TierPost.user))
    
    if tier:
        query = query.filter(TierPost.tier_code == tier.upper())
    
    if status_filter:
        query = query.filter(TierPost.status == status_filter.upper())
    
    posts = query.order_by(TierPost.created_at.desc()).all()
    
    responses = []
    for post in posts:
        likes_count = db.query(PostLike).filter(PostLike.post_id == post.id).count()
        comments_count = db.query(PostComment).filter(PostComment.post_id == post.id).count()
        
        responses.append(TierPostResponse(
            id=str(post.id),
            user_id=str(post.user_id),
            tier_code=post.tier_code,
            content=post.content,
            image_url=post.image_url,
            status=post.status.value,
            created_at=post.created_at,
            updated_at=post.updated_at,
            user_first_name=post.user.first_name if post.user else None,
            user_last_name=post.user.last_name if post.user else None,
            user_avatar=post.user.avatar if post.user else None,
            likes_count=likes_count,
            comments_count=comments_count,
            is_liked_by_current_user=False
        ))
    
    return responses


@router.put("/{post_id}/approve")
def approve_post(
    post_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Approve a post"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    post = db.query(TierPost).filter(TierPost.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = PostStatus.APPROVED
    db.commit()
    
    return {"success": True, "message": "Post approved"}


@router.put("/{post_id}/reject")
def reject_post(
    post_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reject a post"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    post = db.query(TierPost).filter(TierPost.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post.status = PostStatus.REJECTED
    db.commit()
    
    return {"success": True, "message": "Post rejected"}


@router.delete("/{post_id}")
def delete_post(
    post_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a post (admin only)"""
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID")
    
    post = db.query(TierPost).filter(TierPost.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    
    return {"success": True, "message": "Post deleted"}


@router.put("/comments/{comment_id}/approve")
def approve_comment(
    comment_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Approve a comment"""
    try:
        comment_uuid = uuid.UUID(comment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID")
    
    comment = db.query(PostComment).filter(PostComment.id == comment_uuid).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.status = PostStatus.APPROVED
    db.commit()
    
    return {"success": True, "message": "Comment approved"}


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a comment (admin only)"""
    try:
        comment_uuid = uuid.UUID(comment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid comment ID")
    
    comment = db.query(PostComment).filter(PostComment.id == comment_uuid).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    db.delete(comment)
    db.commit()
    
    return {"success": True, "message": "Comment deleted"}
