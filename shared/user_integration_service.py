from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timedelta
import json
import logging

from modules.users.models import User, UserRole, UserStatus
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus
from modules.points.service import PointsService
from modules.wallet.models import Wallet
from shared.exceptions import BadRequestException
from shared.utils import hash_password

logger = logging.getLogger(__name__)


class UserIntegrationService:
    """
    Integrated service for managing complete user lifecycle including:
    - User creation/updates
    - Membership subscriptions
    - Points and wallet initialization
    - Atomic transactions for all operations
    """

    def __init__(self, db: Session):
        self.db = db
        self.points_service = PointsService(db)

    def create_user_with_membership(self, user_data: Dict[str, Any], created_by_admin: bool = False) -> Dict[str, Any]:
        """
        Create a complete user with membership, points, and wallet in a single atomic transaction.

        Args:
            user_data: User creation data including membership info
            created_by_admin: Whether this is admin creation (affects verification status)

        Returns:
            Dict containing success status and created user data

        Raises:
            BadRequestException: If validation fails
            Exception: If database operations fail (transaction will be rolled back)
        """

        # Use SQLAlchemy's automatic transaction management
        # All operations will be rolled back if any exception occurs

        try:
            # 1. Validate input data
            self._validate_user_creation_data(user_data)

            # 2. Create user
            user = self._create_user_record(user_data, created_by_admin)
            self.db.add(user)
            self.db.flush()  # Get user ID without committing

            created_subscription_id = None
            awarded_points = 0

            # 3. Create membership subscription if plan specified
            if user_data.get("plan_id"):
                subscription, points_awarded = self._create_membership_subscription(user, user_data)
                created_subscription_id = str(subscription.id)
                awarded_points = points_awarded

            # 4. Initialize points balance
            self.points_service.get_or_create_balance(str(user.id))

            # 5. Initialize wallet
            self._create_wallet_if_not_exists(user.id)

            # 6. Update membership plan user count if subscription was created
            if created_subscription_id:
                self._update_plan_user_count(user_data["plan_id"])

            # SQLAlchemy will automatically commit on successful completion
            self.db.refresh(user)

            logger.info(f"✅ Successfully created user {user.email} with complete integration")

            return {
                "success": True,
                "message": "User created successfully with membership and points",
                "user_id": str(user.id),
                "subscription_id": created_subscription_id,
                "points_awarded": awarded_points,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "name": f"{user.first_name} {user.last_name}",
                    "role": user.role.value,
                    "status": user.status.value,
                    "membership_id": user.membership_id_display,
                    "plan": self._get_user_plan_info(user.id)
                }
            }

        except Exception as e:
            # SQLAlchemy will automatically rollback on exception
            logger.error(f"❌ Failed to create user with integration: {str(e)}")
            raise

    def update_user_with_membership(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user and handle membership changes atomically.

        Args:
            user_id: User ID to update
            user_data: Updated user data including membership changes

        Returns:
            Dict containing success status and updated user data
        """

        # Use SQLAlchemy's automatic transaction management

        try:
            # Get existing user with subscription
            user = self.db.query(User).options(joinedload(User.subscriptions)).filter(User.id == user_id).first()
            if not user:
                raise BadRequestException("User not found")

            # Track changes for response
            changes_made = []
            subscription_updated = False
            points_awarded = 0

            # Update user fields
            if self._update_user_fields(user, user_data):
                changes_made.append("user_profile")

            # Handle membership changes
            if "plan_id" in user_data:
                old_plan_info = self._get_user_plan_info(user.id)
                subscription, awarded = self._handle_membership_change(user, user_data)
                if subscription:
                    subscription_updated = True
                    points_awarded = awarded
                    changes_made.append("membership")

                    # Update plan user counts
                    self._update_plan_user_counts_on_change(old_plan_info, user_data["plan_id"])

            # Handle user status changes that affect membership subscription
            if "status" in user_data:
                self._handle_user_status_change(user, user_data["status"])

            # Ensure points and wallet exist (for legacy users)
            self.points_service.get_or_create_balance(str(user.id))
            self._create_wallet_if_not_exists(user.id)

            # Commit changes explicitly
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"💾 Committed changes to database for user {user.email}")
            logger.info(f"🔍 User avatar after commit: {bool(user.avatar)}, length: {len(str(user.avatar)) if user.avatar else 0}")

            logger.info(f"✅ Successfully updated user {user.email} with changes: {changes_made}")

            # Refresh user to get latest data from DB
            self.db.refresh(user)
            
            return {
                "success": True,
                "message": "User updated successfully",
                "changes": changes_made,
                "points_awarded": points_awarded,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "avatar": user.avatar,  # Include avatar in response
                    "name": f"{user.first_name} {user.last_name}",
                    "role": user.role.value,
                    "status": user.status.value,
                    "plan": self._get_user_plan_info(user.id)
                }
            }

        except Exception as e:
            # SQLAlchemy will automatically rollback on exception
            logger.error(f"❌ Failed to update user with integration: {str(e)}")
            raise

    def _validate_user_creation_data(self, data: Dict[str, Any]) -> None:
        """Validate user creation data"""
        required_fields = ["email", "username", "password", "first_name", "last_name"]
        for field in required_fields:
            if not data.get(field):
                raise BadRequestException(f"{field} is required")

        if len(data["password"]) < 6:
            raise BadRequestException("Password must be at least 6 characters")

        # Check uniqueness
        if self.db.query(User).filter(User.email == data["email"]).first():
            raise BadRequestException("Email already registered")

        if self.db.query(User).filter(User.username == data["username"]).first():
            raise BadRequestException("Username already taken")

        # Validate membership ID if provided
        membership_id = data.get("membership_id")
        if membership_id:
            if not membership_id.startswith("ALT-"):
                membership_id = f"ALT-{membership_id}"

            existing = self.db.query(User).filter(User.membership_id_display == membership_id).first()
            if existing:
                raise BadRequestException(f"Membership ID {membership_id} already exists")

            data["membership_id"] = membership_id  # Update with formatted ID

    def _create_user_record(self, data: Dict[str, Any], created_by_admin: bool) -> User:
        """Create user record from validated data"""
        user = User(
            email=data["email"],
            username=data["username"],
            phone=data.get("phone"),
            first_name=data["first_name"],
            last_name=data["last_name"],
            avatar=data.get("avatar"),
            password_hash=hash_password(data["password"]),
            role=UserRole(data.get("role", "CUSTOMER")),
            status=UserStatus(data.get("status", "ACTIVE")),
            gender=data.get("gender"),
            country=data.get("country", "Egypt"),
            membership_id_display=data.get("membership_id", f"ALT-{uuid.uuid4().hex[:6].upper()}"),
            email_verified=created_by_admin,  # Admin-created users are pre-verified
            phone_verified=False,
            language="ar"
        )

        # Handle birthdate
        if data.get("birthdate"):
            try:
                if isinstance(data["birthdate"], str):
                    user.birthdate = datetime.fromisoformat(data["birthdate"].replace('Z', '+00:00'))
                else:
                    user.birthdate = data["birthdate"]
            except Exception as e:
                logger.warning(f"Failed to parse birthdate: {e}")

        return user

    def _create_membership_subscription(self, user: User, data: Dict[str, Any]) -> Tuple[MembershipSubscription, int]:
        """Create membership subscription and award initial points"""
        plan_id = data["plan_id"]
        plan = self.db.query(MembershipPlan).filter(MembershipPlan.id == str(plan_id)).first()

        if not plan:
            raise BadRequestException(f"Membership plan {plan_id} not found")

        # Calculate subscription dates
        start_date = datetime.utcnow()
        if data.get("plan_start_date"):
            try:
                start_date = datetime.fromisoformat(data["plan_start_date"].replace('Z', '+00:00'))
            except:
                pass

        end_date = None
        if plan.duration_days:
            end_date = (start_date + timedelta(days=plan.duration_days)).date()
        elif plan.plan_type not in ['PAID_INFINITE', 'FREE']:
            end_date = (start_date + timedelta(days=30)).date()

        # Create subscription
        sub_id = uuid.uuid4()
        subscription = MembershipSubscription(
            id=sub_id,
            user_id=user.id,
            plan_id=plan.id,
            membership_number=f"MEM-{uuid.uuid4().hex[:8].upper()}",
            start_date=start_date,
            expiry_date=end_date,
            status=MembershipStatus.ACTIVE
        )

        self.db.add(subscription)
        self.db.flush()

        # Award initial points
        points_awarded = 0
        if plan.perks:
            try:
                perks = plan.perks
                if isinstance(perks, str):
                    perks = json.loads(perks)

                initial_points = perks.get('points', 0) if isinstance(perks, dict) else 0

                if initial_points > 0:
                    self.points_service.add_bonus_points(
                        user_id=str(user.id),
                        points=int(initial_points),
                        description_en=f"Welcome bonus for {plan.tier_name_en}",
                        description_ar=f"مكافأة ترحيبية لعضوية {plan.tier_name_ar}"
                    )
                    points_awarded = initial_points
                    logger.info(f"✅ Awarded {points_awarded} initial points to user {user.email}")
            except Exception as e:
                logger.error(f"Failed to award initial points: {e}")

        return subscription, points_awarded

    def _handle_membership_change(self, user: User, data: Dict[str, Any]) -> Tuple[Optional[MembershipSubscription], int]:
        """Handle membership plan changes for existing user"""
        plan_id = data["plan_id"]
        points_awarded = 0

        # Find existing active subscription
        existing_sub = self.db.query(MembershipSubscription).filter(
            and_(
                MembershipSubscription.user_id == user.id,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            )
        ).first()

        if not plan_id:
            # Remove membership
            if existing_sub:
                existing_sub.status = MembershipStatus.CANCELLED
                existing_sub.expiry_date = datetime.utcnow().date()
            return None, 0

        # Get new plan
        plan = self.db.query(MembershipPlan).filter(MembershipPlan.id == str(plan_id)).first()
        if not plan:
            raise BadRequestException(f"Membership plan {plan_id} not found")

        # Calculate start date from user data or default to now
        start_date = datetime.utcnow()
        if data.get("plan_start_date"):
            try:
                start_date = datetime.fromisoformat(data["plan_start_date"].replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Failed to parse plan_start_date, using current time: {e}")

        # Handle membership upgrade - UPDATE existing subscription instead of creating new one
        if existing_sub:
            # Check if same plan
            if str(existing_sub.plan_id) == str(plan.id):
                # Even if same plan, check if start date changed
                if existing_sub.start_date != start_date.date():
                    logger.info(f"Updating start date for existing subscription from {existing_sub.start_date} to {start_date}")
                    existing_sub.start_date = start_date
                    # Recalculate expiry date based on new start date
                    if plan.duration_days:
                        existing_sub.expiry_date = (start_date + timedelta(days=plan.duration_days)).date()
                    return existing_sub, 0
                logger.info("Same plan and start date, no changes needed")
                return None, 0

            # Upgrade existing subscription
            logger.info(f"Upgrading subscription from plan {existing_sub.plan_id} to {plan.id}")

            # Store previous plan info
            existing_sub.previous_plan_id = existing_sub.plan_id
            existing_sub.upgraded_at = datetime.utcnow()

            # Update to new plan
            existing_sub.plan_id = plan.id
            existing_sub.start_date = start_date

            # Update membership number to reflect upgrade
            existing_sub.membership_number = f"MEM-{uuid.uuid4().hex[:8].upper()}"

            # Update expiry date if needed
            if plan.duration_days:
                existing_sub.expiry_date = (start_date + timedelta(days=plan.duration_days)).date()
            # For infinite plans, keep existing expiry_date (null)

            # Award upgrade bonus points
            if plan.perks:
                try:
                    perks = plan.perks
                    if isinstance(perks, str):
                        perks = json.loads(perks)

                    bonus_points = perks.get('points', 0) if isinstance(perks, dict) else 0

                    if bonus_points > 0:
                        self.points_service.add_bonus_points(
                            user_id=str(user.id),
                            points=int(bonus_points),
                            description_en=f"Membership upgrade to {plan.tier_name_en}",
                            description_ar=f"ترقية العضوية إلى {plan.tier_name_ar}"
                        )
                        points_awarded = bonus_points
                        logger.info(f"Awarded {bonus_points} upgrade points")
                except Exception as e:
                    logger.error(f"Failed to award upgrade points: {e}")

            return existing_sub, points_awarded

        else:
            # No existing subscription - create new one
            logger.info(f"Creating new subscription for plan {plan.id}")

            end_date = None

            if plan.duration_days:
                end_date = (start_date + timedelta(days=plan.duration_days)).date()
            elif plan.plan_type not in ['PAID_INFINITE', 'FREE']:
                end_date = (start_date + timedelta(days=30)).date()

            sub_id = uuid.uuid4()
            subscription = MembershipSubscription(
                id=sub_id,
                user_id=user.id,
                plan_id=plan.id,
                membership_number=f"MEM-{uuid.uuid4().hex[:8].upper()}",
                start_date=start_date,
                expiry_date=end_date,
                status=MembershipStatus.ACTIVE
            )

            self.db.add(subscription)

            # Award welcome points for new subscription
            if plan.perks:
                try:
                    perks = plan.perks
                    if isinstance(perks, str):
                        perks = json.loads(perks)

                    welcome_points = perks.get('points', 0) if isinstance(perks, dict) else 0

                    if welcome_points > 0:
                        self.points_service.add_bonus_points(
                            user_id=str(user.id),
                            points=int(welcome_points),
                            description_en=f"Welcome bonus for {plan.tier_name_en}",
                            description_ar=f"مكافأة ترحيبية لعضوية {plan.tier_name_ar}"
                        )
                        points_awarded = welcome_points
                        logger.info(f"Awarded {welcome_points} welcome points")
                except Exception as e:
                    logger.error(f"Failed to award welcome points: {e}")

            return subscription, points_awarded

    def _handle_user_status_change(self, user: User, new_status: str) -> None:
        """Handle user status changes that affect membership subscription status"""
        try:
            user_status = UserStatus(new_status)

            # Find active membership subscription
            active_sub = self.db.query(MembershipSubscription).filter(
                and_(
                    MembershipSubscription.user_id == user.id,
                    MembershipSubscription.status.in_([MembershipStatus.ACTIVE, MembershipStatus.SUSPENDED])
                )
            ).first()

            if active_sub:
                # Update membership status based on user status
                if user_status == UserStatus.ACTIVE and active_sub.status != MembershipStatus.ACTIVE:
                    active_sub.status = MembershipStatus.ACTIVE
                    logger.info(f"Activated membership subscription {active_sub.id} for user {user.email}")
                elif user_status == UserStatus.SUSPENDED and active_sub.status != MembershipStatus.SUSPENDED:
                    active_sub.status = MembershipStatus.SUSPENDED
                    logger.info(f"Suspended membership subscription {active_sub.id} for user {user.email}")

        except ValueError as e:
            logger.warning(f"Invalid user status '{new_status}': {e}")

    def _create_wallet_if_not_exists(self, user_id: uuid.UUID) -> None:
        """Create wallet for user if it doesn't exist"""
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=0.0)
            self.db.add(wallet)
            logger.info(f"✅ Created wallet for user {user_id}")

    def _update_user_fields(self, user: User, data: Dict[str, Any]) -> bool:
        """Update user fields, return True if any changes made"""
        changed = False

        field_mappings = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'phone': 'phone',
            'gender': 'gender',
            'country': 'country',
            'avatar': 'avatar'
        }

        for field, attr in field_mappings.items():
            if field in data:
                # Special handling for avatar: allow None/empty string to clear avatar
                if field == 'avatar':
                    new_value = data[field] if data[field] else None
                    current_value = getattr(user, attr) if getattr(user, attr) else None
                    logger.info(f"🔍 Avatar update check for {user.email}: new={bool(new_value)}, current={bool(current_value)}")
                    if new_value != current_value:
                        logger.info(f"📝 Setting avatar for {user.email}, length: {len(str(new_value)) if new_value else 0}")
                        setattr(user, attr, new_value)
                        changed = True
                        logger.info(f"✅ Updated {field} for user {user.email}: {bool(new_value)}")
                    else:
                        logger.info(f"⏭️ Avatar unchanged for {user.email}")
                elif getattr(user, attr) != data[field]:
                    setattr(user, attr, data[field])
                    changed = True

        # Handle special fields
        if "role" in data:
            try:
                user.role = UserRole(data["role"])
                changed = True
            except ValueError:
                pass

        if "status" in data:
            try:
                user.status = UserStatus(data["status"])
                changed = True
            except ValueError:
                pass

        if "membership_id" in data:
            mid = data["membership_id"]
            if mid and mid != user.membership_id_display:
                if not mid.startswith("ALT-"):
                    mid = f"ALT-{mid}"

                # Check uniqueness
                existing = self.db.query(User).filter(
                    and_(
                        User.membership_id_display == mid,
                        User.id != user.id
                    )
                ).first()

                if existing:
                    raise BadRequestException(f"Membership ID {mid} already exists")

                user.membership_id_display = mid
                changed = True

        if "birthdate" in data and data["birthdate"]:
            try:
                if isinstance(data["birthdate"], str):
                    user.birthdate = datetime.fromisoformat(data["birthdate"].replace('Z', '+00:00'))
                else:
                    user.birthdate = data["birthdate"]
                changed = True
            except Exception as e:
                logger.warning(f"Failed to parse birthdate: {e}")

        return changed

    def _get_user_plan_info(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get current plan information for user"""
        active_sub = self.db.query(MembershipSubscription).options(
            joinedload(MembershipSubscription.plan)
        ).filter(
            and_(
                MembershipSubscription.user_id == user_id,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            )
        ).first()

        if active_sub and active_sub.plan:
            return {
                "name": active_sub.plan.tier_name_en,
                "status": active_sub.status.value
            }

        return None

    def get_membership_stats(self) -> Dict[str, Any]:
        """Get comprehensive membership statistics"""
        from modules.memberships.models import MembershipPlan, MembershipSubscription

        # Get all active plans
        plans = self.db.query(MembershipPlan).filter(MembershipPlan.is_active == True).all()

        total_members = 0
        active_plans = len(plans)
        plan_stats = []

        for plan in plans:
            # Count active subscriptions for this plan
            active_count = self.db.query(MembershipSubscription).filter(
                MembershipSubscription.plan_id == plan.id,
                MembershipSubscription.status == MembershipStatus.ACTIVE
            ).count()

            total_members += active_count

            plan_stats.append({
                "id": str(plan.id),
                "name": plan.tier_name_en,
                "tier_code": plan.tier_code,
                "user_count": active_count,
                "price": plan.price,
                "currency": plan.currency
            })

        # Count expiring soon (next 30 days)
        from datetime import datetime, timedelta
        expiry_threshold = datetime.utcnow() + timedelta(days=30)

        expiring_soon = self.db.query(MembershipSubscription).filter(
            MembershipSubscription.status == MembershipStatus.ACTIVE,
            MembershipSubscription.expiry_date <= expiry_threshold.date(),
            MembershipSubscription.expiry_date >= datetime.utcnow().date()
        ).count()

        return {
            "total_members": total_members,
            "active_plans": active_plans,
            "expiring_soon": expiring_soon,
            "plans": plan_stats
        }

    def _update_plan_user_count(self, plan_id: str) -> None:
        """Update user count for membership plan (if tracking is needed)"""
        # For now, we use real-time queries instead of cached counts
        # This ensures accuracy and avoids synchronization issues
        pass

    def _update_plan_user_counts_on_change(self, old_plan_info: Optional[Dict], new_plan_id: str) -> None:
        """Update user counts when plan changes"""
        # Real-time counts don't need updates
        pass
