from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin


class EmployeeAdminMessage(Base, UUIDMixin, TimestampMixin):
    """
    Admin -> Employee messages shown on employee dashboard.

    - If target_employee_id is NULL: message is broadcast to all employees
    - If target_employee_id is set: only that employee sees it
    """

    __tablename__ = "employee_admin_messages"

    target_employee_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    priority = Column(String(20), default="NORMAL", nullable=False)  # NORMAL | HIGH
    is_active = Column(Boolean, default=True, nullable=False)

    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_by_role = Column(String(20), nullable=True)

    target_employee = relationship("User", foreign_keys=[target_employee_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

