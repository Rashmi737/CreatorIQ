from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from main import app


def setup_test_user():
    database = SessionLocal()
    if not database.get(Organization, 'org-yt-test'):
        database.add(Organization(id='org-yt-test', name='YouTube Test Org'))
    user = database.get(User, 'user-yt-test')
    if not user:
        user = User(
            id='user-yt-test',
            organization_id='org-yt-test',
            email='youtubetest@example.com',
            display_name='Tech Creator',
            password_hash=hash_password('Password123!'),
            role='creator',
        )
        database.add(user)
    database.query(SocialContent).filter_by(user_id='user-yt-test').delete()
    database.query(PlatformAccount).filter_by(user_id='user-yt-test').delete()
    database.commit()
    database.close()
    return 'user-yt-test', 'org-yt-test'


def test_youtube_oauth_callback_and_sync():
    user_id, org_id = setup_test_user()
    client = TestClient(app, follow_redirects=False)

    fake_token_data = {
        "access_token": "ya29.fake-token-test-123",
        "refresh_token": "1//fake-refresh-token",
        "expires_in": 3600,
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
    }
    fake_channel_data = {
        "channel_id": "UC1234567890",
        "title": "Tech With CreatorIQ",
        "thumbnail_url": "https://images.example.com/yt-avatar.jpg",
        "subscribers_count": 25400,
        "total_views": 850000,
        "video_count": 35,
        "uploads_playlist_id": "UU1234567890",
    }
    fake_videos = [
        {
            "id": "vid-001",
            "title": "FastAPI Full Tutorial 2026",
            "description": "Learn FastAPI #shorts",
            "content_type": "Short",
            "views": 45000,
            "likes": 3800,
            "comments": 420,
            "shares": 0,
            "thumbnail_url": "https://images.example.com/vid1.jpg",
            "published_at": datetime.utcnow() - timedelta(days=2),
            "status": "Published",
            "engagement_rate": 9.4,
        },
        {
            "id": "vid-002",
            "title": "React 19 Complete Architecture",
            "description": "Deep dive into React 19",
            "content_type": "Video",
            "views": 62000,
            "likes": 5100,
            "comments": 610,
            "shares": 0,
            "thumbnail_url": "https://images.example.com/vid2.jpg",
            "published_at": datetime.utcnow() - timedelta(days=5),
            "status": "Published",
            "engagement_rate": 9.2,
        },
    ]

    with patch("app.services.connectors.youtube.YouTubeConnector.exchange_code", new=AsyncMock(return_value=fake_token_data)), \
         patch("app.services.connectors.youtube.YouTubeConnector.fetch_channel_details", new=AsyncMock(return_value=fake_channel_data)), \
         patch("app.services.connectors.youtube.YouTubeConnector.fetch_recent_videos", new=AsyncMock(return_value=fake_videos)):

        from app.routers.social import make_state
        db_temp = SessionLocal()
        user_temp = db_temp.get(User, user_id)
        state_param = make_state(user_temp, "youtube")
        db_temp.close()

        # 1. Test OAuth callback handler
        response = client.get(f"/api/auth/youtube/callback?code=mock-google-code&state={state_param}")
        assert response.status_code in (302, 307)
        assert "/dashboard?connected=youtube" in response.headers["location"]

        # Verify platform account was stored with channel data
        db = SessionLocal()
        account = db.scalar(
            select(PlatformAccount).where(
                PlatformAccount.user_id == user_id,
                PlatformAccount.platform_name == "youtube",
            )
        )
        assert account is not None
        assert account.access_token == "ya29.fake-token-test-123"
        assert account.refresh_token == "1//fake-refresh-token"
        assert account.channel_title == "Tech With CreatorIQ"
        assert account.subscribers_count == 25400
        assert account.total_views == 850000

        # Verify videos were upserted into SocialContent
        contents = db.scalars(
            select(SocialContent).where(SocialContent.user_id == user_id)
        ).all()
        assert len(contents) >= 2
        db.close()

        # 2. Test Sync endpoint
        auth_token = create_access_token(user_id, org_id, "creator")
        sync_res = client.post(
            "/api/v1/social/sync/youtube",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert sync_res.status_code == 200
        sync_json = sync_res.json()
        assert sync_json["status"] == "completed"
        assert sync_json["synced_videos_count"] >= 2

        # 3. Test Analytics Content endpoint serves real YouTube videos
        content_res = client.get(
            "/api/v1/analytics/content",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert content_res.status_code == 200
        items = content_res.json()["items"]
        assert len(items) >= 2
        assert items[0]["platform"] == "Youtube"

        # 4. Test Analytics Overview serves real KPIs and content
        overview_res = client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert overview_res.status_code == 200
        overview_json = overview_res.json()
        assert overview_json["kpis"]["reach"] >= 850000
        assert overview_json["kpis"]["audience_growth"] >= 25400
        assert len(overview_json["content"]) >= 2

        # 5. Test Compare Content endpoint
        compare_res = client.get(
            "/api/v1/analytics/content/compare?id1=vid-001&id2=vid-002",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert compare_res.status_code == 200
        compare_json = compare_res.json()
        assert "winner" in compare_json or "metrics" in compare_json or "comparison" in compare_json or "summary" in compare_json
