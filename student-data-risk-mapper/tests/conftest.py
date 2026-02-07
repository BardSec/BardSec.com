"""Pytest configuration and fixtures."""
import pytest
from app.schemas.assessment import AssessmentAnswers


@pytest.fixture
def minimal_answers():
    """Minimal answers with defaults (all unknown)."""
    return AssessmentAnswers()


@pytest.fixture
def low_risk_answers():
    """Answers representing a low-risk system."""
    return AssessmentAnswers(
        data_types=["directory_info", "auth_identifiers"],
        data_types_unknown=False,
        storage_location="vendor_cloud",
        data_region="us_only",
        subprocessors_disclosed="yes",
        retention_policy_stated="yes",
        deletion_process="self_serve",
        sso_supported="entra",
        mfa_available="yes",
        rbac_available="yes",
        encryption_transit="yes",
        encryption_rest="yes",
        audit_logs_available="yes",
        third_party_sharing="no",
        used_for_advertising="no",
        used_for_ai_training="no",
        data_sold="no",
        integration_types=["sso"],
        integration_method="oauth",
        integration_frequency="nightly",
        sis_writeback="no",
    )


@pytest.fixture
def high_risk_answers():
    """Answers representing a high-risk system."""
    return AssessmentAnswers(
        data_types=[
            "iep_504", "health", "behavioral_sel", "biometrics",
            "academic_records", "directory_info"
        ],
        data_types_unknown=False,
        storage_location="both",
        data_region="global",
        subprocessors_disclosed="no",
        retention_policy_stated="no",
        deletion_process="no",
        sso_supported="none",
        mfa_available="no",
        rbac_available="unknown",
        encryption_transit="unknown",
        encryption_rest="no",
        audit_logs_available="no",
        third_party_sharing="yes",
        used_for_advertising="yes",
        used_for_ai_training="yes",
        data_sold="unknown",
        integration_types=["sis", "lms", "api"],
        integration_method="api_key",
        integration_frequency="realtime",
        sis_writeback="yes",
    )


@pytest.fixture
def unknown_data_answers():
    """Answers where data types are unknown."""
    return AssessmentAnswers(
        data_types_unknown=True,
    )
