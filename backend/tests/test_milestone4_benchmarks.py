"""
Milestone 4: Cross-Platform Performance Benchmarking & Predictive Analytics Tests
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from app.services.analytics.predictive import (
    FORMAT_BENCHMARKS,
    PredictiveAnalyticsService,
)
from main import app


@pytest.fixture
def predictive_service():
    return PredictiveAnalyticsService()


@pytest.fixture
def auth_user():
    """Create a test user and return auth token."""
    db = SessionLocal()
    try:
        org = db.get(Organization, "org-m4-api-test")
        if not org:
            org = Organization(id="org-m4-api-test", name="M4 API Test Org")
            db.add(org)

        user = db.get(User, "user-m4-api-test")
        if not user:
            user = User(
                id="user-m4-api-test",
                organization_id="org-m4-api-test",
                email="m4api@creatoriq.dev",
                display_name="M4 API Test User",
                password_hash=hash_password("SecureM4Api1!"),
                role="creator",
            )
            db.add(user)
        db.commit()

        token = create_access_token(user.id, user.organization_id, user.role or "creator")
        return {"user_id": user.id, "token": token}
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        org = db.get(Organization, "org-m4-test")
        if not org:
            org = Organization(id="org-m4-test", name="M4 Test Org")
            db.add(org)

        user = db.get(User, "user-m4-test")
        if not user:
            user = User(
                id="user-m4-test",
                organization_id="org-m4-test",
                email="m4@creatoriq.dev",
                display_name="M4 Test User",
                password_hash=hash_password("SecureM4Test1!"),
                role="creator",
            )
            db.add(user)
        db.commit()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        accounts_to_seed = [
            {
                "id": "acc-m4-yt",
                "platform_name": "youtube",
                "platform_user_id": "mkbhd",
                "channel_title": "MKBHD",
                "subscribers_count": 2_500_000,
                "total_views": 500_000_000,
                "video_count": 1500,
                "scopes": "live_api",
            },
            {
                "id": "acc-m4-gh",
                "platform_name": "github",
                "platform_user_id": "torvalds",
                "channel_title": "Linus Torvalds",
                "subscribers_count": 210_000,
                "total_views": 50_000,
                "video_count": 50,
                "scopes": "public_web",
            },
        ]

        for acc_info in accounts_to_seed:
            existing = db.get(PlatformAccount, acc_info["id"])
            if not existing:
                db.add(PlatformAccount(
                    id=acc_info["id"],
                    user_id="user-m4-test",
                    platform_name=acc_info["platform_name"],
                    platform_user_id=acc_info["platform_user_id"],
                    channel_title=acc_info["channel_title"],
                    subscribers_count=acc_info["subscribers_count"],
                    total_views=acc_info["total_views"],
                    video_count=acc_info["video_count"],
                    access_token="test-token",
                    scopes=acc_info["scopes"],
                    created_at=now,
                    updated_at=now,
                ))

        contents_to_seed = [
            {
                "id": "content-m4-1",
                "platform_account_id": "acc-m4-yt",
                "platform": "youtube",
                "external_id": "vid-m4-1",
                "title": "Tutorial: Building a Full-Stack App",
                "content_type": "Video",
                "views": 1_000_000,
                "likes": 50_000,
                "comments": 5_000,
                "shares": 2_000,
                "published_at": now - timedelta(days=1),
            },
            {
                "id": "content-m4-2",
                "platform_account_id": "acc-m4-yt",
                "platform": "youtube",
                "external_id": "vid-m4-2",
                "title": "Quick Tips for Developers",
                "content_type": "Video",
                "views": 500_000,
                "likes": 20_000,
                "comments": 2_000,
                "shares": 1_000,
                "published_at": now - timedelta(days=2),
            },
            {
                "id": "content-m4-3",
                "platform_account_id": "acc-m4-gh",
                "platform": "github",
                "external_id": "repo-m4-1",
                "title": "Linux Kernel Architecture Deep Dive",
                "content_type": "Repository",
                "views": 10_000,
                "likes": 5_000,
                "comments": 500,
                "shares": 200,
                "published_at": now - timedelta(days=3),
            },
        ]

        for c_info in contents_to_seed:
            existing = db.get(SocialContent, c_info["id"])
            if not existing:
                db.add(SocialContent(
                    id=c_info["id"],
                    user_id="user-m4-test",
                    platform_account_id=c_info["platform_account_id"],
                    platform=c_info["platform"],
                    external_id=c_info["external_id"],
                    title=c_info["title"],
                    content_type=c_info["content_type"],
                    views=c_info["views"],
                    likes=c_info["likes"],
                    comments=c_info["comments"],
                    shares=c_info["shares"],
                    published_at=c_info["published_at"],
                    created_at=now,
                    updated_at=now,
                ))

        db.commit()
        yield db
    finally:
        db.rollback()
        db.close()


class TestCreatorPerformanceScore:
    """Tests for Creator Performance Score calculation."""

    def test_score_bounds_zero_to_100(self, predictive_service, db_session):
        """Score must always be between 0 and 100."""
        result = predictive_service.compute_creator_performance_score("user-m4-test", db_session)
        assert 0 <= result["score"] <= 100

    def test_score_with_no_accounts(self, predictive_service, db_session):
        """Score should be 0 when no accounts exist at all."""
        with patch.object(predictive_service, '_get_workspace_accounts', return_value=[]):
            result = predictive_service.compute_creator_performance_score("nonexistent-user", db_session)
            assert result["score"] == 0
            assert result["tier"] == "Unmeasured"

    def test_sub_metrics_structure(self, predictive_service, db_session):
        """Sub-metrics should have correct structure with weights summing to 1.0."""
        result = predictive_service.compute_creator_performance_score("user-m4-test", db_session)
        assert "sub_metrics" in result
        weights = sum(m["weight"] for m in result["sub_metrics"].values())
        assert abs(weights - 1.0) < 0.01

    def test_tier_classification(self, predictive_service, db_session):
        """Tier should be correctly classified based on score."""
        result = predictive_service.compute_creator_performance_score("user-m4-test", db_session)
        score = result["score"]
        tier = result["tier"]

        if score >= 80:
            assert tier == "Top Tier Velocity"
        elif score >= 60:
            assert tier == "Strong Performer"
        elif score >= 40:
            assert tier == "Growing Presence"
        elif score >= 20:
            assert tier == "Early Stage"
        else:
            assert tier == "Unmeasured"


class TestPredictions:
    """Tests for predictive analytics and growth forecasting."""

    def test_predictions_with_no_accounts(self, predictive_service, db_session):
        """Predictions should return insufficient_data status when no accounts exist."""
        with patch.object(predictive_service, '_get_workspace_accounts', return_value=[]):
            result = predictive_service.compute_predictions("nonexistent-user", db_session)
            assert result["status"] == "insufficient_data"
            assert result["projections"] is None

    def test_predictions_structure(self, predictive_service, db_session):
        """Predictions should have correct structure with projections."""
        result = predictive_service.compute_predictions("user-m4-test", db_session, forecast_days=30)
        assert result["status"] == "active"
        assert "projections" in result
        assert len(result["projections"]) == 30
        assert "current_followers" in result
        assert "ema_daily_views" in result

    def test_prediction_ranges(self, predictive_service, db_session):
        """Conservative <= Expected <= Optimistic for all projections."""
        result = predictive_service.compute_predictions("user-m4-test", db_session, forecast_days=30)
        for proj in result["projections"]:
            assert proj["views"]["conservative"] <= proj["views"]["expected"]
            assert proj["views"]["expected"] <= proj["views"]["optimistic"]
            assert proj["followers"]["conservative"] <= proj["followers"]["expected"]
            assert proj["followers"]["expected"] <= proj["followers"]["optimistic"]


class TestFormatBenchmarks:
    """Tests for format benchmark matrix."""

    def test_format_benchmarks_structure(self, predictive_service, db_session):
        """Format benchmarks should have correct structure."""
        result = predictive_service.compute_format_benchmarks("user-m4-test", db_session)
        assert "formats" in result
        assert len(result["formats"]) == 4

        for fmt in result["formats"]:
            assert "format_key" in fmt
            assert "label" in fmt
            assert "target_engagement" in fmt
            assert "actual_engagement" in fmt
            assert "vs_benchmark" in fmt
            assert "status" in fmt
            assert fmt["status"] in ["outperforming", "underperforming", "at_benchmark"]

    def test_format_benchmark_targets(self, predictive_service):
        """Format benchmarks should have correct target engagement rates."""
        assert FORMAT_BENCHMARKS["long_form_tutorials"]["target_engagement"] == 5.5
        assert FORMAT_BENCHMARKS["short_form_reels"]["target_engagement"] == 4.2
        assert FORMAT_BENCHMARKS["architecture_deep_dives"]["target_engagement"] == 5.0
        assert FORMAT_BENCHMARKS["release_notes"]["target_engagement"] == 3.5

    def test_format_benchmarks_with_no_content(self, predictive_service, db_session):
        """Format benchmarks should handle empty content gracefully."""
        with patch.object(predictive_service, '_get_workspace_accounts', return_value=[]):
            result = predictive_service.compute_format_benchmarks("nonexistent-user", db_session)
            assert "formats" in result
            for fmt in result["formats"]:
                assert fmt["actual_engagement"] == 0.0
                assert fmt["content_count"] == 0


class TestAPIEndpoints:
    """Tests for the new API endpoints."""

    def test_predictions_endpoint(self, auth_user):
        """Test GET /api/v1/analytics/predictions returns valid structure."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {auth_user['token']}"}

        res = client.get("/api/v1/analytics/predictions", headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert "predictions" in data
        assert "performance_score" in data
        assert "format_benchmarks" in data

        # Performance score structure
        assert "score" in data["performance_score"]
        assert "tier" in data["performance_score"]
        assert "sub_metrics" in data["performance_score"]

        # Format benchmarks structure
        assert "formats" in data["format_benchmarks"]
        assert len(data["format_benchmarks"]["formats"]) == 4

    def test_predictions_endpoint_with_forecast_days(self, auth_user):
        """Test predictions endpoint with custom forecast_days parameter."""
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {auth_user['token']}"}

        res = client.get("/api/v1/analytics/predictions?forecast_days=14", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["predictions"]["forecast_days"] == 14
