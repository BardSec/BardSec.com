"""Risk assessment model."""
import uuid
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.system import System
    from app.models.user import User


class RiskTier(str, enum.Enum):
    """Risk tier classification based on score."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"

    @classmethod
    def from_score(cls, score: int) -> "RiskTier":
        """Determine tier from numeric score."""
        if score <= 25:
            return cls.LOW
        elif score <= 50:
            return cls.MODERATE
        elif score <= 75:
            return cls.HIGH
        else:
            return cls.CRITICAL


class RiskAssessment(Base):
    """
    Risk assessment for a system containing questionnaire answers,
    computed scores, and reason codes.
    """
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("systems.id", ondelete="CASCADE"), nullable=False
    )

    # Who and when
    assessed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Raw questionnaire answers
    answers_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Computed scores
    score_total: Mapped[int] = mapped_column(Integer, default=0)
    score_breakdown_json: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    reason_codes_json: Mapped[list[dict[str, str]]] = mapped_column(JSONB, default=list)
    risk_tier: Mapped[RiskTier] = mapped_column(
        SQLEnum(RiskTier), default=RiskTier.LOW
    )

    # Relationships
    system: Mapped["System"] = relationship("System", back_populates="assessments")
    assessed_by: Mapped["User"] = relationship("User", foreign_keys=[assessed_by_id])

    def __repr__(self) -> str:
        return f"<RiskAssessment {self.system_id} score={self.score_total}>"

    @property
    def data_types(self) -> list[str]:
        """Get list of data types from answers."""
        return self.answers_json.get("data_types", [])

    @property
    def has_sensitive_data(self) -> bool:
        """Check if system handles sensitive data types."""
        sensitive_types = {
            "iep_504", "health", "behavioral_sel", "biometrics",
            "precise_location", "discipline"
        }
        return bool(set(self.data_types) & sensitive_types)

    @property
    def top_reason_codes(self) -> list[dict[str, str]]:
        """Get top 5 reason codes."""
        return self.reason_codes_json[:5] if self.reason_codes_json else []
