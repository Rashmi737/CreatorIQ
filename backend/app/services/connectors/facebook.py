from typing import Any

from app.services.connectors.base import SocialConnector


class FacebookConnector(SocialConnector):
    platform = "facebook"
    authorize_url = "https://www.facebook.com/v18.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"

    @property
    def client_id(self) -> str:
        return self.settings.facebook_app_id or ""

    @property
    def client_secret(self) -> str:
        return self.settings.facebook_app_secret or ""

    @property
    def redirect_uri(self) -> str:
        return self.settings.facebook_redirect_uri or "http://localhost:8000/api/v1/social/callback/facebook"

    def authorization_params(self, state: str) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "pages_read_engagement,pages_read_user_content,pages_manage_posts",
            "state": state,
            "response_type": "code",
        }

    def token_params(self, code: str) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

    async def fetch_metrics(self, access_token: str, platform_user_id: str | None = None) -> dict[str, Any]:
        if not self.credentials_configured:
            return self._mock_metrics()
        # In production: fetch from Facebook Graph API
        return self._mock_metrics()

    def _mock_metrics(self) -> dict[str, Any]:
        return {
            "page": {
                "id": "demo-facebook",
                "name": "Demo Creator Page",
                "followers": 42300,
                "description": "Creator content for demo purposes",
                "category": "Creator",
            },
            "posts": [
                {
                    "id": "fb-1",
                    "message": "New content drop",
                    "type": "video",
                    "created_time": "2024-01-14T10:00:00+0000",
                    "shares": 120,
                    "likes": 3450,
                    "comments": 280,
                    "reach": 12340,
                    "impressions": 18900,
                },
                {
                    "id": "fb-2",
                    "message": "Behind the scenes",
                    "type": "photo",
                    "created_time": "2024-01-13T14:30:00+0000",
                    "shares": 85,
                    "likes": 2890,
                    "comments": 210,
                    "reach": 9870,
                    "impressions": 15600,
                },
                {
                    "id": "fb-3",
                    "message": "Q&A session",
                    "type": "video",
                    "created_time": "2024-01-12T11:00:00+0000",
                    "shares": 210,
                    "likes": 5670,
                    "comments": 450,
                    "reach": 18200,
                    "impressions": 28300,
                },
            ],
            "insights": {
                "page_fans": 42300,
                "page_fan_adds": 320,
                "page_impressions": 450000,
                "page_post_engagements": 42300,
                "avg_engagement_rate": 9.4,
            },
        }
