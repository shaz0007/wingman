import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from .config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces essential production security headers on all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=self, geolocation=()"
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter per IP address for API protection."""

    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self._requests_per_minute = requests_per_minute
        self.request_history: dict[str, list[float]] = defaultdict(list)
        # Paths excluded from rate limiting (healthchecks, static info)
        self.exempt_paths = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    @property
    def limit(self) -> int:
        return self._requests_per_minute if self._requests_per_minute is not None else settings.RATE_LIMIT_PER_MINUTE

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client IP (support proxies via X-Forwarded-For if available)
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        history = [ts for ts in self.request_history[client_ip] if ts > window_start]
        self.request_history[client_ip] = history

        if len(history) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Too Many Requests",
                    "detail": "Rate limit exceeded. Please wait a minute before making more requests."
                },
                headers={"Retry-After": "60"}
            )

        self.request_history[client_ip].append(now)
        return await call_next(request)


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Adds execution duration header to help monitor performance."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
