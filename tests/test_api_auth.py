from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import SessionLocal
from backend.app.db.models.enums import UserRole
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User
from backend.app.main import app
from backend.app.services import user_service
from conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def admin_user():
    db = SessionLocal()
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    password = "correct horse battery staple"
    user = user_service.create_user(db, email, password, UserRole.ADMIN)
    user_id = user.id
    db.close()

    yield {"email": email, "password": password, "id": user_id}

    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


class TestLogin:
    def test_login_with_correct_credentials_returns_tokens(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user["email"], "password": admin_user["password"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["refresh_token"]

    def test_login_with_wrong_password_returns_401(self, client, admin_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user["email"], "password": "wrong password"},
        )
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "unauthorized"

    def test_login_with_unknown_email_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever12345"},
        )
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_rotates_token_and_old_one_becomes_unusable(self, client, admin_user):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user["email"], "password": admin_user["password"]},
        )
        first_refresh = login_resp.json()["refresh_token"]

        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["refresh_token"] != first_refresh

        reuse_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert reuse_resp.status_code == 401

    def test_refresh_with_garbage_token_returns_401(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
        assert resp.status_code == 401


class TestLogout:
    def test_logout_then_refresh_fails(self, client, admin_user):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user["email"], "password": admin_user["password"]},
        )
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 204

        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 401


class TestCurrentUser:
    def test_me_requires_authentication(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_me_returns_current_user_with_valid_token(self, client, admin_user):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user["email"], "password": admin_user["password"]},
        )
        access_token = login_resp.json()["access_token"]

        resp = client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == admin_user["email"]
        assert resp.json()["role"] == "admin"


class TestUserCreationRbac:
    def test_non_admin_cannot_create_users(self, client):
        db = SessionLocal()
        email = f"officer-{uuid.uuid4().hex[:8]}@example.com"
        password = "loan officer password"
        officer = user_service.create_user(db, email, password, UserRole.LOAN_OFFICER)
        officer_id = officer.id
        db.close()

        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        access_token = login_resp.json()["access_token"]

        resp = client.post(
            "/api/v1/users",
            json={"email": "new@example.com", "password": "whatever12345", "role": "admin"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 403

        db = SessionLocal()
        db.query(RefreshToken).filter(RefreshToken.user_id == officer_id).delete()
        db.query(User).filter(User.id == officer_id).delete()
        db.commit()
        db.close()
