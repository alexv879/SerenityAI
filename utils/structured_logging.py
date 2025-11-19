"""
Structured JSON Logging - Production-Grade Observability

Provides structured JSON logging for easy parsing by log aggregation systems.
Replaces text-based logging with machine-readable JSON format.

Features:
- JSON log output for CloudWatch/Datadog/ELK
- Automatic request context (trace ID, user ID, call SID)
- Log correlation across services
- PII redaction in production
- Performance metrics logging

Author: Claude Code
Date: 2025-11-19
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
import re
import traceback
import os

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
call_sid_var: ContextVar[Optional[str]] = ContextVar('call_sid', default=None)


class StructuredLogger:
    """
    Structured JSON logger with automatic context injection

    Usage:
        from utils.structured_logging import get_logger

        logger = get_logger(__name__)
        logger.info("User called", extra={
            "phone_number": "+44...",
            "call_duration": 120
        })

    Output:
        {
            "timestamp": "2025-11-19T10:30:45.123Z",
            "level": "INFO",
            "logger": "endpoints.conversation_handler",
            "message": "User called",
            "request_id": "req_abc123",
            "user_id": "+447411237771",
            "call_sid": "CA123...",
            "phone_number": "[REDACTED]",
            "call_duration": 120
        }
    """

    def __init__(self, name: str, enable_json: bool = True):
        """
        Initialize structured logger

        Args:
            name: Logger name (usually __name__)
            enable_json: Enable JSON output (default: True in production)
        """
        self.name = name
        self.enable_json = enable_json
        self.logger = logging.getLogger(name)

        # Detect environment
        self.is_production = os.getenv("ENV") == "production"

        # PII patterns for redaction
        self.pii_patterns = [
            (re.compile(r'\+?\d{10,15}'), '[PHONE_REDACTED]'),  # Phone numbers
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),  # Emails
            (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), '[CARD_REDACTED]'),  # Credit cards
            (re.compile(r'\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b', re.IGNORECASE), '[IBAN_REDACTED]'),  # IBAN
        ]

    def _redact_pii(self, text: str) -> str:
        """
        Redact PII from text in production

        Args:
            text: Input text

        Returns:
            Text with PII redacted
        """
        if not self.is_production:
            return text  # Don't redact in development

        for pattern, replacement in self.pii_patterns:
            text = pattern.sub(replacement, text)

        return text

    def _format_log_record(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> Dict[str, Any]:
        """
        Format log record as structured JSON

        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message
            extra: Additional fields
            exc_info: Exception info (if any)

        Returns:
            Structured log record dictionary
        """
        # Redact PII from message
        message = self._redact_pii(message)

        # Base log record
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": message,
            "environment": os.getenv("ENV", "unknown")
        }

        # Add request context
        request_id = request_id_var.get()
        if request_id:
            record["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            # Redact user ID in production
            record["user_id"] = self._redact_pii(user_id) if self.is_production else user_id

        call_sid = call_sid_var.get()
        if call_sid:
            record["call_sid"] = call_sid

        # Add extra fields
        if extra:
            for key, value in extra.items():
                # Redact PII in extra fields
                if isinstance(value, str):
                    value = self._redact_pii(value)
                record[key] = value

        # Add exception info
        if exc_info:
            record["exception"] = {
                "type": type(exc_info).__name__,
                "message": str(exc_info),
                "traceback": traceback.format_exc()
            }

        return record

    def _log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """
        Internal log method

        Args:
            level: Log level
            message: Log message
            extra: Additional fields
            exc_info: Exception info
        """
        if self.enable_json:
            # JSON format
            record = self._format_log_record(level, message, extra, exc_info)
            print(json.dumps(record), file=sys.stdout)
        else:
            # Standard text format (for development/debugging)
            log_method = getattr(self.logger, level.lower())
            log_method(message, extra=extra, exc_info=exc_info)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self._log("DEBUG", message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self._log("INFO", message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self._log("WARNING", message, extra)

    def error(
        self,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """Log error message with optional exception"""
        self._log("ERROR", message, extra, exc_info)

    def critical(
        self,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """Log critical message with optional exception"""
        self._log("CRITICAL", message, extra, exc_info)


def get_logger(name: str, enable_json: bool = None) -> StructuredLogger:
    """
    Get a structured logger instance

    Args:
        name: Logger name (usually __name__)
        enable_json: Enable JSON output (default: auto-detect from ENV)

    Returns:
        StructuredLogger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("User action", extra={"user_id": "123", "action": "call_started"})
    """
    if enable_json is None:
        # Auto-detect: JSON in production, text in development
        enable_json = os.getenv("ENV") == "production"

    return StructuredLogger(name, enable_json)


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    call_sid: Optional[str] = None
):
    """
    Set request context for automatic injection into logs

    Args:
        request_id: Unique request identifier
        user_id: User identifier (phone number, etc.)
        call_sid: Twilio call SID

    Usage:
        from utils.structured_logging import set_request_context

        # At start of request
        set_request_context(
            request_id="req_abc123",
            user_id="+447411237771",
            call_sid="CA123..."
        )

        # All subsequent logs will include this context
        logger.info("Processing request")  # Automatically includes request_id, user_id, call_sid
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if call_sid:
        call_sid_var.set(call_sid)


