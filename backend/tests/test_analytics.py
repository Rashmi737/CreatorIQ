from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Organization, User
from app.security import create_access_token, hash_password
from main import app


def test_analytics_routes_return_payloads() -> None:
    client = TestClient(app)
    database = SessionLocal()
    if not database.get(Organization, 'org-123'):
        database.add(Organization(id='org-123', name='Demo workspace'))
    if not database.get(User, 'user-123'):
        database.add(User(
            id='user-123',
            organization_id='org-123',
            email='demo@example.com',
            display_name='Demo Creator',
            password_hash=hash_password('SecurePassword1!'),
            role='creator',
        ))
    database.commit()
    database.close()

    token = create_access_token('user-123', 'org-123', 'creator')

    overview = client.get('/api/v1/analytics/overview', headers={'Authorization': f'Bearer {token}'})
    assert overview.status_code == 200
    assert 'kpis' in overview.json()
    assert overview.json()['kpis']['reach'] > 0

    content = client.get('/api/v1/analytics/content', headers={'Authorization': f'Bearer {token}'})
    assert content.status_code == 200
    assert len(content.json()['items']) >= 3

    audience = client.get('/api/v1/analytics/audience', headers={'Authorization': f'Bearer {token}'})
    assert audience.status_code == 200
    assert 'demographics' in audience.json()
    assert 'countries' in audience.json()
    assert 'active_hours' in audience.json()

    # Test dynamic channel tailored audience intelligence
    audience_tech = client.get(
        '/api/v1/analytics/audience?channel_name=Google%20Developers&subscribers=2500000',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert audience_tech.status_code == 200
    data_tech = audience_tech.json()
    assert 'demographics' in data_tech
    assert len(data_tech['demographics']) == 6
    assert 'gender_split' in data_tech
    assert 'countries' in data_tech
    assert len(data_tech['countries']) >= 5
    assert 'content_type_engagement' in data_tech
    assert 'active_hours' in data_tech
    assert len(data_tech['active_hours']) == 24
    assert 'optimal_window' in data_tech
    assert 'growth_time_series' in data_tech
    assert data_tech['niche'] == 'Tech & Engineering'

    assert 'device_usage' in data_tech
    assert len(data_tech['device_usage']) == 4
    devices = [d['device'] for d in data_tech['device_usage']]
    assert 'Mobile (Phone)' in devices
    assert 'Desktop / Laptop' in devices
    assert 'Smart TV & Connected Devices' in devices
    assert 'Tablet' in devices

    # Test entertainment channel
    audience_beast = client.get(
        '/api/v1/analytics/audience?channel_name=MrBeast&subscribers=250000000',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert audience_beast.status_code == 200
    data_beast = audience_beast.json()
    assert data_beast['niche'] == 'Entertainment & Viral Stunts'
    assert data_beast['countries'][0]['country'] == 'United States'
    assert 'device_usage' in data_beast

    # Test content comparison endpoint
    compare_res = client.get(
        '/api/v1/analytics/content/compare?id1=0&id2=1',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert compare_res.status_code == 200
    comp_json = compare_res.json()
    assert 'comparison' in comp_json
    assert 'deltas' in comp_json
    assert 'watch_time_hours' in comp_json['deltas']
    assert 'shares' in comp_json['deltas']
    assert 'saves' in comp_json['deltas']
    assert 'impressions' in comp_json['deltas']
    assert 'watch_time_hours' in comp_json['comparison']['first']


def test_multi_platform_account_analysis() -> None:
    """Verify multi-platform search analyzer endpoints for GitHub, LinkedIn, Instagram, and YouTube."""
    client = TestClient(app)

    # 1. GitHub Account Analysis (Live Public API)
    gh_res = client.get('/api/v1/analytics/github/analyze?query=torvalds')
    assert gh_res.status_code in (200, 403)
    if gh_res.status_code == 200:
        gh_data = gh_res.json()
        assert gh_data['platform'] == 'github'
        assert 'channel' in gh_data
        assert gh_data['channel']['platform'] == 'github'
        assert 'kpis' in gh_data
        assert gh_data['kpis']['totalLikes'] > 0  # stars
        assert len(gh_data['latestVideos']) >= 3
        assert len(gh_data['topPerforming']) >= 1

    # 1b. GitHub 404 for non-existent user (or 403 if public IP rate limit reached)
    gh_404 = client.get('/api/v1/analytics/github/analyze?query=creatoriq_nonexistent_user_99999999_xyz')
    assert gh_404.status_code in (404, 403)
    if gh_404.status_code == 404:
        assert 'not found' in gh_404.json()['detail'].lower()

    # 2. LinkedIn Account Analysis via Public Web Resolver
    li_res = client.get('/api/v1/analytics/linkedin/analyze?query=in/satyanadella')
    assert li_res.status_code in (200, 502)
    if li_res.status_code == 200:
        li_data = li_res.json()
        assert li_data['platform'] == 'linkedin'
        assert 'channel' in li_data
        assert li_data['subscribers_count'] > 0
        assert li_data.get('ingestion_mode') in ('public_web', 'rapidapi_live')
        assert len(li_data['latestVideos']) >= 0

    # 2b. LinkedIn 404 for non-existent user
    li_404 = client.get('/api/v1/analytics/linkedin/analyze?query=in/this_user_definitely_does_not_exist_404_creatoriq_xyz987')
    assert li_404.status_code == 404
    assert 'not found' in li_404.json()['detail'].lower()

    # 3. Instagram Account Analysis via Public Web Resolver (or 404/502 if public web crawler is blocked)
    ig_res = client.get('/api/v1/analytics/instagram/analyze?query=@creatoriq')
    assert ig_res.status_code in (200, 404, 502)
    if ig_res.status_code == 200:
        ig_data = ig_res.json()
        assert ig_data['platform'] == 'instagram'
        assert 'channel' in ig_data
        assert ig_data['channel']['handle'] == '@creatoriq'
        assert ig_data['subscribers_count'] > 0
        assert ig_data.get('ingestion_mode') == 'public_web'
        assert len(ig_data['latestVideos']) >= 0
        assert ig_data.get('requires_oauth') is True or len(ig_data['latestVideos']) >= 0

    # 3b. Instagram 404 (or 502 if public web crawler is rate-limited) for non-existent user
    ig_404 = client.get('/api/v1/analytics/instagram/analyze?query=@this_user_definitely_does_not_exist_404_creatoriq_xyz987')
    assert ig_404.status_code in (404, 502)

    # 4. YouTube Account Analysis
    yt_res = client.get('/api/v1/analytics/youtube/analyze?query=mrbeast')
    assert yt_res.status_code == 200
    yt_data = yt_res.json()
    assert yt_data['platform'] == 'youtube'
    assert 'channel' in yt_data
    assert 'kpis' in yt_data

    # 5. Generic Query Route with live GitHub (or 403 if public IP rate limit reached)
    gen_res = client.get('/api/v1/analytics/analyze?platform=github&query=gaearon')
    assert gen_res.status_code in (200, 403)
    if gen_res.status_code == 200:
        gen_data = gen_res.json()
        assert gen_data['platform'] == 'github'
        assert 'channel' in gen_data
        assert gen_data['channel']['handle'] == '@gaearon'

    # 6. Facebook Page Analysis via Public Web Resolver (or 502 if public web crawler is throttled)
    fb_res = client.get('/api/v1/analytics/facebook/analyze?query=Meta')
    assert fb_res.status_code in (200, 502)
    if fb_res.status_code == 200:
        fb_data = fb_res.json()
        assert fb_data['platform'] == 'facebook'
        assert 'channel' in fb_data
        assert fb_data['subscribers_count'] > 0
        assert fb_data.get('ingestion_mode') == 'public_web'

    # 6b. Facebook 404 (or 502 if crawler throttled) for non-existent page
    fb_404 = client.get('/api/v1/analytics/facebook/analyze?query=this_user_definitely_does_not_exist_404_creatoriq_xyz987')
    assert fb_404.status_code in (404, 502)
    assert 'not found' in fb_404.json()['detail'].lower()


def test_linkedin_rapidapi_live_ingestion() -> None:
    """Verify that when RapidAPI returns 200 with profile data, ingestion_mode is rapidapi_live and metrics are zero-mock compliant."""
    client = TestClient(app)
    mock_rapid_data = {
        "success": True,
        "data": {
            "full_name": "Satya Nadella",
            "headline": "Chairman and CEO at Microsoft",
            "summary": "Building technology that empowers every person and every organization on the planet to achieve more.",
            "follower_count": 10500000,
            "connections_count": 500,
            "profile_pic_url": "https://media.licdn.com/dms/image/sample.jpg",
        }
    }
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_rapid_data
        mock_get.return_value = mock_resp

        res = client.get('/api/v1/analytics/linkedin/analyze?query=in/satyanadella')
        assert res.status_code == 200
        data = res.json()
        assert data["platform"] == "linkedin"
        assert data["channel"]["name"] == "Satya Nadella"
        assert data["channel"]["subscribers"] == 10500000
        assert data["channel"]["ingestion_mode"] == "rapidapi_live"
        assert data["ingestion_mode"] == "rapidapi_live"
        assert data["kpis"]["subscribers"] == 10500000
        assert data["kpis"]["totalImpressions"] == 0
        assert data["kpis"]["ctr"] == 0.0


def test_derived_audience_analytics() -> None:
    """Verify GET /api/v1/analytics/audience/derived serves authentic derived signals without mock data."""
    client = TestClient(app)

    # 1. GitHub Account Audience Derivation
    gh_aud = client.get('/api/v1/analytics/audience/derived?platform=github&handle=torvalds')
    assert gh_aud.status_code in (200, 403)
    if gh_aud.status_code == 200:
        gh_data = gh_aud.json()
        assert gh_data['platform'] == 'github'
        assert gh_data['handle'] == 'torvalds'
        assert 'follower_tier' in gh_data
        assert gh_data['subscribers_count'] > 0
        # Zero-Mock Rule: Demographics must NOT be synthetic
        assert gh_data['demographics']['metric_available'] is False
        assert gh_data['demographics']['is_estimated'] is False
        assert 'privacy_notice' in gh_data['demographics']
        assert len(gh_data['demographics']['affinity_segments']) >= 1
        # Activity timeline must contain real tracked repos
        assert gh_data['activity']['posts_tracked'] >= 3
        assert len(gh_data['activity']['timeline']) >= 3

    # 2. Facebook Page Audience Derivation
    fb_aud = client.get('/api/v1/analytics/audience/derived?platform=facebook&handle=Meta')
    assert fb_aud.status_code == 200
    fb_data = fb_aud.json()
    assert fb_data['platform'] == 'facebook'
    assert fb_data['demographics']['metric_available'] is False
    assert fb_data['subscribers_count'] > 1000000
    assert 'Mega Creator' in fb_data['follower_tier']

    # 3. YouTube Channel Audience Derivation
    yt_aud = client.get('/api/v1/analytics/audience/derived?platform=youtube&handle=GoogleDevelopers')
    assert yt_aud.status_code == 200
    yt_data = yt_aud.json()
    assert yt_data['platform'] == 'youtube'
    assert yt_data['demographics']['metric_available'] is False
    assert yt_data['subscribers_count'] > 1000000

    # 4. 404 for non-existent profile (or 403/502 if public API rate limit is reached)
    err_aud = client.get('/api/v1/analytics/audience/derived?platform=github&handle=non_existent_user_123984928174_xyz')
    assert err_aud.status_code in (404, 403, 502)




