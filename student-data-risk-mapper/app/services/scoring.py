"""
Risk scoring module for Student Data Risk Mapper.

Computes an explainable risk score (0-100) based on:
1. Sensitivity (0-30): Data types collected
2. Exposure (0-25): Sharing, subprocessors, storage
3. Security Controls (0-20): Missing controls increase score
4. Vendor Posture (0-15): Retention, deletion clarity
5. Integration Blast Radius (0-10): Integration risk

Each factor generates "reason codes" that explain the score.
"""
from typing import Any
from dataclasses import dataclass, field

from app.schemas.assessment import AssessmentAnswers


@dataclass
class ReasonCode:
    """A single reason code explaining a risk factor."""
    code: str
    explanation: str
    category: str
    points: int


@dataclass
class ScoreResult:
    """Complete scoring result."""
    total: int
    breakdown: dict[str, int]
    reason_codes: list[ReasonCode]
    risk_tier: str


# Data type sensitivity weights
DATA_TYPE_POINTS = {
    # High sensitivity (6+ points each)
    "iep_504": 8,
    "health": 8,
    "behavioral_sel": 7,
    "biometrics": 8,
    "precise_location": 7,
    "discipline": 6,
    # Medium sensitivity
    "photos_video_audio": 4,
    "staff_notes": 4,
    "academic_records": 3,
    "attendance_discipline": 3,
    # Low sensitivity
    "directory_info": 2,
    "contact_info": 2,
    "auth_identifiers": 1,
    "device_identifiers": 1,
}

# Reason code templates
REASON_TEMPLATES = {
    # Sensitivity
    "SENS-IEP": "System handles IEP/504 data, which is highly sensitive under FERPA and IDEA.",
    "SENS-HEALTH": "System collects health data, protected under FERPA and potentially HIPAA.",
    "SENS-BEHAV": "System stores behavioral/SEL data, which can be stigmatizing if mishandled.",
    "SENS-BIO": "System uses biometric data, requiring special consent and protections.",
    "SENS-LOC": "System tracks precise student location, raising significant privacy concerns.",
    "SENS-DISC": "System contains discipline records, which are sensitive under FERPA.",
    "SENS-MEDIA": "System stores student photos, video, or audio recordings.",
    "SENS-UNK": "Data types collected are unknown, adding uncertainty to risk assessment.",

    # Exposure
    "EXPO-SHARE": "Vendor indicates data is shared with third parties.",
    "EXPO-ADS": "Data may be used for advertising or marketing purposes.",
    "EXPO-AI": "Data may be used to train AI models.",
    "EXPO-SOLD": "Vendor indicates data may be sold or monetized.",
    "EXPO-SUBP": "Subprocessors are not disclosed, creating unknown exposure.",
    "EXPO-GLOBAL": "Data may be stored or processed outside the US.",
    "EXPO-BOTH": "Data stored in both vendor cloud and district systems increases exposure.",

    # Security Controls
    "CTRL-NOSSO": "SSO is not supported or status is unknown.",
    "CTRL-NOMFA": "Admin MFA is not available or unknown.",
    "CTRL-NORBAC": "Role-based access controls are not available or unknown.",
    "CTRL-NOTRANS": "Encryption in transit is not confirmed.",
    "CTRL-NOREST": "Encryption at rest is not confirmed.",
    "CTRL-NOAUDIT": "Audit logs are not available or unknown.",

    # Vendor Posture
    "POST-RETUNK": "Retention policy is missing or unknown.",
    "POST-DELUNK": "Data deletion process is unclear or requires manual support.",
    "POST-NODEL": "No clear process exists for data deletion.",

    # Integration
    "INT-APIKEY": "Integration uses API keys, increasing blast radius if exposed.",
    "INT-REALTIME": "Real-time data sync increases potential impact of breaches.",
    "INT-SISWB": "System writes data back to SIS, amplifying integration risk.",
    "INT-MULTI": "Multiple integration types increase attack surface.",
}


