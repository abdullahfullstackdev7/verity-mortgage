from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import bcrypt
import jwt

from backend.app.core.config import settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised for any invalid, expired, or malformed JWT."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def _create_token(
    subject: uuid.UUID, role: str, token_type: TokenType, expires_delta: timedelta, jti: uuid.UUID
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "role": role,
        "type": token_type.value,
        "jti": str(jti),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        user_id,
        role,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        jti=uuid.uuid4(),
    )


def create_refresh_token(user_id: uuid.UUID, role: str, jti: uuid.UUID) -> str:
    return _create_token(
        user_id,
        role,
        TokenType.REFRESH,
        timedelta(days=settings.refresh_token_expire_days),
        jti=jti,
    )


def decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid") from exc

    if payload.get("type") != expected_type.value:
        raise TokenError(f"Expected a {expected_type.value} token")

    return payload
