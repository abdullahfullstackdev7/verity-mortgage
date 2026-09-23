from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.app.db.models.refresh_token import RefreshToken
from backend.app.db.models.user import User


class AuthError(Exception):
    """Raised for any authentication failure (bad credentials, bad/expired/
    revoked refresh token). Routes map this to HTTP 401."""


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


def _issue_token_pair(db: Session, user: User) -> TokenPair:
    jti = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(id=jti, user_id=user.id, expires_at=expires_at))

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id, user.role.value, jti)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def login(db: Session, email: str, password: str) -> TokenPair:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")

    tokens = _issue_token_pair(db, user)
    db.commit()
    return tokens


def refresh(db: Session, refresh_token_str: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token_str, expected_type=TokenType.REFRESH)
    except TokenError as exc:
        raise AuthError(str(exc)) from exc

    jti = uuid.UUID(payload["jti"])
    stored = db.get(RefreshToken, jti)
    now = datetime.now(UTC)

    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise AuthError("Refresh token is invalid, expired, or has already been used")

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AuthError("User not found")

    # Rotation: the presented refresh token is single-use.
    stored.revoked_at = now
    tokens = _issue_token_pair(db, user)
    db.commit()
    return tokens


def logout(db: Session, refresh_token_str: str) -> None:
    try:
        payload = decode_token(refresh_token_str, expected_type=TokenType.REFRESH)
    except TokenError:
        return  # already unusable; logout is idempotent

    jti = uuid.UUID(payload["jti"])
    stored = db.get(RefreshToken, jti)
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()
