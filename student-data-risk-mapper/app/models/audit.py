"""Audit log model for tracking user actions."""
import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""
    # System actions
    SYSTEM_CREATE = "system.create"
    SYSTEM_UPDATE = "system.update"
    SYSTEM_DELETE = "system.delete"

    # Assessment actions
    ASSESSMENT_CREATE = "assessment.create"

    # Export actions
    EXPORT_PDF = "export.pdf"
    EXPORT_CSV = "export.csv"

    # Auth actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"


class AuditLog(Base):
    """
    Audit log entry for tracking who did what and when.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Relationship
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog {self.action.value} by {self.user_id}>"


async def log_action(
    session,
    user_id: Optional[uuid.UUID],
    action: AuditAction,
    target_type: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Helper to create an audit log entry."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata,
    )
    session.add(entry)
    await session.flush()
    return entry
