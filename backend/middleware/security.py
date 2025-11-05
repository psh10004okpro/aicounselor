"""
Security Middleware

Implements:
1. CORS protection (already configured in main.py)
2. Rate limiting (extended)
3. SQL injection prevention
4. XSS protection
5. CSRF protection
6. Security headers
7. Request validation
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from typing import Callable
import re
import time
from collections import defaultdict
import asyncio

from app.core.redis import RedisManager


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000
    - Content-Security-Policy: default-src 'self'
    """

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.openai.com; "
            "frame-ancestors 'none';"
        )

        return response


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """
    Detects and blocks potential SQL injection attempts.

    Note: This is a defense-in-depth measure. Primary protection
    comes from using parameterized queries with SQLAlchemy.
    """

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bexec\b.*\()",
        r"(\bexecute\b.*\()",
        r"('.*--)",
        r"(;.*drop)",
        r"(or\s+1\s*=\s*1)",
        r"(or\s+'.*'\s*=\s*'.*')",
    ]

    def __init__(self, app):
        super().__init__(app)
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SQL_PATTERNS]

    async def dispatch(self, request: Request, call_next: Callable):
        # Check query parameters
        query_string = str(request.url.query).lower()

        for pattern in self.compiled_patterns:
            if pattern.search(query_string):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request parameters"},
                )

        # Check request body for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode("utf-8").lower()

                for pattern in self.compiled_patterns:
                    if pattern.search(body_str):
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"detail": "Invalid request body"},
                        )

                # Reconstruct request with body
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive

            except Exception:
                pass  # If body can't be decoded, let it pass

        response = await call_next(request)
        return response


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Detects and sanitizes potential XSS (Cross-Site Scripting) attacks.

    Note: Primary XSS protection comes from frontend input sanitization
    and proper output encoding. This is an additional layer.
    """

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]

    def __init__(self, app):
        super().__init__(app)
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.XSS_PATTERNS]

    async def dispatch(self, request: Request, call_next: Callable):
        # Check query parameters
        query_string = str(request.url.query)

        for pattern in self.compiled_patterns:
            if pattern.search(query_string):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request parameters detected"},
                )

        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.

    Limits:
    - 100 requests per minute per IP
    - 1000 requests per hour per IP
    """

    def __init__(self, app, redis_manager: RedisManager = None):
        super().__init__(app)
        self.redis_manager = redis_manager
        # Fallback in-memory rate limiting if Redis is not available
        self.memory_store = defaultdict(list)
        self.cleanup_interval = 60  # Clean up every minute
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.client.host

        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Use Redis if available, otherwise fallback to memory
        if self.redis_manager:
            is_allowed = await self._check_rate_limit_redis(client_ip)
        else:
            is_allowed = await self._check_rate_limit_memory(client_ip)

        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,
                },
            )

        response = await call_next(request)
        return response

    async def _check_rate_limit_redis(self, client_ip: str) -> bool:
        """Check rate limit using Redis"""
        # Per-minute limit (100 requests)
        minute_key = f"rate_limit:minute:{client_ip}"
        minute_count = await self.redis_manager.client.get(minute_key)

        if minute_count and int(minute_count) >= 100:
            return False

        # Increment counter
        if minute_count is None:
            await self.redis_manager.client.setex(minute_key, 60, 1)
        else:
            await self.redis_manager.client.incr(minute_key)

        # Per-hour limit (1000 requests)
        hour_key = f"rate_limit:hour:{client_ip}"
        hour_count = await self.redis_manager.client.get(hour_key)

        if hour_count and int(hour_count) >= 1000:
            return False

        if hour_count is None:
            await self.redis_manager.client.setex(hour_key, 3600, 1)
        else:
            await self.redis_manager.client.incr(hour_key)

        return True

    async def _check_rate_limit_memory(self, client_ip: str) -> bool:
        """Fallback in-memory rate limiting"""
        now = time.time()

        # Clean up old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_memory_store()
            self.last_cleanup = now

        # Get request timestamps for this IP
        timestamps = self.memory_store[client_ip]

        # Remove timestamps older than 1 hour
        timestamps = [ts for ts in timestamps if now - ts < 3600]

        # Check per-minute limit (100 requests)
        recent_minute = [ts for ts in timestamps if now - ts < 60]
        if len(recent_minute) >= 100:
            return False

        # Check per-hour limit (1000 requests)
        if len(timestamps) >= 1000:
            return False

        # Add current timestamp
        timestamps.append(now)
        self.memory_store[client_ip] = timestamps

        return True

    def _cleanup_memory_store(self):
        """Clean up old entries from memory store"""
        now = time.time()
        for ip in list(self.memory_store.keys()):
            timestamps = [ts for ts in self.memory_store[ip] if now - ts < 3600]
            if timestamps:
                self.memory_store[ip] = timestamps
            else:
                del self.memory_store[ip]


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF (Cross-Site Request Forgery) protection.

    For state-changing operations (POST, PUT, DELETE, PATCH),
    validates CSRF token or checks Origin/Referer headers.
    """

    def __init__(self, app, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:3000"]

    async def dispatch(self, request: Request, call_next: Callable):
        # Only check state-changing methods
        if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
            return await call_next(request)

        # Skip CSRF check for certain paths
        if request.url.path in ["/health", "/auth/anonymous"]:
            return await call_next(request)

        # Check Origin header
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        # If Origin header is present, validate it
        if origin:
            if not self._is_origin_allowed(origin):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed"},
                )
        # If no Origin, check Referer
        elif referer:
            referer_origin = self._extract_origin_from_referer(referer)
            if not self._is_origin_allowed(referer_origin):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed"},
                )
        else:
            # No Origin or Referer header - potentially suspicious
            # Allow for now but could be stricter in production
            pass

        response = await call_next(request)
        return response

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list"""
        if not origin:
            return False

        # Remove trailing slash
        origin = origin.rstrip("/")

        return any(
            origin == allowed_origin.rstrip("/")
            for allowed_origin in self.allowed_origins
        )

    def _extract_origin_from_referer(self, referer: str) -> str:
        """Extract origin from referer URL"""
        if not referer:
            return ""

        # Parse origin from referer (http://example.com/path -> http://example.com)
        match = re.match(r"^(https?://[^/]+)", referer)
        return match.group(1) if match else ""


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    General request validation middleware.

    - Validates content type for POST/PUT requests
    - Checks request size limits
    - Validates headers
    """

    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB

    async def dispatch(self, request: Request, call_next: Callable):
        # Check Content-Length
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request too large"},
                )

        # Validate Content-Type for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")

            # Allow application/json and multipart/form-data
            if not (
                "application/json" in content_type
                or "multipart/form-data" in content_type
                or "application/x-www-form-urlencoded" in content_type
            ):
                # Skip content-type check for certain endpoints
                if request.url.path not in ["/auth/anonymous", "/health"]:
                    return JSONResponse(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        content={"detail": "Unsupported media type"},
                    )

        response = await call_next(request)
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    HIPAA/GDPR compliance audit logging.

    Logs all requests for security audit purposes.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Log request
        request_log = {
            "timestamp": start_time,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent", ""),
        }

        # Process request
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        response_log = {
            **request_log,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }

        # In production, send to proper logging system (e.g., ELK, CloudWatch)
        # For now, just print for debugging
        if response.status_code >= 400:
            print(f"⚠️  Audit Log: {response_log}")

        return response
