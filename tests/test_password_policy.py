from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

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
def admin(client):
    db = SessionLocal()
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    password = "AdminPassw0rd1"
    user = user_service.create_user(db, email, password, UserRole.ADMIN)
    user_id = user.id
    db.close()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    yield {"id": user_id, "token": token}

    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


def _create_user(client, admin, email, password):
    return client.post(
        "/api/v1/users",
        json={"email": email, "password": password, "role": "loan_officer"},
        headers={"Authorization": f"Bearer {admin['token']}"},
    )


class TestPasswordPolicy:
    def test_too_short_is_rejected(self, client, admin):
        resp = _create_user(client, admin, "short1@example.com", "Ab1")
        assert resp.status_code == 422

    def test_missing_digit_is_rejected(self, client, admin):
        resp = _create_user(client, admin, "nodigit@example.com", "onlylettershere")
        assert resp.status_code == 422

    def test_missing_letter_is_rejected(self, client, admin):
        resp = _create_user(client, admin, "noletter@example.com", "1234567890")
        assert resp.status_code == 422

    def test_valid_password_is_accepted(self, client, admin):
        email = f"validpw-{uuid.uuid4().hex[:8]}@example.com"
        resp = _create_user(client, admin, email, "validPassw0rd")
        assert resp.status_code == 201

        db = SessionLocal()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
