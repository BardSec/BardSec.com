"""Tests for the risk scoring module."""
import pytest
from app.services.scoring import (
    calculate_risk_score,
    calculate_sensitivity_score,
    calculate_exposure_score,
    calculate_security_score,
    calculate_posture_score,
    calculate_integration_score,
    determine_risk_tier,
    reason_codes_to_json,
)
from app.schemas.assessment import AssessmentAnswers


class TestRiskTierDetermination:
    """Tests for risk tier classification."""

    def test_low_tier(self):
        assert determine_risk_tier(0) == "Low"
        assert determine_risk_tier(25) == "Low"

    def test_moderate_tier(self):
        assert determine_risk_tier(26) == "Moderate"
        assert determine_risk_tier(50) == "Moderate"

    def test_high_tier(self):
        assert determine_risk_tier(51) == "High"
        assert determine_risk_tier(75) == "High"

    def test_critical_tier(self):
        assert determine_risk_tier(76) == "Critical"
        assert determine_risk_tier(100) == "Critical"


class TestSensitivityScoring:
    """Tests for data sensitivity scoring."""

    def test_no_data_types(self):
        answers = AssessmentAnswers(data_types=[], data_types_unknown=False)
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 0
        assert len(reasons) == 0

    def test_unknown_data_types_penalty(self):
        answers = AssessmentAnswers(data_types_unknown=True)
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 10
        assert any(r.code == "SENS-UNK" for r in reasons)

    def test_iep_data_high_score(self):
        answers = AssessmentAnswers(data_types=["iep_504"])
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 8
        assert any(r.code == "SENS-IEP" for r in reasons)

    def test_health_data_high_score(self):
        answers = AssessmentAnswers(data_types=["health"])
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 8
        assert any(r.code == "SENS-HEALTH" for r in reasons)

    def test_biometrics_high_score(self):
        answers = AssessmentAnswers(data_types=["biometrics"])
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 8
        assert any(r.code == "SENS-BIO" for r in reasons)

    def test_low_sensitivity_data(self):
        answers = AssessmentAnswers(data_types=["directory_info", "auth_identifiers"])
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 3  # 2 + 1
        assert len(reasons) == 0  # Low sensitivity types don't generate reason codes

    def test_mixed_sensitivity_data(self):
        answers = AssessmentAnswers(
            data_types=["iep_504", "health", "directory_info"]
        )
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 18  # 8 + 8 + 2
        assert any(r.code == "SENS-IEP" for r in reasons)
        assert any(r.code == "SENS-HEALTH" for r in reasons)

    def test_sensitivity_capped_at_30(self):
        # Add many high-sensitivity types to exceed cap
        answers = AssessmentAnswers(
            data_types=[
                "iep_504", "health", "behavioral_sel", "biometrics",
                "precise_location", "discipline"
            ]
        )
        score, reasons = calculate_sensitivity_score(answers)
        assert score == 30  # Should be capped


class TestExposureScoring:
    """Tests for data exposure scoring."""

    def test_no_exposure(self):
        answers = AssessmentAnswers(
            third_party_sharing="no",
            used_for_advertising="no",
            used_for_ai_training="no",
            data_sold="no",
            subprocessors_disclosed="yes",
            data_region="us_only",
            storage_location="vendor_cloud",
        )
        score, reasons = calculate_exposure_score(answers)
        assert score == 0
        assert len(reasons) == 0

    def test_third_party_sharing(self):
        answers = AssessmentAnswers(third_party_sharing="yes")
        score, reasons = calculate_exposure_score(answers)
        assert any(r.code == "EXPO-SHARE" for r in reasons)
        assert score >= 6

    def test_advertising_use(self):
        answers = AssessmentAnswers(used_for_advertising="yes")
        score, reasons = calculate_exposure_score(answers)
        assert any(r.code == "EXPO-ADS" for r in reasons)

    def test_ai_training(self):
        answers = AssessmentAnswers(used_for_ai_training="yes")
        score, reasons = calculate_exposure_score(answers)
        assert any(r.code == "EXPO-AI" for r in reasons)

    def test_data_sold(self):
        answers = AssessmentAnswers(data_sold="yes")
        score, reasons = calculate_exposure_score(answers)
        assert any(r.code == "EXPO-SOLD" for r in reasons)

    def test_global_region(self):
        answers = AssessmentAnswers(data_region="global")
        score, reasons = calculate_exposure_score(answers)
        assert any(r.code == "EXPO-GLOBAL" for r in reasons)

    def test_unknown_values_add_points(self):
        answers = AssessmentAnswers(
            third_party_sharing="unknown",
            used_for_advertising="unknown",
            data_sold="unknown",
        )
        score, reasons = calculate_exposure_score(answers)
        assert score > 0  # Unknowns should add some points


