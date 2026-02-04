# Import all models to ensure they're registered with SQLAlchemy
# Import referrals first (needed for User model relationships)
from .referrals.models import ReferralCode, Referral

from .users.models import User, UserRole, UserStatus, EmployeeType
from .orders.models import Order, OrderItem, OrderStatus, PaymentStatus as OrderPaymentStatus
from .payments.models import Payment, PaymentWebhookLog, PaymentType, PaymentStatus, PaymentMethod, PaymentProvider
from .bookings.models import Booking, BookingItem, BookingStatusHistory, BookingStatus, BookingSource, PaymentStatus as BookingPaymentStatus
from .wallet.models import Wallet, WalletTransaction, TransactionType, TransactionStatus
from .points.models import PointsBalance, PointsTransaction, PointsTransactionType
from .cashback.models import ClubGiftRecord, ClubGiftStatus
# Backward compatibility aliases
CashbackRecord = ClubGiftRecord
CashbackStatus = ClubGiftStatus
from .offers.models import Offer, OfferStatus, OfferType, Category
from .chat.models import Conversation, Message, ConversationStatus, MessageType
from .memberships.models import (
    MembershipPlan, MembershipSubscription, MembershipHistory,
    MembershipPDFTemplate, MembershipGeneratedPDF, MembershipStatus
)
from .entitlements.models import UserEntitlement, EntitlementUsageLog
from .roles_permissions.models import Role, Permission
