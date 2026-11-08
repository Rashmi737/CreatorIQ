from datetime import datetime, timezone
from typing import Annotated
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_token, oauth2_scheme, require_roles
from app.core.config import get_settings
from app.db import get_db
from app.db import redis
from app.models import Organization, User
from app.schemas import AuthResponse, UserCreate, UserResponse, Token
from app.security import create_access_token, hash_password, verify_password
from app.services.oauth import GoogleOAuthService

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "creatoriq-api"}


@router.get("/ready")
def ready(database: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    database.execute(select(1))
    return {"status": "ready"}


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, database: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    email = payload.email.strip().lower()
    existing = database.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    organization = Organization(name=f"{payload.display_name}'s workspace")
    user = User(
        organization=organization,
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return AuthResponse(
        access_token=create_access_token(user.id, user.organization_id, user.role),
        user=user,
    )


@router.post("/auth/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    database: Annotated[Session, Depends(get_db)],
) -> Token:
    settings = get_settings()
    email = form.username.strip().lower()
    user = database.scalar(select(User).where(User.email == email))

    if user is None:
        if settings.environment == "development":
            # Auto-provision user in development mode for seamless testing and smooth login
            display_name = email.split("@")[0].replace(".", " ").title() or "Creator"
            organization = Organization(name=f"{display_name}'s workspace")
            user = User(
                organization=organization,
                email=email,
                display_name=display_name,
                password_hash=hash_password(form.password),
                role="creator",
            )
            database.add(user)
            database.commit()
            database.refresh(user)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    elif not verify_password(form.password, user.password_hash):
        if settings.environment == "development":
            # In development mode, allow smooth login by updating password hash
            user.password_hash = hash_password(form.password)
            database.commit()
            database.refresh(user)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return Token(access_token=create_access_token(user.id, user.organization_id, user.role))



@router.post("/auth/logout")
async def logout(token: Annotated[str, Depends(get_token)]) -> dict[str, str]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"verify_exp": False})
    token_id = payload.get("jti")
    expires_at = payload.get("exp")
    if token_id and expires_at and redis.redis_client is not None:
        ttl = max(1, int(expires_at - datetime.now(timezone.utc).timestamp()))
        try:
            await redis.blacklist_token(token_id, ttl)
        except Exception:
            if settings.environment != "development":
                raise HTTPException(status_code=503, detail="Session service unavailable") from None
    return {"message": "Signed out"}


@router.get("/auth/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.get("/admin/ping")
def admin_ping(user: Annotated[User, Depends(require_roles("administrator"))]) -> dict[str, str]:
    return {"message": f"Administrator access confirmed for {user.display_name}"}


# ============================================================================
# Google OAuth 2.0 Endpoints
# ============================================================================


@router.get("/auth/google")
def initiate_google_login(settings: Annotated[dict, Depends(lambda: get_settings())]) -> dict[str, str]:
    """
    Initiate Google OAuth 2.0 login flow.
    
    Returns a JSON response with the authorization URL that the frontend 
    should redirect the user to.
    
    Response:
        {"url": "https://accounts.google.com/o/oauth2/v2/auth?..."}
    """
    if not settings.google_client_id_effective:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured"
        )
    
    authorization_url, state = GoogleOAuthService.generate_authorization_url()
    
    return {
        "url": authorization_url,
        "state": state,
    }


@router.get("/auth/google/callback")
async def handle_google_callback(
    code: str,
    state: str,
    database: Annotated[Session, Depends(get_db)],
) -> RedirectResponse:
    """
    Handle Google OAuth 2.0 callback.
    
    This endpoint is called by Google's OAuth servers after the user 
    authenticates. It exchanges the authorization code for an access token,
    fetches user information, provisions/logs in the user, and redirects
    to the frontend with a JWT token in the URL.
    
    Query Parameters:
        code: Authorization code from Google
        state: State token for CSRF validation
    
    Redirect:
        - New users: /welcome?token=<JWT_TOKEN>
        - Existing users: /dashboard?token=<JWT_TOKEN>
    """
    settings = get_settings()
    
    if not settings.google_client_id_effective or not settings.google_client_secret_effective:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured"
        )
    
    try:
        # Handle OAuth callback and get user info
        user_info = await GoogleOAuthService.handle_callback(code, state)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to authenticate with Google"
        ) from error
    
    google_id = user_info["google_id"]
    email = user_info["email"].lower().strip()
    display_name = user_info["display_name"]
    avatar_url = user_info.get("avatar_url")
    
    # Check if user already exists by email or google_id
    existing_user = database.scalar(
        select(User).where(
            (User.email == email) | (User.google_id == google_id)
        )
    )
    
    is_new_user = existing_user is None
    
    if existing_user:
        # Update existing user's Google info
        user = existing_user
        if not user.google_id:
            user.google_id = google_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        user.email_verified = True
        database.commit()
        database.refresh(user)
    else:
        # Create new user
        organization = Organization(name=f"{display_name}'s workspace")
        user = User(
            organization=organization,
            email=email,
            display_name=display_name,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # Random password for OAuth users
            google_id=google_id,
            avatar_url=avatar_url,
            email_verified=True,  # Mark email as verified for OAuth users
        )
        database.add(user)
        database.commit()
        database.refresh(user)
    
    # Generate JWT token
    access_token = create_access_token(user.id, user.organization_id, user.role)
    
    # Determine redirect URL based on whether user is new
    redirect_path = "/welcome" if is_new_user else "/dashboard"
    redirect_url = f"{settings.frontend_url}{redirect_path}?token={access_token}"
    
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)