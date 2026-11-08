import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import PlatformAccount, SocialContent, User
from app.services.activity_ingestion import (
    PLATFORM_CONTENT_TEMPLATES,
    generate_and_persist_channel_catalog,
    generate_catalog_dicts,
    generate_performance_takeaways,
    rollup_channel_metrics,
    auto_heal_all_channels,
)
from app.services.multi_platform_analyzer import analyze_multi_platform_account
from main import app


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_client():
    return TestClient(app)


def test_generate_catalog_dicts_scaling():
    """Verify micro-creator followers scale impressions between 850 and 3200."""
    items = generate_catalog_dicts(
        platform="linkedin",
        handle="johndoe",
        followers=227,
        target_count=10,
    )
    assert len(items) == 10
    for it in items:
        assert 800 <= it["impressions"] <= 3500
        assert it["likes"] > 0
        assert it["comments"] >= 1
        assert it["shares"] >= 1
        assert it["dwell_time_mins"] >= 1.0
        assert it["durationSeconds"] >= 60
        assert it["format"] in ["Deep Dive", "Static Post/Update", "Long-form Tutorial", "Shorts/Reel"]
        assert it["engagementRate"] > 0.0


def test_channel_catalog_persistence_and_rollup(db_session):
    """Verify channel catalog generation persists SocialContent and rolls up PlatformAccount metrics."""
    from sqlalchemy import select
    user = db_session.scalar(select(User).limit(1))
    user_id = user.id if user else "test-user-id"

    test_account = PlatformAccount(
        id=f"pa-test-{uuid4().hex[:8]}",
        user_id=user_id,
        platform_name="linkedin",
        platform_user_id="testcreator",
        channel_title="Test Creator Profile",
        subscribers_count=227,
        total_views=0,
        video_count=0,
        total_posts=0,
        total_impressions=0,
        engagement_rate=0.0,
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        token_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
        scopes="public_web",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(test_account)
    db_session.commit()

    try:
        # Initial check
        assert test_account.total_posts == 0
        assert test_account.total_impressions == 0

        # Run catalog generation on empty channel - ensures zero mock post fabrication
        items = generate_and_persist_channel_catalog(test_account, db_session, target_count=12)
        assert len(items) == 0

        # Check database rows remain zero
        db_session.refresh(test_account)
        assert test_account.total_posts == 0
        assert test_account.total_impressions == 0
        assert test_account.engagement_rate == 0.0

        # Add genuine ingested content to test genuine rollup calculation
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sc1 = SocialContent(
            id=f"sc-test-1-{uuid4().hex[:6]}",
            platform_account_id=test_account.id,
            user_id=user_id,
            title="Real Post 1",
            content_type="video",
            external_id="ext-1",
            views=1000,
            likes=100,
            comments=10,
            shares=5,
            dwell_time_mins=3.5,
            published_at=now - timedelta(days=2),
            created_at=now,
            updated_at=now,
        )
        sc2 = SocialContent(
            id=f"sc-test-2-{uuid4().hex[:6]}",
            platform_account_id=test_account.id,
            user_id=user_id,
            title="Real Post 2",
            content_type="video",
            external_id="ext-2",
            views=2000,
            likes=200,
            comments=20,
            shares=10,
            dwell_time_mins=4.5,
            published_at=now - timedelta(days=5),
            created_at=now,
            updated_at=now,
        )
        db_session.add_all([sc1, sc2])
        db_session.commit()

        # Check rollups on genuine posts
        items = generate_and_persist_channel_catalog(test_account, db_session)
        assert len(items) == 2
        db_session.refresh(test_account)
        assert test_account.total_posts == 2
        assert test_account.total_impressions == 3000
        assert test_account.engagement_rate > 0.0

        rollup = rollup_channel_metrics(test_account, db_session)
        assert rollup["total_impressions"] == 3000
        assert rollup["reactions"] == 330
        assert rollup["avg_dwell_time"] == 4.0
        assert rollup["performance_ratio"] > 0.0
        assert "takeaways" in rollup
    finally:
        # Cleanup
        contents = list(db_session.scalars(select(SocialContent).where(SocialContent.platform_account_id == test_account.id)).all())
        for row in contents:
            db_session.delete(row)
        acc = db_session.get(PlatformAccount, test_account.id)
        if acc:
            db_session.delete(acc)
        db_session.commit()


@pytest.mark.anyio
async def test_multi_platform_analyzer_strict_live_data():
    """Verify multi-platform analyzer enforces 100% strict live data without fabricating mock posts."""
    res_li = await analyze_multi_platform_account(platform="linkedin", query="satyanadella")
    assert res_li["platform"] == "linkedin"
    assert res_li["channel"]["name"] != ""
    assert res_li["channel"]["subscribers"] > 0
    assert res_li.get("requires_oauth") is True
    assert "OAuth" in res_li.get("badge", "")
    assert len(res_li["latestVideos"]) == 0
    assert res_li["kpis"]["totalImpressions"] == 0

    res_ig = await analyze_multi_platform_account(platform="instagram", query="instagram")
    assert res_ig["platform"] == "instagram"
    assert res_ig["channel"]["subscribers"] > 0
    assert res_ig.get("requires_oauth") is True
    assert "OAuth" in res_ig.get("badge", "")
    assert len(res_ig["latestVideos"]) == 0


def test_api_performance_and_catalog_endpoints(test_client):
    """Verify GET /api/v1/analytics/performance and GET /api/v1/content/catalog."""
    # Performance endpoint
    res_perf = test_client.get("/api/v1/analytics/performance")
    assert res_perf.status_code == 200
    perf_data = res_perf.json()
    assert "kpis" in perf_data
    assert "takeaways" in perf_data
    assert "peakDayInsight" in perf_data["takeaways"]

    # Content catalog endpoint
    res_cat = test_client.get("/api/v1/content/catalog?limit=10")
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    assert "items" in cat_data
    assert "summary" in cat_data
    assert cat_data["summary"]["total_impressions"] >= 0

    # Social sync-all endpoint
    res_sync = test_client.post("/api/v1/social/sync-all")
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["status"] == "success"
