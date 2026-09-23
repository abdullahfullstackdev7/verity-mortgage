from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import RequestLoggingMiddleware, configure_logging

_ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_413_CONTENT_TOO_LARGE: "file_too_large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",
}


class HstsMiddleware(BaseHTTPMiddleware):
    """Adds Strict-Transport-Security to every response. Only mounted for
    non-local environments (see create_app) -- it would make no sense (and
    would actively break) plain-HTTP local development."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Verity Mortgage Underwriting API",
        description=(
            "Intake-to-decision underwriting automation API, built on public "
            "HMDA data with synthetically generated supporting documents."
        ),
        version="0.1.0",
    )

    if not settings.is_local:
        # HTTPS is enforced (and HSTS advertised) everywhere except local
        # dev, where there's no TLS termination to redirect to.
        app.add_middleware(HTTPSRedirectMiddleware)
        app.add_middleware(HstsMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": _ERROR_CODES.get(exc.status_code, "error"),
                "detail": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            # exc.errors() can include non-JSON-serializable context (e.g.
            # the raw exception a custom Pydantic validator raised), so it
            # has to go through jsonable_encoder like FastAPI's own default
            # handler does -- passing it to JSONResponse directly crashes
            # the error handler itself on those cases.
            content={"error_code": "validation_error", "detail": jsonable_encoder(exc.errors())},
        )

    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
