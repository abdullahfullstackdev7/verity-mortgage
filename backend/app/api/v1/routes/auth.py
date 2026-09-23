from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.cookies import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)
from backend.app.core.rate_limit import (
    RateLimitExceeded,
    check_login_rate_limit,
    record_failed_login,
    reset_login_attempts,
)
from backend.app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from backend.app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    ip = _client_ip(request)

    try:
        check_login_rate_limit(ip, body.email)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    try:
        tokens = auth_service.login(db, body.email, body.password)
    except auth_service.AuthError as exc:
        record_failed_login(ip, body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    reset_login_attempts(ip, body.email)
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    refresh_token_str = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided")

    try:
        tokens = auth_service.refresh(db, refresh_token_str)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> None:
    refresh_token_str = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token_str:
        auth_service.logout(db, refresh_token_str)
    clear_auth_cookies(response)
