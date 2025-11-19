"""
Retry Handler - Exponential Backoff for External API Calls

Provides retry logic with exponential backoff for resilient external API calls.
Prevents single network glitches from failing user conversations.

Features:
- Exponential backoff with jitter
- Configurable retry attempts and delays
- Specific exception handling
- Logging of retry attempts
- Circuit breaker integration

Author: Claude Code
Date: 2025-11-19
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    operation_name: Optional[str] = None
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 1.0)
        max_wait: Maximum wait time in seconds (default: 10.0)
        exceptions: Tuple of exception types to retry on (default: all exceptions)
        operation_name: Name of the operation for logging (default: function name)

    Usage:
        @retry_with_backoff(max_attempts=3, min_wait=1.0, max_wait=10.0)
        async def fetch_from_api():
            response = await external_api.get(...)
            return response

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                logger.warning(f"[{name}] Retry failed with: {type(e).__name__}: {e}")
                raise

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                logger.warning(f"[{name}] Retry failed with: {type(e).__name__}: {e}")
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Specific retry strategies for different external services

def retry_openai_api(func: Callable) -> Callable:
    """
    Retry strategy for OpenAI API calls

    Retries on:
    - Connection errors
    - Timeout errors
    - Rate limit errors (429)
    - Server errors (5xx)

    Config:
    - Max attempts: 3
    - Wait: 1-10 seconds with exponential backoff
    """
    from openai import (
        APIConnectionError,
        APITimeoutError,
        RateLimitError,
        InternalServerError
    )

    return retry_with_backoff(
        max_attempts=3,
        min_wait=1.0,
        max_wait=10.0,
        exceptions=(
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
            ConnectionError,
            TimeoutError
        ),
        operation_name="OpenAI API"
    )(func)


def retry_groq_api(func: Callable) -> Callable:
    """
    Retry strategy for Groq API calls

    Retries on:
    - Connection errors
    - Timeout errors
    - Rate limit errors

    Config:
    - Max attempts: 3
    - Wait: 1-10 seconds with exponential backoff
    """
    return retry_with_backoff(
        max_attempts=3,
        min_wait=1.0,
        max_wait=10.0,
        exceptions=(
            ConnectionError,
            TimeoutError,
            OSError
        ),
        operation_name="Groq API"
    )(func)


def retry_twilio_api(func: Callable) -> Callable:
    """
    Retry strategy for Twilio API calls

    Retries on:
    - Connection errors
    - Timeout errors
    - Service unavailable (503)

    Config:
    - Max attempts: 2 (Twilio is usually reliable)
    - Wait: 0.5-5 seconds with exponential backoff
    """
    from twilio.base.exceptions import TwilioException

    return retry_with_backoff(
        max_attempts=2,
        min_wait=0.5,
        max_wait=5.0,
        exceptions=(
            TwilioException,
            ConnectionError,
            TimeoutError
        ),
        operation_name="Twilio API"
    )(func)


def retry_stripe_api(func: Callable) -> Callable:
    """
    Retry strategy for Stripe API calls

    Retries on:
    - Connection errors
    - Timeout errors
    - Rate limit errors

    Config:
    - Max attempts: 3
    - Wait: 1-10 seconds with exponential backoff
    """
    import stripe

    return retry_with_backoff(
        max_attempts=3,
        min_wait=1.0,
        max_wait=10.0,
        exceptions=(
            stripe.error.APIConnectionError,
            stripe.error.RateLimitError,
            ConnectionError,
            TimeoutError
        ),
        operation_name="Stripe API"
    )(func)


def retry_database(func: Callable) -> Callable:
    """
    Retry strategy for database operations

    Retries on:
    - Connection errors
    - Timeout errors
    - Deadlock errors

    Config:
    - Max attempts: 3
    - Wait: 0.5-5 seconds with exponential backoff
    """
    import asyncpg

    return retry_with_backoff(
        max_attempts=3,
        min_wait=0.5,
        max_wait=5.0,
        exceptions=(
            asyncpg.PostgresConnectionError,
            asyncpg.TooManyConnectionsError,
            asyncpg.DeadlockDetectedError,
            ConnectionError,
            TimeoutError
        ),
        operation_name="Database"
    )(func)


def retry_redis(func: Callable) -> Callable:
    """
    Retry strategy for Redis operations

    Retries on:
    - Connection errors
    - Timeout errors
    - Response errors

    Config:
    - Max attempts: 3
    - Wait: 0.5-5 seconds with exponential backoff
    """
    import redis.exceptions

    return retry_with_backoff(
        max_attempts=3,
        min_wait=0.5,
        max_wait=5.0,
        exceptions=(
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            redis.exceptions.ResponseError,
            ConnectionError,
            TimeoutError
        ),
        operation_name="Redis"
    )(func)


async def retry_async_operation(
    operation: Callable,
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    operation_name: str = "operation"
) -> Any:
    """
    Manual retry logic for operations that can't use decorators

    Args:
        operation: Async function to retry
        max_attempts: Maximum number of attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        operation_name: Name for logging

    Returns:
        Result of the operation

    Raises:
        Exception from the last failed attempt

    Usage:
        result = await retry_async_operation(
            lambda: external_api.fetch(),
            max_attempts=3,
            operation_name="External API Fetch"
        )
    """
    import random

    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            logger.warning(
                f"[{operation_name}] Attempt {attempt}/{max_attempts} failed: "
                f"{type(e).__name__}: {e}"
            )

            if attempt < max_attempts:
                # Calculate exponential backoff with jitter
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                jitter = random.uniform(0, wait_time * 0.1)  # Add 10% jitter
                total_wait = wait_time + jitter

                logger.info(f"[{operation_name}] Retrying in {total_wait:.2f}s...")
                await asyncio.sleep(total_wait)
            else:
                logger.error(
                    f"[{operation_name}] All {max_attempts} attempts failed. "
                    f"Final error: {type(e).__name__}: {e}"
                )

    # Raise the last exception if all retries failed
    raise last_exception


class RetryStats:
    """
    Track retry statistics for monitoring and alerting

    Usage:
        stats = RetryStats()
        stats.record_retry("OpenAI API", success=False, attempts=3)
        metrics = stats.get_metrics()
    """

    def __init__(self):
        self.retry_counts = {}
        self.success_counts = {}
        self.failure_counts = {}

    def record_retry(self, operation: str, success: bool, attempts: int):
        """Record a retry attempt"""
        if operation not in self.retry_counts:
            self.retry_counts[operation] = []
            self.success_counts[operation] = 0
            self.failure_counts[operation] = 0

        self.retry_counts[operation].append(attempts)

        if success:
            self.success_counts[operation] += 1
        else:
            self.failure_counts[operation] += 1

    def get_metrics(self) -> dict:
        """Get retry metrics for all operations"""
        metrics = {}

        for operation in self.retry_counts:
            total_retries = len(self.retry_counts[operation])
            avg_attempts = sum(self.retry_counts[operation]) / total_retries if total_retries > 0 else 0

            metrics[operation] = {
                "total_operations": total_retries,
                "average_attempts": round(avg_attempts, 2),
                "success_count": self.success_counts[operation],
                "failure_count": self.failure_counts[operation],
                "success_rate": round(
                    self.success_counts[operation] / total_retries * 100, 2
                ) if total_retries > 0 else 0
            }

        return metrics

    def reset(self):
        """Reset all statistics"""
        self.retry_counts.clear()
        self.success_counts.clear()
        self.failure_counts.clear()


# Global retry statistics instance
_retry_stats = RetryStats()


def get_retry_stats() -> RetryStats:
    """Get the global retry statistics instance"""
    return _retry_stats
