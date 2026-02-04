from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
import os
import uuid
from sqlalchemy.orm import Session
import logging

from database.base import get_db
from modules.auth.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
    UserProfile,
    UpdateProfileRequest,
    UpdateProfileResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)
from modules.auth.service import AuthService
from modules.users.models import User
from shared.dependencies import get_current_user
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage directory for avatars
AVATARS_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'storage', 'avatars')
os.makedirs(AVATARS_STORAGE_DIR, exist_ok=True)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new customer account.
    
    - Email must be unique
    - Password must be at least 8 characters with uppercase, lowercase, and digit
    - Phone is optional but must be unique if provided
    """
    auth_service = AuthService(db)
    user = auth_service.register(request)
    
    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        message="Registration successful. Please login."
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    
    Returns:
    - access_token: Short-lived token for API requests
    - refresh_token: Long-lived token to get new access tokens
    - user: User profile information
    """
    auth_service = AuthService(db)
    user, access_token, refresh_token = auth_service.login(request)
    
    user_profile = auth_service.get_user_profile(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_profile
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    Triggers logout notification.
    """
    auth_service = AuthService(db)
    auth_service.logout(current_user)
    
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """
    Get a new access token using refresh token.
    
    Use this when the access token expires.
    """
    auth_service = AuthService(db)
    new_access_token = auth_service.refresh_token(request.refresh_token)
    
    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user's profile.
    
    Requires: Bearer token in Authorization header
    """
    auth_service = AuthService(db)
    return auth_service.get_user_profile(current_user)


@router.put("/me", response_model=UpdateProfileResponse)
def update_current_user_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current authenticated user's profile.
    
    - Can update first_name, last_name, phone, language, avatar
    - Email cannot be changed
    - Phone must be unique if provided
    """
    auth_service = AuthService(db)
    updated_user = auth_service.update_profile(current_user, request)
    user_profile = auth_service.get_user_profile(updated_user)
    
    # Notify Admin about profile update
    try:
        from modules.notifications.service import NotificationService
        from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
        from modules.notifications.schemas import NotificationCreate
        
        notification_service = NotificationService(db)
        user_name = f"{updated_user.first_name} {updated_user.last_name}".strip() or updated_user.email
        
        notification_data = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,
            target_user_id=None,
            type=NotificationType.USER_PROFILE_UPDATED,
            title=f"Profile Updated / تحديث الملف الشخصي",
            message=f"User {user_name} updated their profile info.",
            related_entity_id=str(updated_user.id),
            related_entity_type=NotificationEntityType.USER,
            action_url=f"/users/{updated_user.id}",
            triggered_by_id=str(current_user.id),
            triggered_by_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        )
        notification_service.create_notification(notification_data)
    except Exception as e:
        logger.warning(f"Failed to send profile update notification to admin: {e}")

    return UpdateProfileResponse(
        success=True,
        message="Profile updated successfully",
        user=user_profile
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    
    - Must provide current password for verification
    - New password must meet strength requirements
    """
    auth_service = AuthService(db)
    auth_service.change_password(current_user, request.current_password, request.new_password)
    
    return ChangePasswordResponse(
        success=True,
        message="Password changed successfully"
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset code.
    
    - Sends a 6-digit code to the user's email
    - Code expires in 15 minutes
    - Does not reveal if email exists (security)
    """
    auth_service = AuthService(db)
    result = auth_service.request_password_reset(request.email)
    
    return ForgotPasswordResponse(
        success=True,
        message="If the email exists, a reset code has been sent"
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using verification code.
    
    - Requires email, verification code, and new password
    - Code must be valid and not expired
    - New password must meet strength requirements
    """
    auth_service = AuthService(db)
    auth_service.reset_password(request.email, request.code, request.new_password)
    
    return ResetPasswordResponse(
        success=True,
        message="Password reset successfully"
    )


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload user avatar image.
    Returns the URL of the uploaded image.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Validate content type (images only)
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
            
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.heic']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            # Try to infer from content type
            content_type_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/webp': '.webp', 
                'image/heic': '.heic'
            }
            file_ext = content_type_map.get(file.content_type, '.jpg')
            
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_ext}"
        file_path = os.path.join(AVATARS_STORAGE_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # Generate URL
        avatar_url = f"{settings.APP_BASE_URL}/api/auth/avatar/{filename}"
        
        return {"url": avatar_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")


@router.get("/avatar/{filename}")
def get_avatar_image(filename: str):
    """Get avatar image file"""
    # Security check
    if '..' in filename or '/' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    file_path = os.path.join(AVATARS_STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
        
    return FileResponse(file_path)
