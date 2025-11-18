"""
Circuit Breaker Pattern - Prevent cascade failures from external API issues

Protects the system from repeated calls to failing external services by:
1. Tracking failure rates for each service
2. "Opening" the circuit after threshold failures (fast-fail mode)
3. Periodically testing recovery (half-open state)
4. Automatically closing when service recovers

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation, requests pass through
    OPEN = "open"            # Circuit tripped, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: int = 60      # Seconds before attempting recovery
    success_threshold: int = 2      # Successes in half-open to close circuit
    timeout: int = 10               # Request timeout in seconds

    # Stats
    total_requests: int = field(default=0, init=False)
    total_failures: int = field(default=0, init=False)
    total_successes: int = field(default=0, init=False)
    total_rejections: int = field(default=0, init=False)


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures

    Usage:
        breaker = CircuitBreaker(name="newsapi")
        result = await breaker.call(some_async_function, arg1, arg2)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout: int = 10
    ):
        """
        Initialize circuit breaker

        Args:
            name: Identifier for this circuit (e.g., "newsapi", "openweather")
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed in half-open to close
            timeout: Request timeout in seconds
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout
        )

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        async with self.lock:
            self.config.total_requests += 1

            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    logger.info(f"Circuit breaker {self.name}: transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    # Circuit still open, fail fast
                    self.config.total_rejections += 1
                    logger.warning(f"Circuit breaker {self.name}: OPEN - rejecting request")
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker for {self.name} is OPEN. "
                        f"Service will be retried in {int(self.config.recovery_timeout - (time.time() - self.last_failure_time))} seconds."
                    )

        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            # Success - update state
            async with self.lock:
                await self._on_success()

            return result

        except asyncio.TimeoutError as e:
            async with self.lock:
                await self._on_failure()
            logger.error(f"Circuit breaker {self.name}: timeout after {self.config.timeout}s")
            raise CircuitBreakerTimeoutError(f"Request to {self.name} timed out") from e

        except Exception as e:
            async with self.lock:
                await self._on_failure()
            logger.error(f"Circuit breaker {self.name}: failure - {type(e).__name__}")
            raise

    async def _on_success(self):
        """Handle successful request"""
        self.config.total_successes += 1
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker {self.name}: transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    async def _on_failure(self):
        """Handle failed request"""
        self.config.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failure during recovery attempt - reopen circuit
            logger.warning(f"Circuit breaker {self.name}: recovery failed, reopening")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.config.failure_threshold:
            # Too many failures - open circuit
            logger.error(
                f"Circuit breaker {self.name}: OPENING circuit after "
                f"{self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.config.total_requests,
            "total_successes": self.config.total_successes,
            "total_failures": self.config.total_failures,
            "total_rejections": self.config.total_rejections,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }

    async def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        async with self.lock:
            logger.info(f"Circuit breaker {self.name}: manually reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests"""
    pass


class CircuitBreakerTimeoutError(Exception):
    """Raised when request times out"""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


async def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: int = 10
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name (singleton pattern)

    Args:
        name: Circuit breaker identifier
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before retry
        success_threshold: Successes to close in half-open
        timeout: Request timeout

    Returns:
        CircuitBreaker instance
    """
    async with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                timeout=timeout
            )
            logger.info(f"Created circuit breaker: {name}")
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers for monitoring"""
    return _circuit_breakers.copy()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: int = 10
):
    """
    Decorator to apply circuit breaker protection to async functions

    Usage:
        @circuit_breaker(name="newsapi", timeout=5)
        async def get_news():
            ...

    Args:
        name: Circuit breaker identifier
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before recovery attempt
        success_threshold: Successes needed to close circuit
        timeout: Request timeout in seconds
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = await get_circuit_breaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                timeout=timeout
            )

            # Execute with circuit breaker protection
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError:
                # Circuit is open - return graceful fallback
                logger.warning(f"Circuit {name} is OPEN - returning fallback")
                return {
                    "error": f"Service temporarily unavailable ({name})",
                    "circuit_breaker_open": True,
                    "retry_after": int(breaker.config.recovery_timeout)
                }
            except CircuitBreakerTimeoutError as e:
                # Timeout - return graceful error
                logger.error(f"Circuit {name} timeout: {e}")
                return {
                    "error": f"Service timeout ({name})",
                    "timeout": True
                }

        return wrapper
    return decorator
