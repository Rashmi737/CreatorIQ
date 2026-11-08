import pytest
from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from app.services.youtube_api_service import fetch_youtube_channel_and_videos, sync_youtube_channel_for_user
from fastapi.testclient import TestClient
from main import app


@pytest.mark.anyio
async def test_youtube_api_key_fetcher():
    data = await fetch_youtube_channel_and_videos(
        api_key="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",
        channel_handle="GoogleDevelopers",
    )
    assert "channel" in data
    assert "videos" in data
    channel = data["channel"]
    assert channel["subscribers_count"] > 0
    assert channel["total_views"] > 0
    videos = data["videos"]
    assert len(videos) == 10
    assert videos[0]["views"] > 0
    assert videos[0]["likes"] > 0


def test_youtube_api_key_sync_and_analytics():
    db = SessionLocal()
    org = db.get(Organization, "org-apikey-test")
    if not org:
        db.add(Organization(id="org-apikey-test", name="API Key Org"))
    user = db.get(User, "user-apikey-test")
    if not user:
        user = User(
            id="user-apikey-test",
            organization_id="org-apikey-test",
            email="apikeytest@example.com",
            display_name="API Key Creator",
            password_hash=hash_password("Pass123!"),
            role="creator",
        )
        db.add(user)
    db.query(SocialContent).filter_by(user_id="user-apikey-test").delete()
    db.query(PlatformAccount).filter_by(user_id="user-apikey-test").delete()
    db.commit()
    db.close()

    client = TestClient(app)
    auth_token = create_access_token("user-apikey-test", "org-apikey-test", "creator")

    # Connect via YouTube endpoint (triggers API key sync)
    connect_res = client.post(
        "/api/v1/social/connect/youtube",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert connect_res.status_code == 200
    assert connect_res.json()["platform"] == "youtube"

    # Verify content endpoint returns the 10 videos
    content_res = client.get(
        "/api/v1/analytics/content",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert content_res.status_code == 200
    items = content_res.json()["items"]
    assert len(items) >= 10
    assert items[0]["views"] > 0

    # Verify overview endpoint returns real metrics
    overview_res = client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert overview_res.status_code == 200
    kpis = overview_res.json()["kpis"]
    assert kpis["reach"] >= 1000000
    assert kpis["audience_growth"] >= 2000000
