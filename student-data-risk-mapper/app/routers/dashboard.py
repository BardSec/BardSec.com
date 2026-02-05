"""Dashboard routes."""
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.session import get_session
from app.models.system import System, PurposeCategory
from app.models.assessment import RiskAssessment, RiskTier
from app.schemas.assessment import DATA_TYPES

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

# Sensitive data types for heatmap
SENSITIVE_TYPES = [
    ("iep_504", "IEP/504"),
    ("health", "Health"),
    ("behavioral_sel", "Behavioral/SEL"),
    ("biometrics", "Biometrics"),
    ("precise_location", "Location"),
    ("discipline", "Discipline"),
]


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    data_type: Optional[str] = Query(None),
    sso: Optional[str] = Query(None),
    sharing: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Main dashboard with system list and filters."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Build query
    query = select(System).options(selectinload(System.assessments))

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                System.name.ilike(search_term),
                System.vendor.ilike(search_term),
            )
        )

    if purpose:
        try:
            purpose_cat = PurposeCategory(purpose)
            query = query.where(System.purpose_category == purpose_cat)
        except ValueError:
            pass

    # Execute query
    result = await db.execute(query.order_by(System.name))
    systems = result.scalars().all()

    # Post-query filtering for assessment-related filters
    filtered_systems = []
    for system in systems:
        assessment = system.current_assessment

        # Filter by tier
        if tier:
            if not assessment or assessment.risk_tier.value != tier:
                continue

        # Filter by data type
        if data_type:
            if not assessment:
                continue
            answers = assessment.answers_json
            if data_type not in answers.get("data_types", []):
                continue

        # Filter by SSO
        if sso:
            if not assessment:
                continue
            answers = assessment.answers_json
            sso_val = answers.get("sso_supported", "unknown")
            if sso == "yes" and sso_val in ("none", "unknown"):
                continue
            if sso == "no" and sso_val not in ("none", "unknown"):
                continue

        # Filter by sharing
        if sharing:
            if not assessment:
                continue
            answers = assessment.answers_json
            sharing_val = answers.get("third_party_sharing", "unknown")
            if sharing == "yes" and sharing_val != "yes":
                continue
            if sharing == "no" and sharing_val not in ("no",):
                continue

        filtered_systems.append(system)

    # Pagination
    total = len(filtered_systems)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_systems = filtered_systems[start:end]

    # Count by tier for summary
    tier_counts = {"Low": 0, "Moderate": 0, "High": 0, "Critical": 0, "Unassessed": 0}
    for system in systems:
        if system.current_assessment:
            tier_counts[system.current_assessment.risk_tier.value] += 1
        else:
            tier_counts["Unassessed"] += 1

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "systems": paginated_systems,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "tier_counts": tier_counts,
            "purpose_categories": list(PurposeCategory),
            "risk_tiers": ["Low", "Moderate", "High", "Critical"],
            "data_types": DATA_TYPES,
            # Current filter values
            "filter_search": search or "",
            "filter_purpose": purpose or "",
            "filter_tier": tier or "",
            "filter_data_type": data_type or "",
            "filter_sso": sso or "",
            "filter_sharing": sharing or "",
        }
    )


@router.get("/heatmap", response_class=HTMLResponse)
async def heatmap_view(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Heatmap/matrix view of systems vs sensitive data types."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get all systems with assessments
    result = await db.execute(
        select(System)
        .options(selectinload(System.assessments))
        .order_by(System.name)
    )
    systems = result.scalars().all()

    # Build heatmap data
    heatmap_data = []
    for system in systems:
        assessment = system.current_assessment
        row = {
            "system": system,
            "data_types": {},
            "has_assessment": assessment is not None,
        }

        if assessment:
            data_types = assessment.answers_json.get("data_types", [])
            for type_key, type_label in SENSITIVE_TYPES:
                row["data_types"][type_key] = type_key in data_types

        heatmap_data.append(row)

    return templates.TemplateResponse(
        "heatmap.html",
        {
            "request": request,
            "user": user,
            "heatmap_data": heatmap_data,
            "sensitive_types": SENSITIVE_TYPES,
        }
    )


@router.get("/high-risk", response_class=HTMLResponse)
async def high_risk_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List of high and critical risk systems."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get systems with high/critical assessments
    result = await db.execute(
        select(System)
        .options(selectinload(System.assessments))
        .order_by(System.name)
    )
    systems = result.scalars().all()

    # Filter to high/critical only
    high_risk_systems = []
    for system in systems:
        assessment = system.current_assessment
        if assessment and assessment.risk_tier in (RiskTier.HIGH, RiskTier.CRITICAL):
            high_risk_systems.append(system)

    # Sort by score descending
    high_risk_systems.sort(
        key=lambda s: s.current_assessment.score_total if s.current_assessment else 0,
        reverse=True
    )

    return templates.TemplateResponse(
        "high_risk.html",
        {
            "request": request,
            "user": user,
            "systems": high_risk_systems,
        }
    )
