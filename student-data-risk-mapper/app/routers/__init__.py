"""API routers."""
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.systems import router as systems_router
from app.routers.assessments import router as assessments_router
from app.routers.exports import router as exports_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "systems_router",
    "assessments_router",
    "exports_router",
]
