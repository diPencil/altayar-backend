from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

class PlanType(str, Enum):
    FREE = "FREE"
    PAID_INFINITE = "PAID_INFINITE"
    PAID_FINITE = "PAID_FINITE"
    RECURRING = "RECURRING"

class MembershipPlanBase(BaseModel):
    tier_code: str
    tier_name_ar: str
    tier_name_en: str
    tier_order: int
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    price: float = 0.0
    currency: str = "USD"
    plan_type: str = "PAID_INFINITE" # Changed from Enum to str to avoid validation errors if DB has strings
    duration_days: Optional[int] = None # For finite plans
    
    # Perks & benefits
    cashback_rate: float = 0.0
    points_multiplier: float = 1.0
    perks: Optional[Dict[str, Any]] = None
    
    # UI
    color_hex: Optional[str] = None
    icon_url: Optional[str] = None
    
    is_active: bool = True
    purchase_limit: int = 0 # 0 means unlimited

class MembershipPlanCreate(MembershipPlanBase):
    pass

class MembershipPlanUpdate(BaseModel):
    tier_code: Optional[str] = None
    tier_name_ar: Optional[str] = None
    tier_name_en: Optional[str] = None
    tier_order: Optional[int] = None
    description_ar: Optional[str] = None
    description_en: Optional[str] = None
    price: Optional[float] = None
    plan_type: Optional[PlanType] = None
    duration_days: Optional[int] = None
    purchase_limit: Optional[int] = None
    perks: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    color_hex: Optional[str] = None

class MembershipPlanResponse(MembershipPlanBase):
    id: str  # Use str instead of UUID to avoid validation issues with SQLite strings
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    members_count: int = 0
    
    class Config:
        from_attributes = True

class SubscriptionCreate(BaseModel):
    plan_id: UUID
    payment_method: Optional[str] = "WALLET"

# New Response Schemas for Subscriptions
class UserSummary(BaseModel):
    id: UUID
    first_name: Optional[str] = "Unknown"
    last_name: Optional[str] = ""
    email: Optional[str] = None
    avatar: Optional[str] = None
    
    class Config:
        from_attributes = True

class SubscriptionResponse(BaseModel):
    id: UUID
    membership_number: str
    status: str
    start_date: Any
    expiry_date: Any
    user: UserSummary
    plan: MembershipPlanResponse
    
    class Config:
        from_attributes = True


# Membership Benefits Schemas
class MembershipBenefitsBase(BaseModel):
    plan_id: UUID
    image_url: Optional[str] = None
    welcome_message_en: Optional[str] = None
    welcome_message_ar: Optional[str] = None
    hotel_discounts_en: Optional[List[Dict[str, Any]]] = None
    hotel_discounts_ar: Optional[List[Dict[str, Any]]] = None
    membership_benefits_en: Optional[List[Dict[str, Any]]] = None
    membership_benefits_ar: Optional[List[Dict[str, Any]]] = None
    flight_coupons_en: Optional[List[Dict[str, Any]]] = None
    flight_coupons_ar: Optional[List[Dict[str, Any]]] = None
    free_flight_terms_en: Optional[str] = None
    free_flight_terms_ar: Optional[str] = None
    car_rental_services_en: Optional[List[Dict[str, Any]]] = None
    car_rental_services_ar: Optional[List[Dict[str, Any]]] = None
    restaurant_benefits_en: Optional[List[Dict[str, Any]]] = None
    restaurant_benefits_ar: Optional[List[Dict[str, Any]]] = None
    immediate_coupons_en: Optional[List[Dict[str, Any]]] = None
    immediate_coupons_ar: Optional[List[Dict[str, Any]]] = None
    tourism_services_en: Optional[List[Dict[str, Any]]] = None
    tourism_services_ar: Optional[List[Dict[str, Any]]] = None
    terms_conditions_en: Optional[str] = None
    terms_conditions_ar: Optional[str] = None
    comparison_guarantee_en: Optional[str] = None
    comparison_guarantee_ar: Optional[str] = None
    availability_terms_en: Optional[str] = None
    availability_terms_ar: Optional[str] = None
    coupon_usage_terms_en: Optional[str] = None
    coupon_usage_terms_ar: Optional[str] = None
    upgrade_to_plan_id: Optional[UUID] = None
    upgrade_info_en: Optional[str] = None
    upgrade_info_ar: Optional[str] = None


class MembershipBenefitsCreate(MembershipBenefitsBase):
    pass


class MembershipBenefitsUpdate(BaseModel):
    image_url: Optional[str] = None
    welcome_message_en: Optional[str] = None
    welcome_message_ar: Optional[str] = None
    hotel_discounts_en: Optional[List[Dict[str, Any]]] = None
    hotel_discounts_ar: Optional[List[Dict[str, Any]]] = None
    membership_benefits_en: Optional[List[Dict[str, Any]]] = None
    membership_benefits_ar: Optional[List[Dict[str, Any]]] = None
    flight_coupons_en: Optional[List[Dict[str, Any]]] = None
    flight_coupons_ar: Optional[List[Dict[str, Any]]] = None
    free_flight_terms_en: Optional[str] = None
    free_flight_terms_ar: Optional[str] = None
    car_rental_services_en: Optional[List[Dict[str, Any]]] = None
    car_rental_services_ar: Optional[List[Dict[str, Any]]] = None
    restaurant_benefits_en: Optional[List[Dict[str, Any]]] = None
    restaurant_benefits_ar: Optional[List[Dict[str, Any]]] = None
    immediate_coupons_en: Optional[List[Dict[str, Any]]] = None
    immediate_coupons_ar: Optional[List[Dict[str, Any]]] = None
    tourism_services_en: Optional[List[Dict[str, Any]]] = None
    tourism_services_ar: Optional[List[Dict[str, Any]]] = None
    terms_conditions_en: Optional[str] = None
    terms_conditions_ar: Optional[str] = None
    comparison_guarantee_en: Optional[str] = None
    comparison_guarantee_ar: Optional[str] = None
    availability_terms_en: Optional[str] = None
    availability_terms_ar: Optional[str] = None
    coupon_usage_terms_en: Optional[str] = None
    coupon_usage_terms_ar: Optional[str] = None
    upgrade_to_plan_id: Optional[UUID] = None
    upgrade_info_en: Optional[str] = None
    upgrade_info_ar: Optional[str] = None


class MembershipBenefitsResponse(MembershipBenefitsBase):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True