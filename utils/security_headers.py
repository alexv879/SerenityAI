"""
Security Headers Middleware - Production Security Best Practices

Adds security headers to all HTTP responses to protect against common attacks.

Headers implemented:
- X-Frame-Options: Prevent clickjacking
- X-Content-Type-Options: Prevent MIME sniffing
- X-XSS-Protection: Enable XSS filter (legacy browsers)
- Strict-Transport-Security (HSTS): Enforce HTTPS
- Content-Security-Policy: Prevent XSS and injection attacks
- Referrer-Policy: Control referrer information
- Permissions-Policy: Control browser features

Author: Claude Code
Date: 2025-11-19
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging
import os

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all HTTP responses

    Usage:
        from fastapi import FastAPI
        from utils.security_headers import SecurityHeadersMiddleware

        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
    """

    def __init__(self, app, enable_hsts: bool = True, enable_csp: bool = True):
        """
        Initialize security headers middleware

        Args:
            app: FastAPI application
            enable_hsts: Enable HSTS header (default: True in production)
            enable_csp: Enable Content Security Policy (default: True)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts and os.getenv("ENV") == "production"
        self.enable_csp = enable_csp

        logger.info(
            f"Security headers middleware initialized "
            f"(HSTS: {self.enable_hsts}, CSP: {self.enable_csp})"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with security headers
        """
        # Process request
        response = await call_next(request)

        # Add security headers
        response.headers.update(self._get_security_headers())

        return response

    def _get_security_headers(self) -> dict:
        """
        Get security headers dictionary

        Returns:
            Dictionary of security headers
        """
        headers = {
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",

            # Prevent MIME sniffing
            "X-Content-Type-Options": "nosniff",

            # Enable XSS filter (legacy browsers)
            "X-XSS-Protection": "1; mode=block",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Disable browser features that could be exploited
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),

            # Server identification (generic)
            "Server": "SerenityAI",

            # Cache control for sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }

        # Add HSTS header in production (enforce HTTPS)
        if self.enable_hsts:
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Add Content Security Policy
        if self.enable_csp:
            headers["Content-Security-Policy"] = self._get_csp()

        return headers

    def _get_csp(self) -> str:
        """
        Get Content Security Policy directive

        Returns:
            CSP header value
        """
        # Strict CSP to prevent XSS and injection attacks
        csp_directives = [
            "default-src 'self'",  # Only load resources from same origin
            "script-src 'self' 'unsafe-inline'",  # Allow inline scripts (needed for some frameworks)
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles
            "img-src 'self' data: https:",  # Allow images from same origin, data URIs, and HTTPS
            "font-src 'self' data:",  # Allow fonts from same origin and data URIs
            "connect-src 'self' https://api.openai.com https://api.groq.com https://api.twilio.com https://api.stripe.com",  # Allow API connections
            "media-src 'self'",  # Only load media from same origin
            "object-src 'none'",  # Block plugins (Flash, Java, etc.)
            "frame-src 'none'",  # Block framing (prevent clickjacking)
            "base-uri 'self'",  # Restrict base URI
            "form-action 'self'",  # Only submit forms to same origin
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
            "block-all-mixed-content"  # Block mixed content (HTTP on HTTPS page)
        ]

        return "; ".join(csp_directives)


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Secure CORS middleware with strict origin validation

    Only allows CORS from explicitly whitelisted origins.
    Prevents unauthorized cross-origin requests.

    Usage:
        from fastapi import FastAPI
        from utils.security_headers import CORSSecurityMiddleware

        app = FastAPI()
        app.add_middleware(
            CORSSecurityMiddleware,
            allowed_origins=["https://yourdomain.com"]
        )
    """

    def __init__(
        self,
        app,
        allowed_origins: list = None,
        allow_credentials: bool = False,
        max_age: int = 600
    ):
        """
        Initialize CORS security middleware

        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins (default: none)
            allow_credentials: Allow credentials (default: False)
            max_age: Preflight cache duration in seconds (default: 600)
        """
        super().__init__(app)
        self.allowed_origins = set(allowed_origins or [])
        self.allow_credentials = allow_credentials
        self.max_age = max_age

        logger.info(
            f"CORS security middleware initialized "
            f"(origins: {len(self.allowed_origins)}, credentials: {allow_credentials})"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add CORS headers if origin is allowed

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with CORS headers (if applicable)
        """
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            if origin in self.allowed_origins:
                return Response(
                    status_code=200,
                    headers=self._get_cors_headers(origin)
                )
            else:
                # Reject preflight from unauthorized origin
                return Response(status_code=403)

        # Process request
        response = await call_next(request)

        # Add CORS headers if origin is allowed
        if origin in self.allowed_origins:
            response.headers.update(self._get_cors_headers(origin))

        return response

    def _get_cors_headers(self, origin: str) -> dict:
        """
        Get CORS headers for allowed origin

        Args:
            origin: Origin that made the request

        Returns:
            Dictionary of CORS headers
        """
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": str(self.max_age)
        }

        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        return headers


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add rate limit information headers to responses

    Informs clients about their rate limit status.

    Headers added:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests
    - X-RateLimit-Reset: Time when limit resets (Unix timestamp)

    Usage:
        from fastapi import FastAPI
        from utils.security_headers import RateLimitHeadersMiddleware

        app = FastAPI()
        app.add_middleware(RateLimitHeadersMiddleware)
    """

    def __init__(self, app):
        super().__init__(app)
        logger.info("Rate limit headers middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add rate limit headers

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        # Process request
        response = await call_next(request)

        # Add rate limit info if available
        if hasattr(request.state, "rate_limit_info"):
            rate_limit = request.state.rate_limit_info
            response.headers.update({
                "X-RateLimit-Limit": str(rate_limit.get("limit", "unknown")),
                "X-RateLimit-Remaining": str(rate_limit.get("remaining", "unknown")),
                "X-RateLimit-Reset": str(rate_limit.get("reset", "unknown"))
            })

        return response


def add_security_middleware(app, enable_hsts: bool = True, enable_csp: bool = True):
    """
    Add all security middleware to FastAPI app

    Args:
        app: FastAPI application
        enable_hsts: Enable HSTS header (default: True in production)
        enable_csp: Enable Content Security Policy (default: True)

    Usage:
        from fastapi import FastAPI
        from utils.security_headers import add_security_middleware

        app = FastAPI()
        add_security_middleware(app)
    """
    # Security headers (should be first)
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts, enable_csp=enable_csp)

    # Rate limit headers
    app.add_middleware(RateLimitHeadersMiddleware)

    logger.info("All security middleware added to application")
