from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, SocialContent, User
from app.security import create_access_token, hash_password
from app.services.analytics.benchmarking import BenchmarkingAnalyticsService
from main import app


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        # Seed test organization and user
        org = db.get(Organization, "org-benchmarks-test")
        if not org:
            org = Organization(id="org-benchmarks-test", name="Benchmark Test Org")
            db.add(org)

        user = db.get(User, "user-benchmarks-test")
        if not user:
            user = User(
                id="user-benchmarks-test",
                organization_id="org-benchmarks-test",
                email="benchmarks@creatoriq.dev",
                display_name="Benchmark Creator",
                password_hash=hash_password("SecureBenchmark1!"),
                role="creator",
            )
            db.add(user)
        db.commit()

        # Seed authentic platform accounts for this user
        now = datetime.now(timezone.utc)
        accounts_to_seed = [
            {
                "id": "acc-yt-test",
                "platform_name": "youtube",
                "platform_user_id": "googledevs",
                "channel_title": "Google Developers",
                "subscribers_count": 2500000,
                "total_views": 85000000,
                "video_count": 1200,
                "scopes": "live_api",
            },
            {
                "id": "acc-gh-test",
                "platform_name": "github",
                "platform_user_id": "torvalds",
                "channel_title": "Linus Torvalds",
                "subscribers_count": 210000,
                "total_views": 195000,  # stars sum
                "video_count": 8,       # repos count
                "scopes": "public_web",
            },
            {
                "id": "acc-li-test",
                "platform_name": "linkedin",
                "platform_user_id": "satyanadella",
                "channel_title": "Satya Nadella",
                "subscribers_count": 10200000,
                "total_views": 0,
                "video_count": 14,
                "scopes": "rapidapi_live",
            },
        ]

        for acc_info in accounts_to_seed:
            existing = db.get(PlatformAccount, acc_info["id"])
            if not existing:
                db.add(PlatformAccount(
                    id=acc_info["id"],
                    user_id="user-benchmarks-test",
                    platform_name=acc_info["platform_name"],
                    platform_user_id=acc_info["platform_user_id"],
                    channel_title=acc_info["channel_title"],
                    subscribers_count=acc_info["subscribers_count"],
                    total_views=acc_info["total_views"],
                    video_count=acc_info["video_count"],
                    access_token=f"test-token-{acc_info['platform_name']}",
                    scopes=acc_info["scopes"],
                    created_at=now,
                    updated_at=now,
                ))

        # Seed authentic social content items
        content_items = [
            {
                "id": "cnt-yt-1",
                "platform": "youtube",
                "platform_account_id": "acc-yt-test",
                "external_id": "yt_video_001",
                "title": "Building Next-Gen AI Applications with Gemini",
                "views": 450000,
                "likes": 22000,
                "comments": 1400,
                "shares": 800,
                "engagement_rate": 5.2,
            },
            {
                "id": "cnt-gh-1",
                "platform": "github",
                "platform_account_id": "acc-gh-test",
                "external_id": "gh_repo_001",
                "title": "linux",
                "views": 0,
                "likes": 178000,
                "comments": 52000,
                "shares": 0,
                "engagement_rate": 8.4,
            },
        ]

        for c_info in content_items:
            existing_c = db.get(SocialContent, c_info["id"])
            if not existing_c:
                db.add(SocialContent(
                    id=c_info["id"],
                    user_id="user-benchmarks-test",
                    platform_account_id=c_info["platform_account_id"],
                    platform=c_info["platform"],
                    external_id=c_info["external_id"],
                    title=c_info["title"],
                    views=c_info["views"],
                    likes=c_info["likes"],
                    comments=c_info["comments"],
                    shares=c_info["shares"],
                    engagement_rate=c_info["engagement_rate"],
                    published_at=now,
                    created_at=now,
                    updated_at=now,
                ))

        # Ensure acc-li-test has 0 social contents for test_zero_mock_handling_for_empty_interactions
        for c in db.scalars(select(SocialContent).where(SocialContent.platform_account_id == "acc-li-test")).all():
            db.delete(c)

        db.commit()
        yield db
    finally:
        db.close()


