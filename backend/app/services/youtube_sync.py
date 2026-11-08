from datetime import datetime, timedelta
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PlatformAccount, SocialContent
from app.services.connectors.youtube import YouTubeConnector

logger = logging.getLogger("creatoriq.youtube_sync")


async def sync_youtube_channel_and_videos(account: PlatformAccount, database: Session) -> dict[str, Any]:
    """
    Synchronize YouTube channel statistics and uploaded videos using the YouTube Data API v3.
    Upserts channel metrics into PlatformAccount and video items into SocialContent.
    """
    settings = get_settings()
    connector = YouTubeConnector(settings)

    # 1. Refresh access token if expired or about to expire
    if account.refresh_token and account.token_expires_at:
        if account.token_expires_at <= datetime.utcnow() + timedelta(minutes=5):
            try:
                refreshed = await connector.refresh_token(account.refresh_token)
                new_token = refreshed.get("access_token")
                expires_in = refreshed.get("expires_in", 3600)
                if new_token:
                    account.access_token = new_token
                    account.token_expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
                    database.commit()
            except Exception as exc:
                logger.warning("Failed to refresh YouTube access token: %s", exc)

    # 2. Fetch channel details
    channel_info = await connector.fetch_channel_details(account.access_token)

    # 3. Update PlatformAccount with channel metrics
    account.channel_title = channel_info.get("title") or account.channel_title
    account.avatar_url = channel_info.get("thumbnail_url") or account.avatar_url
    account.subscribers_count = int(channel_info.get("subscribers_count", 0))
    account.total_views = int(channel_info.get("total_views", 0))
    account.video_count = int(channel_info.get("video_count", 0))
    if channel_info.get("title"):
        account.platform_user_id = channel_info["title"]
    account.updated_at = datetime.utcnow()

    # 4. Fetch recent uploaded videos
    uploads_playlist_id = channel_info.get("uploads_playlist_id")
    videos = await connector.fetch_recent_videos(account.access_token, uploads_playlist_id)

    # 5. Upsert videos into SocialContent table
    synced_count = 0
    for video in videos:
        ext_id = str(video.get("id"))
        if not ext_id:
            continue

        existing = database.scalar(
            select(SocialContent).where(
                SocialContent.user_id == account.user_id,
                SocialContent.platform == "youtube",
                SocialContent.external_id == ext_id,
            )
        )

        views = int(video.get("views", 0))
        likes = int(video.get("likes", 0))
        comments = int(video.get("comments", 0))
        shares = int(video.get("shares", 0))
        engagement_rate = float(video.get("engagement_rate") or (round((likes + comments) / views * 100, 1) if views > 0 else 0.0))

        if existing:
            existing.platform_account_id = account.id
            existing.title = video.get("title", existing.title)
            existing.description = video.get("description", existing.description)
            existing.content_type = video.get("content_type", existing.content_type)
            existing.views = views
            existing.likes = likes
            existing.comments = comments
            existing.shares = shares
            existing.thumbnail_url = video.get("thumbnail_url") or existing.thumbnail_url
            if video.get("published_at"):
                existing.published_at = video["published_at"]
            existing.status = video.get("status", "Published")
            existing.engagement_rate = engagement_rate
            existing.updated_at = datetime.utcnow()
        else:
            new_item = SocialContent(
                user_id=account.user_id,
                platform_account_id=account.id,
                platform="youtube",
                external_id=ext_id,
                title=video.get("title", "Untitled Video"),
                description=video.get("description", ""),
                content_type=video.get("content_type", "Video"),
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                thumbnail_url=video.get("thumbnail_url"),
                published_at=video.get("published_at"),
                status=video.get("status", "Published"),
                engagement_rate=engagement_rate,
            )
            database.add(new_item)
        synced_count += 1

    database.commit()
    database.refresh(account)

    return {
        "account_id": account.id,
        "platform": "youtube",
        "channel": channel_info,
        "synced_videos_count": synced_count,
        "status": "completed",
    }
