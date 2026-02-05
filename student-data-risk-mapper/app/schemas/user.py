"""User schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserSession(BaseModel):
    """User session data stored in cookie."""
    user_id: UUID
    email: str
    display_name: str
    role: UserRole
    entra_oid: str
