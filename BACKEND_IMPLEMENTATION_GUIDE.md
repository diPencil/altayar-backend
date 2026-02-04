# 🏗️ ALTAYARVIP TOURISM PLATFORM - COMPLETE BACKEND IMPLEMENTATION GUIDE

## 📋 TABLE OF CONTENTS
1. [Project Overview](#project-overview)
2. [Database Schema Summary](#database-schema-summary)
3. [Remaining Models to Create](#remaining-models-to-create)
4. [Service Layer Architecture](#service-layer-architecture)
5. [API Routes Structure](#api-routes-structure)
6. [Fawaterk Payment Integration](#fawaterk-payment-integration)
7. [Authentication & Authorization](#authentication--authorization)
8. [Business Logic Implementation](#business-logic-implementation)
9. [Database Migrations](#database-migrations)
10. [Seeding Initial Data](#seeding-initial-data)

---

## 1. PROJECT OVERVIEW

### Tech Stack
- **Backend Framework**: FastAPI 0.109.0
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **Migrations**: Alembic
- **Payment Gateway**: Fawaterk
- **PDF Generation**: ReportLab
- **Task Queue**: Celery + Redis (for async tasks)

### Project Structure
```
/app/backend/
├── config/
│   ├── __init__.py
│   └── settings.py             # Environment configuration
├── database/
│   ├── __init__.py
│   ├── base.py                  # Database engine & session
│   └── mixins.py                # Common model mixins
├── modules/
│   ├── auth/                    # Authentication logic
│   ├── users/                   # User management
│   ├── roles_permissions/       # RBAC
│   ├── memberships/             # Membership plans & subscriptions
│   ├── entitlements/            # Membership entitlements
│   ├── wallet/                  # Wallet ledger
│   ├── points/                  # Points ledger
│   ├── cashback/                # Cashback ledger
│   ├── bookings/                # Bookings system
│   ├── orders/                  # Manual orders/invoices
│   ├── packages/                # Travel packages
│   ├── activities/              # Standalone activities
│   ├── vouchers/                # Vouchers & redemptions
│   ├── offers/                  # Offers & promotions
│   ├── proposals/               # Custom quotations
│   ├── payments/                # Payments & Fawaterk integration
│   ├── invoices/                # Invoice generation
│   ├── agents/                  # Agent profiles & commissions
│   ├── cms/                     # CMS pages, blogs, reels
│   ├── media/                   # Media library
│   ├── chat/                    # Live chat
│   ├── ads/                     # Advertisements
│   ├── notifications/           # Notification system
│   └── audit_logs/              # Audit trail
├── shared/
│   ├── __init__.py
│   ├── dependencies.py          # Reusable dependencies
│   ├── schemas.py               # Base Pydantic schemas
│   ├── exceptions.py            # Custom exceptions
│   └── utils.py                 # Utility functions
├── migrations/                  # Alembic migrations
│   └── versions/
├── seeders/                     # Database seeding scripts
├── tests/                       # Unit & integration tests
├── .env                         # Environment variables
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Alembic configuration
└── server.py                   # FastAPI application entry point
```

---

## 2. DATABASE SCHEMA SUMMARY

### ✅ Already Created Models
1. **users** - User accounts (all roles)
2. **roles** - User roles (SUPER_ADMIN, ADMIN, EMPLOYEE, CUSTOMER, AGENT)
3. **permissions** - Granular permissions
4. **role_permissions** - Many-to-many role-permission mapping
5. **membership_plans** - Membership tier definitions
6. **membership_subscriptions** - User membership subscriptions
7. **membership_history** - Membership change history
8. **membership_pdf_templates** - PDF templates for cards & benefits
9. **membership_generated_pdfs** - Generated PDF tracking
10. **membership_entitlements** - Plan-level entitlements
11. **user_entitlements** - User entitlement usage tracking
12. **entitlement_usage_log** - Entitlement usage audit trail
13. **wallet_ledger** - Immutable wallet transaction ledger
14. **points_ledger** - Immutable points transaction ledger
15. **cashback_ledger** - Cashback records

### 🔨 Remaining Models to Create

#### A. Bookings Module
```python
# modules/bookings/models.py

class BookingType(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "booking_types"
    type_code: str (HOTEL, FLIGHT, TOUR, TRANSPORTATION, CAR_RENTAL, ACTIVITY, PACKAGE)
    type_name_ar: str
    type_name_en: str
    icon_name: str
    color_hex: str
    is_active: bool
    display_order: int

class Booking(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "bookings"
    booking_number: str (unique, indexed)
    user_id: UUID (FK users)
    agent_id: UUID (FK users, nullable)
    booking_type_id: UUID (FK booking_types)
    package_id: UUID (FK packages, nullable)
    status: Enum (DRAFT, PENDING_PAYMENT, CONFIRMED, IN_PROGRESS, COMPLETED, CANCELLED, REFUNDED)
    payment_status: Enum (UNPAID, PARTIALLY_PAID, PAID, REFUNDED, PARTIALLY_REFUNDED)
    base_amount: float
    discount_amount: float
    voucher_discount: float
    tax_amount: float
    final_amount: float
    currency: str
    booking_details: JSONB
    customer_info: JSONB
    special_requests: str
    start_date: date
    end_date: date
    travelers_count: int
    cancellation_reason: str
    cancelled_by_user_id: UUID (FK users)
    cancelled_at: datetime
    created_by_user_id: UUID (FK users)
    
    # COMPUTED FIELD: booking_source (SELF|ADMIN|AGENT)
    # Logic in service layer based on created_by_user_id vs user_id

class BookingItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "booking_items"
    booking_id: UUID (FK bookings, CASCADE)
    booking_type_id: UUID (FK booking_types)
    item_name_ar: str
    item_name_en: str
    item_details: JSONB
    quantity: int
    unit_price: float
    total_price: float
    currency: str
    status: Enum (PENDING, CONFIRMED, COMPLETED, CANCELLED)
    notes: str

class BookingStatusHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "booking_status_history"
    booking_id: UUID (FK bookings, CASCADE)
    from_status: str
    to_status: str
    changed_by_user_id: UUID (FK users)
    change_reason: str
```

#### B. Orders Module (NEW - Manual Admin Orders)
```python
# modules/orders/models.py

class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"
    order_number: str (unique, indexed)
    user_id: UUID (FK users)
    created_by_user_id: UUID (FK users) # Admin who created it
    order_type: Enum (SERVICE, MANUAL_INVOICE, EXTRA, CUSTOM_FEE, OTHER)
    status: Enum (DRAFT, ISSUED, PAID, CANCELLED, REFUNDED)
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    notes_ar: str
    notes_en: str
    payment_status: Enum (UNPAID, PARTIALLY_PAID, PAID, REFUNDED)
    due_date: date
    issued_at: datetime
    paid_at: datetime
    cancelled_at: datetime
    cancellation_reason: str

class OrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "order_items"
    order_id: UUID (FK orders, CASCADE)
    description_ar: str
    description_en: str
    quantity: int
    unit_price: float
    total_price: float
    currency: str
    metadata: JSONB
```

#### C. Packages & Activities
```python
# modules/packages/models.py

class Package(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "packages"
    slug: str (unique, indexed)
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    category: Enum (HONEYMOON, FAMILY, ADVENTURE, LUXURY, BUSINESS, WEEKEND, SEASONAL)
    base_price: float
    discounted_price: float
    currency: str
    duration_days: int
    duration_nights: int
    max_travelers: int
    min_travelers: int
    destinations: ARRAY[str]
    inclusions_ar: ARRAY[str]
    inclusions_en: ARRAY[str]
    exclusions_ar: ARRAY[str]
    exclusions_en: ARRAY[str]
    itinerary: JSONB
    is_customizable: bool
    featured_image: str
    status: Enum (DRAFT, ACTIVE, INACTIVE, ARCHIVED)
    availability_start: date
    availability_end: date
    total_bookings: int
    total_revenue: float
    average_rating: float
    views_count: int
    is_featured: bool
    display_order: int
    meta_title_ar: str
    meta_title_en: str
    meta_description_ar: str
    meta_description_en: str
    created_by_user_id: UUID (FK users)

class PackageImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "package_images"
    package_id: UUID (FK packages, CASCADE)
    image_data: str (base64)
    caption_ar: str
    caption_en: str
    display_order: int
    is_featured: bool

class Activity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "activities"
    slug: str (unique)
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    category: Enum (ADVENTURE, CULTURAL, ENTERTAINMENT, SPORTS, WELLNESS)
    price: float
    currency: str
    duration_hours: int
    location: str
    max_participants: int
    min_participants: int
    difficulty_level: Enum (EASY, MODERATE, CHALLENGING, EXTREME)
    featured_image: str
    status: Enum (ACTIVE, INACTIVE)
    is_featured: bool
    total_bookings: int
    average_rating: float
    created_by_user_id: UUID (FK users)
```

#### D. Vouchers & Offers
```python
# modules/vouchers/models.py

class Voucher(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vouchers"
    code: str (unique, uppercase, indexed)
    title_ar: str
    title_en: str
    description_ar: str
    description_en: str
    voucher_type: Enum (DISCOUNT_PERCENTAGE, DISCOUNT_FIXED, CASHBACK, FREE_SERVICE)
    discount_value: float
    applicable_to: Enum (ALL, HOTEL, FLIGHT, TOUR, PACKAGE, ACTIVITY)
    min_purchase_amount: float
    max_discount: float
    usage_limit_total: int
    usage_limit_per_user: int
    usage_count: int
    valid_from: datetime
    valid_until: datetime
    status: Enum (ACTIVE, INACTIVE, EXPIRED, EXHAUSTED)
    is_public: bool
    created_by_user_id: UUID (FK users)

class VoucherAssignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "voucher_assignments"
    voucher_id: UUID (FK vouchers, CASCADE)
    user_id: UUID (FK users, CASCADE)
    assigned_by_user_id: UUID (FK users)
    UNIQUE(voucher_id, user_id)

class VoucherRedemption(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "voucher_redemptions"
    voucher_id: UUID (FK vouchers)
    user_id: UUID (FK users)
    booking_id: UUID (FK bookings, SET NULL)
    discount_applied: float
    currency: str
    redeemed_at: datetime

class Offer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offers"
    title_ar: str
    title_en: str
    description_ar: str
    description_en: str
    featured_image: str
    offer_type: Enum (DISCOUNT_PERCENTAGE, DISCOUNT_FIXED, BOGO, FREE_UPGRADE, BONUS_POINTS)
    discount_value: float
    applicable_to: Enum (ALL, HOTEL, FLIGHT, TOUR, PACKAGE, ACTIVITY, SPECIFIC_ITEMS)
    target_item_ids: ARRAY[UUID]
    membership_tiers: ARRAY[str]
    min_purchase_amount: float
    max_discount: float
    usage_limit_total: int
    usage_limit_per_user: int
    usage_count: int
    start_date: datetime
    end_date: datetime
    status: Enum (DRAFT, ACTIVE, EXPIRED, DISABLED)
    is_featured: bool
    priority: int
    created_by_user_id: UUID (FK users)

class Proposal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "proposals"
    proposal_number: str (unique, indexed)
    user_id: UUID (FK users)
    created_by_user_id: UUID (FK users)
    title_ar: str
    title_en: str
    description_ar: str
    description_en: str
    items: JSONB
    total_amount: float
    discount_amount: float
    final_amount: float
    currency: str
    valid_until: date
    status: Enum (DRAFT, SENT, VIEWED, ACCEPTED, REJECTED, EXPIRED)
    accepted_at: datetime
    rejected_at: datetime
    rejection_reason: str
    converted_booking_id: UUID (FK bookings)
    notes: str
```

#### E. Payments & Invoices
```python
# modules/payments/models.py

class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"
    payment_number: str (unique, indexed)
    user_id: UUID (FK users)
    booking_id: UUID (FK bookings, nullable)
    order_id: UUID (FK orders, nullable) # NEW
    subscription_id: UUID (FK membership_subscriptions, nullable)
    payment_type: Enum (BOOKING, MEMBERSHIP_PURCHASE, MEMBERSHIP_RENEWAL, WALLET_DEPOSIT, MANUAL, ORDER) # Added ORDER
    amount: float
    currency: str
    payment_method: Enum (CREDIT_CARD, DEBIT_CARD, WALLET, BANK_TRANSFER, CASH, FAWRY, MEEZA, VODAFONE_CASH, MIXED, OTHER)
    provider: str (FAWATERK, STRIPE, MANUAL)
    provider_transaction_id: str (indexed)
    provider_invoice_id: str
    status: Enum (PENDING, PAID, FAILED, CANCELLED, REFUNDED, PARTIALLY_REFUNDED)
    payment_details: JSONB
    webhook_payload: JSONB
    webhook_received_at: datetime
    webhook_event_id: str (indexed, for idempotency)
    idempotency_key: str (unique, indexed)
    refund_amount: float
    refund_reason: str
    refund_requested_at: datetime
    refund_processed_at: datetime
    error_message: str
    paid_at: datetime
    failed_at: datetime

class PaymentWebhookLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payment_webhook_logs"
    webhook_event_id: str (unique, indexed)
    provider: str (FAWATERK)
    event_type: str
    payment_id: UUID (FK payments)
    provider_transaction_id: str (indexed)
    payload: JSONB
    status: Enum (RECEIVED, PROCESSING, PROCESSED, FAILED, DUPLICATE)
    processed_at: datetime
    error_message: str
    ip_address: str
    processing_time_ms: int

class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"
    invoice_number: str (unique, indexed)
    user_id: UUID (FK users)
    booking_id: UUID (FK bookings, nullable)
    order_id: UUID (FK orders, nullable) # NEW
    payment_id: UUID (FK payments, nullable)
    invoice_type: Enum (STANDARD, PROFORMA, CREDIT_NOTE)
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    currency: str
    status: Enum (DRAFT, ISSUED, PAID, OVERDUE, CANCELLED, REFUNDED)
    issue_date: date
    due_date: date
    paid_date: date
    notes_ar: str
    notes_en: str
    pdf_generated: bool
    pdf_url: str
    created_by_user_id: UUID (FK users)

class InvoiceItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoice_items"
    invoice_id: UUID (FK invoices, CASCADE)
    item_type: Enum (BOOKING_FEE, SERVICE_CHARGE, DISCOUNT, TAX, MEMBERSHIP_FEE)
    description_ar: str
    description_en: str
    quantity: int
    unit_price: float
    total_price: float
    currency: str
```

#### F. Agent Profiles & Commissions
```python
# modules/agents/models.py

class AgentProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_profiles"
    user_id: UUID (FK users, CASCADE, unique)
    company_name: str
    license_number: str
    commission_rate: float (percentage)
    status: Enum (ACTIVE, SUSPENDED, PENDING_APPROVAL)
    total_bookings: int
    total_revenue: float
    total_commission_earned: float
    bank_account_name: str
    bank_account_number: str
    bank_name: str
    bank_branch: str
    bank_swift_code: str
    documents: JSONB
    approved_by_user_id: UUID (FK users)
    approved_at: datetime

class AgentCommission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_commissions"
    agent_id: UUID (FK users)
    booking_id: UUID (FK bookings)
    booking_amount: float
    commission_rate: float
    commission_amount: float
    currency: str
    status: Enum (PENDING, APPROVED, PAID, CANCELLED)
    approved_by_user_id: UUID (FK users)
    approved_at: datetime
    paid_at: datetime
    payment_reference: str
    payment_method: Enum (BANK_TRANSFER, WALLET)
    notes: str
```

#### G. Content Management (CMS, Blogs, Reels)
```python
# modules/cms/models.py

class CMSPage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cms_pages"
    slug: str (unique, indexed)
    title_ar: str
    title_en: str
    content_ar: str
    content_en: str
    page_type: Enum (ABOUT, TERMS, PRIVACY, FAQ, CONTACT, CUSTOM)
    meta_title_ar: str
    meta_title_en: str
    meta_description_ar: str
    meta_description_en: str
    status: Enum (DRAFT, PUBLISHED, ARCHIVED)
    published_at: datetime
    created_by_user_id: UUID (FK users)

class Blog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "blogs"
    slug: str (unique, indexed)
    title_ar: str
    title_en: str
    excerpt_ar: str
    excerpt_en: str
    content_ar: str
    content_en: str
    featured_image: str
    category: Enum (TRAVEL_TIPS, DESTINATIONS, REVIEWS, NEWS, GUIDES)
    tags: ARRAY[str]
    author_id: UUID (FK users)
    status: Enum (DRAFT, PUBLISHED, ARCHIVED)
    published_at: datetime
    views_count: int
    likes_count: int
    shares_count: int
    comments_count: int
    is_featured: bool
    meta_title_ar: str
    meta_title_en: str
    meta_description_ar: str
    meta_description_en: str

class Reel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reels"
    title_ar: str
    title_en: str
    description_ar: str
    description_en: str
    video_data: str (base64 or URL)
    thumbnail: str
    duration_seconds: int
    category: Enum (DESTINATION, HOTEL_TOUR, CUSTOMER_REVIEW, TRAVEL_TIP, BEHIND_SCENES)
    tags: ARRAY[str]
    author_id: UUID (FK users)
    status: Enum (DRAFT, PUBLISHED, ARCHIVED)
    published_at: datetime
    views_count: int
    likes_count: int
    shares_count: int
    comments_count: int
    is_featured: bool

class MediaAsset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "media_assets"
    filename: str
    file_type: Enum (IMAGE, VIDEO, DOCUMENT, AUDIO)
    mime_type: str
    file_size_bytes: int
    file_data: str (base64)
    thumbnail: str
    alt_text_ar: str
    alt_text_en: str
    tags: ARRAY[str]
    uploaded_by_user_id: UUID (FK users)
    usage_count: int

class Comment(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "comments"
    user_id: UUID (FK users, CASCADE)
    content_type: Enum (BLOG, REEL, PACKAGE, ACTIVITY)
    content_id: UUID (indexed)
    parent_comment_id: UUID (FK comments, CASCADE, nullable)
    content: str
    status: Enum (PENDING, APPROVED, REJECTED, DELETED)
    approved_by_user_id: UUID (FK users)
    approved_at: datetime
    likes_count: int

class Like(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "likes"
    user_id: UUID (FK users, CASCADE)
    likeable_type: Enum (BLOG, REEL, COMMENT, PACKAGE)
    likeable_id: UUID (indexed)
    UNIQUE(user_id, likeable_type, likeable_id)

class Share(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shares"
    user_id: UUID (FK users, CASCADE)
    shareable_type: Enum (BLOG, REEL, PACKAGE, ACTIVITY)
    shareable_id: UUID (indexed)
    share_platform: Enum (FACEBOOK, TWITTER, WHATSAPP, INSTAGRAM, EMAIL, COPY_LINK)
```

#### H. Chat System
```python
# modules/chat/models.py

class ChatThread(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_threads"
    thread_number: str (unique, indexed)
    customer_id: UUID (FK users, CASCADE)
    agent_id: UUID (FK users, nullable)
    thread_type: Enum (SUPPORT, SALES, BOOKING_INQUIRY)
    status: Enum (OPEN, ASSIGNED, WAITING, RESOLVED, CLOSED)
    priority: Enum (LOW, MEDIUM, HIGH, URGENT)
    subject: str
    last_message_at: datetime
    last_message_preview: str
    unread_count_customer: int
    unread_count_agent: int
    tags: ARRAY[str]
    rating: int (1-5)
    feedback: str
    rated_at: datetime
    assigned_at: datetime
    closed_at: datetime

class ChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_messages"
    thread_id: UUID (FK chat_threads, CASCADE)
    sender_id: UUID (FK users)
    sender_role: Enum (CUSTOMER, AGENT, ADMIN, SYSTEM)
    message_type: Enum (TEXT, IMAGE, FILE, SYSTEM)
    content: str
    is_read: bool
    read_at: datetime

class ChatAttachment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_attachments"
    message_id: UUID (FK chat_messages, CASCADE)
    file_name: str
    file_type: Enum (IMAGE, PDF, DOCUMENT)
    file_size_bytes: int
    file_data: str (base64)
    mime_type: str
```

#### I. Advertisements & Notifications
```python
# modules/ads/models.py

class Advertisement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "advertisements"
    title_ar: str
    title_en: str
    description_ar: str
    description_en: str
    ad_type: Enum (BANNER, POPUP, INLINE, VIDEO)
    placement: Enum (HOME_TOP, HOME_MIDDLE, OFFERS_PAGE, BOOKING_CONFIRMATION, PROFILE)
    image: str
    video_url: str
    link_url: str
    link_type: Enum (EXTERNAL, PACKAGE, OFFER, BOOKING_PAGE, ACTIVITY, NONE)
    target_id: UUID (nullable)
    target_audience: JSONB
    start_date: datetime
    end_date: datetime
    impressions_count: int
    clicks_count: int
    priority: int
    status: Enum (DRAFT, ACTIVE, PAUSED, EXPIRED)
    created_by_user_id: UUID (FK users)

class AdImpression(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ad_impressions"
    ad_id: UUID (FK advertisements, CASCADE)
    user_id: UUID (FK users, SET NULL)
    session_id: str
    clicked: bool
    device_type: Enum (MOBILE, TABLET, DESKTOP)
    ip_address: str

# modules/notifications/models.py

class NotificationCampaign(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_campaigns"
    campaign_name: str
    title_ar: str
    title_en: str
    message_ar: str
    message_en: str
    notification_type: Enum (MARKETING, ANNOUNCEMENT, REMINDER, ALERT)
    target_audience: JSONB
    send_via: ARRAY[str] (IN_APP, EMAIL, SMS, PUSH)
    schedule_at: datetime
    status: Enum (DRAFT, SCHEDULED, SENDING, SENT, FAILED)
    total_recipients: int
    sent_count: int
    failed_count: int
    sent_at: datetime
    created_by_user_id: UUID (FK users)

class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"
    user_id: UUID (FK users, CASCADE)
    campaign_id: UUID (FK notification_campaigns, SET NULL)
    notification_type: Enum (BOOKING_CONFIRMED, PAYMENT_SUCCESS, CASHBACK_CREDITED, POINTS_EARNED, OFFER_AVAILABLE, MEMBERSHIP_UPGRADE, CHAT_MESSAGE, SYSTEM, MARKETING)
    title_ar: str
    title_en: str
    message_ar: str
    message_en: str
    icon: str
    link_type: Enum (BOOKING, OFFER, WALLET, CHAT, PACKAGE, NONE)
    link_id: UUID
    is_read: bool
    read_at: datetime
    priority: Enum (LOW, MEDIUM, HIGH)
    sent_via: ARRAY[str]

class NotificationPreference(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_preferences"
    user_id: UUID (FK users, CASCADE, unique)
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    preferences: JSONB
```

#### J. System Settings & Audit Logs
```python
# modules/system_settings/models.py

class SystemSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_settings"
    setting_key: str (unique, indexed)
    setting_value: JSONB
    setting_type: Enum (STRING, NUMBER, BOOLEAN, JSON, ARRAY)
    category: Enum (general, payment, notification, membership, booking)
    description_ar: str
    description_en: str
    is_public: bool
    updated_by_user_id: UUID (FK users)

# modules/audit_logs/models.py

class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"
    user_id: UUID (FK users, SET NULL)
    action: str
    module: str
    resource_type: str
    resource_id: UUID
    changes: JSONB (before/after)
    ip_address: str
    user_agent: str
    status: Enum (SUCCESS, FAILED, PARTIAL)
    error_message: str
```

#### K. Analytics (Optional - Aggregated Data)
```python
# modules/analytics/models.py

class AnalyticsDaily(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics_daily"
    date: date (unique, indexed)
    total_bookings: int
    total_revenue: float
    total_users_registered: int
    total_wallet_deposits: float
    total_points_earned: int
    total_cashback_given: float
    bookings_by_type: JSONB
    revenue_by_type: JSONB
    top_packages: JSONB
```

---

## 3. SERVICE LAYER ARCHITECTURE

Each module should have a **service layer** that encapsulates business logic:

### Example: Membership Service
```python
# modules/memberships/service.py

from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from shared.utils import generate_unique_number
from modules.memberships.models import MembershipPlan, MembershipSubscription
from modules.users.models import User

class MembershipService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_subscription(self, user_id: UUID, plan_id: UUID) -> MembershipSubscription:
        """Create new membership subscription"""
        plan = self.db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException("Membership plan not found")
        
        # Generate membership number
        sequence = self.db.query(MembershipSubscription).count() + 1
        membership_number = generate_unique_number("MB", sequence)
        
        subscription = MembershipSubscription(
            user_id=user_id,
            plan_id=plan_id,
            membership_number=membership_number,
            start_date=datetime.now().date(),
            expiry_date=datetime.now().date() + timedelta(days=365),
            status="ACTIVE"
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def upgrade_membership(self, user_id: UUID, new_plan_id: UUID) -> MembershipSubscription:
        """Upgrade user membership to higher tier"""
        subscription = self.db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == user_id
        ).first()
        
        if not subscription:
            raise NotFoundException("Membership subscription not found")
        
        # Create history record
        history = MembershipHistory(
            subscription_id=subscription.id,
            from_plan_id=subscription.plan_id,
            to_plan_id=new_plan_id,
            change_type="UPGRADE",
            changed_at=datetime.now()
        )
        
        # Update subscription
        subscription.previous_plan_id = subscription.plan_id
        subscription.plan_id = new_plan_id
        subscription.upgraded_at = datetime.now()
        
        self.db.add(history)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def get_user_subscription(self, user_id: UUID) -> Optional[MembershipSubscription]:
        """Get user's current membership subscription"""
        return self.db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == user_id
        ).first()
    
    def check_expiry(self, user_id: UUID) -> bool:
        """Check if membership is expired"""
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            return True
        
        if subscription.expiry_date and subscription.expiry_date < datetime.now().date():
            subscription.status = "EXPIRED"
            self.db.commit()
            return True
        
        return False
```

### Key Service Layers to Implement:
1. **AuthService** - Login, register, token management
2. **UserService** - User CRUD, profile management
3. **MembershipService** - Subscription management, upgrades
4. **EntitlementService** - Entitlement usage tracking, redemption
5. **WalletService** - Wallet operations, ledger entries
6. **PointsService** - Points earning, redemption, expiry
7. **CashbackService** - Cashback calculation, approval, crediting
8. **BookingService** - Booking creation, status management
9. **OrderService** - Manual order creation, issuance
10. **PaymentService** - Payment initiation, webhook processing
11. **InvoiceService** - Invoice generation (PDF)
12. **NotificationService** - Send notifications (email, in-app, SMS)
13. **ChatService** - Chat thread management, message sending
14. **AuditService** - Audit log creation

---

## 4. FAWATERK PAYMENT INTEGRATION

### Fawaterk Service Implementation
```python
# modules/payments/fawaterk_service.py

import requests
import hmac
import hashlib
from typing import Dict, Any
from config.settings import settings

class FawaterkService:
    def __init__(self):
        self.api_key = settings.FAWATERK_API_KEY
        self.secret_key = settings.FAWATERK_SECRET_KEY
        self.base_url = settings.FAWATERK_BASE_URL
        self.webhook_secret = settings.FAWATERK_WEBHOOK_SECRET
    
    def create_invoice(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment invoice on Fawaterk"""
        url = f"{self.base_url}/invoices"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "customer_name": payment_data["customer_name"],
            "customer_email": payment_data["customer_email"],
            "customer_phone": payment_data["customer_phone"],
            "amount": payment_data["amount"],
            "currency": payment_data.get("currency", "EGP"),
            "description": payment_data["description"],
            "success_url": payment_data["success_url"],
            "cancel_url": payment_data["cancel_url"],
            "webhook_url": f"{settings.BACKEND_URL}/api/payments/webhook/fawaterk",
            "metadata": payment_data.get("metadata", {})
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature from Fawaterk"""
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def check_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        """Query payment status from Fawaterk"""
        url = f"{self.base_url}/transactions/{transaction_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def process_refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """Process refund via Fawaterk API"""
        url = f"{self.base_url}/refunds"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return response.json()
```

### Payment Service with Idempotency
```python
# modules/payments/service.py

from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from uuid import uuid4
from modules.payments.models import Payment, PaymentWebhookLog
from modules.payments.fawaterk_service import FawaterkService
from shared.exceptions import PaymentException

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.fawaterk = FawaterkService()
    
    def initiate_payment(
        self,
        user_id: UUID,
        payment_type: str,
        amount: float,
        currency: str,
        booking_id: Optional[UUID] = None,
        order_id: Optional[UUID] = None,
        subscription_id: Optional[UUID] = None,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """Initiate payment and create Fawaterk invoice"""
        
        # Generate payment number
        sequence = self.db.query(Payment).count() + 1
        payment_number = generate_unique_number("PAY", sequence)
        
        # Generate idempotency key
        idempotency_key = str(uuid4())
        
        # Create payment record
        payment = Payment(
            payment_number=payment_number,
            user_id=user_id,
            booking_id=booking_id,
            order_id=order_id,
            subscription_id=subscription_id,
            payment_type=payment_type,
            amount=amount,
            currency=currency,
            provider="FAWATERK",
            status="PENDING",
            idempotency_key=idempotency_key
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Get user info
        from modules.users.models import User
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Create Fawaterk invoice
        try:
            fawaterk_data = {
                "customer_name": f"{user.first_name} {user.last_name}",
                "customer_email": user.email,
                "customer_phone": user.phone or "",
                "amount": amount,
                "currency": currency,
                "description": f"Payment for {payment_type}",
                "success_url": success_url or f"app://payment/success",
                "cancel_url": cancel_url or f"app://payment/cancel",
                "metadata": {
                    "payment_id": str(payment.id),
                    "payment_number": payment_number,
                    "payment_type": payment_type
                }
            }
            
            invoice_response = self.fawaterk.create_invoice(fawaterk_data)
            
            # Update payment with Fawaterk details
            payment.provider_transaction_id = invoice_response.get("transaction_id")
            payment.provider_invoice_id = invoice_response.get("invoice_id")
            payment.payment_details = invoice_response
            
            self.db.commit()
            
            return {
                "payment_id": str(payment.id),
                "payment_number": payment_number,
                "fawaterk_invoice_id": invoice_response.get("invoice_id"),
                "payment_url": invoice_response.get("payment_url"),
                "qr_code": invoice_response.get("qr_code"),
                "amount": amount,
                "currency": currency,
                "status": "PENDING"
            }
        
        except Exception as e:
            payment.status = "FAILED"
            payment.error_message = str(e)
            self.db.commit()
            raise PaymentException(f"Failed to initiate payment: {str(e)}")
    
    def process_webhook(
        self,
        webhook_event_id: str,
        event_type: str,
        payload: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """Process Fawaterk webhook with idempotency"""
        
        # Verify signature
        import json
        payload_str = json.dumps(payload, sort_keys=True)
        if not self.fawaterk.verify_webhook_signature(payload_str, signature):
            raise PaymentException("Invalid webhook signature")
        
        # Check idempotency
        existing_log = self.db.query(PaymentWebhookLog).filter(
            PaymentWebhookLog.webhook_event_id == webhook_event_id
        ).first()
        
        if existing_log:
            if existing_log.status == "PROCESSED":
                return {"status": "already_processed", "message": "Webhook already processed"}
            elif existing_log.status == "PROCESSING":
                return {"status": "processing", "message": "Webhook currently being processed"}
        
        # Create webhook log
        webhook_log = PaymentWebhookLog(
            webhook_event_id=webhook_event_id,
            provider="FAWATERK",
            event_type=event_type,
            provider_transaction_id=payload.get("transaction_id"),
            payload=payload,
            status="PROCESSING",
            ip_address=payload.get("ip_address", "")
        )
        
        self.db.add(webhook_log)
        self.db.commit()
        
        try:
            # Find payment
            transaction_id = payload.get("transaction_id")
            payment = self.db.query(Payment).filter(
                Payment.provider_transaction_id == transaction_id
            ).first()
            
            if not payment:
                raise PaymentException(f"Payment not found for transaction {transaction_id}")
            
            webhook_log.payment_id = payment.id
            
            # Process based on event type
            if event_type == "payment.success":
                payment.status = "PAID"
                payment.paid_at = datetime.now()
                payment.webhook_payload = payload
                payment.webhook_received_at = datetime.now()
                payment.webhook_event_id = webhook_event_id
                
                # Execute post-payment actions
                self._execute_post_payment_actions(payment)
            
            elif event_type == "payment.failed":
                payment.status = "FAILED"
                payment.failed_at = datetime.now()
                payment.error_message = payload.get("error_message", "Payment failed")
            
            elif event_type == "payment.cancelled":
                payment.status = "CANCELLED"
            
            elif event_type == "refund.completed":
                payment.status = "REFUNDED"
                payment.refund_processed_at = datetime.now()
            
            # Mark webhook as processed
            webhook_log.status = "PROCESSED"
            webhook_log.processed_at = datetime.now()
            
            self.db.commit()
            
            return {"status": "success", "message": "Webhook processed successfully"}
        
        except Exception as e:
            webhook_log.status = "FAILED"
            webhook_log.error_message = str(e)
            self.db.commit()
            raise
    
    def _execute_post_payment_actions(self, payment: Payment):
        """Execute actions after successful payment"""
        
        if payment.payment_type == "BOOKING":
            # Update booking status
            from modules.bookings.models import Booking
            booking = self.db.query(Booking).filter(Booking.id == payment.booking_id).first()
            if booking:
                booking.status = "CONFIRMED"
                booking.payment_status = "PAID"
                
                # Calculate cashback
                self._create_cashback(booking)
                
                # Award points
                self._award_points(booking)
        
        elif payment.payment_type in ["MEMBERSHIP_PURCHASE", "MEMBERSHIP_RENEWAL"]:
            # Update membership
            from modules.memberships.models import MembershipSubscription
            subscription = self.db.query(MembershipSubscription).filter(
                MembershipSubscription.id == payment.subscription_id
            ).first()
            if subscription:
                subscription.status = "ACTIVE"
        
        elif payment.payment_type == "WALLET_DEPOSIT":
            # Create wallet transaction
            from modules.wallet.service import WalletService
            wallet_service = WalletService(self.db)
            wallet_service.add_transaction(
                user_id=payment.user_id,
                amount=payment.amount,
                transaction_type="DEPOSIT",
                reference_type="PAYMENT",
                reference_id=payment.id,
                description_en=f"Wallet deposit - {payment.payment_number}",
                description_ar=f"إيداع في المحفظة - {payment.payment_number}"
            )
        
        elif payment.payment_type == "ORDER":
            # Update order status
            from modules.orders.models import Order
            order = self.db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.payment_status = "PAID"
                order.status = "PAID"
                order.paid_at = datetime.now()
        
        # Generate invoice
        self._generate_invoice(payment)
        
        # Send notification
        self._send_payment_notification(payment)
    
    def _create_cashback(self, booking):
        """Create cashback record for booking"""
        from modules.cashback.models import CashbackLedger
        from modules.memberships.models import MembershipSubscription
        
        subscription = self.db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == booking.user_id
        ).first()
        
        if subscription and subscription.plan:
            cashback_rate = subscription.plan.cashback_rate
            if cashback_rate > 0:
                cashback_amount = booking.final_amount * (cashback_rate / 100)
                
                cashback = CashbackLedger(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    booking_amount=booking.final_amount,
                    cashback_rate=cashback_rate,
                    cashback_amount=cashback_amount,
                    currency=booking.currency,
                    status="PENDING"
                )
                
                self.db.add(cashback)
    
    def _award_points(self, booking):
        """Award points for booking"""
        from modules.points.service import PointsService
        from modules.memberships.models import MembershipSubscription
        
        subscription = self.db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == booking.user_id
        ).first()
        
        if subscription and subscription.plan:
            points_multiplier = subscription.plan.points_multiplier
            base_points = int(booking.final_amount / 10)  # 1 point per 10 currency units
            points_to_award = int(base_points * points_multiplier)
            
            points_service = PointsService(self.db)
            points_service.add_points(
                user_id=booking.user_id,
                points=points_to_award,
                transaction_type="EARNED",
                reference_type="BOOKING",
                reference_id=booking.id,
                description_en=f"Points earned from booking {booking.booking_number}",
                description_ar=f"نقاط مكتسبة من الحجز {booking.booking_number}",
                multiplier=points_multiplier
            )
```

---

## 5. API ROUTES STRUCTURE

### Main Application (server.py)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from database.base import engine, Base

# Import routers
from modules.auth.routes import router as auth_router
from modules.users.routes import router as users_router
from modules.memberships.routes import router as memberships_router
from modules.bookings.routes import router as bookings_router
from modules.orders.routes import router as orders_router
from modules.payments.routes import router as payments_router
# ... import all other routers

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users_router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(memberships_router, prefix=f"{settings.API_V1_PREFIX}/memberships", tags=["Memberships"])
app.include_router(bookings_router, prefix=f"{settings.API_V1_PREFIX}/bookings", tags=["Bookings"])
app.include_router(orders_router, prefix=f"{settings.API_V1_PREFIX}/orders", tags=["Orders"])
app.include_router(payments_router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
# ... include all other routers

@app.get("/")
def root():
    return {"message": "AltayarVIP Tourism Platform API", "version": settings.APP_VERSION}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

---

## 6. DATABASE MIGRATIONS (Alembic)

### Initialize Alembic
```bash
cd /app/backend
alembic init migrations
```

### Configure alembic.ini
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/altayarvip

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### Create Initial Migration
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

## 7. SEEDING INITIAL DATA

### Seed Script for Roles & Permissions
```python
# seeders/seed_roles_permissions.py

from database.base import SessionLocal
from modules.roles_permissions.models import Role, Permission

def seed_roles_permissions():
    db = SessionLocal()
    
    try:
        # Create system roles
        roles_data = [
            {"role_name": "SUPER_ADMIN", "display_name_ar": "مدير عام", "display_name_en": "Super Admin", "is_system_role": True},
            {"role_name": "ADMIN", "display_name_ar": "مشرف", "display_name_en": "Admin", "is_system_role": True},
            {"role_name": "EMPLOYEE", "display_name_ar": "موظف", "display_name_en": "Employee", "is_system_role": True},
            {"role_name": "CUSTOMER", "display_name_ar": "عميل", "display_name_en": "Customer", "is_system_role": True},
            {"role_name": "AGENT", "display_name_ar": "وكيل", "display_name_en": "Agent", "is_system_role": True},
        ]
        
        for role_data in roles_data:
            existing = db.query(Role).filter(Role.role_name == role_data["role_name"]).first()
            if not existing:
                role = Role(**role_data)
                db.add(role)
        
        db.commit()
        
        # Create permissions
        permissions_data = [
            # Users
            {"permission_code": "users.read", "module": "users", "action": "read", "description_en": "View users"},
            {"permission_code": "users.create", "module": "users", "action": "create", "description_en": "Create users"},
            {"permission_code": "users.update", "module": "users", "action": "update", "description_en": "Update users"},
            {"permission_code": "users.delete", "module": "users", "action": "delete", "description_en": "Delete users"},
            
            # Memberships
            {"permission_code": "memberships.read", "module": "memberships", "action": "read", "description_en": "View memberships"},
            {"permission_code": "memberships.update", "module": "memberships", "action": "update", "description_en": "Update memberships"},
            {"permission_code": "memberships.adjust", "module": "memberships", "action": "adjust", "description_en": "Manual adjustments"},
            
            # ... add all other permissions
        ]
        
        for perm_data in permissions_data:
            existing = db.query(Permission).filter(Permission.permission_code == perm_data["permission_code"]).first()
            if not existing:
                permission = Permission(**perm_data)
                db.add(permission)
        
        db.commit()
        print("✅ Roles and permissions seeded successfully")
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding roles and permissions: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles_permissions()
```

### Seed Membership Plans
```python
# seeders/seed_membership_plans.py

from database.base import SessionLocal
from modules.memberships.models import MembershipPlan

def seed_membership_plans():
    db = SessionLocal()
    
    try:
        plans_data = [
            {
                "tier_code": "GUEST",
                "tier_name_ar": "ضيف",
                "tier_name_en": "Guest",
                "tier_order": 0,
                "price": 0.00,
                "cashback_rate": 0.00,
                "points_multiplier": 1.00,
                "color_hex": "#9E9E9E"
            },
            {
                "tier_code": "BRONZE",
                "tier_name_ar": "برونزي",
                "tier_name_en": "Bronze",
                "tier_order": 1,
                "price": 499.00,
                "cashback_rate": 2.00,
                "points_multiplier": 1.10,
                "color_hex": "#CD7F32"
            },
            {
                "tier_code": "SILVER",
                "tier_name_ar": "فضي",
                "tier_name_en": "Silver",
                "tier_order": 2,
                "price": 999.00,
                "cashback_rate": 3.00,
                "points_multiplier": 1.25,
                "color_hex": "#C0C0C0"
            },
            {
                "tier_code": "GOLD",
                "tier_name_ar": "ذهبي",
                "tier_name_en": "Gold",
                "tier_order": 3,
                "price": 1999.00,
                "cashback_rate": 5.00,
                "points_multiplier": 1.50,
                "color_hex": "#FFD700"
            },
            {
                "tier_code": "PLATINUM",
                "tier_name_ar": "بلاتيني",
                "tier_name_en": "Platinum",
                "tier_order": 4,
                "price": 3999.00,
                "cashback_rate": 7.00,
                "points_multiplier": 1.75,
                "color_hex": "#E5E4E2"
            },
            {
                "tier_code": "DIAMOND",
                "tier_name_ar": "ماسي",
                "tier_name_en": "Diamond",
                "tier_order": 5,
                "price": 7999.00,
                "cashback_rate": 10.00,
                "points_multiplier": 2.00,
                "color_hex": "#B9F2FF"
            }
        ]
        
        for plan_data in plans_data:
            existing = db.query(MembershipPlan).filter(
                MembershipPlan.tier_code == plan_data["tier_code"]
            ).first()
            if not existing:
                plan = MembershipPlan(**plan_data)
                db.add(plan)
        
        db.commit()
        print("✅ Membership plans seeded successfully")
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding membership plans: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_membership_plans()
```

---

## 8. BUSINESS LOGIC SUMMARY

### Wallet Ledger (Immutable)
- Every wallet transaction creates an **immutable record**
- Records `balance_before` and `balance_after`
- Current balance is **computed** from ledger, NOT stored in a single field
- Transactions: DEPOSIT, WITHDRAWAL, PAYMENT, REFUND, CASHBACK, BONUS, COMMISSION

### Points Ledger (Immutable)
- Similar to wallet ledger
- Points expire after 365 days (configurable)
- Tracks `expires_at` for earned points
- Background job marks expired points

### Cashback Flow
1. Booking completed + payment confirmed
2. Cashback record created with `status=PENDING`
3. After 7 days (configurable), admin/accounting approves
4. Approved cashback credited to wallet via ledger entry
5. Wallet balance increases

### Entitlements
- Plan-level: Defined in `membership_entitlements`
- User-level: Tracked in `user_entitlements`
- Quota-based entitlements reset monthly/yearly
- Usage logged in `entitlement_usage_log`

### Booking Source (Computed Field)
```python
def get_booking_source(booking):
    if booking.created_by_user_id == booking.user_id:
        return "SELF"
    elif booking.agent_id:
        return "AGENT"
    else:
        # Check creator role
        creator = db.query(User).filter(User.id == booking.created_by_user_id).first()
        if creator and creator.role in ["SUPER_ADMIN", "ADMIN", "EMPLOYEE"]:
            return "ADMIN"
    return "SELF"
```

### Payment Idempotency
- Each webhook has unique `webhook_event_id`
- Check `payment_webhook_logs` table before processing
- If `status=PROCESSED`, return immediately
- If `status=PROCESSING`, another instance is handling it
- Prevents double crediting/booking confirmation

---

## 9. NEXT STEPS FOR IMPLEMENTATION

### Priority 1: Core Authentication & User Management
1. Create `modules/auth/` with login, register, JWT logic
2. Create `modules/users/routes.py` with CRUD endpoints
3. Test authentication flow

### Priority 2: Membership System
1. Complete `modules/memberships/service.py`
2. Create `modules/memberships/routes.py`
3. Test membership purchase & upgrade flow

### Priority 3: Financial Ledgers
1. Complete wallet/points/cashback services
2. Create routes for each
3. Test ledger immutability

### Priority 4: Bookings & Orders
1. Create booking models & services
2. Create order models & services
3. Implement booking source logic

### Priority 5: Payments (Fawaterk)
1. Complete Fawaterk integration
2. Implement webhook with idempotency
3. Test payment flow end-to-end

### Priority 6: Remaining Modules
1. Packages & activities
2. Vouchers & offers
3. Chat system
4. Notifications
5. CMS & content

---

## 10. TESTING STRATEGY

### Unit Tests
- Test each service method independently
- Mock database interactions
- Test edge cases (insufficient balance, expired memberships, etc.)

### Integration Tests
- Test full API flows (register → login → create booking → pay)
- Test webhook processing with real payloads
- Test RBAC (ensure customers can't access admin routes)

### Load Testing
- Test wallet ledger performance with high transaction volume
- Test webhook idempotency under concurrent requests

---

## 📦 DEPLOYMENT CHECKLIST

- [ ] Environment variables configured (.env)
- [ ] Database created & migrated
- [ ] Initial data seeded (roles, permissions, plans)
- [ ] Fawaterk API keys obtained (live mode)
- [ ] SMTP/SMS credentials configured
- [ ] CORS origins whitelisted
- [ ] JWT secret keys generated (strong, random)
- [ ] Database backups configured
- [ ] Monitoring & logging setup
- [ ] Rate limiting configured
- [ ] API documentation generated (Swagger UI at `/docs`)

---

## 🎯 COMPLETION STATUS

### ✅ COMPLETED
- Project structure
- Configuration management
- Database connection & mixins
- Base schemas & exceptions
- Dependencies (auth, RBAC)
- User models
- Roles & permissions models
- Membership models
- Entitlement models
- Wallet/points/cashback ledger models

### 🔨 TODO (Implement These Next)
- Complete all remaining models (bookings, orders, payments, etc.)
- Create service layer for each module
- Create API routes for each module
- Implement Fawaterk payment integration
- Create PDF generation service
- Create notification service (email, SMS)
- Create audit logging middleware
- Write unit & integration tests
- Create database seeders
- Document API with examples

---

**This guide provides the complete blueprint for the AltayarVIP backend. Follow it systematically, module by module, and you'll have a production-ready tourism platform!**
