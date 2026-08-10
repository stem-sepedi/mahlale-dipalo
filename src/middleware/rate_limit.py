"""Rate limiting middleware — per-role RPM limits using in-memory sliding window."""

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

_ROLE_LIMITS = {
    "learner": settings.RATE_LIMIT_LEARNER,
    "translator": settings.RATE_LIMIT_TRANSLATOR,
    "reviewer": settings.RATE_LIMIT_REVIEWER,
    "teacher": settings.RATE_LIMIT_TEACHER,
    "admin": settings.RATE_LIMIT_ADMIN,
    "worker": 0,  # unlimited for internal workers
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter — tracks requests per user/role in memory."""

    def __init__(self, app, window_seconds: int = 60):
        super().__init__(app)
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        key = self._extract_key(request)
        if key is None:
            return await call_next(request)

        role = self._extract_role(request)
        limit = _ROLE_LIMITS.get(role, 60)
        if limit == 0:
            return await call_next(request)

        now = time.time()
        window_start = now - self._window
        self._hits[key] = [t for t in self._hits[key] if t > window_start]

        if len(self._hits[key]) >= limit:
            retry_after = int(self._hits[key][0] - window_start) + 1
            return Response(
                content='{"error": {"code": "RATE_LIMITED", "message": "Too many requests"}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        self._hits[key].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - len(self._hits[key]))
        return response

    def _extract_key(self, request: Request) -> str | None:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return f"bearer:{auth[7:]}"
        api_key = request.headers.get(settings.API_KEY_HEADER, "")
        if api_key:
            return f"apikey:{api_key}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _extract_role(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return "learner"
        try:
            from src.middleware.jwt import decode_token
            payload = decode_token(auth[7:])
            return payload.role
        except Exception:
            return "learner"
