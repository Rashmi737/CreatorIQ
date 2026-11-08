from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from main import app


@pytest.fixture
def test_user_and_auth():
    database = SessionLocal()
    org = database.get(Organization, "org-social-test")
    if not org:
        org = Organization(id="org-social-test", name="Social Hub Org")
        database.add(org)
    
    user = database.get(User, "user-social-test")
    if not user:
        user = User(
            id="user-social-test",
            organization_id="org-social-test",
            email="socialhub@example.com",
            display_name="Social Lead",
            password_hash=hash_password("SecurePass123!"),
            role="creator",
        )
        database.add(user)
    
    database.query(SocialContent).filter_by(user_id="user-social-test").delete()
    database.query(PlatformAccount).filter_by(user_id="user-social-test").delete()
    database.commit()
    database.close()

    token = create_access_token("user-social-test", "org-social-test", "creator")
    return {"user_id": "user-social-test", "org_id": "org-social-test", "token": token}


MOCK_LI_PROFILE = {
    "platform": "linkedin",
    "clean_handle": "rashmi-sharma",
    "handle": "in/rashmi-sharma",
    "channel_title": "Rashmi Sharma",
    "name": "Rashmi Sharma",
    "avatar_url": "https://media.licdn.com/mock.jpg",
    "subscribers_count": 5200,
    "followers": 5200,
    "total_views": 45000,
    "posts_count": 5,
    "video_count": 5,
    "engagement_rate": 3.8,
    "sample_items": [],
    "posts": [],
    "external_url": "https://www.linkedin.com/in/rashmi-sharma",
}

MOCK_IG_PROFILE = {
    "platform": "instagram",
    "clean_handle": "creatoriq_hub",
    "handle": "@creatoriq_hub",
    "channel_title": "CreatorIQ Hub",
    "name": "CreatorIQ Hub",
    "avatar_url": "https://scontent.cdninstagram.com/mock.jpg",
    "subscribers_count": 12000,
    "followers": 12000,
    "total_views": 85000,
    "media_count": 8,
    "video_count": 8,
    "engagement_rate": 4.2,
    "sample_items": [],
    "media": [],
    "external_url": "https://www.instagram.com/creatoriq_hub",
}

MOCK_FB_PROFILE = {
    "platform": "facebook",
    "clean_handle": "Meta",
    "handle": "Meta",
    "channel_title": "Meta",
    "name": "Meta",
    "avatar_url": "https://scontent.xx.fbcdn.net/mock.jpg",
    "subscribers_count": 106000000,
    "followers": 106000000,
    "likes_count": 100000000,
    "talking_about_count": 50000,
    "total_views": 100000000,
    "posts_count": 1,
    "video_count": 1,
    "engagement_rate": 0.05,
    "sample_items": [],
    "posts": [],
    "external_url": "https://www.facebook.com/Meta",
}


