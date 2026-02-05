"""
Student Data Risk Mapper - Main Application

A privacy risk assessment tool for K-12 school districts to inventory
edtech systems and evaluate student data handling practices.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import engine
from app.routers import (
    auth_router,
    dashboard_router,
    systems_router,
    assessments_router,
    exports_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Student Data Risk Mapper",
    description="Privacy risk assessment tool for K-12 edtech systems",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="sdrm_oauth_session",
    max_age=3600,  # 1 hour for OAuth state
    same_site="lax",
    https_only=not settings.debug,
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(systems_router)
app.include_router(assessments_router)
app.include_router(exports_router)

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler."""
    if request.headers.get("accept", "").startswith("text/html"):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Page not found", "status_code": 404},
            status_code=404
        )
    return {"detail": "Not found"}


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 handler."""
    if request.headers.get("accept", "").startswith("text/html"):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Internal server error", "status_code": 500},
            status_code=500
        )
    return {"detail": "Internal server error"}
