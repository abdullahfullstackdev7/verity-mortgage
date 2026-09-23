from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Optional because a browser client relies on the httpOnly refresh
    # cookie instead of sending the token back in the body.
    refresh_token: str | None = None
