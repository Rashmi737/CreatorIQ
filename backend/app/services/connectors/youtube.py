import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.connectors.base import SocialConnector


def parse_iso8601_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration (e.g. PT1M30S, PT45S) into total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


class YouTubeConnector(SocialConnector):
    platform = "youtube"
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"

    @property
    def client_id(self) -> str:
        return self.settings.google_client_id or self.settings.google_auth_client_id

    @property
    def client_secret(self) -> str:
        return self.settings.google_client_secret or self.settings.google_auth_client_secret

    @property
    def redirect_uri(self) -> str:
        return self.settings.google_redirect_uri or "http://localhost:8000/api/auth/youtube/callback"

    def authorization_params(self, state: str) -> dict[str, str]:
        return {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/userinfo.profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }

    def token_params(self, code: str) -> dict[str, str]:
        return {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

    async def fetch_channel_details(self, access_token: str) -> dict[str, Any]:
        """Fetch YouTube channel snippet, statistics, and contentDetails for the authenticated user."""
        if not self.credentials_configured or access_token.startswith("synthetic-"):
            return {
                "channel_id": "demo-youtube",
                "title": "Demo YouTube Channel",
                "thumbnail_url": "",
                "subscribers_count": 18400,
                "total_views": 342000,
                "video_count": 12,
                "uploads_playlist_id": "UU_demo_uploads",
            }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet,statistics,contentDetails", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            if not items:
                raise ValueError("No YouTube channel found for authenticated Google account")

            channel = items[0]
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            content_details = channel.get("contentDetails", {})
            thumbnails = snippet.get("thumbnails", {})

            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )
            uploads_playlist_id = (
                content_details.get("relatedPlaylists", {}).get("uploads")
            )

            return {
                "channel_id": channel.get("id"),
                "title": snippet.get("title", "My YouTube Channel"),
                "thumbnail_url": thumbnail_url,
                "subscribers_count": int(statistics.get("subscriberCount", 0)),
                "total_views": int(statistics.get("viewCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "uploads_playlist_id": uploads_playlist_id,
            }

    async def fetch_recent_videos(
        self, access_token: str, uploads_playlist_id: str | None, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch recent videos published by the channel using playlistItems and videos endpoints."""
        if not self.credentials_configured or access_token.startswith("synthetic-") or not uploads_playlist_id:
            mock_data = synthetic_youtube_metrics()
            return mock_data.get("content", [])

        async with httpx.AsyncClient(timeout=25) as client:
            # Step 1: Query playlistItems to retrieve recent video IDs from uploads playlist
            playlist_response = await client.get(
                "https://www.googleapis.com/youtube/v3/playlistItems",
                params={
                    "part": "snippet,contentDetails",
                    "playlistId": uploads_playlist_id,
                    "maxResults": min(max_results, 50),
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            playlist_response.raise_for_status()
            playlist_items = playlist_response.json().get("items", [])

            video_ids = [
                item.get("contentDetails", {}).get("videoId")
                for item in playlist_items
                if item.get("contentDetails", {}).get("videoId")
            ]

            if not video_ids:
                return []

            # Step 2: Query videos endpoint with batch IDs to get full stats and details
            video_response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids[:50]),
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            video_response.raise_for_status()
            video_items = video_response.json().get("items", [])

            results: list[dict[str, Any]] = []
            for item in video_items:
                v_id = item.get("id")
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                c_details = item.get("contentDetails", {})
                thumbnails = snippet.get("thumbnails", {})

                title = snippet.get("title", "Untitled Video")
                description = snippet.get("description", "")
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                shares = 0

                duration_secs = parse_iso8601_duration(c_details.get("duration", ""))
                is_short = (
                    (0 < duration_secs <= 60)
                    or ("#shorts" in title.lower())
                    or ("#shorts" in description.lower())
                )
                content_type = "Short" if is_short else "Video"

                thumb = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                )

                published_at_str = snippet.get("publishedAt")
                published_at = None
                if published_at_str:
                    try:
                        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    except Exception:
                        published_at = None

                engagement_rate = round(((likes + comments) / views * 100), 1) if views > 0 else 0.0

                results.append({
                    "id": v_id,
                    "title": title,
                    "description": description,
                    "content_type": content_type,
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "thumbnail_url": thumb,
                    "published_at": published_at,
                    "status": "Published",
                    "engagement_rate": engagement_rate,
                })

            return results

    async def fetch_metrics(self, access_token: str, platform_user_id: str | None = None) -> dict[str, Any]:
        if not self.credentials_configured or access_token.startswith("synthetic-"):
            return synthetic_youtube_metrics()

        channel = await self.fetch_channel_details(access_token)
        videos = await self.fetch_recent_videos(access_token, channel.get("uploads_playlist_id"))
        return {
            "platform": self.platform,
            "channel": channel,
            "content": videos,
        }


def synthetic_youtube_metrics() -> dict[str, Any]:
    return {
        "platform": "youtube",
        "channel": {
            "id": "demo-youtube",
            "title": "Demo YouTube Channel",
            "subscribers": 18400,
            "views": 342000,
        },
        "content": [
            {
                "id": "yt-demo-1",
                "title": "Behind the scenes",
                "type": "Short",
                "views": 34000,
                "likes": 3020,
                "comments": 284,
                "shares": 410,
                "reach": 34000,
                "status": "Published",
                "engagement_rate": 9.1,
            },
            {
                "id": "yt-demo-2",
                "title": "Creator workflow",
                "type": "Video",
                "views": 27600,
                "likes": 2310,
                "comments": 190,
                "shares": 280,
                "reach": 27600,
                "status": "Published",
                "engagement_rate": 8.6,
            },
            {
                "id": "yt-demo-3",
                "title": "Brand partnership recap",
                "type": "Video",
                "views": 40200,
                "likes": 3890,
                "comments": 310,
                "shares": 520,
                "reach": 40200,
                "status": "Published",
                "engagement_rate": 10.4,
            },
        ],
        "audience": {
            "age": [
                {"age": "18-24", "female": 28, "male": 22},
                {"age": "25-34", "female": 19, "male": 11},
            ],
            "countries": [
                {"country": "United States", "value": 38},
                {"country": "United Kingdom", "value": 23},
            ],
        },
    }
