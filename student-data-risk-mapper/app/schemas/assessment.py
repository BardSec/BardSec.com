"""Assessment schemas for risk questionnaire."""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.assessment import RiskTier


# Data type options with definitions
DATA_TYPES = {
    "directory_info": "Directory info (name, grade, student ID)",
    "contact_info": "Contact info (address, parent email, phone)",
    "attendance_discipline": "Attendance and discipline records",
    "academic_records": "Academic records and grades",
    "iep_504": "IEP/504 or special services documentation",
    "health": "Health data (medical conditions, medications)",
    "behavioral_sel": "Behavioral/SEL data (observations, assessments)",
    "biometrics": "Biometric data (fingerprints, facial recognition)",
    "precise_location": "Precise location tracking",
    "photos_video_audio": "Photos, video, or audio recordings",
    "staff_notes": "Free-text staff notes about students",
    "auth_identifiers": "Authentication identifiers (SSO IDs)",
    "device_identifiers": "Device identifiers",
}

# Storage location options
StorageLocation = Literal["vendor_cloud", "district", "both", "unknown"]

# Data region options
DataRegion = Literal["us_only", "eu", "global", "unknown"]

# Yes/No/Unknown for most controls
YesNoUnknown = Literal["yes", "no", "unknown"]

# SSO options
SSOOption = Literal["entra", "google", "other", "none", "unknown"]

# Deletion process options
DeletionProcess = Literal["self_serve", "support_ticket", "no", "unknown"]

# Integration types
IntegrationType = Literal["sis", "lms", "sso", "oneroster", "api", "csv_upload"]

# Integration method
IntegrationMethod = Literal["oauth", "api_key", "csv_manual", "unknown"]

# Frequency options
IntegrationFrequency = Literal["realtime", "nightly", "adhoc", "unknown"]


class AssessmentAnswers(BaseModel):
    """
    Structured questionnaire answers.
    All fields support 'unknown' or empty values.
    """

    # Step B: Data types collected
    data_types: list[str] = Field(default_factory=list)
    data_types_unknown: bool = False

    # Step C: Storage and processing
    storage_location: StorageLocation = "unknown"
    data_region: DataRegion = "unknown"
    subprocessors_disclosed: YesNoUnknown = "unknown"
    retention_policy_stated: YesNoUnknown = "unknown"
    deletion_process: DeletionProcess = "unknown"

    # Step D: Access and security controls
    sso_supported: SSOOption = "unknown"
    mfa_available: YesNoUnknown = "unknown"
    rbac_available: YesNoUnknown = "unknown"
    encryption_transit: YesNoUnknown = "unknown"
    encryption_rest: YesNoUnknown = "unknown"
    audit_logs_available: YesNoUnknown = "unknown"

    # Step E: Sharing and secondary use
    third_party_sharing: YesNoUnknown = "unknown"
    used_for_advertising: YesNoUnknown = "unknown"
    used_for_ai_training: YesNoUnknown = "unknown"
    data_sold: YesNoUnknown = "unknown"

    # Step F: Integrations
    integration_types: list[str] = Field(default_factory=list)
    integration_method: IntegrationMethod = "unknown"
    integration_frequency: IntegrationFrequency = "unknown"
    sis_writeback: YesNoUnknown = "unknown"


class ReasonCode(BaseModel):
    """Explanation for a risk factor."""
    code: str
    explanation: str
    category: str
    points: int


class AssessmentCreate(BaseModel):
    """Schema for creating an assessment."""
    system_id: UUID
    answers: AssessmentAnswers


class AssessmentResponse(BaseModel):
    """Assessment response with scores."""
    id: UUID
    system_id: UUID
    assessed_by_id: UUID
    assessed_at: datetime
    answers_json: dict
    score_total: int
    score_breakdown_json: dict
    reason_codes_json: list
    risk_tier: RiskTier

    class Config:
        from_attributes = True


class ScoreBreakdown(BaseModel):
    """Breakdown of risk score by category."""
    sensitivity: int = Field(ge=0, le=30)
    exposure: int = Field(ge=0, le=25)
    security_controls: int = Field(ge=0, le=20)
    vendor_posture: int = Field(ge=0, le=15)
    integration_blast_radius: int = Field(ge=0, le=10)
    total: int = Field(ge=0, le=100)
