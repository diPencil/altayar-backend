from pydantic import BaseModel, Field
from typing import Optional, List, Any, Generic, TypeVar
from datetime import datetime
from uuid import UUID

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response"""
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class SuccessResponse(BaseModel):
    """Standard success response"""
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None


class BaseSchema(BaseModel):
    """Base schema with common fields"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }