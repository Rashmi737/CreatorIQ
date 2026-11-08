from typing import Any

from app.services.connectors.base import SocialConnector


class TikTokConnector(SocialConnector):
    platform = "tiktok"
    authorize_url = "https://www.tiktok.com/v1/oauth/authorize"
    token_url = "https://open.tiktokapis.com/v1/oauth/token"

    @property
    def client_id(self) -> str:
        return self.settings.tiktok_client_id or ""

    @property
    def client_secret(self) -> str:
        return self.settings.tiktok_client_secret or ""

    @property
    def redirect_uri(self) -> str:
        return self.settings.tiktok_redirect_uri or "http://localhost:8000/api/v1/social/callback/tiktok"

    def authorization_params(self, state: str) -> dict[str, str]:
        return {
            "client_key": self.client_id,
            "response_type": "code",
            "scope": "user.info.basic,video.list",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

    def token_params(self, code: str) -> dict[str, str]:
        return {
            "client_key": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

    async def fetch_metrics(self, access_token: str, platform_user_id: str | None = None) -> dict[str, Any]:
        if not self.credentials_configured:
            return self._mock_metrics()
        # In production: fetch from TikTok API
        return self._mock_metrics()

    def _mock_metrics(self) -> dict[str, Any]:
        return {
            "user": {
                "id": "demo-tiktok",
                "username": "demo_tiktok_creator",
                "display_name": "Demo TikTok Creator",
                "follower_count": 85600,
                "following_count": 240,
                "video_count": 156,
                "heart_count": 2840000,
            },
            "videos": [
                {
                    "id": "tt-1",
                    "title": "Quick tutorial",
                    "views": 128900,
                    "likes": 9870,
                    "comments": 234,
                    "shares": 456,
                    "created_at": "2024-01-14T10:30:00Z",
                },
                {
                    "id": "tt-2",
                    "title": "Day in my life",
                    "views": 95600,
                    "likes": 7240,
                    "comments": 180,
                    "shares": 320,
                    "created_at": "2024-01-13T15:45:00Z",
                },
                {
                    "id": "tt-3",
                    "title": "Trending sounds",
                    "views": 156300,
                    "likes": 12450,
                    "comments": 310,
                    "shares": 680,
                    "created_at": "2024-01-12T09:20:00Z",
                },
            ],
            "stats": {
                "avg_engagement_rate": 8.2,
                "total_reach": 2450000,
                "avg_video_views": 126933,
            },
        }
