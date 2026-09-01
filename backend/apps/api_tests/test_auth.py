import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_signup_creates_user_and_returns_tokens():
    client = APIClient()
    resp = client.post(
        "/api/auth/signup/",
        {"username": "ruslan", "password": "a-strong-pw-123"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert "access" in resp.data and "refresh" in resp.data
    assert User.objects.filter(username="ruslan").exists()


@pytest.mark.django_db
def test_signup_rejects_duplicate_username():
    User.objects.create_user(username="ruslan", password="whatever123")
    client = APIClient()
    resp = client.post("/api/auth/signup/", {"username": "ruslan", "password": "a-strong-pw-123"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_login_with_correct_credentials_returns_tokens():
    User.objects.create_user(username="ruslan", password="a-strong-pw-123")
    client = APIClient()
    resp = client.post("/api/auth/login/", {"username": "ruslan", "password": "a-strong-pw-123"}, format="json")
    assert resp.status_code == 200
    assert "access" in resp.data and "refresh" in resp.data


@pytest.mark.django_db
def test_login_with_wrong_password_rejected():
    User.objects.create_user(username="ruslan", password="a-strong-pw-123")
    client = APIClient()
    resp = client.post("/api/auth/login/", {"username": "ruslan", "password": "wrong"}, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_protected_endpoint_requires_token():
    client = APIClient()
    resp = client.get("/api/orders/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_access_token_grants_access_to_own_data_only():
    User.objects.create_user(username="ruslan", password="a-strong-pw-123")
    client = APIClient()
    login = client.post("/api/auth/login/", {"username": "ruslan", "password": "a-strong-pw-123"}, format="json")
    access = login.data["access"]

    resp = client.get("/api/orders/", HTTP_AUTHORIZATION=f"Bearer {access}")
    assert resp.status_code == 200
    assert resp.data["count"] == 0


@pytest.mark.django_db
def test_me_returns_current_username():
    User.objects.create_user(username="ruslan", password="a-strong-pw-123")
    client = APIClient()
    login = client.post("/api/auth/login/", {"username": "ruslan", "password": "a-strong-pw-123"}, format="json")
    access = login.data["access"]

    resp = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
    assert resp.status_code == 200
    assert resp.data["username"] == "ruslan"


@pytest.mark.django_db
def test_me_requires_auth():
    client = APIClient()
    resp = client.get("/api/auth/me/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token():
    User.objects.create_user(username="ruslan", password="a-strong-pw-123")
    client = APIClient()
    login = client.post("/api/auth/login/", {"username": "ruslan", "password": "a-strong-pw-123"}, format="json")
    access, refresh = login.data["access"], login.data["refresh"]

    logout_resp = client.post(
        "/api/auth/logout/", {"refresh": refresh}, format="json", HTTP_AUTHORIZATION=f"Bearer {access}"
    )
    assert logout_resp.status_code == 205

    # the blacklisted refresh token can no longer mint new access tokens
    refresh_resp = client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert refresh_resp.status_code == 401




