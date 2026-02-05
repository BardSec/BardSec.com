"""CSV export for system inventory."""
import csv
import io
from typing import Sequence

from app.models.system import System
from app.schemas.assessment import DATA_TYPES


# CSV columns
CSV_COLUMNS = [
    "system_id",
    "name",
    "vendor",
    "purpose_category",
    "owner_department",
    "owner_contact",
    "risk_score",
    "risk_tier",
    "assessed_at",
    # Data types (boolean columns)
    "has_directory_info",
    "has_contact_info",
    "has_attendance_discipline",
    "has_academic_records",
    "has_iep_504",
    "has_health",
    "has_behavioral_sel",
    "has_biometrics",
    "has_precise_location",
    "has_photos_video_audio",
    "has_staff_notes",
    "has_auth_identifiers",
    "has_device_identifiers",
    # Storage
    "storage_location",
    "data_region",
    # Security
    "sso_supported",
    "mfa_available",
    "encryption_transit",
    "encryption_rest",
    "audit_logs_available",
    # Sharing
    "third_party_sharing",
    "used_for_advertising",
    "used_for_ai_training",
    "data_sold",
    # Integration
    "integration_types",
    "integration_method",
    "sis_writeback",
    # Metadata
    "created_at",
    "notes",
]


def generate_systems_csv(systems: Sequence[System]) -> bytes:
    """
    Generate CSV export of all systems with their assessments.

    Returns CSV as bytes (UTF-8 encoded with BOM for Excel compatibility).
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()

    for system in systems:
        assessment = system.current_assessment
        answers = assessment.answers_json if assessment else {}
        data_types = answers.get("data_types", [])

        row = {
            "system_id": str(system.id),
            "name": system.name,
            "vendor": system.vendor or "",
            "purpose_category": system.purpose_category.value,
            "owner_department": system.owner_department or "",
            "owner_contact": system.owner_contact or "",
            "risk_score": assessment.score_total if assessment else "",
            "risk_tier": assessment.risk_tier.value if assessment else "",
            "assessed_at": assessment.assessed_at.isoformat() if assessment else "",
            # Data types
            "has_directory_info": "directory_info" in data_types,
            "has_contact_info": "contact_info" in data_types,
            "has_attendance_discipline": "attendance_discipline" in data_types,
            "has_academic_records": "academic_records" in data_types,
            "has_iep_504": "iep_504" in data_types,
            "has_health": "health" in data_types,
            "has_behavioral_sel": "behavioral_sel" in data_types,
            "has_biometrics": "biometrics" in data_types,
            "has_precise_location": "precise_location" in data_types,
            "has_photos_video_audio": "photos_video_audio" in data_types,
            "has_staff_notes": "staff_notes" in data_types,
            "has_auth_identifiers": "auth_identifiers" in data_types,
            "has_device_identifiers": "device_identifiers" in data_types,
            # Storage
            "storage_location": answers.get("storage_location", ""),
            "data_region": answers.get("data_region", ""),
            # Security
            "sso_supported": answers.get("sso_supported", ""),
            "mfa_available": answers.get("mfa_available", ""),
            "encryption_transit": answers.get("encryption_transit", ""),
            "encryption_rest": answers.get("encryption_rest", ""),
            "audit_logs_available": answers.get("audit_logs_available", ""),
            # Sharing
            "third_party_sharing": answers.get("third_party_sharing", ""),
            "used_for_advertising": answers.get("used_for_advertising", ""),
            "used_for_ai_training": answers.get("used_for_ai_training", ""),
            "data_sold": answers.get("data_sold", ""),
            # Integration
            "integration_types": ";".join(answers.get("integration_types", [])),
            "integration_method": answers.get("integration_method", ""),
            "sis_writeback": answers.get("sis_writeback", ""),
            # Metadata
            "created_at": system.created_at.isoformat(),
            "notes": (system.notes or "").replace("\n", " "),
        }
        writer.writerow(row)

    # Get CSV string and encode with BOM for Excel
    csv_string = output.getvalue()
    return ('\ufeff' + csv_string).encode('utf-8')
