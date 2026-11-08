import jwt
import pytest
from fastapi.testclient import TestClient
from main import app
from app.db import get_db
from app.models.identity import User
from sqlalchemy import select

client = TestClient(app)


def test_google_auth_success_new_user():
    test_email = "new_google_creator@example.com"
    test_sub = "google_sub_987654321"
    token = jwt.encode(
        {
            "email": test_email,
            "name": "Alex Google Creator",
            "picture": "https://lh3.googleusercontent.com/alex_pic.jpg",
            "sub": test_sub,
            "email_verified": True,
        },
        "test_secret",
        algorithm="HS256",
    )

    response = client.post("/api/v1/auth/google", json={"credential": token})
    assert response.status_code == 200
    data = response.json()

    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "token" in data
    assert data["user_name"] == "Alex Google Creator"
    assert data["user_email"] == test_email
    assert data["user_avatar"] == "https://lh3.googleusercontent.com/alex_pic.jpg"
    assert data["user"]["email"] == test_email
    assert data["user"]["display_name"] == "Alex Google Creator"
    assert data["user"]["auth_provider"] == "google"
    assert data["user"]["avatar_url"] == "https://lh3.googleusercontent.com/alex_pic.jpg"


def test_google_auth_account_linking_existing_user():
    test_email = "linking_creator@example.com"
    test_sub = "google_sub_link_112233"

    # First sign in / create
    token1 = jwt.encode(
        {
            "email": test_email,
            "name": "Initial Name",
            "picture": "https://lh3.googleusercontent.com/pic1.jpg",
            "sub": test_sub,
        },
        "test_secret",
        algorithm="HS256",
    )
    res1 = client.post("/api/v1/auth/google", json={"credential": token1})
    assert res1.status_code == 200
    user_id_1 = res1.json()["user"]["id"]

    # Second sign in / link
    token2 = jwt.encode(
        {
            "email": test_email,
            "name": "Updated Name",
            "picture": "https://lh3.googleusercontent.com/pic2_updated.jpg",
            "sub": test_sub,
        },
        "test_secret",
        algorithm="HS256",
    )
    res2 = client.post("/api/v1/auth/google", json={"credential": token2})
    assert res2.status_code == 200
    data2 = res2.json()

    # Must be the exact same user record in SQLite
    assert data2["user"]["id"] == user_id_1
    assert data2["user_avatar"] == "https://lh3.googleusercontent.com/pic2_updated.jpg"
    assert data2["user"]["avatar_url"] == "https://lh3.googleusercontent.com/pic2_updated.jpg"


def test_google_auth_missing_credential():
    response = client.post("/api/v1/auth/google", json={})
    assert response.status_code == 400


def test_google_auth_invalid_token():
    response = client.post("/api/v1/auth/google", json={"credential": "not-a-valid-jwt-token"})
    assert response.status_code == 401


def test_google_auth_token_missing_email():
    token = jwt.encode({"name": "No Email User", "sub": "12345"}, "test_secret", algorithm="HS256")
    response = client.post("/api/v1/auth/google", json={"credential": token})
    assert response.status_code == 400


def test_google_auth_verified_profile_fallback():
    payload = {
        "email": "rashmi732007@gmail.com",
        "name": "Rashmi V",
        "picture": "https://lh3.googleusercontent.com/a/ACg8ocKQy-rashmi-profile=s96-c",
        "sub": "google_1074878265244_rashmi732007",
        "auth_provider": "google",
    }
    response = client.post("/api/v1/auth/google", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "token" in data
    assert data["user_name"] == "Rashmi V"
    assert data["user_email"] == "rashmi732007@gmail.com"
    assert data["user"]["auth_provider"] == "google"
    assert data["user"]["display_name"] == "Rashmi V"

