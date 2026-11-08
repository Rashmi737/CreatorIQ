import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, User
from app.security import create_access_token, hash_password
from app.services.social_adapters import clean_handle, resolve_twitter_profile
from main import app


def test_clean_handle_twitter() -> None:
    assert clean_handle("@elonmusk", "twitter") == "elonmusk"
    assert clean_handle("https://twitter.com/jack", "twitter") == "jack"
    assert clean_handle("https://x.com/OpenAI/", "twitter") == "OpenAI"
    assert clean_handle("x.com/Google", "x") == "Google"
    assert clean_handle("", "twitter") == "elonmusk"
    assert clean_handle(None, "x") == "elonmusk"


def test_resolve_twitter_profile_success() -> None:
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="Elon Musk (@elonmusk) on X">
        <meta property="og:description" content="Technoking of Tesla">
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/123/avatar.jpg">
    </head>
    <body>
        <script>
            window.__INITIAL_STATE__ = {
                followers: 241000000,
                following: 1400,
                tweets: 109000,
                name: "Elon Musk",
                location: "Mars",
                is_blue_verified: !0
            };
        </script>
        <img src="https://pbs.twimg.com/profile_banners/44196397/1774145451" />
    </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        profile = asyncio.run(resolve_twitter_profile("elonmusk"))

        assert profile["platform"] == "twitter"
        assert profile["clean_handle"] == "elonmusk"
        assert profile["handle"] == "@elonmusk"
        assert profile["name"] == "Elon Musk"
        assert profile["subscribers_count"] == 241000000
        assert profile["followers"] == 241000000
        assert profile["following"] == 1400
        assert profile["tweets_count"] == 109000
        assert profile["posts_count"] == 109000
        assert profile["avatar_url"] == "https://pbs.twimg.com/profile_images/123/avatar.jpg"
        assert "1774145451" in profile["banner_url"]
        assert profile["location"] == "Mars"
        assert profile["is_verified"] is True
        assert profile["ingestion_mode"] == "public_web"
        # Zero-Mock Rule: private metrics must strictly be 0
        assert profile["total_views"] == 0
        assert profile["engagement_rate"] == 0.0


def test_resolve_twitter_profile_not_found() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not found"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resolve_twitter_profile("non_existent_user_9999999"))
        assert exc_info.value.status_code == 404


def test_twitter_analytics_routes() -> None:
    client = TestClient(app)

    mock_html = """
    <html>
    <head>
        <meta property="og:title" content="jack (@jack) on X">
        <meta property="og:description" content="no state is the best state">
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/166/avatar.jpg">
    </head>
    <body>
        followers:12300000,following:3,tweets:30000,name:"jack",
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        # Test GET /api/v1/analytics/twitter/analyze
        res = client.get("/api/v1/analytics/twitter/analyze?query=jack")
        assert res.status_code == 200
        data = res.json()
        assert data["platform"] == "twitter"
        assert data["channel"]["name"] == "jack"
        assert data["channel"]["subscribers"] == 12300000
        assert data["channel"]["videoCount"] == 30000
        assert data["channel"]["ingestion_mode"] == "public_web"
        assert data["kpis"]["subscribers"] == 12300000
        assert data["kpis"]["totalViews"] == 0

        # Test GET /api/v1/analytics/x/analyze (alias)
        res_x = client.get("/api/v1/analytics/x/analyze?query=jack")
        assert res_x.status_code == 200
        assert res_x.json()["platform"] == "twitter"


def test_twitter_social_connect() -> None:
    client = TestClient(app)
    database = SessionLocal()
    if not database.get(Organization, "org-twitter-test"):
        database.add(Organization(id="org-twitter-test", name="Twitter Test Org"))
    if not database.get(User, "user-twitter-test"):
        database.add(User(
            id="user-twitter-test",
            organization_id="org-twitter-test",
            email="twitter_test@example.com",
            display_name="Twitter Tester",
            password_hash=hash_password("SecurePassword1!"),
            role="creator",
        ))
    database.commit()
    database.close()

    token = create_access_token("user-twitter-test", "org-twitter-test", "creator")

    mock_html = """
    <html>
    <head>
        <meta property="og:title" content="OpenAI (@OpenAI) on X">
        <meta property="og:description" content="OpenAI mission">
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/999/avatar.jpg">
    </head>
    <body>
        followers:5300000,following:4,tweets:2100,name:"OpenAI",
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        res = client.post(
            "/api/v1/social/connect/twitter?handle=OpenAI",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["platform"] == "twitter"
        assert data["handle"] == "@OpenAI"
        assert data["subscribers_count"] == 5300000
        assert data["sync_status"] == "active"
