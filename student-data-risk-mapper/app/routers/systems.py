"""System CRUD routes."""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.session import get_session
from app.auth.oidc import get_current_user_required
from app.models.system import System, PurposeCategory
from app.models.audit import log_action, AuditAction
from app.schemas.user import UserSession
from app.schemas.system import SystemCreate, SystemUpdate

router = APIRouter(prefix="/systems", tags=["systems"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/new", response_class=HTMLResponse)
async def new_system_form(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Show form to create a new system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    return templates.TemplateResponse(
        "system_form.html",
        {
            "request": request,
            "user": user,
            "system": None,
            "purpose_categories": list(PurposeCategory),
            "is_edit": False,
        }
    )


@router.post("/new")
async def create_system(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    vendor: Optional[str] = Form(None),
    owner_department: Optional[str] = Form(None),
    owner_contact: Optional[str] = Form(None),
    purpose_category: str = Form("Other"),
    notes: Optional[str] = Form(None),
):
    """Create a new system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Validate purpose category
    try:
        purpose = PurposeCategory(purpose_category)
    except ValueError:
        purpose = PurposeCategory.OTHER

    system = System(
        name=name.strip(),
        vendor=vendor.strip() if vendor else None,
        owner_department=owner_department.strip() if owner_department else None,
        owner_contact=owner_contact.strip() if owner_contact else None,
        purpose_category=purpose,
        notes=notes.strip() if notes else None,
        created_by_id=user.user_id,
    )

    db.add(system)
    await db.flush()
    await db.refresh(system)

    # Log action
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.SYSTEM_CREATE,
        target_type="system",
        target_id=system.id,
        metadata={"name": system.name},
    )

    # Redirect to assessment wizard
    return RedirectResponse(
        url=f"/assessments/wizard/{system.id}",
        status_code=302,
    )


@router.get("/{system_id}", response_class=HTMLResponse)
async def view_system(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """View system details and current assessment."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(System)
        .options(selectinload(System.assessments))
        .where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    return templates.TemplateResponse(
        "system_detail.html",
        {
            "request": request,
            "user": user,
            "system": system,
            "assessment": system.current_assessment,
        }
    )


@router.get("/{system_id}/edit", response_class=HTMLResponse)
async def edit_system_form(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Show form to edit a system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(System).where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    return templates.TemplateResponse(
        "system_form.html",
        {
            "request": request,
            "user": user,
            "system": system,
            "purpose_categories": list(PurposeCategory),
            "is_edit": True,
        }
    )


@router.post("/{system_id}/edit")
async def update_system(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    vendor: Optional[str] = Form(None),
    owner_department: Optional[str] = Form(None),
    owner_contact: Optional[str] = Form(None),
    purpose_category: str = Form("Other"),
    notes: Optional[str] = Form(None),
):
    """Update an existing system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(System).where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    # Update fields
    system.name = name.strip()
    system.vendor = vendor.strip() if vendor else None
    system.owner_department = owner_department.strip() if owner_department else None
    system.owner_contact = owner_contact.strip() if owner_contact else None
    try:
        system.purpose_category = PurposeCategory(purpose_category)
    except ValueError:
        system.purpose_category = PurposeCategory.OTHER
    system.notes = notes.strip() if notes else None

    await db.flush()

    # Log action
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.SYSTEM_UPDATE,
        target_type="system",
        target_id=system.id,
        metadata={"name": system.name},
    )

    return RedirectResponse(url=f"/systems/{system_id}", status_code=302)


@router.post("/{system_id}/delete")
async def delete_system(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    result = await db.execute(
        select(System).where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    system_name = system.name

    # Log before deletion
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.SYSTEM_DELETE,
        target_type="system",
        target_id=system_id,
        metadata={"name": system_name},
    )

    await db.delete(system)
    await db.flush()

    return RedirectResponse(url="/", status_code=302)
