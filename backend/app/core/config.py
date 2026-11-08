from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Explicitly load .env using python-dotenv from root, backend, and current directory
for env_path in [PROJECT_ROOT / ".env", BACKEND_DIR / ".env", Path(".env")]:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)


class Settings(BaseSettings):
    app_name: str = "CreatorIQ API"
    environment: str = "development"
    database_url: str = "sqlite:///./creatoriq.db"
    mongo_url: str = "mongodb://creatoriq:creatoriq@localhost:27017"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    jwt_secret: str = "change-me-in-development"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    # Google OAuth 2.0 Configuration
    google_auth_client_id: str = ""
    google_auth_client_secret: str = ""
    google_auth_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    # Fallback to older variable names for backward compatibility
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/social/callback/youtube"
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://127.0.0.1:8000/api/v1/social/callback/instagram"
    tiktok_client_id: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8000/api/v1/social/callback/tiktok"
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_redirect_uri: str = "http://localhost:8000/api/v1/social/callback/facebook"
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://127.0.0.1:8000/api/v1/social/callback/linkedin"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://127.0.0.1:8000/api/v1/social/callback/github"
    # YouTube Data API v3 Direct Key Configuration
    youtube_api_key: str = ""
    youtube_channel_handle: str = "GoogleDevelopers"
    frontend_url: str = "http://localhost:5173"

    # Live Multi-Platform REST & Graph API Credentials
    github_token: str | None = None
    instagram_access_token: str | None = None
    instagram_account_id: str | None = None
    instagram_business_account_id: str | None = None
    linkedin_access_token: str | None = None
    rapidapi_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=[str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def google_client_id_effective(self) -> str:
        """Return Google client ID, preferring new config over fallback."""
        return self.google_auth_client_id or self.google_client_id

    @property
    def google_client_secret_effective(self) -> str:
        """Return Google client secret, preferring new config over fallback."""
        return self.google_auth_client_secret or self.google_client_secret

    @property
    def google_redirect_uri_effective(self) -> str:
        """Return Google redirect URI, preferring new config."""
        return self.google_auth_redirect_uri

    @property
    def instagram_account_id_effective(self) -> str:
        """Return Instagram Business/Creator Account ID, preferring new config."""
        return self.instagram_account_id or self.instagram_business_account_id or ""



@lru_cache
def get_settings() -> Settings:
    return Settings()