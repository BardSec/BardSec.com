"""User model for session and audit tracking."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """User roles for authorization."""
    USER = "user"
    ADMIN = "admin"
    AUDITOR = "auditor"


class User(Base):
    """
    User record for tracking who performed actions.
    Created/updated on each login via Entra ID.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Entra Object ID (sub claim)
    entra_oid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.USER
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    def is_auditor(self) -> bool:
        """Check if user has auditor role."""
        return self.role == UserRole.AUDITOR

    def can_export_csv(self) -> bool:
        """Check if user can export full CSV (admin only)."""
        return self.role == UserRole.ADMIN
