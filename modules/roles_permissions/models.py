from sqlalchemy import Column, String, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.base import Base
from database.mixins import UUIDMixin, TimestampMixin

# Association table for many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()'),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True),
    Column('granted_at', DateTime(timezone=True), server_default='NOW()')
)


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"
    
    role_name = Column(String(50), unique=True, nullable=False, index=True)
    display_name_ar = Column(String(100), nullable=False)
    display_name_en = Column(String(100), nullable=False)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted
    description_ar = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    
    def __repr__(self):
        return f"<Role {self.role_name}>"


class Permission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "permissions"
    
    permission_code = Column(String(100), unique=True, nullable=False, index=True)
    module = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description_ar = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission {self.permission_code}>"