def test_benchmarking_service_calculations(db_session):
    service = BenchmarkingAnalyticsService()
    benchmarks = service.compute_cross_platform_benchmarks(
        user_id="user-benchmarks-test", db=db_session
    )

    scale = benchmarks["workspace_scale"]
    assert scale["total_audience"] >= 12910000  # 2.5M + 210k + 10.2M
    assert scale["connected_platforms_count"] >= 3
    assert scale["active_accounts_count"] >= 3

    # Platform share distribution checks
    shares = benchmarks["platform_share_distribution"]
    assert len(shares) >= 3
    total_pct = sum(s["share_percentage"] for s in shares)
    assert 99.0 <= total_pct <= 101.0  # Normalized ~100%

    # Velocity ranking checks
    velocity = benchmarks["velocity_ranking"]
    assert len(velocity) >= 3
    # Top follower scale should be Satya Nadella (10.2M)
    assert velocity[0]["followers"] >= velocity[1]["followers"]

    # Zero-Mock attestation
    attestation = benchmarks["zero_mock_attestation"]
    assert attestation["synthetic_data_present"] is False
    assert "SQLite" in attestation["data_source"]


def test_zero_mock_handling_for_empty_interactions(db_session):
    service = BenchmarkingAnalyticsService()
    # Test zero-mock rule for account with 0 tracked items
    benchmarks = service.compute_cross_platform_benchmarks(
        user_id="user-benchmarks-test", db=db_session
    )
    # LinkedIn account has 0 seeded social content items
    li_acc = next((a for a in benchmarks["accounts_matrix"] if a["platform"] == "linkedin"), None)
    assert li_acc is not None
    assert li_acc["tracked_items_count"] == 0
    # Must report 0.0 efficiency ratio, NOT fabricate a synthetic average
    assert li_acc["efficiency_ratio"] == 0.0


def test_creator_recommendations_generation(db_session):
    service = BenchmarkingAnalyticsService()
    recommendations = service.generate_creator_recommendations(
        user_id="user-benchmarks-test", db=db_session
    )
    assert len(recommendations) >= 3
    # Verify GitHub star recommendation exists
    gh_rec = next((r for r in recommendations if "GitHub" in r["title"] or "GitHub" in r["badge"]), None)
    assert gh_rec is not None
    assert gh_rec["impact"] == "High"

    # Verify audience concentration recommendation exists
    conc_rec = next((r for r in recommendations if "Audience" in r["category"]), None)
    assert conc_rec is not None


def test_api_benchmarks_endpoint(db_session):
    client = TestClient(app)
    token = create_access_token("user-benchmarks-test", "org-benchmarks-test", "creator")

    # Authenticated call
    resp = client.get(
        "/api/v1/analytics/benchmarks?user_id=user-benchmarks-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "workspace_scale" in data
    assert "platform_share_distribution" in data
    assert "velocity_ranking" in data
    assert "creator_recommendations" in data
    assert "accounts_matrix" in data

    # Unauthenticated / workspace fallback call
    unauth_resp = client.get("/api/v1/analytics/benchmarks")
    assert unauth_resp.status_code == 200
    assert "workspace_scale" in unauth_resp.json()


def test_api_export_csv_endpoint(db_session):
    client = TestClient(app)
    token = create_access_token("user-benchmarks-test", "org-benchmarks-test", "creator")

    resp = client.get(
        "/api/v1/analytics/export/csv?user_id=user-benchmarks-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=creatoriq_workspace_export.csv" in resp.headers["content-disposition"]

    csv_text = resp.text
    # Verify CSV headers
    assert "Platform,Handle,Display Name,Followers / Subscribers" in csv_text
    # Verify rows contain seeded authentic accounts
    assert "@googledevs" in csv_text
    assert "@torvalds" in csv_text
    assert "@satyanadella" in csv_text


def test_api_export_sponsor_report_endpoint(db_session):
    client = TestClient(app)
    token = create_access_token("user-benchmarks-test", "org-benchmarks-test", "creator")

    resp = client.get(
        "/api/v1/analytics/export/report?user_id=user-benchmarks-test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "creator_media_kit" in data
    kit = data["creator_media_kit"]
    assert kit["verified_total_reach"] > 0
    assert len(kit["verified_profiles"]) >= 3
    assert kit["zero_mock_attestation"]["verified"] is True
    assert "Zero synthetic" in kit["zero_mock_attestation"]["notice"]
