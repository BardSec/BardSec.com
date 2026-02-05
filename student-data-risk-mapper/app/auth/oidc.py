"""OIDC authentication with Microsoft Entra ID."""
from functools import wraps
from typing import Optional, Callable
from uuid import UUID
from authlib.integrations.starlette_client import OAuth
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.session import get_session, create_session, clear_session
from app.schemas.user import UserSession

settings = get_settings()

# Configure OAuth client
oauth = OAuth()

oauth.register(
    name="entra",
    client_id=settings.entra_client_id,
    client_secret=settings.entra_client_secret,
    server_metadata_url=settings.entra_openid_config_url,
    client_kwargs={
        "scope": "openid email profile",
        # Request group claims for role mapping
        "response_type": "code",
    },
)


def determine_role_from_groups(groups: list[str]) -> UserRole:
    """Determine user role based on Entra group membership."""
    if settings.entra_admin_group_id and settings.entra_admin_group_id in groups:
        return UserRole.ADMIN
    if settings.entra_auditor_group_id and settings.entra_auditor_group_id in groups:
        return UserRole.AUDITOR
    return UserRole.USER


async def get_or_create_user(
    db: AsyncSession,
    entra_oid: str,
    email: str,
    display_name: str,
    groups: list[str],
) -> User:
    """Get existing user or create new one based on Entra ID."""
    result = await db.execute(
        select(User).where(User.entra_oid == entra_oid)
    )
    user = result.scalar_one_or_none()

    role = determine_role_from_groups(groups)

    if user:
        # Update user info on each login
        user.email = email
        user.display_name = display_name
        user.role = role
        from datetime import datetime
        user.last_login = datetime.utcnow()
    else:
        # Create new user
        from datetime import datetime
        user = User(
            entra_oid=entra_oid,
            email=email,
            display_name=display_name,
            role=role,
            last_login=datetime.utcnow(),
        )
        db.add(user)

    await db.flush()
    await db.refresh(user)
    return user


async def get_current_user(request: Request) -> Optional[UserSession]:
    """Get current user from session cookie."""
    return get_session(request)


async def get_current_user_required(request: Request) -> UserSession:
    """Get current user, raising exception if not authenticated."""
    user = get_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a route."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_session(request)
        if not user:
            # Redirect to login for page requests
            if request.headers.get("accept", "").startswith("text/html"):
                return RedirectResponse(url="/auth/login", status_code=302)
            raise HTTPException(status_code=401, detail="Not authenticated")
        return await func(request, *args, **kwargs)
    return wrapper


def require_admin(func: Callable) -> Callable:
    """Decorator to require admin role."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_session(request)
        if not user:
            if request.headers.get("accept", "").startswith("text/html"):
                return RedirectResponse(url="/auth/login", status_code=302)
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin access required")
        return await func(request, *args, **kwargs)
    return wrapper


def require_roles(*roles: UserRole) -> Callable:
    """Decorator factory to require specific roles."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = get_session(request)
            if not user:
                if request.headers.get("accept", "").startswith("text/html"):
                    return RedirectResponse(url="/auth/login", status_code=302)
                raise HTTPException(status_code=401, detail="Not authenticated")
            if user.role not in roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {', '.join(r.value for r in roles)}"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
