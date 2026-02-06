from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config.settings import settings
from modules.users.models import User, UserRole, UserStatus
from modules.auth.schemas import RegisterRequest, LoginRequest, UserProfile
from modules.notifications.service import NotificationService
from shared.utils import hash_password, verify_password
from shared.exceptions import BadRequestException, UnauthorizedException, ConflictException
from modules.referrals.models import ReferralCode, Referral

logger = logging.getLogger(__name__)

# Global storage for reset codes (in-memory persistent across requests)
_RESET_CODES = {}


class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def register(self, data: RegisterRequest) -> User:
        """
        Register a new customer user.
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise ConflictException("Email already registered")

        # Check if username already exists
        existing_username = self.db.query(User).filter(User.username == data.username).first()
        if existing_username:
            raise ConflictException("Username already taken")

        # Check if phone already exists (if provided)
        if data.phone:
            existing_phone = self.db.query(User).filter(User.phone == data.phone).first()
            if existing_phone:
                raise ConflictException("Phone number already registered")
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            gender=data.gender,
            country=data.country,
            role=UserRole.CUSTOMER,  # New registrations are always customers
            status=UserStatus.ACTIVE,
            language=data.language,
            email_verified=False,
            phone_verified=False
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Handle Referral Code
        if data.referral_code:
            try:
                referral_code_obj = self.db.query(ReferralCode).filter(ReferralCode.code == data.referral_code).first()
                if referral_code_obj:
                    # Prevent self-referral
                    if referral_code_obj.user_id == user.id:
                        logger.warning("User attempted to refer themselves")
                    else:
                        # Create Pending Referral
                        referral = Referral(
                            id=str(uuid.uuid4()),
                            referrer_id=referral_code_obj.user_id,
                            referred_user_id=user.id,
                            status="PENDING",
                            points_earned=0
                        )
                        self.db.add(referral)
                        referral_code_obj.usage_count += 1
                        self.db.commit()
                        logger.info(f"✅ Referral recorded: {user.email} referred by {referral_code_obj.user_id}")
                else:
                    logger.warning(f"⚠️ Invalid referral code provided: {data.referral_code}")
            except Exception as e:
                logger.error(f"❌ Error processing referral code: {e}")
                # Don't block registration if referral fails

        logger.info(f"✅ User registered: {user.email}")

        # Create notification for user registration
        try:
            notification_service = NotificationService(self.db)
            notification_service.notify_user_registered(user)
        except Exception as e:
            logger.warning(f"Failed to create registration notification: {e}")

        return user
    
    def login(self, data: LoginRequest) -> Tuple[User, str, str]:
        """
        Authenticate user and return tokens.
        Returns: (user, access_token, refresh_token)
        """
        # Find user by email or username
        logger.info(f"🔍 Login attempt for identifier: '{data.identifier}'")
        user = self.db.query(User).filter(
            (User.email == data.identifier) | (User.username == data.identifier)
        ).first()
        
        logger.info(f"🔍 User found in DB: {user}")
        if user:
            logger.info(f"   ID: {user.id}")
            logger.info(f"   Email: {user.email}")
            logger.info(f"   Hash: {user.password_hash[:20]}...")

        if not user:
            logger.warning(f"❌ User not found for identifier: {data.identifier}")
            # Debug: Check if any users exist
            count = self.db.query(User).count()
            logger.info(f"   Total users in DB: {count}")
            raise UnauthorizedException("Invalid credentials")
        
        # Verify password
        if not verify_password(data.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise UnauthorizedException(f"Account is {user.status.value.lower()}")
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        self.db.commit()

        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)

        logger.info(f"✅ User logged in: {user.email}")

        # Create notification for user login - notify admin for all user logins
        try:
            notification_service = NotificationService(self.db)
            notification_service.notify_user_login(user)
        except Exception as e:
            logger.warning(f"Failed to create login notification: {e}")

        return user, access_token, refresh_token

    def logout(self, user: User) -> None:
        """
        Handle user logout and create notification.
        """
        logger.info(f"✅ User logged out: {user.email}")

        # Create notification for user logout - notify admin for all user logouts
        try:
            notification_service = NotificationService(self.db)
            notification_service.notify_user_logout(user)
        except Exception as e:
            logger.warning(f"Failed to create logout notification: {e}")

    def refresh_token(self, refresh_token: str) -> str:
        """
        Validate refresh token and return new access token.
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check token type
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException("Invalid token")
            
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise UnauthorizedException("User not found")
            
            if user.status != UserStatus.ACTIVE:
                raise UnauthorizedException(f"Account is {user.status.value.lower()}")
            
            # Generate new access token
            new_access_token = self._create_access_token(user)
            
            logger.info(f"✅ Token refreshed for: {user.email}")
            
            return new_access_token
        
        except JWTError as e:
            logger.warning(f"⚠️ Invalid refresh token: {str(e)}")
            raise UnauthorizedException("Invalid or expired refresh token")
    
    def _create_access_token(self, user: User) -> str:
        """
        Create JWT access token.
        """
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    def _create_refresh_token(self, user: User) -> str:
        """
        Create JWT refresh token (longer expiry).
        """
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    def get_user_profile(self, user: User) -> UserProfile:
        """
        Convert User model to UserProfile schema with membership data.
        """
        from modules.memberships.models import MembershipSubscription, MembershipPlan
        from modules.auth.schemas import MembershipData
        
        # Fetch user's membership subscription
        membership_data = None
        subscription = self.db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == user.id
        ).order_by(MembershipSubscription.created_at.desc()).first()
        
        if subscription:
            # Get the plan details
            plan = self.db.query(MembershipPlan).filter(
                MembershipPlan.id == subscription.plan_id
            ).first()
            
            if plan:
                # Determine if membership is lifetime
                is_lifetime = subscription.expiry_date is None or plan.plan_type == "PAID_INFINITE"
                
                # Get points balance from PointsService/Table directly for accuracy
                from modules.points.models import PointsBalance
                points_record = self.db.query(PointsBalance).filter(PointsBalance.user_id == user.id).first()
                actual_points = points_record.current_balance if points_record else 0

                membership_data = MembershipData(
                    membership_number=subscription.membership_number,
                    membership_id_display=user.membership_id_display,  # Custom Member ID from User
                    plan_name_ar=plan.tier_name_ar,
                    plan_name_en=plan.tier_name_en,
                    tier_code=plan.tier_code,
                    expiry_date=subscription.expiry_date.isoformat() if subscription.expiry_date else None,
                    status=subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status),
                    points_balance=actual_points,
                    is_lifetime=is_lifetime
                )
        
        
        # Get Wallet Balance
        from modules.wallet.models import Wallet
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user.id).first()
        wallet_balance = wallet.balance if wallet else 0.0
        
        # Get Cashback Balance (Total Earned/Credited)
        from modules.cashback.models import ClubGiftRecord, ClubGiftStatus
        cashback_records = self.db.query(ClubGiftRecord).filter(
            ClubGiftRecord.user_id == user.id,
            ClubGiftRecord.status == ClubGiftStatus.CREDITED
        ).all()
        cashback_balance = sum(r.cashback_amount for r in cashback_records)

        return UserProfile(
            id=str(user.id),
            email=user.email,
            username=user.username,  # Add username
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            language=user.language,
            avatar=user.avatar,
            email_verified=user.email_verified or False,
            phone_verified=user.phone_verified or False,
            membership_id_display=user.membership_id_display,  # Custom Member ID
            created_at=user.created_at.isoformat() if user.created_at else None,  # Joined date
            membership=membership_data,
            wallet_balance=wallet_balance,
            cashback_balance=cashback_balance
        )
    
    def update_profile(self, user: User, data) -> User:
        """
        Update user profile information.
        """
        # Check if phone is being changed and is unique
        if data.phone and data.phone != user.phone:
            existing_phone = self.db.query(User).filter(
                User.phone == data.phone,
                User.id != user.id
            ).first()
            if existing_phone:
                raise ConflictException("Phone number already registered")
        
        # Update fields
        if data.first_name:
            user.first_name = data.first_name
        if data.last_name:
            user.last_name = data.last_name
        if data.phone is not None:
            user.phone = data.phone
        if data.language:
            user.language = data.language
        if data.avatar is not None:
            user.avatar = data.avatar
        
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"✅ Profile updated for: {user.email}")
        
        return user
    
    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        """
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedException("Current password is incorrect")
        
        # Update password
        user.password_hash = hash_password(new_password)
        self.db.commit()
        
        logger.info(f"✅ Password changed for: {user.email}")
        
        return True
    
    def request_password_reset(self, email: str) -> dict:
        """
        Generate and send password reset code to user's email.
        Returns a dict with the code (for development/testing).
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Don't reveal if email exists or not (security best practice)
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return {"code": None}  # Still return success to not reveal email existence
        
        # Generate 6-digit code
        import random
        reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store code with expiry (15 minutes) - using a simple in-memory cache
        # In production, use Redis or database table
        _RESET_CODES[email] = {
            'code': reset_code,
            'expiry': expiry,
            'user_id': user.id
        }
        
        logger.info(f"Password reset code generated for {email}: {reset_code} (expires at {expiry})")
        
        # Send email with reset code
        try:
            self._send_password_reset_email(email, reset_code)
            logger.info(f"📧 Reset code email sent to {email}")
        except Exception as e:
            logger.error(f"❌ Failed to send reset email to {email}: {e}")
            # Still return success to help with debugging/manual testing from logs
        
        return {"code": reset_code}  # Return for development/testing
    
    def _send_password_reset_email(self, email: str, code: str):
        """Send password reset email using SMTP settings"""
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning(f"SMTP not configured. Reset code for {email} is: {code}")
            return
            
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = f"{settings.APP_NAME} - Password Reset Code"
            message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            message["To"] = email

            text = f"Your password reset code is: {code}. It will expire in 15 minutes."
            html = f"""
            <html>
                <body>
                    <h2>Password Reset Request</h2>
                    <p>You requested to reset your password for <strong>{settings.APP_NAME}</strong>.</p>
                    <p>Your verification code is: <strong>{code}</strong></p>
                    <p>This code will expire in 15 minutes.</p>
                    <p>If you did not request this, please ignore this email.</p>
                </body>
            </html>
            """

            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            message.attach(part1)
            message.attach(part2)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, email, message.as_string())
        except Exception as e:
            raise Exception(f"SMTP error: {str(e)}")
    
    def reset_password(self, email: str, code: str, new_password: str) -> None:
        """
        Reset user password using verification code.
        """
        # Check if code exists and is valid
        if email not in _RESET_CODES:
            raise BadRequestException("Invalid or expired reset code")
        
        stored_data = _RESET_CODES[email]
        
        # Check if code matches
        if stored_data['code'] != code:
            raise BadRequestException("Invalid reset code")
        
        # Check if code is expired
        if datetime.utcnow() > stored_data['expiry']:
            del _RESET_CODES[email]
            raise BadRequestException("Reset code has expired")
        
        # Find user
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise BadRequestException("User not found")
        
        # Validate new password strength
        if len(new_password) < 8:
            raise BadRequestException("Password must be at least 8 characters")
        
        # Update password
        user.password_hash = hash_password(new_password)
        self.db.commit()
        
        # Delete used code
        del _RESET_CODES[email]
        
        logger.info(f"Password reset successfully for user {user.id}")
