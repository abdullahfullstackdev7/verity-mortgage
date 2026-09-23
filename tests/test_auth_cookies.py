from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

from backend.app.core.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from backend.app.db.base import SessionLocal
from backend.app.db.models.enums import UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service

pytestmark = requires_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def user(client):
    db = SessionLocal()
    email = f"cookie-{uuid.uuid4().hex[:8]}@example.com"
    password = "CookieTestPassw0rd"
    created = user_service.create_user(db, email, password, UserRole.LOAN_OFFICER)
    user_id = created.id
    db.close()

    yield {"id": user_id, "email": email, "password": password}

    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


class TestLoginSetsCookies:
    def test_login_sets_httponly_samesite_strict_cookies(self, client, user):
        resp = client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
        assert resp.status_code == 200

        set_cookie_headers = resp.headers.get_list("set-cookie")
        assert any(ACCESS_COOKIE_NAME in h for h in set_cookie_headers)
        assert any(REFRESH_COOKIE_NAME in h for h in set_cookie_headers)
        for header in set_cookie_headers:
            assert "HttpOnly" in header
            assert "samesite=strict" in header.lower()

    def test_local_env_cookies_are_not_marked_secure(self, client, user):
        # settings.env defaults to "local" in this test environment, where
        # there's no TLS -- Secure cookies would just never be sent.
        resp = client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
        set_cookie_headers = resp.headers.get_list("set-cookie")
        for header in set_cookie_headers:
            assert "Secure" not in header


class TestCookieBasedAuth:
    def test_cookie_alone_authenticates_a_request(self, client, user):
        client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})

        # No Authorization header at all -- the TestClient's cookie jar
        # (populated by the Set-Cookie above) is the only credential.
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == user["email"]

    def test_bearer_header_still_works_independently_of_cookies(self, client, user):
        login_resp = client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
        access_token = login_resp.json()["access_token"]

        fresh_client = TestClient(app)  # no cookie jar carried over
        resp = fresh_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
        assert resp.status_code == 200

    def test_refresh_reads_cookie_when_no_body_sent(self, client, user):
        client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})

        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200

        # Rotated cookie authenticates the next request too.
        me_resp = client.get("/api/v1/users/me")
        assert me_resp.status_code == 200

    def test_logout_clears_cookies_and_revokes_session(self, client, user):
        client.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})

        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 204

        # The cookie jar still holds the (now-revoked) cookies until the
        # client actually honors the clearing Set-Cookie; check the
        # server-side effect instead: refreshing with that same cookie now
        # fails.
        refresh_resp = client.post("/api/v1/auth/refresh")
        assert refresh_resp.status_code == 401