class TestSecurityScoring:
    """Tests for security controls scoring."""

    def test_all_controls_present(self):
        answers = AssessmentAnswers(
            sso_supported="entra",
            mfa_available="yes",
            rbac_available="yes",
            encryption_transit="yes",
            encryption_rest="yes",
            audit_logs_available="yes",
        )
        score, reasons = calculate_security_score(answers)
        assert score == 0
        assert len(reasons) == 0

    def test_no_sso(self):
        answers = AssessmentAnswers(sso_supported="none")
        score, reasons = calculate_security_score(answers)
        assert any(r.code == "CTRL-NOSSO" for r in reasons)

    def test_no_mfa(self):
        answers = AssessmentAnswers(mfa_available="no")
        score, reasons = calculate_security_score(answers)
        assert any(r.code == "CTRL-NOMFA" for r in reasons)

    def test_no_encryption(self):
        answers = AssessmentAnswers(
            encryption_transit="no",
            encryption_rest="no",
        )
        score, reasons = calculate_security_score(answers)
        assert any(r.code == "CTRL-NOTRANS" for r in reasons)
        assert any(r.code == "CTRL-NOREST" for r in reasons)

    def test_unknown_controls_add_points(self):
        answers = AssessmentAnswers()  # All defaults to unknown
        score, reasons = calculate_security_score(answers)
        assert score > 0


class TestPostureScoring:
    """Tests for vendor posture scoring."""

    def test_good_posture(self):
        answers = AssessmentAnswers(
            retention_policy_stated="yes",
            deletion_process="self_serve",
        )
        score, reasons = calculate_posture_score(answers)
        assert score == 0

    def test_no_retention_policy(self):
        answers = AssessmentAnswers(retention_policy_stated="no")
        score, reasons = calculate_posture_score(answers)
        assert any(r.code == "POST-RETUNK" for r in reasons)

    def test_no_deletion_process(self):
        answers = AssessmentAnswers(deletion_process="no")
        score, reasons = calculate_posture_score(answers)
        assert any(r.code == "POST-NODEL" for r in reasons)

    def test_support_ticket_deletion(self):
        answers = AssessmentAnswers(deletion_process="support_ticket")
        score, reasons = calculate_posture_score(answers)
        assert any(r.code == "POST-DELUNK" for r in reasons)
        assert score == 3  # Lower penalty than no deletion


class TestIntegrationScoring:
    """Tests for integration blast radius scoring."""

    def test_minimal_integration(self):
        answers = AssessmentAnswers(
            integration_types=[],
            integration_method="csv_manual",
            integration_frequency="adhoc",
            sis_writeback="no",
        )
        score, reasons = calculate_integration_score(answers)
        assert score == 0

    def test_api_key_integration(self):
        answers = AssessmentAnswers(integration_method="api_key")
        score, reasons = calculate_integration_score(answers)
        assert any(r.code == "INT-APIKEY" for r in reasons)

    def test_realtime_integration(self):
        answers = AssessmentAnswers(integration_frequency="realtime")
        score, reasons = calculate_integration_score(answers)
        assert any(r.code == "INT-REALTIME" for r in reasons)

    def test_sis_writeback(self):
        answers = AssessmentAnswers(sis_writeback="yes")
        score, reasons = calculate_integration_score(answers)
        assert any(r.code == "INT-SISWB" for r in reasons)

    def test_multiple_integration_types(self):
        answers = AssessmentAnswers(
            integration_types=["sis", "lms", "api", "sso"]
        )
        score, reasons = calculate_integration_score(answers)
        assert any(r.code == "INT-MULTI" for r in reasons)


