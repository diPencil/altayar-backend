from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import uuid
import logging
from datetime import datetime
from sqlalchemy import or_, func

from database.base import get_db
from modules.offers.models import Offer, OfferStatus, OfferType, Category, OfferFavorite, OfferRating
from modules.offers.schemas import (
    OfferCreate, OfferUpdate, OfferResponse, OfferListResponse, OfferAdminListResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse, OfferBookRequest,
    OfferRateRequest, OfferRatingSummaryResponse,
)
from modules.users.models import User, UserRole
from modules.users.models import User, UserRole
from shared.dependencies import get_current_user, get_current_user_optional, require_admin, require_employee_or_admin, require_active_membership
from modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Category Endpoints ============

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all categories.
    """
    query = db.query(Category)
    
    if active_only:
        query = query.filter(Category.is_active == True)
        
    categories = query.order_by(Category.sort_order.asc()).all()
    
    return categories


@router.get("/categories/public", response_model=List[CategoryResponse])
def get_public_categories(db: Session = Depends(get_db)):
    """
    Get active categories (public).
    """
    categories = db.query(Category).filter(
        Category.is_active == True
    ).order_by(Category.sort_order.asc()).all()
    
    return categories


@router.post("/categories", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new category (admin only).
    """
    # Check slug uniqueness
    existing = db.query(Category).filter(Category.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
        
    category = Category(
        id=str(uuid.uuid4()),
        name_ar=data.name_ar,
        name_en=data.name_en,
        slug=data.slug,
        icon=data.icon,
        sort_order=data.sort_order,
        is_active=data.is_active
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update a category (admin only).
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a category (admin only).
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if used
    if category.offers:
        raise HTTPException(status_code=400, detail="Cannot delete category with offers")
        
    db.delete(category)
    db.commit()
    
    return {"success": True, "message": "Category deleted"}


# ============ Public Endpoints ============

@router.get("/public", response_model=List[OfferListResponse])
def get_public_offers(
    offer_type: Optional[str] = None,
    category: Optional[str] = None,
    featured_only: bool = False,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get public active offers (no auth required).
    Used for homepage carousel and offers page.
    """
    query = db.query(Offer).filter(
        Offer.status == OfferStatus.ACTIVE,
        Offer.deleted_at.is_(None)
    )
    
    if offer_type:
        query = query.filter(Offer.offer_type == offer_type)
    if category:
        query = query.filter(Offer.category == category)
    if featured_only:
        query = query.filter(Offer.is_featured == True)

    # Filter expired offers
    now = datetime.utcnow()
    query = query.filter(
        or_(
            Offer.valid_until.is_(None),
            Offer.valid_until >= now
        ),
        or_(
            Offer.target_audience == 'ALL',
            Offer.target_audience.is_(None)
        ),
        # Strict Separation: Public offers must NOT be Marketing offers
        or_(Offer.offer_source == 'ADMIN', Offer.offer_source.is_(None))
    )
    
    offers = query.order_by(Offer.display_order.asc(), Offer.created_at.desc()).offset(offset).limit(limit).all()
    offer_ids = [str(o.id) for o in offers]

    fav_ids = set()
    if current_user and offers:
        fav_rows = db.query(OfferFavorite.offer_id).filter(
            OfferFavorite.user_id == str(current_user.id),
            OfferFavorite.offer_id.in_(offer_ids),
        ).all()
        fav_ids = {str(r[0]) for r in fav_rows}

    ratings_map = _get_offer_ratings_map(
        db,
        offer_ids,
        current_user_id=str(current_user.id) if current_user else None,
    )

    return [
        _offer_to_list_response(
            o,
            is_favorited=(str(o.id) in fav_ids),
            rating_count=ratings_map.get(str(o.id), {}).get("rating_count", 0),
            average_rating=ratings_map.get(str(o.id), {}).get("average_rating", 0.0),
            my_rating=ratings_map.get(str(o.id), {}).get("my_rating"),
        )
        for o in offers
    ]


@router.get("/public/featured", response_model=List[OfferListResponse])
def get_featured_offers(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get featured offers for carousel (no auth required).
    """
    from sqlalchemy import or_
    now = datetime.utcnow()
    offers = db.query(Offer).filter(
        Offer.status == OfferStatus.ACTIVE,
        or_(Offer.is_featured == True, Offer.is_hot == True),
        Offer.deleted_at.is_(None),
        or_(Offer.valid_until.is_(None), Offer.valid_until >= now),
        or_(Offer.target_audience == 'ALL', Offer.target_audience.is_(None)),
        # Strict Separation: Featured offers must NOT be Marketing offers
        or_(Offer.offer_source == 'ADMIN', Offer.offer_source.is_(None))
    ).order_by(Offer.display_order.asc()).limit(10).all()
    offer_ids = [str(o.id) for o in offers]

    fav_ids = set()
    if current_user and offers:
        fav_rows = db.query(OfferFavorite.offer_id).filter(
            OfferFavorite.user_id == str(current_user.id),
            OfferFavorite.offer_id.in_(offer_ids),
        ).all()
        fav_ids = {str(r[0]) for r in fav_rows}

    ratings_map = _get_offer_ratings_map(
        db,
        offer_ids,
        current_user_id=str(current_user.id) if current_user else None,
    )

    return [
        _offer_to_list_response(
            o,
            is_favorited=(str(o.id) in fav_ids),
            rating_count=ratings_map.get(str(o.id), {}).get("rating_count", 0),
            average_rating=ratings_map.get(str(o.id), {}).get("average_rating", 0.0),
            my_rating=ratings_map.get(str(o.id), {}).get("my_rating"),
        )
        for o in offers
    ]


@router.get("/public/{offer_id}", response_model=OfferResponse)
def get_public_offer(
    offer_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get single offer details (no auth required).
    Increments view count.
    """
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.status == OfferStatus.ACTIVE,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Increment view count
    offer.view_count = (offer.view_count or 0) + 1
    db.commit()

    is_favorited = False
    if current_user:
        is_favorited = db.query(OfferFavorite).filter(
            OfferFavorite.user_id == str(current_user.id),
            OfferFavorite.offer_id == str(offer.id),
        ).first() is not None

    ratings_map = _get_offer_ratings_map(
        db,
        [str(offer.id)],
        current_user_id=str(current_user.id) if current_user else None,
    )
    stats = ratings_map.get(str(offer.id), {})

    return _offer_to_response(
        offer,
        is_favorited=is_favorited,
        rating_count=stats.get("rating_count", 0),
        average_rating=stats.get("average_rating", 0.0),
        my_rating=stats.get("my_rating"),
    )


# ============ Favorites Endpoints (MUST come before /{offer_id}) ============

@router.get("/favorites", response_model=List[OfferListResponse])
def get_offer_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all favorite offers for the current user.
    """
    favs = db.query(OfferFavorite).filter(OfferFavorite.user_id == str(current_user.id)).all()
    if not favs:
        return []

    ids = [str(f.offer_id) for f in favs]
    offers = db.query(Offer).filter(
        Offer.id.in_(ids),
        Offer.deleted_at.is_(None),
        Offer.status == OfferStatus.ACTIVE,
    ).all()

    # Preserve favorite order (roughly) by ids list
    offer_by_id = {str(o.id): o for o in offers}
    ordered = [offer_by_id[i] for i in ids if i in offer_by_id]
    ordered_ids = [str(o.id) for o in ordered]
    ratings_map = _get_offer_ratings_map(db, ordered_ids, current_user_id=str(current_user.id))

    return [
        _offer_to_list_response(
            o,
            is_favorited=True,
            rating_count=ratings_map.get(str(o.id), {}).get("rating_count", 0),
            average_rating=ratings_map.get(str(o.id), {}).get("average_rating", 0.0),
            my_rating=ratings_map.get(str(o.id), {}).get("my_rating"),
        )
        for o in ordered
    ]


@router.post("/{offer_id}/favorite")
def add_offer_to_favorites(
    offer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add an offer to user's favorites.
    """
    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.deleted_at.is_(None)).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    existing = db.query(OfferFavorite).filter(
        OfferFavorite.user_id == str(current_user.id),
        OfferFavorite.offer_id == offer_id,
    ).first()
    if existing:
        return {"message": "Already in favorites"}

    fav = OfferFavorite(id=str(uuid.uuid4()), user_id=str(current_user.id), offer_id=offer_id)
    db.add(fav)
    db.commit()
    return {"message": "Added to favorites"}


@router.delete("/{offer_id}/favorite")
def remove_offer_from_favorites(
    offer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an offer from user's favorites.
    """
    fav = db.query(OfferFavorite).filter(
        OfferFavorite.user_id == str(current_user.id),
        OfferFavorite.offer_id == offer_id,
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")

    db.delete(fav)
    db.commit()
    return {"message": "Removed from favorites"}


@router.post("/{offer_id}/rate", response_model=OfferRatingSummaryResponse)
def rate_offer(
    offer_id: str,
    data: OfferRateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rate an offer (1-5 stars).
    If the user already rated this offer, updates their rating (count will not increase).
    """
    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.deleted_at.is_(None)).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    user_id = str(current_user.id)
    existing = db.query(OfferRating).filter(
        OfferRating.user_id == user_id,
        OfferRating.offer_id == offer_id,
    ).first()

    if existing:
        existing.rating = int(data.rating)
    else:
        db.add(
            OfferRating(
                id=str(uuid.uuid4()),
                user_id=user_id,
                offer_id=offer_id,
                rating=int(data.rating),
            )
        )

    db.commit()

    rating_count, avg_rating = db.query(
        func.count(OfferRating.id),
        func.avg(OfferRating.rating),
    ).filter(OfferRating.offer_id == offer_id).first()

    return OfferRatingSummaryResponse(
        rating_count=int(rating_count or 0),
        average_rating=float(avg_rating or 0.0),
        my_rating=int(data.rating),
    )


# ============ Admin Endpoints ============

@router.get("", response_model=List[OfferAdminListResponse])
def get_all_offers(
    status: Optional[str] = None,
    offer_type: Optional[str] = None,
    offer_source: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get all offers (admin/employee).
    Includes drafts and paused offers.
    """
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    query = db.query(Offer).filter(Offer.deleted_at.is_(None))

    # Employees should only see their own offers in this endpoint.
    # (Admin can see everything.)
    if user_role == "EMPLOYEE":
        query = query.filter(Offer.created_by_user_id == str(current_user.id))
    
    if status:
        query = query.filter(Offer.status == status)
    if offer_type:
        query = query.filter(Offer.offer_type == offer_type)
    if offer_source:
        query = query.filter(Offer.offer_source == offer_source)
    
    offers = query.order_by(Offer.created_at.desc()).offset(offset).limit(limit).all()

    offer_ids = [str(o.id) for o in offers]
    ratings_map = _get_offer_ratings_map(db, offer_ids, current_user_id=None)

    creator_ids = {str(o.created_by_user_id) for o in offers if o.created_by_user_id}
    creators_map: dict[str, dict] = {}
    if creator_ids:
        rows = db.query(
            User.id,
            User.first_name,
            User.last_name,
            User.email,
            User.role,
        ).filter(User.id.in_(list(creator_ids))).all()

        for user_id, first_name, last_name, email, role in rows:
            role_str = role.value if hasattr(role, "value") else str(role)
            name = f"{first_name} {last_name}".strip()
            creators_map[str(user_id)] = {
                "name": name or None,
                "email": email or None,
                "role": role_str or None,
            }

    return [
        _offer_to_admin_list_response(
            o,
            creator=creators_map.get(str(o.created_by_user_id)) if o.created_by_user_id else None,
            rating_count=ratings_map.get(str(o.id), {}).get("rating_count", 0),
            average_rating=ratings_map.get(str(o.id), {}).get("average_rating", 0.0),
            my_rating=ratings_map.get(str(o.id), {}).get("my_rating"),
        )
        for o in offers
    ]


@router.get("/{offer_id}", response_model=OfferResponse)
def get_offer(
    offer_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get offer details (admin or employee).
    """
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role == "EMPLOYEE":
        # Employees can only view their own marketing offers
        if offer.created_by_user_id != str(current_user.id) or offer.offer_source != "MARKETING":
            raise HTTPException(status_code=403, detail="Access denied")

    ratings_map = _get_offer_ratings_map(db, [str(offer.id)], current_user_id=None)
    stats = ratings_map.get(str(offer.id), {})

    return _offer_to_response(
        offer,
        rating_count=stats.get("rating_count", 0),
        average_rating=stats.get("average_rating", 0.0),
        my_rating=stats.get("my_rating"),
    )


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    data: OfferCreate,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new offer (admin or employee).
    """
    # Enforce Role Restrictions
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    
    if user_role == "EMPLOYEE":
        # Employees cannot create Global offers
        target = getattr(data, 'target_audience', 'ASSIGNED')
        if target == 'ALL':
             raise HTTPException(status_code=403, detail="Employees cannot create Global offers. Please select Assigned or Specific audience.")
        
        # Employees cannot set Featured/Hot
        if data.is_featured or data.is_hot:
             raise HTTPException(status_code=403, detail="Employees cannot set Featured or Hot deals.")

    offer = Offer(
        id=str(uuid.uuid4()),
        title_ar=data.title_ar,
        title_en=data.title_en,
        description_ar=data.description_ar,
        description_en=data.description_en,
        image_url=data.image_url,
        offer_type=data.offer_type,
        category=data.category,
        category_id=data.category_id,
        destination=data.destination,
        original_price=data.original_price,
        discounted_price=data.discounted_price,
        currency=data.currency,
        discount_percentage=data.discount_percentage,
        duration_days=data.duration_days,
        duration_nights=data.duration_nights,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        status=data.status,
        is_featured=data.is_featured,
        is_hot=data.is_hot,
        display_order=data.display_order,
        includes=json.dumps(data.includes) if data.includes else None,
        excludes=json.dumps(data.excludes) if data.excludes else None,
        terms=data.terms,
        # Creator & Targeting
        created_by_user_id=str(current_user.id),
        target_audience=getattr(data, 'target_audience', 'ALL'),
        target_user_ids=json.dumps(getattr(data, 'target_user_ids', [])) if hasattr(data, 'target_user_ids') and data.target_user_ids else None,
        offer_source=data.offer_source,
    )
    
    db.add(offer)
    db.commit()
    db.refresh(offer)
    
    # Trigger Notification (In-App + Push)
    try:
        notification_service = NotificationService(db)
        notification_service.notify_offer_created(offer)
    except Exception as e:
        logger.error(f"Failed to send offer notification: {e}")
    
    logger.info(f"✅ Offer created: {offer.title_en} by {current_user.email}")
    
    return _offer_to_response(offer)


@router.put("/{offer_id}", response_model=OfferResponse)
def update_offer(
    offer_id: str,
    data: OfferUpdate,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Update an offer (admin or employee).
    """
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role == "EMPLOYEE":
        # Employees can only update their own marketing offers
        if offer.created_by_user_id != str(current_user.id) or offer.offer_source != "MARKETING":
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    if user_role == "EMPLOYEE":
        # Enforce employee restrictions (same spirit as create_offer)
        if update_data.get("target_audience") == "ALL":
            raise HTTPException(status_code=403, detail="Employees cannot create Global offers. Please select Assigned or Specific audience.")
        if update_data.get("is_featured") is True or update_data.get("is_hot") is True:
            raise HTTPException(status_code=403, detail="Employees cannot set Featured or Hot deals.")
        if "offer_source" in update_data and update_data.get("offer_source") not in (None, "MARKETING"):
            raise HTTPException(status_code=403, detail="Employees cannot change offer source.")
    
    for field, value in update_data.items():
        # Prevent employees from changing offer_source away from MARKETING (even if request passes validation)
        if user_role == "EMPLOYEE" and field == "offer_source":
            continue
        if field in ['includes', 'excludes'] and value is not None:
            setattr(offer, field, json.dumps(value))
        else:
            setattr(offer, field, value)
    
    db.commit()
    db.refresh(offer)
    
    logger.info(f"✅ Offer updated: {offer.title_en} by {current_user.email}")
    
    return _offer_to_response(offer)


@router.delete("/{offer_id}")
def delete_offer(
    offer_id: str,
    current_user: User = Depends(require_employee_or_admin),
    db: Session = Depends(get_db)
):
    """
    Soft delete an offer (admin or employee).
    """
    from datetime import datetime
    
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role == "EMPLOYEE":
        # Employees can only delete their own marketing offers
        if offer.created_by_user_id != str(current_user.id) or offer.offer_source != "MARKETING":
            raise HTTPException(status_code=403, detail="Access denied")
    
    offer.deleted_at = datetime.utcnow()
    offer.status = OfferStatus.DELETED
    db.commit()
    
    logger.info(f"✅ Offer deleted: {offer.title_en} by {current_user.email}")
    
    return {"success": True, "message": "Offer deleted"}


@router.post("/{offer_id}/activate")
def activate_offer(
    offer_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activate an offer (admin only).
    """
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer.status = OfferStatus.ACTIVE
    db.commit()
    
    return {"success": True, "message": "Offer activated"}


@router.post("/{offer_id}/pause")
def pause_offer(
    offer_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Pause an offer (admin only).
    """
    offer = db.query(Offer).filter(
        Offer.id == offer_id,
        Offer.deleted_at.is_(None)
    ).first()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer.status = OfferStatus.PAUSED
    db.commit()
    
    return {" success": True, "message": "Offer paused"}


# ============ User-Specific Offers ============

@router.get("/user/my-offers", response_model=List[OfferListResponse])
def get_user_offers(
    exclude_global: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get offers targeted to the current user.
    Includes:
    - ALL audience offers (unless exclude_global=True)
    - ASSIGNED offers (if user is assigned to the creator employee)
    - SPECIFIC offers (if user ID is in target_user_ids)
    """
    user_id = str(current_user.id)
    
    # Base query for active offers
    now = datetime.utcnow()
    query = db.query(Offer).filter(
        Offer.status == OfferStatus.ACTIVE,
        Offer.deleted_at.is_(None),
        or_(Offer.valid_until.is_(None), Offer.valid_until >= now)
    )
    
    # Get all offers and filter by targeting logic
    all_offers = query.all()
    targeted_offers = []
    
    for offer in all_offers:
        # ALL audience - everyone sees it
        if offer.target_audience == "ALL" or not offer.target_audience:
            if not exclude_global:
                targeted_offers.append(offer)
            continue
        
        # ASSIGNED - only assigned users of the creator
        if offer.target_audience == "ASSIGNED":
            if offer.created_by_user_id and current_user.assigned_employee_id == offer.created_by_user_id:
                targeted_offers.append(offer)
            continue
        
        # SPECIFIC - check if user ID is in target list
        if offer.target_audience == "SPECIFIC":
            if offer.target_user_ids:
                try:
                    target_ids = json.loads(offer.target_user_ids)
                    if user_id in target_ids:
                        targeted_offers.append(offer)
                except:
                    pass
    
    # Sort by display order and creation date
    targeted_offers.sort(key=lambda x: (x.display_order or 0, x.created_at), reverse=True)
    
    fav_ids = set()
    if targeted_offers:
        ids = [str(o.id) for o in targeted_offers]
        fav_rows = db.query(OfferFavorite.offer_id).filter(
            OfferFavorite.user_id == str(current_user.id),
            OfferFavorite.offer_id.in_(ids),
        ).all()
        fav_ids = {str(r[0]) for r in fav_rows}

    offer_ids = [str(o.id) for o in targeted_offers]
    ratings_map = _get_offer_ratings_map(db, offer_ids, current_user_id=str(current_user.id))

    return [
        _offer_to_list_response(
            o,
            is_favorited=(str(o.id) in fav_ids),
            rating_count=ratings_map.get(str(o.id), {}).get("rating_count", 0),
            average_rating=ratings_map.get(str(o.id), {}).get("average_rating", 0.0),
            my_rating=ratings_map.get(str(o.id), {}).get("my_rating"),
        )
        for o in targeted_offers
    ]


@router.post("/{offer_id}/book")
def book_offer(
    offer_id: str,
    book_data: OfferBookRequest,
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    Create a booking from an offer and initiate payment.
    """
    from modules.bookings.models import Booking, BookingItem, BookingStatus, PaymentStatus as BookingPaymentStatus, BookingType
    from modules.bookings.payment_helper import create_payment_for_booking
    from modules.payments.service import PaymentService
    from shared.utils import generate_unique_number

    # 1. Get Offer
    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.status == OfferStatus.ACTIVE, Offer.deleted_at.is_(None)).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found or no longer active")

    # 2. Create Booking
    sequence = db.query(Booking).count() + 1
    booking_number = generate_unique_number("BK-OFF", sequence)
    
    price = offer.discounted_price if offer.discounted_price is not None else offer.original_price
    
    booking = Booking(
        id=str(uuid.uuid4()),
        booking_number=booking_number,
        user_id=str(current_user.id),
        created_by_user_id=str(current_user.id),
        offer_id=offer.id,
        booking_type=BookingType.PACKAGE, # Default to package for offers
        status=BookingStatus.PENDING,
        start_date=datetime.utcnow(), # Default to now (or offer validity start if provided)
        subtotal=price,
        tax_amount=0,
        discount_amount=0,
        total_amount=price,
        currency=offer.currency or "USD",
        payment_status=BookingPaymentStatus.UNPAID,
        title_ar=offer.title_ar,
        title_en=offer.title_en,
        description_ar=offer.description_ar,
        description_en=offer.description_en,
    )
    db.add(booking)
    db.flush()

    # 3. Create Booking Item
    item = BookingItem(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        item_type="offer",
        description_ar=offer.title_ar,
        description_en=offer.title_en,
        quantity=1,
        unit_price=price,
        total_price=price,
        currency=offer.currency or "USD",
        item_details={"offer_id": offer.id, "offer_type": str(offer.offer_type)}
    )
    db.add(item)
    
    # Update offer stats
    offer.booking_count = (offer.booking_count or 0) + 1
    
    # 4. Create Payment Record
    try:
        create_payment_for_booking(booking, db)
    except Exception as e:
        logger.error(f"Failed to create payment for offer booking: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to initiate booking payment")

    db.commit()
    db.refresh(booking)

    # 5. Initiate Payment (use settings: URLs + payment method, e.g. 2=Fawry works when Card fails)
    from config.settings import settings
    payment_service = PaymentService(db)
    result = payment_service.initiate_booking_payment(
        booking_id=str(booking.id),
        user_id=str(current_user.id),
        payment_method_id=getattr(settings, "FAWATERK_DEFAULT_PAYMENT_METHOD", 2),
        success_url=settings.PAYMENT_SUCCESS_URL,
        fail_url=settings.PAYMENT_FAIL_URL,
        save_card=book_data.save_card
    )
    
    # Add booking info to result
    result["booking_id"] = str(booking.id)
    result["booking_number"] = booking_number
    
    return result


# ============ Helper Functions ============

def _get_offer_ratings_map(
    db: Session,
    offer_ids: List[str],
    current_user_id: Optional[str] = None,
):
    """
    Returns a map:
      offer_id -> {"rating_count": int, "average_rating": float, "my_rating": Optional[int]}
    """
    stats: dict[str, dict] = {}
    if not offer_ids:
        return stats

    rows = db.query(
        OfferRating.offer_id,
        func.count(OfferRating.id),
        func.avg(OfferRating.rating),
    ).filter(
        OfferRating.offer_id.in_(offer_ids)
    ).group_by(
        OfferRating.offer_id
    ).all()

    for offer_id, cnt, avg in rows:
        stats[str(offer_id)] = {
            "rating_count": int(cnt or 0),
            "average_rating": float(avg or 0.0),
            "my_rating": None,
        }

    if current_user_id:
        my_rows = db.query(
            OfferRating.offer_id,
            OfferRating.rating,
        ).filter(
            OfferRating.user_id == str(current_user_id),
            OfferRating.offer_id.in_(offer_ids),
        ).all()
        for offer_id, rating in my_rows:
            k = str(offer_id)
            if k not in stats:
                stats[k] = {"rating_count": 0, "average_rating": 0.0, "my_rating": None}
            stats[k]["my_rating"] = int(rating)

    return stats


def _offer_to_response(
    offer: Offer,
    is_favorited: bool = False,
    rating_count: int = 0,
    average_rating: float = 0.0,
    my_rating: Optional[int] = None,
) -> OfferResponse:
    return OfferResponse(
        id=str(offer.id),
        title_ar=offer.title_ar,
        title_en=offer.title_en,
        description_ar=offer.description_ar,
        description_en=offer.description_en,
        image_url=offer.image_url,
        offer_type=offer.offer_type.value if hasattr(offer.offer_type, 'value') else str(offer.offer_type),
        category=offer.category,
        category_id=offer.category_id,
        category_details=offer.category_rel,
        destination=offer.destination,
        original_price=offer.original_price,
        discounted_price=offer.discounted_price,
        currency=offer.currency,
        discount_percentage=offer.discount_percentage,
        duration_days=offer.duration_days,
        duration_nights=offer.duration_nights,
        valid_from=offer.valid_from,
        valid_until=offer.valid_until,
        status=offer.status.value if hasattr(offer.status, 'value') else str(offer.status),
        is_featured=offer.is_featured or False,
        is_hot=offer.is_hot or False,
        display_order=offer.display_order or 0,
        view_count=offer.view_count or 0,
        booking_count=offer.booking_count or 0,
        includes=json.loads(offer.includes) if offer.includes else None,
        excludes=json.loads(offer.excludes) if offer.excludes else None,
        terms=offer.terms,
        # Creator & Targeting 
        created_by_user_id=offer.created_by_user_id,
        target_audience=offer.target_audience,
        target_user_ids=json.loads(offer.target_user_ids) if offer.target_user_ids else None,
        offer_source=offer.offer_source,
        is_favorited=is_favorited,
        rating_count=rating_count,
        average_rating=average_rating,
        my_rating=my_rating,
        created_at=offer.created_at,
        updated_at=offer.updated_at,
    )


def _offer_to_list_response(
    offer: Offer,
    is_favorited: bool = False,
    rating_count: int = 0,
    average_rating: float = 0.0,
    my_rating: Optional[int] = None,
) -> OfferListResponse:
    return OfferListResponse(
        id=str(offer.id),
        title_ar=offer.title_ar,
        title_en=offer.title_en,
        image_url=offer.image_url,
        offer_type=offer.offer_type.value if hasattr(offer.offer_type, 'value') else str(offer.offer_type),
        category=offer.category,
        category_id=offer.category_id,
        destination=offer.destination,
        original_price=offer.original_price,
        discounted_price=offer.discounted_price,
        currency=offer.currency,
        discount_percentage=offer.discount_percentage,
        duration_days=offer.duration_days,
        duration_nights=offer.duration_nights,
        valid_from=offer.valid_from,
        valid_until=offer.valid_until,
        status=offer.status.value if hasattr(offer.status, 'value') else str(offer.status),
        is_featured=offer.is_featured or False,
        is_hot=offer.is_hot or False,
        display_order=offer.display_order,
        offer_source=offer.offer_source,
        is_favorited=is_favorited,
        rating_count=rating_count,
        average_rating=average_rating,
        my_rating=my_rating,
    )


def _offer_to_admin_list_response(
    offer: Offer,
    creator: Optional[dict] = None,
    is_favorited: bool = False,
    rating_count: int = 0,
    average_rating: float = 0.0,
    my_rating: Optional[int] = None,
) -> OfferAdminListResponse:
    return OfferAdminListResponse(
        id=str(offer.id),
        title_ar=offer.title_ar,
        title_en=offer.title_en,
        image_url=offer.image_url,
        offer_type=offer.offer_type.value if hasattr(offer.offer_type, "value") else str(offer.offer_type),
        category=offer.category,
        category_id=offer.category_id,
        destination=offer.destination,
        original_price=offer.original_price,
        discounted_price=offer.discounted_price,
        currency=offer.currency,
        discount_percentage=offer.discount_percentage,
        duration_days=offer.duration_days,
        duration_nights=offer.duration_nights,
        valid_from=offer.valid_from,
        valid_until=offer.valid_until,
        status=offer.status.value if hasattr(offer.status, "value") else str(offer.status),
        is_featured=offer.is_featured or False,
        is_hot=offer.is_hot or False,
        display_order=offer.display_order,
        offer_source=offer.offer_source,
        is_favorited=is_favorited,
        rating_count=rating_count,
        average_rating=average_rating,
        my_rating=my_rating,
        created_at=offer.created_at,
        updated_at=offer.updated_at,
        created_by_user_id=offer.created_by_user_id,
        created_by_name=(creator.get("name") if creator else None),
        created_by_email=(creator.get("email") if creator else None),
        created_by_role=(creator.get("role") if creator else None),
    )

