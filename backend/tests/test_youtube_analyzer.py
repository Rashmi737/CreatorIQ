from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_youtube_analyze_mkbhd():
    res = client.get("/api/v1/analytics/youtube/analyze?query=mkbhd")
    assert res.status_code == 200
    data = res.json()

    # Check top-level keys
    assert "channel" in data
    assert "kpis" in data
    assert "topPerforming" in data
    assert "latestVideos" in data

    # Check real channel schema
    ch = data["channel"]
    assert ch["name"] == "Marques Brownlee"
    assert "avatar" in ch
    assert ch["subscribers"] >= 15000000

    # Top performing sorted by views
    top = data["topPerforming"]
    assert len(top) <= 3
    if len(top) > 1:
        assert top[0]["viewCount"] >= top[1]["viewCount"]
    for item in top:
        assert "dQw4w9WgXcQ" not in item["thumbnail"]
        assert "dQw4w9WgXcQ" not in item["id"]

    # Latest videos
    latest = data["latestVideos"]
    assert len(latest) >= 1
    for item in latest:
        assert "dQw4w9WgXcQ" not in item["thumbnail"]
        assert "dQw4w9WgXcQ" not in item["id"]


def test_youtube_analyze_googledevelopers():
    res = client.get("/api/v1/analytics/youtube/analyze?query=GoogleDevelopers")
    assert res.status_code == 200
    data = res.json()
    assert "Google" in data["channel"]["name"]
    assert data["channel"]["subscribers"] >= 1000000
    assert len(data["latestVideos"]) >= 1


def test_youtube_analyze_channel_not_found():
    res = client.get("/api/v1/analytics/youtube/analyze?query=thischannelreallydoesnotexistxyz9999")
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()