def calculate_sensitivity_score(answers: AssessmentAnswers) -> tuple[int, list[ReasonCode]]:
    """
    Calculate sensitivity score (0-30) based on data types.
    High-sensitivity data types contribute more points.
    """
    score = 0
    reasons = []

    if answers.data_types_unknown:
        score += 10  # Significant penalty for unknown
        reasons.append(ReasonCode(
            code="SENS-UNK",
            explanation=REASON_TEMPLATES["SENS-UNK"],
            category="sensitivity",
            points=10,
        ))
        return min(score, 30), reasons

    for data_type in answers.data_types:
        points = DATA_TYPE_POINTS.get(data_type, 0)
        score += points

        # Add reason codes for high-sensitivity types
        if data_type == "iep_504":
            reasons.append(ReasonCode("SENS-IEP", REASON_TEMPLATES["SENS-IEP"], "sensitivity", points))
        elif data_type == "health":
            reasons.append(ReasonCode("SENS-HEALTH", REASON_TEMPLATES["SENS-HEALTH"], "sensitivity", points))
        elif data_type == "behavioral_sel":
            reasons.append(ReasonCode("SENS-BEHAV", REASON_TEMPLATES["SENS-BEHAV"], "sensitivity", points))
        elif data_type == "biometrics":
            reasons.append(ReasonCode("SENS-BIO", REASON_TEMPLATES["SENS-BIO"], "sensitivity", points))
        elif data_type == "precise_location":
            reasons.append(ReasonCode("SENS-LOC", REASON_TEMPLATES["SENS-LOC"], "sensitivity", points))
        elif data_type == "discipline" or data_type == "attendance_discipline":
            reasons.append(ReasonCode("SENS-DISC", REASON_TEMPLATES["SENS-DISC"], "sensitivity", points))
        elif data_type == "photos_video_audio":
            reasons.append(ReasonCode("SENS-MEDIA", REASON_TEMPLATES["SENS-MEDIA"], "sensitivity", points))

    return min(score, 30), reasons


def calculate_exposure_score(answers: AssessmentAnswers) -> tuple[int, list[ReasonCode]]:
    """
    Calculate exposure score (0-25) based on sharing and storage.
    """
    score = 0
    reasons = []

    # Third-party sharing
    if answers.third_party_sharing == "yes":
        score += 6
        reasons.append(ReasonCode("EXPO-SHARE", REASON_TEMPLATES["EXPO-SHARE"], "exposure", 6))
    elif answers.third_party_sharing == "unknown":
        score += 4

    # Advertising use
    if answers.used_for_advertising == "yes":
        score += 5
        reasons.append(ReasonCode("EXPO-ADS", REASON_TEMPLATES["EXPO-ADS"], "exposure", 5))
    elif answers.used_for_advertising == "unknown":
        score += 3

    # AI training
    if answers.used_for_ai_training == "yes":
        score += 4
        reasons.append(ReasonCode("EXPO-AI", REASON_TEMPLATES["EXPO-AI"], "exposure", 4))
    elif answers.used_for_ai_training == "unknown":
        score += 2

    # Data sold
    if answers.data_sold == "yes":
        score += 6
        reasons.append(ReasonCode("EXPO-SOLD", REASON_TEMPLATES["EXPO-SOLD"], "exposure", 6))
    elif answers.data_sold == "unknown":
        score += 4

    # Subprocessors
    if answers.subprocessors_disclosed == "no":
        score += 4
        reasons.append(ReasonCode("EXPO-SUBP", REASON_TEMPLATES["EXPO-SUBP"], "exposure", 4))
    elif answers.subprocessors_disclosed == "unknown":
        score += 3
        reasons.append(ReasonCode("EXPO-SUBP", REASON_TEMPLATES["EXPO-SUBP"], "exposure", 3))

    # Data region
    if answers.data_region == "global":
        score += 3
        reasons.append(ReasonCode("EXPO-GLOBAL", REASON_TEMPLATES["EXPO-GLOBAL"], "exposure", 3))
    elif answers.data_region == "unknown":
        score += 2

    # Storage location
    if answers.storage_location == "both":
        score += 2
        reasons.append(ReasonCode("EXPO-BOTH", REASON_TEMPLATES["EXPO-BOTH"], "exposure", 2))
    elif answers.storage_location == "unknown":
        score += 2

    return min(score, 25), reasons


def calculate_security_score(answers: AssessmentAnswers) -> tuple[int, list[ReasonCode]]:
    """
    Calculate security controls score (0-20).
    Missing controls increase the score.
    """
    score = 0
    reasons = []

    # SSO support
    if answers.sso_supported in ("none", "unknown"):
        score += 4
        reasons.append(ReasonCode("CTRL-NOSSO", REASON_TEMPLATES["CTRL-NOSSO"], "security", 4))

    # MFA
    if answers.mfa_available != "yes":
        score += 4
        reasons.append(ReasonCode("CTRL-NOMFA", REASON_TEMPLATES["CTRL-NOMFA"], "security", 4))

    # RBAC
    if answers.rbac_available != "yes":
        score += 3
        reasons.append(ReasonCode("CTRL-NORBAC", REASON_TEMPLATES["CTRL-NORBAC"], "security", 3))

    # Encryption in transit
    if answers.encryption_transit != "yes":
        score += 3
        reasons.append(ReasonCode("CTRL-NOTRANS", REASON_TEMPLATES["CTRL-NOTRANS"], "security", 3))

    # Encryption at rest
    if answers.encryption_rest != "yes":
        score += 3
        reasons.append(ReasonCode("CTRL-NOREST", REASON_TEMPLATES["CTRL-NOREST"], "security", 3))

    # Audit logs
    if answers.audit_logs_available != "yes":
        score += 3
        reasons.append(ReasonCode("CTRL-NOAUDIT", REASON_TEMPLATES["CTRL-NOAUDIT"], "security", 3))

    return min(score, 20), reasons


