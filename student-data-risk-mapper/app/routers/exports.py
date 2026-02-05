"""Export routes for PDF and CSV."""
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.session import get_session
from app.models.system import System
from app.models.user import UserRole
from app.models.audit import log_action, AuditAction
from app.services.pdf_generator import generate_system_pdf
from app.services.csv_export import generate_systems_csv

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/pdf/{system_id}")
async def export_system_pdf(
    request: Request,
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate and download PDF report for a system."""
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Get system with assessment
    result = await db.execute(
        select(System)
        .options(selectinload(System.assessments))
        .where(System.id == system_id)
    )
    system = result.scalar_one_or_none()

    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    assessment = system.current_assessment
    if not assessment:
        raise HTTPException(
            status_code=400,
            detail="No assessment available for this system"
        )

    # Generate PDF
    pdf_bytes = generate_system_pdf(system, assessment)

    # Log export
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.EXPORT_PDF,
        target_type="system",
        target_id=system_id,
        metadata={"system_name": system.name},
    )

    # Return PDF response
    filename = f"risk-assessment-{system.name.lower().replace(' ', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/csv")
async def export_systems_csv(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Export all systems inventory as CSV.

    Admin only - contains full inventory data.
    """
    user = get_session(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Check admin permission
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="CSV export requires admin access"
        )

    # Get all systems
    result = await db.execute(
        select(System)
        .options(selectinload(System.assessments))
        .order_by(System.name)
    )
    systems = result.scalars().all()

    # Generate CSV
    csv_bytes = generate_systems_csv(systems)

    # Log export
    await log_action(
        session=db,
        user_id=user.user_id,
        action=AuditAction.EXPORT_CSV,
        metadata={"system_count": len(systems)},
    )

    # Return CSV response
    from datetime import datetime
    date_str = datetime.utcnow().strftime("%Y%m%d")
    filename = f"student-data-inventory-{date_str}.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