def clear_request_context():
    """
    Clear request context

    Call at end of request to avoid leaking context to other requests
    """
    request_id_var.set(None)
    user_id_var.set(None)
    call_sid_var.set(None)


class RequestContextMiddleware:
    """
    FastAPI middleware to automatically set request context

    Usage:
        from fastapi import FastAPI
        from utils.structured_logging import RequestContextMiddleware

        app = FastAPI()
        app.middleware("http")(RequestContextMiddleware())
    """

    def __init__(self):
        pass

    async def __call__(self, request, call_next):
        """Process request and inject context"""
        import uuid

        # Generate request ID
        request_id = str(uuid.uuid4())
        set_request_context(request_id=request_id)

        # Extract user context from request if available
        if hasattr(request.state, 'user_id'):
            set_request_context(user_id=request.state.user_id)

        if hasattr(request.state, 'call_sid'):
            set_request_context(call_sid=request.state.call_sid)

        # Process request
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear context after request
            clear_request_context()


class MetricsLogger:
    """
    Logger for performance metrics

    Usage:
        from utils.structured_logging import MetricsLogger

        metrics = MetricsLogger()
        metrics.log_latency("groq_api_call", duration_ms=123.45, success=True)
        metrics.log_cost("openai_api_call", cost_usd=0.0012, tokens=500)
    """

    def __init__(self):
        self.logger = get_logger("metrics")

    def log_latency(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log operation latency

        Args:
            operation: Operation name (e.g., "groq_api_call", "database_query")
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            extra: Additional fields
        """
        log_data = {
            "metric_type": "latency",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            **(extra or {})
        }
        self.logger.info(f"Operation latency: {operation}", extra=log_data)

    def log_cost(
        self,
        operation: str,
        cost_usd: float,
        tokens: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log operation cost

        Args:
            operation: Operation name (e.g., "openai_api_call", "twilio_call")
            cost_usd: Cost in USD
            tokens: Token count (if applicable)
            extra: Additional fields
        """
        log_data = {
            "metric_type": "cost",
            "operation": operation,
            "cost_usd": round(cost_usd, 6),
            **(extra or {})
        }
        if tokens is not None:
            log_data["tokens"] = tokens

        self.logger.info(f"Operation cost: {operation}", extra=log_data)

    def log_usage(
        self,
        operation: str,
        count: int = 1,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Log operation usage counter

        Args:
            operation: Operation name (e.g., "calls_started", "payments_processed")
            count: Count (default: 1)
            extra: Additional fields
        """
        log_data = {
            "metric_type": "usage",
            "operation": operation,
            "count": count,
            **(extra or {})
        }
        self.logger.info(f"Operation usage: {operation}", extra=log_data)


# Global metrics logger instance
_metrics_logger = MetricsLogger()


def get_metrics_logger() -> MetricsLogger:
    """Get the global metrics logger instance"""
    return _metrics_logger
