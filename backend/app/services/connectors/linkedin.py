from typing import Any

from app.services.connectors.base import SocialConnector
from app.services.social_adapters import resolve_linkedin_profile


class LinkedInConnector(SocialConnector):
    platform = "linkedin"
    authorize_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    @property
    def client_id(self) -> str:
        return getattr(self.settings, "linkedin_client_id", "")

    @property
    def client_secret(self) -> str:
        return getattr(self.settings, "linkedin_client_secret", "")

    @property
    def redirect_uri(self) -> str:
        return getattr(self.settings, "linkedin_redirect_uri", "http://127.0.0.1:8000/api/v1/social/callback/linkedin")

    def authorization_params(self, state: str) -> dict[str, str]:
        return {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "r_liteprofile r_emailaddress w_member_social",
        }

    def token_params(self, code: str) -> dict[str, str]:
        return {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }

    async def fetch_metrics(self, access_token: str, platform_user_id: str | None = None) -> dict[str, Any]:
        profile = await resolve_linkedin_profile(platform_user_id or "creator", token=access_token)
        return {
            "platform": self.platform,
            "profile": profile,
            "connections": profile.get("subscribers_count", 5000),
            "impressions": profile.get("total_views", 50000),
            "engagement_rate": profile.get("engagement_rate", 5.2),
        }
