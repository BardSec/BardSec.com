"""Authentication routes for Microsoft Entra ID OIDC."""
import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.auth.oidc import oauth, get_or_create_user
from app.auth.session import create_session, clear_session, get_session
from app.models.audit import log_action, AuditAction

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login(request: Request):
    """Redirect to Microsoft Entra ID login."""
    # Generate state and nonce for security
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    # Store in session for validation
    request.session["oauth_state"] = state
    request.session["oauth_nonce"] = nonce

    redirect_uri = settings.redirect_uri
    return await oauth.entra.authorize_redirect(
        request,
        redirect_uri,
        state=state,
        nonce=nonce,
    )


@router.get("/callback")
async def callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle OIDC callback from Microsoft Entra ID."""
    try:
        # Verify state
        state = request.query_params.get("state")
        stored_state = request.session.get("oauth_state")
        if not state or state != stored_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange code for tokens
        token = await oauth.entra.authorize_access_token(request)

        # Validate ID token and extract claims
        # authlib handles signature verification, issuer, audience, exp
        user_info = token.get("userinfo")
        if not user_info:
            # Fallback to parsing id_token
            id_token = token.get("id_token")
            if not id_token:
                raise HTTPException(status_code=400, detail="No ID token received")
            user_info = await oauth.entra.parse_id_token(token, nonce=request.session.get("oauth_nonce"))

        # Extract user info
        entra_oid = user_info.get("oid") or user_info.get("sub")
        email = user_info.get("email") or user_info.get("preferred_username")
        display_name = user_info.get("name") or email

        if not entra_oid or not email:
            raise HTTPException(status_code=400, detail="Missing required claims")

        # Get group claims (if configured in Entra app)
        groups = user_info.get("groups", [])

        # Get or create user in database
        user = await get_or_create_user(
            db=db,
            entra_oid=entra_oid,
            email=email,
            display_name=display_name,
            groups=groups,
        )

        # Create session
        response = RedirectResponse(url="/", status_code=302)
        create_session(
            response=response,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            entra_oid=user.entra_oid,
        )

        # Log login
        await log_action(
            session=db,
            user_id=user.id,
            action=AuditAction.USER_LOGIN,
            metadata={"email": email},
        )

        # Clear temporary session data
        request.session.pop("oauth_state", None)
        request.session.pop("oauth_nonce", None)

        return response

    except Exception as e:
        # Log error and redirect to login with error message
        print(f"Auth callback error: {e}")
        return RedirectResponse(url="/auth/login?error=auth_failed", status_code=302)


@router.get("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Log out user and clear session."""
    user = get_session(request)

    response = RedirectResponse(url="/auth/login", status_code=302)
    clear_session(response)

    if user:
        await log_action(
            session=db,
            user_id=user.user_id,
            action=AuditAction.USER_LOGOUT,
        )

    # Optionally redirect to Entra logout endpoint
    # entra_logout_url = f"{settings.entra_authority}/oauth2/v2.0/logout?post_logout_redirect_uri={settings.base_url}/auth/login"
    # return RedirectResponse(url=entra_logout_url)

    return response


@router.get("/me")
async def me(request: Request):
    """Get current user info."""
    user = get_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role.value,
    }
