"""OAuth 2.0 services for third-party authentication."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.db import redis


class GoogleOAuthService:
    """Handle Google OAuth 2.0 flow."""

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    SCOPES = ["openid", "email", "profile"]
    STATE_CACHE_TTL = 600  # 10 minutes

    @classmethod
    def generate_authorization_url(cls) -> tuple[str, str]:
        """
        Generate Google OAuth authorization URL and return state token.
        
        Returns:
            (authorization_url, state_token)
        """
        settings = get_settings()
        state = secrets.token_urlsafe(32)
        
        # Store state in cache for CSRF validation
        if redis.redis_client is not None:
            try:
                import asyncio
                asyncio.run(redis.redis_client.setex(
                    f"oauth:state:{state}",
                    cls.STATE_CACHE_TTL,
                    "pending"
                ))
            except Exception:
                # Continue without state caching if Redis unavailable
                pass
        
        params = {
            "client_id": settings.google_client_id_effective,
            "redirect_uri": settings.google_redirect_uri_effective,
            "response_type": "code",
            "scope": " ".join(cls.SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        
        authorization_url = f"{cls.AUTHORIZATION_URL}?{urlencode(params)}"
        return authorization_url, state

    @classmethod
    async def validate_state(cls, state: str) -> bool:
        """Validate CSRF state token."""
        if not state:
            return False
        
        if redis.redis_client is None:
            # Without Redis, accept state (less secure but functional in dev)
            return True
        
        try:
            exists = await redis.redis_client.exists(f"oauth:state:{state}")
            if exists:
                await redis.redis_client.delete(f"oauth:state:{state}")
            return bool(exists)
        except Exception:
            return False

    @classmethod
    async def exchange_code_for_token(cls, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Google callback
            
        Returns:
            Token response from Google
        """
        settings = get_settings()
        
        payload = {
            "client_id": settings.google_client_id_effective,
            "client_secret": settings.google_client_secret_effective,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_redirect_uri_effective,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(cls.TOKEN_URL, data=payload)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def fetch_user_info(cls, access_token: str) -> dict[str, Any]:
        """
        Fetch user information from Google using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            User info dict with id, email, name, picture
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(cls.USERINFO_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            return {
                "google_id": data.get("id"),
                "email": data.get("email"),
                "display_name": data.get("name", data.get("email", "").split("@")[0]),
                "avatar_url": data.get("picture"),
            }

    @classmethod
    async def handle_callback(cls, code: str, state: str) -> dict[str, Any]:
        """
        Complete OAuth flow: validate state, exchange code, fetch user info.
        
        Args:
            code: Authorization code
            state: State token for CSRF validation
            
        Returns:
            User info dict
        """
        # Validate CSRF state
        if not await cls.validate_state(state):
            raise ValueError("Invalid or expired state token")
        
        # Exchange code for access token
        token_response = await cls.exchange_code_for_token(code)
        access_token = token_response.get("access_token")
        
        if not access_token:
            raise ValueError("Failed to obtain access token")
        
        # Fetch user information
        user_info = await cls.fetch_user_info(access_token)
        return user_info
