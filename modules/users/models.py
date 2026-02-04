from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"


class EmployeeType(str, enum.Enum):
    HR = "HR"
    ACCOUNTING = "ACCOUNTING"
    SALES = "SALES"
    RESERVATION = "RESERVATION"
    DATA_ENTRY = "DATA_ENTRY"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"
    DELETED = "DELETED"


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    avatar = Column(String, nullable=True)  # base64 or URL
    
    # Extended Profile
    username = Column(String(100), unique=True, nullable=True, index=True)
    gender = Column(String(10), nullable=True) # MALE, FEMALE
    country = Column(String(100), nullable=True)
    birthdate = Column(DateTime(timezone=True), nullable=True)
    membership_id_display = Column(String(50), nullable=True, index=True) # Custom ID if manual
    
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER, index=True)
    employee_type = Column(SQLEnum(EmployeeType), nullable=True)
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True)
    language = Column(String(5), nullable=False, default="ar")
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    phone_verified = Column(Boolean, default=False)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)
    
    # Employee Assignment
    assigned_employee_id = Column(String(36), nullable=True, index=True)  # FK to users.id (employee)
    
    # Push Notifications
    expo_push_token = Column(String(255), nullable=True)
    
    # Relationships
    subscriptions = relationship("MembershipSubscription", back_populates="user", cascade="all, delete-orphan")
    referral_code_obj = relationship("ReferralCode", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"
