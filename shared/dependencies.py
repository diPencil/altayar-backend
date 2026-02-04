from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
from jose import JWTError, jwt
from datetime import datetime
from sqlalchemy import or_

from database.base import get_db
from config.settings import settings
from modules.users.models import User, UserRole, UserStatus

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.status == UserStatus.ACTIVE:
            return user
    except JWTError:
        pass
    
    return None


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    return current_user


def require_roles(allowed_roles: List[str]):
    """Dependency to check if user has required role"""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Pre-built role dependencies for convenience
def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require SUPER_ADMIN or ADMIN role"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role not in ["SUPER_ADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_employee_or_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require SUPER_ADMIN, ADMIN, or EMPLOYEE role"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role not in ["SUPER_ADMIN", "ADMIN", "EMPLOYEE"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee or admin access required"
        )
    return current_user


def get_customer_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require CUSTOMER role"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )
    return current_user


def require_active_membership(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Require current user to have an ACTIVE membership subscription.

    Returns 403 with detail=MEMBERSHIP_REQUIRED when missing/inactive.
    """
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    # Only enforce for customers; staff can continue to use admin/employee flows.
    if user_role != "CUSTOMER":
        return current_user

    # Import locally to avoid circular imports at module load time.
    from modules.memberships.models import MembershipSubscription, MembershipStatus

    # expiry_date is a DATE (not datetime) in our schema
    now = datetime.utcnow().date()
    active_sub = db.query(MembershipSubscription).filter(
        MembershipSubscription.user_id == str(current_user.id),
        MembershipSubscription.status == MembershipStatus.ACTIVE,
        or_(
            MembershipSubscription.expiry_date.is_(None),
            MembershipSubscription.expiry_date > now,
        )
    ).first()

    if not active_sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MEMBERSHIP_REQUIRED",
        )

    return current_user


# Define all dependency functions explicitly
require_admin = get_admin_user
require_employee_or_admin = get_employee_or_admin_user

# Ensure require_employee_or_admin is available globally
def require_employee_or_admin_dependency(current_user: User = Depends(get_current_active_user)) -> User:
    """Require SUPER_ADMIN, ADMIN, or EMPLOYEE role"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role not in ["SUPER_ADMIN", "ADMIN", "EMPLOYEE"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee or admin access required"
        )
    return current_user

# Make sure the global variable is set
require_employee_or_admin = require_employee_or_admin_dependency

# Explicit export to ensure availability
__all__ = [
    'get_current_user',
    'get_current_user_optional',
    'get_current_active_user',
    'require_roles',
    'get_admin_user',
    'get_employee_or_admin_user',
    'get_customer_user',
    'require_active_membership',
    'require_admin',
    'require_employee_or_admin',
    'security'
]