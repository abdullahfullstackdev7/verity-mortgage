from __future__ import annotations

import uuid

import pytest
from conftest import requires_db
from fastapi.testclient import TestClient

from backend.app.core import rate_limit
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
    email = f"ratelimit-{uuid.uuid4().hex[:8]}@example.com"
    password = "RateLimitPassw0rd"
    created = user_service.create_user(db, email, password, UserRole.LOAN_OFFICER)
    user_id = created.id
    db.close()

    yield {"id": user_id, "email": email, "password": password}

    rate_limit._failed_attempts.clear()
    db = SessionLocal()
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


class TestLoginRateLimit:
    def test_blocks_after_repeated_failures_and_returns_retry_after(self, client, user):
        for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": user["email"], "password": "wrong-password"},
            )
            assert resp.status_code == 401

        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": "wrong-password"},
        )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers

        # Even the *correct* password is blocked while rate-limited -- the
        # point is to slow down guessing, not just reject guesses.
        still_blocked = client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert still_blocked.status_code == 429

    def test_successful_login_resets_the_counter(self, client, user):
        for _ in range(rate_limit.MAX_FAILED_ATTEMPTS - 1):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": user["email"], "password": "wrong-password"},
            )
            assert resp.status_code == 401

        good = client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert good.status_code == 200

        # Counter reset by the success, so this single new failure doesn't
        # trip the limiter.
        after = client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": "wrong-password"},
        )
        assert after.status_code == 401

    def test_rate_limit_is_scoped_per_email_not_globally(self, client, user):
        for _ in range(rate_limit.MAX_FAILED_ATTEMPTS):
            client.post(
                "/api/v1/auth/login",
                json={"email": user["email"], "password": "wrong-password"},
            )

        other_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "someone-else@example.com", "password": "whatever12345"},
        )
        # Unrelated account is unaffected -- 401 (bad creds), not 429.
        assert other_resp.status_code == 401
