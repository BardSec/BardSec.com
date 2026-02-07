"""Assessment wizard routes."""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.session import get_session
from app.models.system import System
from app.models.assessment import RiskAssessment, RiskTier
from app.models.audit import log_action, AuditAction
from app.schemas.assessment import AssessmentAnswers, DATA_TYPES
from app.services.scoring import calculate_risk_score, reason_codes_to_json

router = APIRouter(prefix="/assessments", tags=["assessments"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/wizard/{system_id}", response_class=HTMLResponse)
async def assessment_wizard(
    request: Request,
    system_id: UUID,
    step: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Show assessment wizard for a system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(System).where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    # Ensure step is valid (1-6)
    step = max(1, min(step, 6))

    return templates.TemplateResponse(
        "assessment_wizard.html",
        {
            "request": request,
            "user": user,
            "system": system,
            "step": step,
            "total_steps": 6,
            "data_types": DATA_TYPES,
        }
    )


@router.post("/wizard/{system_id}/submit")
async def submit_assessment(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Submit completed assessment."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Verify system exists
    result = await db.execute(
        select(System).where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    # Parse form data
    form_data = await request.form()

    # Build answers from form
    answers = AssessmentAnswers(
        # Step B: Data types
        data_types=form_data.getlist("data_types"),
        data_types_unknown="data_types_unknown" in form_data,

        # Step C: Storage and processing
        storage_location=form_data.get("storage_location", "unknown"),
        data_region=form_data.get("data_region", "unknown"),
        subprocessors_disclosed=form_data.get("subprocessors_disclosed", "unknown"),
        retention_policy_stated=form_data.get("retention_policy_stated", "unknown"),
        deletion_process=form_data.get("deletion_process", "unknown"),

        # Step D: Access and security
        sso_supported=form_data.get("sso_supported", "unknown"),
        mfa_available=form_data.get("mfa_available", "unknown"),
        rbac_available=form_data.get("rbac_available", "unknown"),
        encryption_transit=form_data.get("encryption_transit", "unknown"),
        encryption_rest=form_data.get("encryption_rest", "unknown"),
        audit_logs_available=form_data.get("audit_logs_available", "unknown"),

        # Step E: Sharing
        third_party_sharing=form_data.get("third_party_sharing", "unknown"),
        used_for_advertising=form_data.get("used_for_advertising", "unknown"),
        used_for_ai_training=form_data.get("used_for_ai_training", "unknown"),
        data_sold=form_data.get("data_sold", "unknown"),

        # Step F: Integrations
        integration_types=form_data.getlist("integration_types"),
        integration_method=form_data.get("integration_method", "unknown"),
        integration_frequency=form_data.get("integration_frequency", "unknown"),
        sis_writeback=form_data.get("sis_writeback", "unknown"),
    )

    # Calculate risk score
    score_result = calculate_risk_score(answers)

    # Create assessment record
    assessment = RiskAssessment(
        system_id=system_id,
        assessed_by_id=user.user_id,
        answers_json=answers.model_dump(),
        score_total=score_result.total,
        score_breakdown_json=score_result.breakdown,
        reason_codes_json=reason_codes_to_json(score_result.reason_codes),
        risk_tier=RiskTier(score_result.risk_tier),
    )

    db.add(assessment)
    await db.flush()

    # Log action
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.ASSESSMENT_CREATE,
        target_type="assessment",
        target_id=assessment.id,
        metadata={
            "system_id": str(system_id),
            "system_name": system.name,
            "score": score_result.total,
            "tier": score_result.risk_tier,
        },
    )

    return RedirectResponse(url=f"/systems/{system_id}", status_code=302)


@router.get("/{assessment_id}", response_class=HTMLResponse)
async def view_assessment(
    request: Request,
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """View a specific assessment."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(RiskAssessment)
        .options(selectinload(RiskAssessment.system))
        .where(RiskAssessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return templates.TemplateResponse(
        "assessment_detail.html",
        {
            "request": request,
            "user": user,
            "assessment": assessment,
            "system": assessment.system,
            "data_types": DATA_TYPES,
        }
    )
