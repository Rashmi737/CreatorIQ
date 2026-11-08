"""
End-to-End Workflow Validation Test Suite for CreatorIQ Platform
Validates the full creator workflow from health check to channel connection,
telemetry ingestion, predictive intelligence, and workspace data export.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from main import app


@pytest.fixture
def e2e_user():
    """Seed test organization and user for end-to-end journey validation."""
    db = SessionLocal()
    try:
        org = db.get(Organization, "org-e2e-test")
        if not org:
            org = Organization(id="org-e2e-test", name="E2E Enterprise Workspace")
            db.add(org)

        user = db.get(User, "user-e2e-test")
        if not user:
            user = User(
                id="user-e2e-test",
                organization_id="org-e2e-test",
                email="creator.e2e@creatoriq.dev",
                display_name="E2E Test Creator",
                password_hash=hash_password("E2eSecurePass2026!"),
                role="creator",
            )
            db.add(user)
        db.commit()

        # Clean any preexisting test contents/accounts for this test user
        db.query(SocialContent).filter_by(user_id="user-e2e-test").delete()
        db.query(PlatformAccount).filter_by(user_id="user-e2e-test").delete()
        db.commit()

        token = create_access_token(user.id, user.organization_id, user.role or "creator")
        return {"user_id": user.id, "org_id": user.organization_id, "token": token}
    finally:
        db.close()


MOCK_INGEST_CHANNEL = {
    "platform": "youtube",
    "handle": "@mkbhd",
    "clean_handle": "mkbhd",
    "channel_title": "Marques Brownlee",
    "subscribers_count": 18500000,
    "total_views": 4200000000,
    "video_count": 1600,
    "sync_status": "active",
    "last_synced_at": datetime.now(timezone.utc).isoformat(),
    "account_id": "acc-e2e-mkbhd",
    "message": "Successfully connected YouTube channel 'Marques Brownlee'",
}

MOCK_SYNC_RESPONSE = {
    "account_id": "acc-e2e-mkbhd",
    "status": "completed",
    "synced_videos_count": 5,
    "channel": {
        "title": "Marques Brownlee",
        "subscribers": 18500000,
        "views": 4200000000,
        "video_count": 1600,
    },
    "data": {"message": "Synchronized 5 YouTube videos"},
}


class TestEndToEndWorkflow:
    """Comprehensive test suite for the complete user journey."""

    def test_step1_application_health(self):
        """1. Application Health Check (GET /api/v1/health)."""
        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("status") == "ok"
        assert payload.get("service") == "creatoriq-api"

    @patch("app.services.social_adapters.connect_and_ingest_platform_account", new_callable=lambda: AsyncMock(return_value=MOCK_INGEST_CHANNEL))
    def test_step2_connect_and_ingest_channel(self, mock_ingest, e2e_user):
        """2. Connecting a channel / ingesting creator data (POST /api/v1/social/connect)."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {e2e_user['token']}"}

        # Test POST /api/v1/social/connect with JSON body
        res = client.post(
            "/api/v1/social/connect",
            json={"platform": "youtube", "handle": "@mkbhd"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["platform"] == "youtube"
        assert "mkbhd" in data["handle"].lower()
        assert data["sync_status"] == "active"
        assert data["subscribers_count"] == 18500000
        assert "account_id" in data

    def test_full_user_journey_workflow(self, e2e_user):
        """
        Executes and validates the complete continuous lifecycle:
        1. Health Check
        2. Channel Connection & Ingestion
        3. Overview Telemetry Fetch
        4. Benchmarks & Predictive Scoring Fetch
        5. Workspace Data Export (CSV & JSON)
        """
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {e2e_user['token']}"}

        # ---------------------------------------------------------
        # Step 1: Health check
        # ---------------------------------------------------------
        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        # ---------------------------------------------------------
        # Step 2: Ingest channel & seed content
        # ---------------------------------------------------------
        with patch("app.services.social_adapters.connect_and_ingest_platform_account", new_callable=lambda: AsyncMock(return_value=MOCK_INGEST_CHANNEL)):
            connect_res = client.post(
                "/api/v1/social/connect",
                json={"platform": "youtube", "handle": "mkbhd"},
                headers=headers,
            )
            assert connect_res.status_code == 200, connect_res.text
            conn_data = connect_res.json()
            assert conn_data["platform"] == "youtube"

        # Seed authentic PlatformAccount & SocialContent in database for analytics verification
        db = SessionLocal()
        try:
            account = db.get(PlatformAccount, "acc-e2e-mkbhd")
            if not account:
                account = PlatformAccount(
                    id="acc-e2e-mkbhd",
                    user_id=e2e_user["user_id"],
                    platform_name="youtube",
                    platform_user_id="mkbhd",
                    channel_title="Marques Brownlee",
                    subscribers_count=18500000,
                    total_views=4200000000,
                    video_count=1600,
                    access_token="tok_e2e_mock",
                    scopes="live_api",
                )
                db.add(account)

            # Add sample items for format benchmarks and predictions
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            test_contents = [
                SocialContent(
                    id="e2e-vid-1",
                    user_id=e2e_user["user_id"],
                    platform_account_id=account.id,
                    platform="youtube",
                    external_id="yt-e2e-001",
                    title="M4 iPad Pro Architecture Walkthrough & Tutorial",
                    content_type="Video",
                    views=1200000,
                    likes=95000,
                    comments=6200,
                    shares=12000,
                    engagement_rate=8.43,
                    published_at=now,
                ),
                SocialContent(
                    id="e2e-vid-2",
                    user_id=e2e_user["user_id"],
                    platform_account_id=account.id,
                    platform="youtube",
                    external_id="yt-e2e-002",
                    title="Quick Tip: Camera Setup in 60s Reel",
                    content_type="Short",
                    views=850000,
                    likes=72000,
                    comments=3100,
                    shares=8500,
                    engagement_rate=8.83,
                    published_at=now,
                ),
                SocialContent(
                    id="e2e-vid-3",
                    user_id=e2e_user["user_id"],
                    platform_account_id=account.id,
                    platform="youtube",
                    external_id="yt-e2e-003",
                    title="Smartphone Studio Deep Dive: System Design",
                    content_type="Video",
                    views=980000,
                    likes=68000,
                    comments=4900,
                    shares=7300,
                    engagement_rate=7.44,
                    published_at=now,
                ),
                SocialContent(
                    id="e2e-vid-4",
                    user_id=e2e_user["user_id"],
                    platform_account_id=account.id,
                    platform="youtube",
                    external_id="yt-e2e-004",
                    title="CreatorIQ Production Release Notes v2.0",
                    content_type="Post",
                    views=450000,
                    likes=21000,
                    comments=1800,
                    shares=2100,
                    engagement_rate=5.07,
                    published_at=now,
                ),
            ]
            for c in test_contents:
                existing = db.get(SocialContent, c.id)
                if not existing:
                    db.add(c)
            db.commit()
        finally:
            db.close()

        # ---------------------------------------------------------
        # Step 3: Fetching overview telemetry (GET /api/v1/analytics/overview)
        # ---------------------------------------------------------
        overview_res = client.get("/api/v1/analytics/overview", headers=headers)
        assert overview_res.status_code == 200, overview_res.text
        overview_data = overview_res.json()
        assert "kpis" in overview_data
        kpis = overview_data["kpis"]
        assert kpis["reach"] > 0
        assert kpis["engagement_rate"] >= 0
        assert "content_items" in overview_data or "time_series" in overview_data

        # ---------------------------------------------------------
        # Step 4: Fetching benchmarks & predictive scoring (GET /api/v1/analytics/predictions)
        # ---------------------------------------------------------
        predictions_res = client.get("/api/v1/analytics/predictions", headers=headers)
        assert predictions_res.status_code == 200, predictions_res.text
        pred_data = predictions_res.json()
        assert "predictions" in pred_data
        assert "performance_score" in pred_data
        assert "format_benchmarks" in pred_data

        score_info = pred_data["performance_score"]
        assert "score" in score_info
        assert 0 <= score_info["score"] <= 100
        assert "tier" in score_info
        assert "sub_metrics" in score_info
        assert "follower_reach" in score_info["sub_metrics"]
        assert "interaction_efficiency" in score_info["sub_metrics"]

        format_info = pred_data["format_benchmarks"]
        assert "formats" in format_info
        assert len(format_info["formats"]) >= 4

        # ---------------------------------------------------------
        # Step 5: Exporting workspace data (GET /api/v1/workspace/export)
        # ---------------------------------------------------------
        export_csv_res = client.get("/api/v1/workspace/export", headers=headers)
        assert export_csv_res.status_code == 200, export_csv_res.text
        assert "text/csv" in export_csv_res.headers.get("content-type", "")
        csv_text = export_csv_res.text
        assert "Platform" in csv_text
        assert "Followers / Subscribers" in csv_text
        assert "Marques Brownlee" in csv_text or "YouTube" in csv_text

        # Verify JSON format export as well
        export_json_res = client.get("/api/v1/workspace/export?format=json", headers=headers)
        assert export_json_res.status_code == 200, export_json_res.text
        json_data = export_json_res.json()
        assert "creator_media_kit" in json_data
        kit = json_data["creator_media_kit"]
        assert kit["verified_total_reach"] > 0
        assert "top_performing_assets" in kit
