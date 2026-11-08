from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, PlatformAccount, User
from app.models.monetization import SponsorshipDeal, WorkspaceAlert
from app.security import create_access_token, hash_password
from main import app


@pytest.fixture
def auth_user():
    database = SessionLocal()
    org = database.get(Organization, "org-monetization-test")
    if not org:
        org = Organization(id="org-monetization-test", name="Monetization Test Org")
        database.add(org)

    user = database.get(User, "user-monetization-test")
    if not user:
        user = User(
            id="user-monetization-test",
            organization_id="org-monetization-test",
            email="monetization_test@example.com",
            display_name="Monetization Tester",
            password_hash=hash_password("SecurePassword1!"),
            role="creator",
        )
        database.add(user)

    # Clean up previous test deals and alerts
    database.query(SponsorshipDeal).filter_by(user_id="user-monetization-test").delete()
    database.query(WorkspaceAlert).filter_by(user_id="user-monetization-test").delete()
    database.query(PlatformAccount).filter_by(user_id="user-monetization-test").delete()
    database.commit()
    database.close()

    token = create_access_token("user-monetization-test", "org-monetization-test", "creator")
    return {"user_id": "user-monetization-test", "token": token}


def test_sponsorship_deals_crud_and_totals(auth_user):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    # 1. Initially 0 deals
    res_init = client.get("/api/v1/monetization/deals", headers=headers)
    assert res_init.status_code == 200
    init_data = res_init.json()
    assert init_data["totals"]["total_pipeline"] == 0.0
    assert init_data["totals"]["total_earned"] == 0.0

    # 2. Create Deal A (Paid)
    deal_a = {
        "brand_name": "Nike",
        "deal_amount": 5000.0,
        "platform": "youtube",
        "status": "paid",
        "deliverable_type": "video",
        "notes": "Dedicated 60s integration",
    }
    res_a = client.post("/api/v1/monetization/deals", json=deal_a, headers=headers)
    assert res_a.status_code == 201
    created_a = res_a.json()
    assert created_a["brand_name"] == "Nike"
    assert created_a["deal_amount"] == 5000.0
    id_a = created_a["id"]

    # 3. Create Deal B (Contracted)
    deal_b = {
        "brand_name": "Cloudflare",
        "deal_amount": 8000.0,
        "platform": "github",
        "status": "contracted",
        "deliverable_type": "repo_sponsor",
    }
    res_b = client.post("/api/v1/monetization/deals", json=deal_b, headers=headers)
    assert res_b.status_code == 201
    id_b = res_b.json()["id"]

    # 4. Create Deal C (Negotiating)
    deal_c = {
        "brand_name": "Datadog",
        "deal_amount": 4000.0,
        "platform": "twitter",
        "status": "negotiating",
        "deliverable_type": "post",
    }
    res_c = client.post("/api/v1/monetization/deals", json=deal_c, headers=headers)
    assert res_c.status_code == 201

    # 5. Verify Totals
    res_totals = client.get("/api/v1/monetization/deals", headers=headers)
    assert res_totals.status_code == 200
    totals_data = res_totals.json()
    assert totals_data["totals"]["total_pipeline"] == 17000.0
    assert totals_data["totals"]["total_earned"] == 5000.0
    assert totals_data["totals"]["contracted_amount"] == 8000.0
    assert totals_data["totals"]["pending_invoices"] == 8000.0
    assert totals_data["totals"]["negotiating_amount"] == 4000.0
    assert totals_data["totals"]["active_deals_count"] == 2
    assert totals_data["totals"]["paid_deals_count"] == 1
    assert totals_data["totals"]["avg_deal_size"] == round(17000.0 / 3, 2)
    assert len(totals_data["deals"]) == 3

    # 6. Update Deal B status to paid
    patch_res = client.patch(
        f"/api/v1/monetization/deals/{id_b}/status",
        json={"status": "paid"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "paid"

    # Verify updated totals
    res_updated = client.get("/api/v1/monetization/deals", headers=headers)
    assert res_updated.json()["totals"]["total_earned"] == 13000.0

    # 7. Delete Deal A
    del_res = client.delete(f"/api/v1/monetization/deals/{id_a}", headers=headers)
    assert del_res.status_code == 200

    res_after_del = client.get("/api/v1/monetization/deals", headers=headers)
    assert len(res_after_del.json()["deals"]) == 2


def test_monetization_analytics_breakdown(auth_user):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    client.post(
        "/api/v1/monetization/deals",
        json={"brand_name": "Acme Inc", "deal_amount": 10000.0, "platform": "youtube", "status": "paid"},
        headers=headers,
    )
    client.post(
        "/api/v1/monetization/deals",
        json={"brand_name": "Sponsor X", "deal_amount": 6000.0, "platform": "twitter", "status": "contracted"},
        headers=headers,
    )

    res = client.get("/api/v1/monetization/analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["kpis"]["total_revenue"] == 10000.0
    assert data["kpis"]["pending_invoices"] == 6000.0
    # New formula: Paid + (0.9 * Contracted) + (0.4 * Negotiating) + (0.15 * Pitched)
    # 10000 + (0.9 * 6000) + 0 + 0 = 15400
    assert data["kpis"]["projected_earnings"] == 15400.0

    # Platform breakdown check
    platforms = [p["platform"] for p in data["revenue_by_platform"]]
    assert "youtube" in platforms
    assert "twitter" in platforms

    # Status breakdown check
    statuses = {s["status"]: s["amount"] for s in data["revenue_by_status"]}
    assert statuses["paid"] == 10000.0
    assert statuses["contracted"] == 6000.0


def test_milestone_notifications_and_read(auth_user):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    # Seed an account with 120,000 subscribers for the test user
    database = SessionLocal()
    acc = PlatformAccount(
        user_id=auth_user["user_id"],
        platform_name="youtube",
        platform_user_id="testcreator",
        channel_title="Test Creator Show",
        subscribers_count=120000,
        total_views=1500000,
        video_count=45,
        access_token="test-token",
        scopes="active",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    database.add(acc)
    database.commit()
    database.close()

    # 1. Fetch notifications - triggers automatic milestone check
    res_notif = client.get("/api/v1/notifications", headers=headers)
    assert res_notif.status_code == 200
    notif_data = res_notif.json()
    assert notif_data["total_count"] >= 1
    assert notif_data["unread_count"] >= 1

    milestone_alert = next((a for a in notif_data["alerts"] if a["alert_type"] == "milestone"), None)
    assert milestone_alert is not None
    assert "100K" in milestone_alert["title"] or "100,000" in milestone_alert["message"]
    assert milestone_alert["is_read"] is False
    alert_id = milestone_alert["id"]

    # 2. Mark specific alert as read
    res_read = client.post(f"/api/v1/notifications/{alert_id}/read", headers=headers)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 3. Mark all as read
    res_read_all = client.post("/api/v1/notifications/read-all", headers=headers)
    assert res_read_all.status_code == 200
    assert res_read_all.json()["success"] is True

    res_after = client.get("/api/v1/notifications", headers=headers)
    assert res_after.json()["unread_count"] == 0


def test_rate_card_endpoint(auth_user):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    database = SessionLocal()
    acc = PlatformAccount(
        user_id=auth_user["user_id"],
        platform_name="youtube",
        platform_user_id="mkbhd_rates",
        channel_title="Marques Brownlee Test",
        subscribers_count=200_000,
        total_views=15_000_000,
        video_count=120,
        access_token="mock_token",
        scopes="rapidapi_live",
    )
    database.add(acc)
    database.commit()
    database.close()

    # 1. Fetch rate card for existing account
    res = client.get("/api/v1/monetization/rate-card?platform=youtube&handle=mkbhd_rates", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["platform"] == "youtube"
    assert data["handle"] == "mkbhd_rates"
    assert data["verified_followers"] == 200_000
    assert len(data["suggested_rate_cards"]) == 4
    assert "Zero-Mock" in data["zero_mock_notice"]

    # Check that rate cards reflect verified follower scale (200k followers -> 24k baseline impressions)
    # baseline_impressions = min(200000 * 0.12, 3000000) = 24000
    integration_card = next(c for c in data["suggested_rate_cards"] if c["deliverable_type"] == "integration")
    assert integration_card["suggested_price"] == 552.0  # (24000/1000) * 23.0

    dedicated_card = next(c for c in data["suggested_rate_cards"] if c["deliverable_type"] == "video")
    assert dedicated_card["suggested_price"] == 1320.0  # (24000/1000) * 55.0

    # 2. Non-existent account should return 404
    res_404 = client.get("/api/v1/monetization/rate-card?platform=youtube&handle=nonexistent_dummy_handle_12345", headers=headers)
    assert res_404.status_code == 404

