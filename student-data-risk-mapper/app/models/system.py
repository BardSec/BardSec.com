"""System model for vendor/app inventory."""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.assessment import RiskAssessment
    from app.models.user import User


class PurposeCategory(str, enum.Enum):
    """Purpose categories for systems."""
    INSTRUCTION = "Instruction"
    ASSESSMENT = "Assessment"
    COMMUNICATION = "Communication"
    OPERATIONS = "Operations"
    OTHER = "Other"


class System(Base):
    """
    System represents a vendor, app, or integration in the district's
    edtech inventory that handles student data.
    """
    __tablename__ = "systems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purpose_category: Mapped[PurposeCategory] = mapped_column(
        SQLEnum(PurposeCategory), default=PurposeCategory.OTHER
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Audit fields
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    assessments: Mapped[list["RiskAssessment"]] = relationship(
        "RiskAssessment",
        back_populates="system",
        order_by="desc(RiskAssessment.assessed_at)",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<System {self.name}>"

    @property
    def current_assessment(self) -> Optional["RiskAssessment"]:
        """Get the most recent assessment."""
        if self.assessments:
            return self.assessments[0]
        return None

    @property
    def risk_tier(self) -> Optional[str]:
        """Get current risk tier from latest assessment."""
        if self.current_assessment:
            return self.current_assessment.risk_tier.value
        return None

    @property
    def risk_score(self) -> Optional[int]:
        """Get current risk score from latest assessment."""
        if self.current_assessment:
            return self.current_assessment.score_total
        return None
