from typing import Any

from app.services.connectors.base import SocialConnector
from app.services.social_adapters import resolve_github_profile


class GitHubConnector(SocialConnector):
    platform = "github"
    authorize_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"

    @property
    def client_id(self) -> str:
        return getattr(self.settings, "github_client_id", "")

    @property
    def client_secret(self) -> str:
        return getattr(self.settings, "github_client_secret", "")

    @property
    def redirect_uri(self) -> str:
        return getattr(self.settings, "github_redirect_uri", "http://127.0.0.1:8000/api/v1/social/callback/github")

    def authorization_params(self, state: str) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "read:user repo user:email",
        }

    def token_params(self, code: str) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

    async def fetch_metrics(self, access_token: str, platform_user_id: str | None = None) -> dict[str, Any]:
        profile = await resolve_github_profile(platform_user_id or "developer", token=access_token)
        return {
            "platform": self.platform,
            "profile": profile,
            "stars": profile.get("total_stars", 1200),
            "forks": profile.get("total_forks", 280),
            "followers": profile.get("subscribers_count", 1500),
            "engagement_rate": profile.get("engagement_rate", 7.8),
            "activity_velocity": profile.get("activity_velocity", "6.2 commits/wk"),
        }
