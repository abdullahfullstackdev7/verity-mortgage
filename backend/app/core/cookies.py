"""httpOnly auth cookies for the browser frontend.

These exist *alongside* the existing JSON-body token response, not instead
of it: the JSON body stays for non-browser API/tooling clients (and is what
the test suite's Bearer-header pattern relies on), while the cookies are
what the actual frontend uses so an XSS payload running on the page can't
read the session token out of localStorage -- `get_current_user` accepts
either a Bearer header or the access-token cookie.

SameSite=Strict is the CSRF mitigation here (no separate CSRF token
scheme): a Strict cookie is never sent on a cross-site request, which
covers the classic CSRF vector for this app's same-site deployment shape.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from fastapi import Response

from backend.app.core.config import settings

ACCESS_COOKIE_NAME = "verity_access_token"
REFRESH_COOKIE_NAME = "verity_refresh_token"


class _CommonCookieKwargs(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["strict", "lax", "none"]
    path: str
    domain: str | None


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = not settings.is_local
    common: _CommonCookieKwargs = {
        "httponly": True,
        "secure": secure,
        "samesite": "strict",
        "path": "/",
        "domain": settings.cookie_domain,
    }
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", domain=settings.cookie_domain)
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", domain=settings.cookie_domain)