def calculate_posture_score(answers: AssessmentAnswers) -> tuple[int, list[ReasonCode]]:
    """
    Calculate vendor posture score (0-15).
    Missing retention/deletion clarity increases score.
    """
    score = 0
    reasons = []

    # Retention policy
    if answers.retention_policy_stated != "yes":
        score += 6
        reasons.append(ReasonCode("POST-RETUNK", REASON_TEMPLATES["POST-RETUNK"], "posture", 6))

    # Deletion process
    if answers.deletion_process == "no":
        score += 6
        reasons.append(ReasonCode("POST-NODEL", REASON_TEMPLATES["POST-NODEL"], "posture", 6))
    elif answers.deletion_process == "unknown":
        score += 5
        reasons.append(ReasonCode("POST-DELUNK", REASON_TEMPLATES["POST-DELUNK"], "posture", 5))
    elif answers.deletion_process == "support_ticket":
        score += 3
        reasons.append(ReasonCode("POST-DELUNK", REASON_TEMPLATES["POST-DELUNK"], "posture", 3))

    return min(score, 15), reasons


def calculate_integration_score(answers: AssessmentAnswers) -> tuple[int, list[ReasonCode]]:
    """
    Calculate integration blast radius score (0-10).
    """
    score = 0
    reasons = []

    # Integration method
    if answers.integration_method == "api_key":
        score += 3
        reasons.append(ReasonCode("INT-APIKEY", REASON_TEMPLATES["INT-APIKEY"], "integration", 3))
    elif answers.integration_method == "unknown":
        score += 2

    # Frequency
    if answers.integration_frequency == "realtime":
        score += 3
        reasons.append(ReasonCode("INT-REALTIME", REASON_TEMPLATES["INT-REALTIME"], "integration", 3))
    elif answers.integration_frequency == "unknown":
        score += 1

    # SIS writeback
    if answers.sis_writeback == "yes":
        score += 3
        reasons.append(ReasonCode("INT-SISWB", REASON_TEMPLATES["INT-SISWB"], "integration", 3))
    elif answers.sis_writeback == "unknown":
        score += 2

    # Multiple integration types
    if len(answers.integration_types) >= 3:
        score += 2
        reasons.append(ReasonCode("INT-MULTI", REASON_TEMPLATES["INT-MULTI"], "integration", 2))

    return min(score, 10), reasons


def determine_risk_tier(score: int) -> str:
    """Determine risk tier from total score."""
    if score <= 25:
        return "Low"
    elif score <= 50:
        return "Moderate"
    elif score <= 75:
        return "High"
    else:
        return "Critical"


def calculate_risk_score(answers: AssessmentAnswers) -> ScoreResult:
    """
    Calculate complete risk score with breakdown and reason codes.

    Args:
        answers: Structured questionnaire answers

    Returns:
        ScoreResult with total score, breakdown, reason codes, and tier
    """
    # Calculate each category
    sens_score, sens_reasons = calculate_sensitivity_score(answers)
    expo_score, expo_reasons = calculate_exposure_score(answers)
    sec_score, sec_reasons = calculate_security_score(answers)
    post_score, post_reasons = calculate_posture_score(answers)
    int_score, int_reasons = calculate_integration_score(answers)

    # Combine
    total = sens_score + expo_score + sec_score + post_score + int_score
    total = min(total, 100)

    breakdown = {
        "sensitivity": sens_score,
        "exposure": expo_score,
        "security_controls": sec_score,
        "vendor_posture": post_score,
        "integration_blast_radius": int_score,
    }

    # Combine and sort reasons by points (highest first)
    all_reasons = sens_reasons + expo_reasons + sec_reasons + post_reasons + int_reasons
    all_reasons.sort(key=lambda r: r.points, reverse=True)

    return ScoreResult(
        total=total,
        breakdown=breakdown,
        reason_codes=all_reasons,
        risk_tier=determine_risk_tier(total),
    )


def reason_codes_to_json(reason_codes: list[ReasonCode]) -> list[dict[str, Any]]:
    """Convert reason codes to JSON-serializable format."""
    return [
        {
            "code": rc.code,
            "explanation": rc.explanation,
            "category": rc.category,
            "points": rc.points,
        }
        for rc in reason_codes
    ]