MOCK_GITHUB_PROFILE = {
    "platform": "github",
    "clean_handle": "torvalds",
    "handle": "@torvalds",
    "channel_title": "Linus Torvalds",
    "name": "Linus Torvalds",
    "avatar_url": "https://avatars.githubusercontent.com/u/1024025?v=4",
    "followers": 210000,
    "subscribers_count": 210000,
    "public_repos": 8,
    "video_count": 8,
    "total_stars": 195000,
    "total_views": 195000,
    "engagement_rate": 8.4,
    "sample_items": [
        {
            "external_id": "gh_linux",
            "title": "linux",
            "views": 0,
            "likes": 178000,
            "comments": 52000,
            "shares": 0,
            "engagement_rate": 8.4,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    ],
    "repos": [],
    "external_url": "https://github.com/torvalds",
    "ingestion_mode": "live_api",
}


@patch("app.services.social_adapters.resolve_github_profile", new_callable=lambda: AsyncMock(return_value=MOCK_GITHUB_PROFILE))
@patch("app.services.social_adapters.resolve_facebook_profile", new_callable=lambda: AsyncMock(return_value=MOCK_FB_PROFILE))
@patch("app.services.social_adapters.resolve_instagram_profile", new_callable=lambda: AsyncMock(return_value=MOCK_IG_PROFILE))
@patch("app.services.social_adapters.resolve_linkedin_profile", new_callable=lambda: AsyncMock(return_value=MOCK_LI_PROFILE))
def test_multi_platform_social_hub(mock_li, mock_ig, mock_fb, mock_gh, test_user_and_auth):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_user_and_auth['token']}"}

    # 1. Connect GitHub profile
    res_gh = client.post("/api/v1/social/connect/github?handle=torvalds", headers=headers)
    assert res_gh.status_code == 200, res_gh.text
    gh_data = res_gh.json()
    assert gh_data["platform"] == "github"
    assert "torvalds" in gh_data["handle"].lower()
    assert gh_data["sync_status"] == "active"
    assert gh_data["subscribers_count"] > 0
    assert "account_id" in gh_data
    gh_account_id = gh_data["account_id"]

    # 2. Connect LinkedIn profile
    res_li = client.post("/api/v1/social/connect/linkedin?handle=in/rashmi-sharma", headers=headers)
    assert res_li.status_code == 200, res_li.text
    li_data = res_li.json()
    assert li_data["platform"] == "linkedin"
    assert "in/" in li_data["handle"] or "rashmi" in li_data["handle"].lower()
    assert li_data["sync_status"] == "active"
    assert li_data["subscribers_count"] >= 5000
    li_account_id = li_data["account_id"]

    # 3. Connect Instagram profile
    res_ig = client.post("/api/v1/social/connect/instagram?handle=@creatoriq_hub", headers=headers)
    assert res_ig.status_code == 200, res_ig.text
    ig_data = res_ig.json()
    assert ig_data["platform"] == "instagram"
    assert "@" in ig_data["handle"]
    assert ig_data["sync_status"] == "active"
    assert ig_data["subscribers_count"] > 0
    ig_account_id = ig_data["account_id"]

    # 4. Connect YouTube channel (mock fallback/simulated)
    res_yt = client.post("/api/v1/social/connect/youtube?handle=@GoogleDevelopers", headers=headers)
    assert res_yt.status_code == 200, res_yt.text
    yt_data = res_yt.json()
    assert yt_data["platform"] == "youtube"
    assert yt_data["sync_status"] == "active"
    yt_account_id = yt_data["account_id"]

    # 4b. Connect Facebook page
    res_fb = client.post("/api/v1/social/connect/facebook?handle=Meta", headers=headers)
    assert res_fb.status_code == 200, res_fb.text
    fb_data = res_fb.json()
    assert fb_data["platform"] == "facebook"
    assert fb_data["sync_status"] == "active"
    assert fb_data["subscribers_count"] > 0

    # 5. Verify GET /api/v1/social/connected lists all 5 platforms
    res_connected = client.get("/api/v1/social/connected", headers=headers)
    assert res_connected.status_code == 200
    conn_data = res_connected.json()
    accounts = conn_data.get("accounts", [])
    assert len(accounts) >= 5
    
    platforms_present = {acc["platform"] for acc in accounts}
    assert {"github", "linkedin", "instagram", "youtube", "facebook"}.issubset(platforms_present)

    for acc in accounts:
        assert "handle" in acc
        assert "channel_title" in acc
        assert "subscribers_count" in acc
        assert "sync_status" in acc
        assert "last_synced_at" in acc

    # 6. Verify GET /api/v1/social/accounts alias matches
    res_accounts = client.get("/api/v1/social/accounts", headers=headers)
    assert res_accounts.status_code == 200
    assert len(res_accounts.json()["accounts"]) == len(accounts)

    # 7. Test pause / resume on GitHub account
    res_pause = client.post(f"/api/v1/social/pause/{gh_account_id}", headers=headers)
    assert res_pause.status_code == 200
    assert res_pause.json()["sync_status"] == "paused"

    # Verify pause state in /connected
    res_check = client.get("/api/v1/social/connected", headers=headers)
    gh_acc = next(a for a in res_check.json()["accounts"] if a["id"] == gh_account_id)
    assert gh_acc["sync_status"] == "paused"

    # Resume sync
    res_resume = client.post(f"/api/v1/social/pause/{gh_account_id}", headers=headers)
    assert res_resume.status_code == 200
    assert res_resume.json()["sync_status"] == "active"

    # 8. Test sync endpoint for LinkedIn
    res_sync = client.post(f"/api/v1/social/sync/{li_account_id}", headers=headers)
    assert res_sync.status_code == 200
    assert res_sync.json()["status"] == "completed"

    # 9. Test disconnect on Instagram account
    res_dc = client.post(f"/api/v1/social/disconnect/{ig_account_id}", headers=headers)
    assert res_dc.status_code == 200
    assert res_dc.json()["status"] == "disconnected"

    # Verify Instagram account is deleted
    res_after_dc = client.get("/api/v1/social/connected", headers=headers)
    remaining_ids = {a["id"] for a in res_after_dc.json()["accounts"]}
    assert ig_account_id not in remaining_ids


def test_unconfigured_credentials_raise_errors(test_user_and_auth):
    """Verify that absent credentials return fallback/404 for non-existent profiles."""
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_user_and_auth['token']}"}

    # 1. LinkedIn without token uses public web fallback; returns 404 for non-existent profile
    res_li = client.post("/api/v1/social/connect/linkedin?handle=in/this_user_definitely_does_not_exist_404_creatoriq", headers=headers)
    assert res_li.status_code == 404
    assert "not found" in res_li.json()["detail"].lower()

    # 2. Instagram without token uses public web fallback; returns 404 for non-existent profile
    res_ig = client.post("/api/v1/social/connect/instagram?handle=@this_user_definitely_does_not_exist_404_creatoriq", headers=headers)
    assert res_ig.status_code == 404
    assert "not found" in res_ig.json()["detail"].lower()

    # 3. GitHub with non-existent user raises 404 (or 403 if public unauthenticated IP rate limit is hit)
    res_gh = client.post("/api/v1/social/connect/github?handle=this_user_definitely_does_not_exist_404_creatoriq", headers=headers)
    assert res_gh.status_code in (404, 403)
    if res_gh.status_code == 404:
        assert "not found" in res_gh.json()["detail"].lower()
    else:
        assert "rate limit" in res_gh.json()["detail"].lower()

    # 4. Facebook with non-existent page raises 404
    res_fb = client.post("/api/v1/social/connect/facebook?handle=this_user_definitely_does_not_exist_404_creatoriq", headers=headers)
    assert res_fb.status_code == 404
    assert "not found" in res_fb.json()["detail"].lower()