class TestFullScoring:
    """Integration tests for complete scoring."""

    def test_minimal_answers_unknown_penalty(self, minimal_answers):
        """Default answers (all unknown) should have moderate risk."""
        result = calculate_risk_score(minimal_answers)
        assert result.total > 0
        assert result.risk_tier in ("Moderate", "High")

    def test_low_risk_scenario(self, low_risk_answers):
        """Well-configured system should be low risk."""
        result = calculate_risk_score(low_risk_answers)
        assert result.total <= 25
        assert result.risk_tier == "Low"

    def test_high_risk_scenario(self, high_risk_answers):
        """Poorly configured system with sensitive data should be high/critical."""
        result = calculate_risk_score(high_risk_answers)
        assert result.total > 50
        assert result.risk_tier in ("High", "Critical")

    def test_score_breakdown_categories(self, low_risk_answers):
        """Score breakdown should have all categories."""
        result = calculate_risk_score(low_risk_answers)
        assert "sensitivity" in result.breakdown
        assert "exposure" in result.breakdown
        assert "security_controls" in result.breakdown
        assert "vendor_posture" in result.breakdown
        assert "integration_blast_radius" in result.breakdown

    def test_reason_codes_sorted_by_impact(self, high_risk_answers):
        """Reason codes should be sorted by points (highest first)."""
        result = calculate_risk_score(high_risk_answers)
        if len(result.reason_codes) > 1:
            for i in range(len(result.reason_codes) - 1):
                assert result.reason_codes[i].points >= result.reason_codes[i + 1].points

    def test_score_capped_at_100(self):
        """Total score should never exceed 100."""
        # Create maximally bad answers
        answers = AssessmentAnswers(
            data_types=[
                "iep_504", "health", "behavioral_sel", "biometrics",
                "precise_location", "discipline", "photos_video_audio",
                "staff_notes", "academic_records"
            ],
            storage_location="both",
            data_region="global",
            subprocessors_disclosed="no",
            retention_policy_stated="no",
            deletion_process="no",
            sso_supported="none",
            mfa_available="no",
            rbac_available="no",
            encryption_transit="no",
            encryption_rest="no",
            audit_logs_available="no",
            third_party_sharing="yes",
            used_for_advertising="yes",
            used_for_ai_training="yes",
            data_sold="yes",
            integration_types=["sis", "lms", "api", "sso"],
            integration_method="api_key",
            integration_frequency="realtime",
            sis_writeback="yes",
        )
        result = calculate_risk_score(answers)
        assert result.total <= 100


class TestReasonCodeSerialization:
    """Tests for reason code JSON serialization."""

    def test_serialization(self, high_risk_answers):
        result = calculate_risk_score(high_risk_answers)
        json_codes = reason_codes_to_json(result.reason_codes)

        assert isinstance(json_codes, list)
        if json_codes:
            first = json_codes[0]
            assert "code" in first
            assert "explanation" in first
            assert "category" in first
            assert "points" in first


class TestUnknownDataPenalty:
    """Tests for unknown data type handling."""

    def test_unknown_overrides_data_types(self, unknown_data_answers):
        """When unknown is set, data_types should be ignored."""
        unknown_data_answers.data_types = ["directory_info"]
        score, reasons = calculate_sensitivity_score(unknown_data_answers)
        assert score == 10  # Unknown penalty only
        assert any(r.code == "SENS-UNK" for r in reasons)
