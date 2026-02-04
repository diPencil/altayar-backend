from sqlalchemy import Column, String, Text, Boolean
from database.base import Base
from database.mixins import TimestampMixin, UUIDMixin

class AppSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_settings"

    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)  # JSON string
    group = Column(String(50), nullable=False, index=True) # e.g. "onboarding", "general"
    description = Column(String(255), nullable=True)
    is_public = Column(Boolean, default=False) # Accessible without auth?

    def __repr__(self):
        return f"<AppSetting {self.key}>"
