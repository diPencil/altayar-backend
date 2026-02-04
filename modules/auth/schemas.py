from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from enum import Enum
import re


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"
    SUPER_ADMIN = "SUPER_ADMIN"


# ============ Register ============
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    gender: Optional[str] = Field("MALE", pattern="^(MALE|FEMALE)$")
    country: Optional[str] = Field("Egypt", max_length=100)
    language: str = Field(default="ar", pattern="^(ar|en)$")
    referral_code: Optional[str] = Field(None, description="Referral code if invited")
    
    @validator('password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v


class RegisterResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    message: str


# ============ Login ============
class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Email or username")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: 'UserProfile'


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============ User Profile ============
class MembershipData(BaseModel):
    """Membership subscription data for user profile"""
    membership_number: str
    membership_id_display: Optional[str] = None  # Custom Member ID (ALT-XXX format)
    plan_name_ar: str
    plan_name_en: str
    tier_code: str
    expiry_date: Optional[str] = None  # ISO date string or None for lifetime
    status: str
    points_balance: int
    is_lifetime: bool = False

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    id: str
    email: str
    username: Optional[str] = None  # Add username
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    language: str
    avatar: Optional[str]
    email_verified: bool
    phone_verified: bool
    membership_id_display: Optional[str] = None  # Custom Member ID (ALT-XXX format)
    created_at: Optional[str] = None  # ISO date string
    membership: Optional[MembershipData] = None  # Add membership data
    wallet_balance: float = 0.0
    cashback_balance: float = 0.0

    class Config:
        from_attributes = True


# ============ Update Profile ============
class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, pattern="^(ar|en)$")
    avatar: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v


class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    user: UserProfile


# ============ Change Password ============
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class ChangePasswordResponse(BaseModel):
    success: bool
    message: str


# ============ Forgot/Reset Password ============
class ForgotPasswordRequest(BaseModel):
    """Request to send password reset code"""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset"""
    success: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """Request to reset password with code"""
    email: EmailStr
    code: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str


# Update forward reference
TokenResponse.model_rebuild()
