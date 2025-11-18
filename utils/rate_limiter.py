"""
Rate Limiting Middleware for SerenityAI
Protects against API abuse and DoS attacks

Uses FastAPI-Limiter with Redis backend for distributed rate limiting
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)


async def rate_limit_middleware(app: FastAPI):
    """
    Initialize rate limiting middleware with Redis backend

    Args:
        app: FastAPI application instance
    """
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Connect to Redis
        redis_connection = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # Initialize FastAPI Limiter
        await FastAPILimiter.init(redis_connection)

        logger.info("Rate limiting middleware initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize rate limiting: {e}")
        # Don't fail the entire application if rate limiting fails
        # Just log the error and continue


# Rate limit configurations for different endpoints
class RateLimits:
    """
    Centralized rate limit configurations

    Format: "requests/period" where period can be:
    - second, minute, hour, day
    """

    # Voice endpoints (protect against call spam)
    VOICE_ENTRY = "30/minute"  # Max 30 call attempts per minute per IP
    VOICE_CHAT = "100/minute"  # Max 100 conversation turns per minute

    # WebSocket connections (protect against connection spam)
    WEBSOCKET_STREAM = "10/minute"  # Max 10 WebSocket connections per minute per IP

    # Payment endpoints (critical - prevent payment spam)
    PAYMENT_TRIGGER = "5/minute"  # Max 5 payment attempts per minute
    PAYMENT_COMPLETE = "20/minute"  # Max 20 payment webhooks per minute (Twilio retries)

    # External API endpoints
    NEWS_WEATHER = "60/minute"  # Max 60 news/weather requests per minute

    # Stripe webhooks (generous limit for retries)
    STRIPE_WEBHOOK = "100/minute"

    # Admin endpoints (if any)
    ADMIN_REFUND = "10/hour"  # Max 10 refunds per hour


def get_rate_limiter(limit: str):
    """
    Get a rate limiter dependency for a specific endpoint

    Args:
        limit: Rate limit string (e.g., "10/minute")

    Returns:
        RateLimiter dependency

    Usage:
        @router.post("/endpoint", dependencies=[Depends(get_rate_limiter("10/minute"))])
        async def my_endpoint():
            pass
    """
    return RateLimiter(times=int(limit.split("/")[0]), seconds=_get_seconds(limit))


def _get_seconds(limit: str) -> int:
    """
    Convert rate limit period to seconds

    Args:
        limit: Rate limit string (e.g., "10/minute")

    Returns:
        Number of seconds for the period
    """
    period = limit.split("/")[1]

    if period == "second":
        return 1
    elif period == "minute":
        return 60
    elif period == "hour":
        return 3600
    elif period == "day":
        return 86400
    else:
        return 60  # Default to minute


async def get_client_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting

    Uses phone number from Twilio if available, otherwise IP address

    Args:
        request: FastAPI request

    Returns:
        Unique identifier string
    """
    # Try to get phone number from Twilio form data
    try:
        if request.method == "POST":
            form = await request.form()
            phone = form.get("From")
            if phone:
                return f"phone:{phone}"
    except:
        pass

    # Fallback to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0]}"

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


# Custom exception handler for rate limit exceeded
async def rate_limit_exceeded_handler(request: Request, exc: HTTPException):
    """
    Custom handler for rate limit exceeded errors

    Returns appropriate response based on request type
    """
    # For Twilio webhooks, return TwiML error
    if request.url.path.startswith("/voice/") or request.url.path.startswith("/payment/"):
        from twilio.twiml.voice_response import VoiceResponse
        from fastapi.responses import Response

        response = VoiceResponse()
        response.say(
            "Sorry, our system is experiencing high traffic. Please try again in a few moments.",
            voice="Polly.Amy-Neural"
        )
        response.hangup()

        return Response(content=str(response), media_type="application/xml", status_code=429)

    # For API endpoints, return JSON error
    return {
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": 60  # seconds
    }
