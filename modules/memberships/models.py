from sqlalchemy import Column, String, Float, Integer, Boolean, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, UUID


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    PENDING_PAYMENT = "PENDING_PAYMENT"  # Awaiting payment from user


class MembershipPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_plans"
    
    tier_code = Column(String(50), unique=True, nullable=False, index=True)
    tier_name_ar = Column(String(100), nullable=False)
    tier_name_en = Column(String(100), nullable=False)
    tier_order = Column(Integer, nullable=False, index=True)
    description_ar = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    price = Column(Float, default=0.00)
    currency = Column(String(3), default="USD")
    plan_type = Column(String(50), default="PAID_INFINITE") # FREE, PAID_INFINITE, PAID_FINITE, RECURRING
    duration_days = Column(Integer, nullable=True) # For finite
    purchase_limit = Column(Integer, default=0) # 0 = unlimited
    initial_points = Column(Integer, default=0, nullable=False)  # Base points awarded with membership
    cashback_rate = Column(Float, default=0.00)
    points_multiplier = Column(Float, default=1.00)
    perks = Column(JSON, nullable=True)
    upgrade_criteria = Column(JSON, nullable=True)
    color_hex = Column(String(7), nullable=True)
    icon_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    subscriptions = relationship("MembershipSubscription", foreign_keys="MembershipSubscription.plan_id", back_populates="plan")
    entitlements = relationship("MembershipEntitlement", back_populates="plan")
    
    def __repr__(self):
        return f"<MembershipPlan {self.tier_code}>"


class MembershipSubscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_subscriptions"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=False, index=True)
    membership_number = Column(String(50), unique=True, nullable=False, index=True)
    points_balance = Column(Integer, default=0)
    start_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    auto_renew = Column(Boolean, default=False)
    status = Column(SQLEnum(MembershipStatus), default=MembershipStatus.ACTIVE, index=True)
    upgrade_eligible_date = Column(Date, nullable=True)
    previous_plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=True)
    upgraded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("MembershipPlan", foreign_keys=[plan_id], back_populates="subscriptions")
    previous_plan = relationship("MembershipPlan", foreign_keys=[previous_plan_id])
    user_entitlements = relationship("UserEntitlement", back_populates="subscription")
    
    def __repr__(self):
        return f"<MembershipSubscription {self.membership_number}>"


class MembershipHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_history"
    
    subscription_id = Column(UUID(), ForeignKey('membership_subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    from_plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=True)
    to_plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=True)
    change_type = Column(String(50), nullable=False)
    reason = Column(String, nullable=True)
    changed_by_user_id = Column(UUID(), ForeignKey('users.id'), nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default='NOW()', index=True)
    
    def __repr__(self):
        return f"<MembershipHistory {self.change_type}>"


class MembershipPDFTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_pdf_templates"
    
    plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=True)
    template_type = Column(String(50), default="CARD")
    template_html = Column(String, nullable=True)
    background_image = Column(String, nullable=True)
    qr_code_enabled = Column(Boolean, default=True)
    fields_config = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<MembershipPDFTemplate {self.template_type}>"


class MembershipGeneratedPDF(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_generated_pdfs"
    
    user_id = Column(UUID(), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = Column(UUID(), ForeignKey('membership_subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    template_id = Column(UUID(), ForeignKey('membership_pdf_templates.id'), nullable=True)
    pdf_type = Column(String(50), nullable=False, index=True)
    pdf_data = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default='NOW()', index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<MembershipGeneratedPDF {self.pdf_type}>"


class MembershipBenefits(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "membership_benefits"
    
    plan_id = Column(UUID(), ForeignKey('membership_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = Column(String, nullable=True)
    
    # Welcome Message
    welcome_message_en = Column(String, nullable=True)
    welcome_message_ar = Column(String, nullable=True)
    
    # Hotel Discounts & Free Night Coupons
    hotel_discounts_en = Column(JSON, nullable=True)
    hotel_discounts_ar = Column(JSON, nullable=True)
    
    # Membership Benefits (Lifetime benefits / Program coupons)
    membership_benefits_en = Column(JSON, nullable=True)
    membership_benefits_ar = Column(JSON, nullable=True)
    
    # Flight Coupons / Free Flight Terms
    flight_coupons_en = Column(JSON, nullable=True)
    flight_coupons_ar = Column(JSON, nullable=True)
    free_flight_terms_en = Column(String, nullable=True)
    free_flight_terms_ar = Column(String, nullable=True)
    
    # Car Rental & Airport Transfers
    car_rental_services_en = Column(JSON, nullable=True)
    car_rental_services_ar = Column(JSON, nullable=True)
    
    # Restaurant Benefits
    restaurant_benefits_en = Column(JSON, nullable=True)
    restaurant_benefits_ar = Column(JSON, nullable=True)
    
    # Immediate Activation Coupons
    immediate_coupons_en = Column(JSON, nullable=True)
    immediate_coupons_ar = Column(JSON, nullable=True)
    
    # Additional Tourism Services
    tourism_services_en = Column(JSON, nullable=True)
    tourism_services_ar = Column(JSON, nullable=True)
    
    # Terms & Conditions
    terms_conditions_en = Column(String, nullable=True)
    terms_conditions_ar = Column(String, nullable=True)
    comparison_guarantee_en = Column(String, nullable=True)
    comparison_guarantee_ar = Column(String, nullable=True)
    availability_terms_en = Column(String, nullable=True)
    availability_terms_ar = Column(String, nullable=True)
    coupon_usage_terms_en = Column(String, nullable=True)
    coupon_usage_terms_ar = Column(String, nullable=True)
    
    # Upgrade Info
    upgrade_to_plan_id = Column(UUID(), ForeignKey('membership_plans.id'), nullable=True)
    upgrade_info_en = Column(String, nullable=True)
    upgrade_info_ar = Column(String, nullable=True)
    
    # Relationships
    plan = relationship("MembershipPlan", foreign_keys=[plan_id])
    upgrade_to_plan = relationship("MembershipPlan", foreign_keys=[upgrade_to_plan_id])
    
    def __repr__(self):
        return f"<MembershipBenefits plan_id={self.plan_id}>"