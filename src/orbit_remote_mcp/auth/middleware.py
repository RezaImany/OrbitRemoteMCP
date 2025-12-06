"""Authentication and request guard middleware."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from typing import Callable, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ..config import Settings
from ..logging import set_request_id

PUBLIC_PATHS = {
    "/diagnostics/healthcheck",
    "/diagnostics/ready",
    "/.well-known/mcp.json",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def _sign(payload: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_session_token(secret: str, ttl_seconds: int) -> str:
    session_id = uuid.uuid4().hex
    expiry = int(time.time()) + ttl_seconds
    payload = f"{session_id}:{expiry}"
    signature = _sign(payload, secret)
    return f"{payload}.{signature}"


def verify_session_token(token: str, secret: str) -> bool:
    try:
        payload, signature = token.rsplit(".", 1)
        expected = _sign(payload, secret)
        if not hmac.compare_digest(signature, expected):
            return False
        _, expiry_str = payload.split(":", 1)
        return int(expiry_str) >= int(time.time())
    except Exception:
        return False


def extract_api_key(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1]
    if api_key := request.headers.get("X-API-Key"):
        return api_key
    return None


def extract_session_token(request: Request) -> Optional[str]:
    if token := request.headers.get("X-Session-Token"):
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("session "):
        return auth_header.split(" ", 1)[1]
    return None


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds request id for logging correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        set_request_id(request_id)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        body = await request.body()
        if len(body) > self.max_body_bytes:
            return JSONResponse(status_code=413, content={"error": "Request body too large"})

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int):
        super().__init__(app)
        self.limit = max(1, limit_per_minute)
        self.window = 60
        self.buckets: dict[str, tuple[int, int]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        now = int(time.time())
        key = request.client.host if request.client else "anonymous"
        count, start = self.buckets.get(key, (0, now))
        if now - start >= self.window:
            count, start = 0, now
        count += 1
        self.buckets[key] = (count, start)

        if count > self.limit:
            return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})

        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if not self.settings.require_auth:
            return await call_next(request)

        if not self.settings.auth_key:
            raise HTTPException(status_code=500, detail="Auth key not configured")

        # Session token check
        if token := extract_session_token(request):
            if verify_session_token(token, self.settings.auth_key):
                return await call_next(request)

        # API key check
        api_key = extract_api_key(request)
        if api_key and api_key == self.settings.auth_key:
            return await call_next(request)

        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

