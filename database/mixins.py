from sqlalchemy import Column, DateTime, func, Boolean, String
from sqlalchemy import TypeDecorator
import uuid


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses String for SQLite compatibility.
    """
    impl = String
    cache_ok = True

    def __init__(self, length=36, *args, **kwargs):
        super().__init__(length, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        # Keep as string for simplicity
        return value


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin to add soft delete functionality"""
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None


class UUIDMixin:
    """Mixin to add UUID primary key - works with both PostgreSQL and SQLite"""
    id = Column(UUID(), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)