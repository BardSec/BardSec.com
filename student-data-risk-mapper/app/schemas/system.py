"""System schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.system import PurposeCategory


class SystemBase(BaseModel):
    """Base system fields."""
    name: str = Field(..., min_length=1, max_length=255)
    vendor: Optional[str] = Field(None, max_length=255)
    owner_department: Optional[str] = Field(None, max_length=255)
    owner_contact: Optional[str] = Field(None, max_length=255)
    purpose_category: PurposeCategory = PurposeCategory.OTHER
    notes: Optional[str] = None


class SystemCreate(SystemBase):
    """Schema for creating a system."""
    pass


class SystemUpdate(BaseModel):
    """Schema for updating a system (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    vendor: Optional[str] = Field(None, max_length=255)
    owner_department: Optional[str] = Field(None, max_length=255)
    owner_contact: Optional[str] = Field(None, max_length=255)
    purpose_category: Optional[PurposeCategory] = None
    notes: Optional[str] = None


class SystemResponse(SystemBase):
    """System response with computed fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID

    # From current assessment
    risk_score: Optional[int] = None
    risk_tier: Optional[str] = None
    has_assessment: bool = False

    class Config:
        from_attributes = True


class SystemListResponse(BaseModel):
    """Paginated list of systems."""
    items: list[SystemResponse]
    total: int
    page: int
    per_page: int
