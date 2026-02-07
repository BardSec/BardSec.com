"""Session management using signed cookies."""
import json
from typing import Optional
from uuid import UUID
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Response

from app.config import get_settings
from app.models.user import UserRole
from app.schemas.user import UserSession

settings = get_settings()

# Session serializer with signing
_serializer = URLSafeTimedSerializer(settings.secret_key)

SESSION_COOKIE_NAME = "sdrm_session"
SESSION_MAX_AGE = 8 * 60 * 60  # 8 hours


def create_session(
    response: Response,
    user_id: UUID,
    email: str,
    display_name: str,
    role: UserRole,
    entra_oid: str,
) -> None:
    """Create a signed session cookie."""
    session_data = {
        "user_id": str(user_id),
        "email": email,
        "display_name": display_name,
        "role": role.value,
        "entra_oid": entra_oid,
    }
    signed_value = _serializer.dumps(session_data)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=not settings.debug,  # Secure in production
        samesite="lax",
    )


def get_session(request: Request) -> Optional[UserSession]:
    """Get and validate session from cookie."""
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_value:
        return None

    try:
        # Verify signature and check expiration
        session_data = _serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
        return UserSession(
            user_id=UUID(session_data["user_id"]),
            email=session_data["email"],
            display_name=session_data["display_name"],
            role=UserRole(session_data["role"]),
            entra_oid=session_data["entra_oid"],
        )
    except (BadSignature, SignatureExpired, KeyError, ValueError):
        return None


def clear_session(response: Response) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )
