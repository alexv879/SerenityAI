"""
Subscription Manager - Track customer subscriptions and usage
Uses Redis for fast access to subscription status during calls

Author: Claude Code
Date: 2025-10-29
"""

import asyncio
import redis.asyncio as redis
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import os

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages customer subscriptions and usage tracking
    
    Stores:
    - Subscription status (trial, active, expired)
    - Payment method ID (Stripe)
    - Usage hours for pay-per-hour model
    - Trial period tracking
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        # Safe defaults
        self.trial_minutes: int = int(os.getenv("FREE_TRIAL_MINUTES", "5"))
        self.price_per_hour: float = float(os.getenv("PRICE_PER_HOUR", "6.00"))

    async def _get_client(self):
        """Get or create Redis connection"""
        if not self.redis_client:
            self.redis_client = await redis.from_url(self.redis_url)
        return self.redis_client

    def _hash_phone(self, phone: str) -> str:
        """SHA256 hash of phone number for privacy"""
        return hashlib.sha256(phone.encode()).hexdigest()

    async def check_active_subscription(self, phone: str) -> Dict:
        """
        Check if phone has active subscription with minutes remaining

        Returns:
            {
                "active": bool,
                "minutes_remaining": int,
                "expires_at": str (ISO timestamp),
                "tier": "standard" | "premium"
            }
        """
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        # Get subscription data
        key = f"user:{phone_hash}:subscription"
        data = await client.get(key)

        if not data:
            return {"active": False, "minutes_remaining": 0}

        sub = json.loads(data)

        # Check if expired
        expires_at = datetime.fromisoformat(sub["expires_at"])
        if datetime.utcnow() > expires_at:
            # Expired, deactivate
            sub["active"] = False
            sub["minutes_remaining"] = 0
            await client.set(key, json.dumps(sub))

        return sub

    async def get_subscription(self, phone: str) -> Optional[Dict]:
        """Legacy method - calls check_active_subscription for compatibility"""
        return await self.check_active_subscription(phone)

    async def can_use_ai(self, phone_number: str) -> bool:
        """
        CRITICAL: Check if customer is allowed to use AI services

        Returns False if:
        - Trial expired and no payment
        - Subscription cancelled

        Returns True if:
        - New customer (trial not started)
        - Trial active and under limit
        - Paid subscriber

        Args:
            phone_number: Customer's phone number

        Returns:
            True if allowed to use AI, False if payment required
        """
        try:
            subscription = await self.get_subscription(phone_number)

            if not subscription:
                return True  # New customer, allow trial

            status = subscription.get("subscription_status", "trial")

            # Allowed statuses
            if status == "active":
                return True  # Paid subscriber

            if status == "trial":
                # Check if trial limit reached
                minutes_used = subscription.get("minutes_used_in_trial", 0)
                if minutes_used >= self.trial_minutes:
                    logger.warning(f"[{phone_number}] BLOCKED: Trial limit reached ({minutes_used} min)")
                    return False
                return True  # Trial still active

            # Blocked statuses
            if status in ["trial_expired", "expired", "cancelled"]:
                logger.warning(f"[{phone_number}] BLOCKED: Status is {status}")
                return False

            # Unknown status, fail closed
            logger.error(f"[{phone_number}] Unknown status: {status}, blocking access")
            return False

        except Exception as e:
            logger.error(f"[{phone_number}] Error checking AI access: {e}")
            return False  # Fail closed (block access on error)
    
    async def create_trial(self, phone_number: str, call_sid: str) -> Dict:
        """
        Create a new trial subscription when customer calls for first time
        
        Args:
            phone_number: Customer's phone number
            call_sid: Twilio call SID
            
        Returns:
            New subscription data
        """
        try:
            now = datetime.utcnow()
            trial_ends = now + timedelta(minutes=self.trial_minutes)
            
            subscription = {
                "phone_number": phone_number,
                "subscription_status": "trial",  # trial, active, expired, cancelled
                "payment_method_id": None,
                "subscription_created": now.isoformat(),
                "trial_started": now.isoformat(),
                "trial_started_call_sid": call_sid,
                "trial_ends": trial_ends.isoformat(),
                "minutes_used_in_trial": 0,
                "hours_used_this_month": 0.0,
                "last_call_date": now.isoformat(),
                "total_calls": 1,
                "pricing_plan": "per_hour",  # per_hour or unlimited
                "price_per_hour": self.price_per_hour
            }
            
            client = await self._get_client()
            phone_hash = self._hash_phone(phone_number)
            key = f"user:{phone_hash}:subscription"
            await client.set(key, json.dumps(subscription))
            
            logger.info(f"[{phone_number}] Created trial subscription (expires: {trial_ends})")
            return subscription
            
        except Exception as e:
            logger.error(f"[{phone_number}] Error creating trial: {e}")
            raise
    
    async def is_trial_expired(self, phone_number: str) -> bool:
        """
        Check if customer's trial period has expired

        Args:
            phone_number: Customer's phone number

        Returns:
            True if trial expired, False if still valid or already subscribed
        """
        try:
            subscription = await self.get_subscription(phone_number)

            if not subscription:
                return False  # New customer, trial not started yet

            if subscription["subscription_status"] == "active":
                return False  # Already paid, no trial check needed

            if subscription["subscription_status"] != "trial":
                return True  # Expired or cancelled

            # Check if trial minutes have been used up
            minutes_used = subscription.get("minutes_used_in_trial", 0)
            if minutes_used >= self.trial_minutes:
                logger.info(f"[{phone_number}] Trial expired - used {minutes_used} of {self.trial_minutes} minutes")
                # Mark as expired in Redis
                subscription["subscription_status"] = "trial_expired"
                client = await self._get_client()
                key = f"user:{self._hash_phone(phone_number)}:subscription"
                await client.set(key, json.dumps(subscription))
                return True

            # Check if trial time has expired (fallback)
            trial_ends = datetime.fromisoformat(subscription["trial_ends"])
            now = datetime.utcnow()

            if now > trial_ends:
                logger.info(f"[{phone_number}] Trial expired at {trial_ends}")
                subscription["subscription_status"] = "trial_expired"
                client = await self._get_client()
                key = f"user:{self._hash_phone(phone_number)}:subscription"
                await client.set(key, json.dumps(subscription))
                return True

            return False

        except Exception as e:
            logger.error(f"[{phone_number}] Error checking trial expiry: {e}")
            return True  # Fail closed (require payment on error)
    
    async def update_trial_usage(self, phone_number: str, minutes_used: float):
        """
        Update how many minutes customer has used in their trial

        CRITICAL: This must be called on EVERY turn to enforce trial limits

        Args:
            phone_number: Customer's phone number
            minutes_used: Total minutes used so far in trial
        """
        try:
            subscription = await self.get_subscription(phone_number)
            if not subscription:
                return

            subscription["minutes_used_in_trial"] = minutes_used

            # Auto-expire if limit reached
            if minutes_used >= self.trial_minutes:
                subscription["subscription_status"] = "trial_expired"
                logger.warning(f"[{phone_number}] AUTO-EXPIRED: Used {minutes_used} of {self.trial_minutes} minutes")

            client = await self._get_client()
            key = f"user:{self._hash_phone(phone_number)}:subscription"
            await client.set(key, json.dumps(subscription))

            logger.debug(f"[{phone_number}] Updated trial usage: {minutes_used}/{self.trial_minutes} minutes")

        except Exception as e:
            logger.error(f"[{phone_number}] Error updating trial usage: {e}")
    
    async def activate_subscription(self, phone_number: str, payment_method_id: str):
        """
        Activate subscription after successful payment
        
        Args:
            phone_number: Customer's phone number
            payment_method_id: Stripe payment method ID
        """
        try:
            subscription = await self.get_subscription(phone_number)
            
            if not subscription:
                # Create new subscription if doesn't exist
                subscription = {
                    "phone_number": phone_number,
                    "subscription_created": datetime.utcnow().isoformat(),
                    "hours_used_this_month": 0.0,
                    "total_calls": 0,
                    "pricing_plan": "per_hour",
                    "price_per_hour": self.price_per_hour
                }
            
            # Update to active status
            subscription["subscription_status"] = "active"
            subscription["payment_method_id"] = payment_method_id
            subscription["activated_at"] = datetime.utcnow().isoformat()
            
            client = await self._get_client()
            key = f"user:{self._hash_phone(phone_number)}:subscription"
            await client.set(key, json.dumps(subscription))
            
            logger.info(f"[{phone_number}] Activated subscription with payment method {payment_method_id}")
            
        except Exception as e:
            logger.error(f"[{phone_number}] Error activating subscription: {e}")
            raise
    
    async def log_call(self, phone_number: str, call_sid: str, duration_minutes: float):
        """
        Log a call and update usage hours
        
        Args:
            phone_number: Customer's phone number
            call_sid: Twilio call SID
            duration_minutes: Call duration in minutes
        """
        try:
            subscription = await self.get_subscription(phone_number)
            
            if not subscription:
                logger.warning(f"[{phone_number}] No subscription found when logging call")
                return
            
            # Update usage
            hours_used = duration_minutes / 60.0
            subscription["hours_used_this_month"] += hours_used
            subscription["total_calls"] += 1
            subscription["last_call_date"] = datetime.utcnow().isoformat()
            
            key = f"subscription:{phone_number}"
            client = await self._get_client()
            await client.set(key, json.dumps(subscription))
            
            # Also log to call history (for billing)
            client = await self._get_client()
            call_key = f"call:{call_sid}"
            call_data = {
                "phone_number": phone_number,
                "call_sid": call_sid,
                "started_at": datetime.utcnow().isoformat(),
                "duration_minutes": duration_minutes,
                "hours": hours_used,
                "cost_estimate": hours_used * self.price_per_hour
            }
            await client.set(call_key, json.dumps(call_data))
            await client.expire(call_key, 60 * 60 * 24 * 90)  # Keep for 90 days
            
            logger.info(f"[{phone_number}] Logged call: {duration_minutes} min, total: {subscription['hours_used_this_month']:.2f} hours this month")
            
        except Exception as e:
            logger.error(f"[{phone_number}] Error logging call: {e}")
    
    async def get_monthly_usage(self, phone_number: str) -> Dict:
        """
        Get customer's usage for the current month
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Dict with usage stats
        """
        try:
            subscription = await self.get_subscription(phone_number)
            
            if not subscription:
                return {
                    "hours_used": 0.0,
                    "estimated_cost": 0.0,
                    "pricing_plan": "per_hour"
                }
            
            hours = subscription.get("hours_used_this_month", 0.0)
            cost = hours * subscription.get("price_per_hour", self.price_per_hour)
            
            return {
                "hours_used": hours,
                "estimated_cost": cost,
                "pricing_plan": subscription.get("pricing_plan", "per_hour"),
                "total_calls": subscription.get("total_calls", 0)
            }
            
        except Exception as e:
            logger.error(f"[{phone_number}] Error getting usage: {e}")
            return {"hours_used": 0.0, "estimated_cost": 0.0}
    
    async def reset_monthly_usage(self, phone_number: str):
        """
        Reset usage hours at the start of a new billing month
        Called by a monthly billing cron job
        
        Args:
            phone_number: Customer's phone number
        """
        try:
            subscription = await self.get_subscription(phone_number)
            
            if not subscription:
                return
            
            # Save previous month's usage to history
            client = await self._get_client()
            phone_hash = self._hash_phone(phone_number)
            history_key = f"billing:{phone_hash}:{datetime.utcnow().strftime('%Y-%m')}"
            history_data = {
                "phone_number": phone_number,
                "month": datetime.utcnow().strftime('%Y-%m'),
                "hours_used": subscription.get("hours_used_this_month", 0.0),
                "amount_charged": subscription.get("hours_used_this_month", 0.0) * subscription.get("price_per_hour", self.price_per_hour),
                "billed_at": datetime.utcnow().isoformat()
            }
            await client.set(history_key, json.dumps(history_data))
            await client.expire(history_key, 60 * 60 * 24 * 365 * 7)  # Keep for 7 years (tax requirement)
            
            # Reset current month's usage
            subscription["hours_used_this_month"] = 0.0
            subscription["last_billed_at"] = datetime.utcnow().isoformat()
            
            key = f"user:{phone_hash}:subscription"
            await client.set(key, json.dumps(subscription))
            
            logger.info(f"[{phone_number}] Reset monthly usage, billed {history_data['amount_charged']:.2f}")
            
        except Exception as e:
            logger.error(f"[{phone_number}] Error resetting usage: {e}")
    
    async def create_subscription(
        self,
        phone: str,
        payment_id: str,
        minutes: int = 60
    ):
        """
        Create new subscription after successful payment

        Args:
            phone: Customer phone number
            payment_id: Stripe charge ID
            minutes: Minutes purchased (default 60)
        """
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        expires_at = datetime.utcnow() + timedelta(hours=1)

        subscription = {
            "active": True,
            "minutes_remaining": minutes,
            "expires_at": expires_at.isoformat(),
            "tier": "standard",
            "stripe_payment_id": payment_id,
            "created_at": datetime.utcnow().isoformat(),
            "total_minutes_purchased": minutes
        }

        key = f"user:{phone_hash}:subscription"
        await client.set(key, json.dumps(subscription))

        # Log purchase
        await self.log_purchase(phone, payment_id, minutes, 6.00)

    async def log_call_start(self, phone: str, call_sid: str):
        """Log when call starts"""
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        call_data = {
            "call_sid": call_sid,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in-progress"
        }

        key = f"user:{phone_hash}:current_call"
        await client.set(key, json.dumps(call_data), ex=7200)  # 2 hour expiry

    async def log_call_end(
        self,
        phone: str,
        call_sid: str,
        duration_seconds: int
    ):
        """
        Log call end and deduct minutes from subscription

        Args:
            phone: Customer phone number
            call_sid: Twilio call SID
            duration_seconds: Total call duration
        """
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        # Calculate minutes used (round up)
        minutes_used = (duration_seconds + 59) // 60  # Ceiling division

        # Update subscription
        sub_key = f"user:{phone_hash}:subscription"
        sub_data = await client.get(sub_key)

        if sub_data:
            subscription = json.loads(sub_data)
            subscription["minutes_remaining"] = max(
                0,
                subscription["minutes_remaining"] - minutes_used
            )

            # Deactivate if no minutes left
            if subscription["minutes_remaining"] == 0:
                subscription["active"] = False

            await client.set(sub_key, json.dumps(subscription))

        # Log to usage history
        usage_key = f"user:{phone_hash}:usage_log"
        usage_entry = {
            "call_sid": call_sid,
            "duration_seconds": duration_seconds,
            "minutes_charged": minutes_used,
            "timestamp": datetime.utcnow().isoformat()
        }
        await client.rpush(usage_key, json.dumps(usage_entry))

        # Remove current call
        await client.delete(f"user:{phone_hash}:current_call")

    async def get_remaining_minutes(self, phone: str) -> int:
        """Get minutes remaining for phone number"""
        subscription = await self.check_active_subscription(phone)
        return subscription.get("minutes_remaining", 0)

    async def log_purchase(
        self,
        phone: str,
        payment_id: str,
        minutes: int,
        amount: float
    ):
        """Log purchase to history"""
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        purchase = {
            "payment_id": payment_id,
            "minutes": minutes,
            "amount_gbp": amount,
            "timestamp": datetime.utcnow().isoformat()
        }

        key = f"user:{phone_hash}:purchase_history"
        await client.rpush(key, json.dumps(purchase))

    async def cancel_subscription(self, phone: str):
        """Cancel/deactivate subscription"""
        client = await self._get_client()
        phone_hash = self._hash_phone(phone)

        key = f"user:{phone_hash}:subscription"
        data = await client.get(key)

        if data:
            subscription = json.loads(data)
            subscription["active"] = False
            subscription["minutes_remaining"] = 0
            subscription["cancelled_at"] = datetime.utcnow().isoformat()
            await client.set(key, json.dumps(subscription))

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global instance (initialized in main.py lifespan)
subscription_manager = None
_manager_lock = asyncio.Lock()


async def get_subscription_manager() -> SubscriptionManager:
    """
    Get the global subscription manager instance (thread-safe)
    Used in FastAPI dependency injection
    """
    global subscription_manager
    if subscription_manager is None:
        async with _manager_lock:
            if subscription_manager is None:  # Double-check after acquiring lock
                subscription_manager = SubscriptionManager()
    return subscription_manager
