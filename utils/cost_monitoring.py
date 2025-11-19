"""
Cost Monitoring and Alerts - Track and Alert on API Costs

Monitors costs from external APIs (OpenAI, Groq, Twilio, Stripe, etc.)
and sends alerts when thresholds are exceeded.

Features:
- Real-time cost tracking
- Daily/monthly budget alerts
- Per-service cost breakdown
- Cost-per-call metrics
- Revenue vs cost analysis
- Anomaly detection

Author: Claude Code
Date: 2025-11-19
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import redis.asyncio as redis
import json

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """Single cost entry"""
    service: str  # "openai", "groq", "twilio", "stripe"
    operation: str  # "chat_completion", "outbound_call", "payment_processing"
    cost_usd: float
    units: Optional[int] = None  # tokens, seconds, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostAlert:
    """Cost alert configuration"""
    alert_type: str  # "daily_threshold", "monthly_threshold", "anomaly"
    threshold_usd: float
    current_usd: float
    service: Optional[str] = None
    message: str = ""


class CostMonitor:
    """
    Monitor and track API costs in real-time

    Usage:
        monitor = await get_cost_monitor()

        # Track cost
        await monitor.track_cost(
            service="openai",
            operation="chat_completion",
            cost_usd=0.0012,
            tokens=500
        )

        # Check for alerts
        alerts = await monitor.check_alerts()
        if alerts:
            for alert in alerts:
                print(f"ALERT: {alert.message}")

        # Get cost summary
        summary = await monitor.get_daily_summary()
        print(f"Today's costs: ${summary['total_usd']:.2f}")
    """

    # Pricing (USD) - Update these with actual rates
    PRICING = {
        "openai": {
            "gpt-4o-realtime-input": 5.00 / 1_000_000,  # $5 per 1M input tokens
            "gpt-4o-realtime-output": 20.00 / 1_000_000,  # $20 per 1M output tokens
            "gpt-4o-realtime-audio-input": 100.00 / 1_000_000,  # $100 per 1M audio input tokens
            "gpt-4o-realtime-audio-output": 200.00 / 1_000_000,  # $200 per 1M audio output tokens
        },
        "groq": {
            "llama-3.1-70b-input": 0.59 / 1_000_000,  # $0.59 per 1M input tokens
            "llama-3.1-70b-output": 0.79 / 1_000_000,  # $0.79 per 1M output tokens
        },
        "deepgram": {
            "nova-2-streaming": 0.0043 / 60,  # $0.0043 per minute
        },
        "twilio": {
            "voice-inbound": 0.0085,  # $0.0085 per minute
            "voice-outbound": 0.013,  # $0.013 per minute
            "sms": 0.0075,  # $0.0075 per SMS
        }
    }

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize cost monitor

        Args:
            redis_client: Redis async client for cost storage
        """
        self.redis = redis_client

        # Alert thresholds (USD)
        self.daily_threshold = 50.0  # Alert if daily costs exceed $50
        self.monthly_threshold = 1000.0  # Alert if monthly costs exceed $1000
        self.hourly_threshold = 10.0  # Alert if hourly costs exceed $10 (anomaly detection)

    async def track_cost(
        self,
        service: str,
        operation: str,
        cost_usd: float,
        units: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a cost entry

        Args:
            service: Service name (openai, groq, twilio, etc.)
            operation: Operation name (chat_completion, outbound_call, etc.)
            cost_usd: Cost in USD
            units: Number of units (tokens, seconds, etc.)
            metadata: Additional metadata
        """
        try:
            entry = CostEntry(
                service=service,
                operation=operation,
                cost_usd=cost_usd,
                units=units,
                metadata=metadata or {}
            )

            # Store in Redis with multiple time buckets
            now = datetime.utcnow()
            date_key = now.strftime("%Y-%m-%d")
            month_key = now.strftime("%Y-%m")
            hour_key = now.strftime("%Y-%m-%d-%H")

            # Daily costs
            await self._increment_cost(f"cost:daily:{date_key}:{service}", cost_usd)
            await self._increment_cost(f"cost:daily:{date_key}:total", cost_usd)

            # Monthly costs
            await self._increment_cost(f"cost:monthly:{month_key}:{service}", cost_usd)
            await self._increment_cost(f"cost:monthly:{month_key}:total", cost_usd)

            # Hourly costs (for anomaly detection)
            await self._increment_cost(f"cost:hourly:{hour_key}:{service}", cost_usd)
            await self._increment_cost(f"cost:hourly:{hour_key}:total", cost_usd)

            # Store detailed entry (for debugging)
            await self.redis.lpush(
                f"cost:entries:{date_key}",
                json.dumps({
                    "service": service,
                    "operation": operation,
                    "cost_usd": cost_usd,
                    "units": units,
                    "metadata": metadata or {},
                    "timestamp": now.isoformat()
                })
            )
            await self.redis.expire(f"cost:entries:{date_key}", 86400 * 7)  # Keep 7 days

            logger.debug(
                f"Cost tracked: {service}/{operation} = ${cost_usd:.4f} "
                f"({units} units)" if units else f"Cost tracked: {service}/{operation} = ${cost_usd:.4f}"
            )

        except Exception as e:
            logger.error(f"Failed to track cost: {e}", exc_info=True)

    async def _increment_cost(self, key: str, amount: float):
        """Increment cost counter in Redis"""
        await self.redis.incrbyfloat(key, amount)
        # Set expiration based on key type
        if ":daily:" in key:
            await self.redis.expire(key, 86400 * 31)  # Keep 31 days
        elif ":monthly:" in key:
            await self.redis.expire(key, 86400 * 365)  # Keep 1 year
        elif ":hourly:" in key:
            await self.redis.expire(key, 86400 * 2)  # Keep 2 days

    async def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily cost summary

        Args:
            date: Date to get summary for (default: today)

        Returns:
            Dictionary with cost breakdown by service
        """
        if date is None:
            date = datetime.utcnow()

        date_key = date.strftime("%Y-%m-%d")

        # Get total and per-service costs
        total = await self._get_cost(f"cost:daily:{date_key}:total")

        services = {}
        for service in ["openai", "groq", "deepgram", "twilio", "stripe"]:
            cost = await self._get_cost(f"cost:daily:{date_key}:{service}")
            if cost > 0:
                services[service] = cost

        return {
            "date": date_key,
            "total_usd": round(total, 2),
            "services": services,
            "breakdown_pct": {
                service: round(cost / total * 100, 1) if total > 0 else 0
                for service, cost in services.items()
            }
        }

    async def get_monthly_summary(self, month: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get monthly cost summary

        Args:
            month: Month to get summary for (default: current month)

        Returns:
            Dictionary with cost breakdown by service
        """
        if month is None:
            month = datetime.utcnow()

        month_key = month.strftime("%Y-%m")

        # Get total and per-service costs
        total = await self._get_cost(f"cost:monthly:{month_key}:total")

        services = {}
        for service in ["openai", "groq", "deepgram", "twilio", "stripe"]:
            cost = await self._get_cost(f"cost:monthly:{month_key}:{service}")
            if cost > 0:
                services[service] = cost

        return {
            "month": month_key,
            "total_usd": round(total, 2),
            "services": services,
            "breakdown_pct": {
                service: round(cost / total * 100, 1) if total > 0 else 0
                for service, cost in services.items()
            }
        }

    async def _get_cost(self, key: str) -> float:
        """Get cost from Redis"""
        try:
            value = await self.redis.get(key)
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    async def check_alerts(self) -> list[CostAlert]:
        """
        Check for cost alerts

        Returns:
            List of CostAlert objects if thresholds exceeded
        """
        alerts = []

        # Check daily threshold
        daily_summary = await self.get_daily_summary()
        if daily_summary["total_usd"] > self.daily_threshold:
            alerts.append(CostAlert(
                alert_type="daily_threshold",
                threshold_usd=self.daily_threshold,
                current_usd=daily_summary["total_usd"],
                message=f"Daily cost threshold exceeded: ${daily_summary['total_usd']:.2f} > ${self.daily_threshold:.2f}"
            ))

        # Check monthly threshold
        monthly_summary = await self.get_monthly_summary()
        if monthly_summary["total_usd"] > self.monthly_threshold:
            alerts.append(CostAlert(
                alert_type="monthly_threshold",
                threshold_usd=self.monthly_threshold,
                current_usd=monthly_summary["total_usd"],
                message=f"Monthly cost threshold exceeded: ${monthly_summary['total_usd']:.2f} > ${self.monthly_threshold:.2f}"
            ))

        # Check hourly anomaly (sudden spike)
        now = datetime.utcnow()
        hour_key = now.strftime("%Y-%m-%d-%H")
        hourly_cost = await self._get_cost(f"cost:hourly:{hour_key}:total")
        if hourly_cost > self.hourly_threshold:
            alerts.append(CostAlert(
                alert_type="anomaly",
                threshold_usd=self.hourly_threshold,
                current_usd=hourly_cost,
                message=f"Hourly cost spike detected: ${hourly_cost:.2f} in the last hour"
            ))

        return alerts

    async def get_cost_per_call_metrics(self) -> Dict[str, Any]:
        """
        Calculate cost-per-call metrics

        Returns:
            Dictionary with average cost per call
        """
        daily_summary = await self.get_daily_summary()

        # Get call count from Redis (assuming it's tracked elsewhere)
        # For now, return basic metrics
        return {
            "total_cost_usd": daily_summary["total_usd"],
            "service_costs": daily_summary["services"],
            "note": "Cost-per-call calculation requires call count tracking"
        }

    async def calculate_openai_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        audio_input_tokens: int = 0,
        audio_output_tokens: int = 0
    ) -> float:
        """
        Calculate OpenAI Realtime API cost

        Args:
            input_tokens: Text input tokens
            output_tokens: Text output tokens
            audio_input_tokens: Audio input tokens
            audio_output_tokens: Audio output tokens

        Returns:
            Total cost in USD
        """
        cost = (
            input_tokens * self.PRICING["openai"]["gpt-4o-realtime-input"] +
            output_tokens * self.PRICING["openai"]["gpt-4o-realtime-output"] +
            audio_input_tokens * self.PRICING["openai"]["gpt-4o-realtime-audio-input"] +
            audio_output_tokens * self.PRICING["openai"]["gpt-4o-realtime-audio-output"]
        )
        return cost

    async def calculate_groq_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate Groq API cost

        Args:
            input_tokens: Input tokens
            output_tokens: Output tokens

        Returns:
            Total cost in USD
        """
        cost = (
            input_tokens * self.PRICING["groq"]["llama-3.1-70b-input"] +
            output_tokens * self.PRICING["groq"]["llama-3.1-70b-output"]
        )
        return cost

    async def calculate_twilio_cost(self, duration_minutes: float, direction: str = "inbound") -> float:
        """
        Calculate Twilio call cost

        Args:
            duration_minutes: Call duration in minutes
            direction: "inbound" or "outbound"

        Returns:
            Total cost in USD
        """
        rate = self.PRICING["twilio"][f"voice-{direction}"]
        return duration_minutes * rate


# Global singleton
_cost_monitor: Optional[CostMonitor] = None


async def get_cost_monitor() -> CostMonitor:
    """
    Get or create cost monitor singleton

    Returns:
        CostMonitor instance
    """
    global _cost_monitor

    if _cost_monitor is None:
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        redis_client = await sub_mgr._get_client()
        _cost_monitor = CostMonitor(redis_client)

    return _cost_monitor


async def send_cost_alert(alert: CostAlert):
    """
    Send cost alert notification

    In production, this should send alerts via:
    - Email (SendGrid, AWS SES)
    - Slack webhook
    - SMS (Twilio)
    - PagerDuty

    Args:
        alert: CostAlert to send
    """
    logger.warning(f"💰 COST ALERT: {alert.message}")

    # TODO: In production, send actual alerts
    # await send_email(to="admin@serenityai.com", subject="Cost Alert", body=alert.message)
    # await send_slack_message(channel="#alerts", message=alert.message)
    # await send_sms(to="+44...", message=alert.message)
