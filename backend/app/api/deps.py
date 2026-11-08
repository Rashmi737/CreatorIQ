from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.db import redis
from app.models import User

# HTTPBearer security scheme allows pasting Bearer tokens directly into Swagger UI
http_bearer = HTTPBearer(auto_error=False)
oauth2_scheme = http_bearer


def get_token(
    request: Request,
    auth: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
) -> str:
    if auth and auth.credentials:
        return auth.credentials.strip().strip('"').strip("'")
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if header:
        if header.lower().startswith("bearer "):
            return header[7:].strip().strip('"').strip("'")
        return header.strip().strip('"').strip("'")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    database: Annotated[Session, Depends(get_db)],
) -> User:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except jwt.InvalidSignatureError:
            # Fallback for tokens issued with development secrets
            if settings.environment == "development" and settings.jwt_secret != "change-me-in-development":
                payload = jwt.decode(token, "change-me-in-development", algorithms=[settings.jwt_algorithm])
            elif settings.environment == "development" and settings.jwt_secret != "replace-with-a-long-random-secret":
                payload = jwt.decode(token, "replace-with-a-long-random-secret", algorithms=[settings.jwt_algorithm])
            else:
                raise

        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise credentials_error

        user_id = payload.get("sub")
        if not user_id:
            raise credentials_error

        token_id = payload.get("jti")
        if token_id and redis.redis_client is not None:
            try:
                if await redis.is_token_blacklisted(token_id):
                    raise credentials_error
            except Exception:
                if settings.environment != "development":
                    raise credentials_error from None
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise credentials_error from None

    user = database.get(User, str(user_id))
    if user is None:
        user = database.scalar(select(User).where(User.email == str(user_id).lower().strip()))
        if user is None:
            raise credentials_error
    return user


def require_roles(*roles: str):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency