"""
Reminder Scheduler - Redis-based reminder system with Twilio outbound calls

Allows elderly users to set reminders that trigger outbound Twilio calls.
Critical feature - AI promises this works, must deliver!

Features:
- Natural language time parsing ("in 30 minutes", "tomorrow at 2pm")
- Redis sorted set for efficient scheduling
- Background worker checks for due reminders
- Twilio outbound call when reminder due
- Retry logic for failed calls

Author: Claude Code
Date: 2025-11-19
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import redis.asyncio as redis
from twilio.rest import Client as TwilioClient
import os
import re

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Manages reminder scheduling and execution via Redis + Twilio

    Usage:
        scheduler = await get_reminder_scheduler()
        await scheduler.create_reminder(
            phone_number="+447411123456",
            reminder_text="Take your medication",
            when="in 30 minutes"
        )
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize reminder scheduler

        Args:
            redis_client: Redis async client
        """
        self.redis = redis_client
        self.reminders_key = "scheduled_reminders"

    async def create_reminder(
        self,
        phone_number: str,
        reminder_text: str,
        when: str
    ) -> Dict[str, Any]:
        """
        Create a new reminder

        Args:
            phone_number: User's phone number
            reminder_text: What to remind them about
            when: Natural language time ("in 30 minutes", "tomorrow at 2pm", "at 9 AM")

        Returns:
            Reminder creation result
        """
        try:
            # Parse natural language time to timestamp
            reminder_time = self._parse_time(when)

            if not reminder_time:
                return {
                    "success": False,
                    "error": "Could not understand time",
                    "message": "I didn't quite understand when you want the reminder. Could you try something like 'in 30 minutes' or 'tomorrow at 2 PM'?"
                }

            # Check if time is in the past
            if reminder_time <= datetime.utcnow():
                return {
                    "success": False,
                    "error": "Time in past",
                    "message": "That time has already passed. When would you like me to remind you?"
                }

            # Create reminder object
            reminder = {
                "phone_number": phone_number,
                "reminder_text": reminder_text,
                "when_requested": when,
                "scheduled_time": reminder_time.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "retry_count": 0
            }

            # Add to Redis sorted set (score = unix timestamp)
            score = reminder_time.timestamp()
            reminder_id = f"reminder:{phone_number}:{score}"

            await self.redis.zadd(
                self.reminders_key,
                {json.dumps(reminder): score}
            )

            # Calculate friendly time message
            time_until = self._format_time_until(reminder_time)

            logger.info(
                f"Created reminder for {phone_number}: '{reminder_text}' "
                f"at {reminder_time.isoformat()} ({time_until})"
            )

            return {
                "success": True,
                "reminder_id": reminder_id,
                "scheduled_time": reminder_time.isoformat(),
                "message": f"Alright, I'll remind you to {reminder_text} {time_until}. I'll give you a call when it's time."
            }

        except ValueError as e:
            logger.error(f"Time parsing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "I had trouble understanding that time. Try saying something like 'in 2 hours' or 'tomorrow morning at 9 AM'."
            }
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to create reminder: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "I had trouble setting that reminder. Could you try again?"
            }

    def _parse_time(self, when: str) -> Optional[datetime]:
        """
        Parse natural language time to datetime

        Args:
            when: Natural language time string

        Returns:
            Datetime object or None if parsing fails
        """
        when = when.lower().strip()
        now = datetime.utcnow()

        # Pattern: "in X minutes/hours/days"
        match = re.search(r'in\s+(\d+)\s+(minute|hour|day|week)s?', when)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            if unit == "minute":
                return now + timedelta(minutes=amount)
            elif unit == "hour":
                return now + timedelta(hours=amount)
            elif unit == "day":
                return now + timedelta(days=amount)
            elif unit == "week":
                return now + timedelta(weeks=amount)

        # Pattern: "at 9 AM", "at 2:30 PM"
        match = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', when, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            am_pm = match.group(3).lower() if match.group(3) else None

            # Convert to 24-hour
            if am_pm == 'pm' and hour < 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0

            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If time has passed today, schedule for tomorrow
            if target_time <= now:
                target_time += timedelta(days=1)

            return target_time

        # Pattern: "tomorrow at 2pm", "tomorrow morning"
        if "tomorrow" in when:
            tomorrow = now + timedelta(days=1)

            if "morning" in when:
                return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            elif "afternoon" in when:
                return tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            elif "evening" in when:
                return tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
            else:
                # Try to extract specific time
                match = re.search(r'(\d{1,2})\s*(am|pm)?', when, re.IGNORECASE)
                if match:
                    hour = int(match.group(1))
                    am_pm = match.group(2).lower() if match.group(2) else None

                    if am_pm == 'pm' and hour < 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0

                    return tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)

                return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

        # Fallback: Try dateutil parser
        try:
            return date_parser.parse(when, fuzzy=True)
        except:
            return None

    def _format_time_until(self, target_time: datetime) -> str:
        """
        Format friendly time until message

        Args:
            target_time: Target datetime

        Returns:
            Friendly string like "in 30 minutes" or "tomorrow at 2:00 PM"
        """
        now = datetime.utcnow()
        diff = target_time - now

        # Less than an hour
        if diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"

        # Less than 24 hours
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"

        # Tomorrow
        elif diff.days == 1:
            time_str = target_time.strftime("%-I:%M %p")
            return f"tomorrow at {time_str}"

        # Multiple days
        else:
            return target_time.strftime("%A at %-I:%M %p")

    async def get_due_reminders(self) -> List[Dict[str, Any]]:
        """
        Get all reminders that are due now

        Returns:
            List of due reminders
        """
        try:
            now_timestamp = datetime.utcnow().timestamp()

            # Get all reminders with score <= now
            reminders_json = await self.redis.zrangebyscore(
                self.reminders_key,
                0,
                now_timestamp,
                withscores=False
            )

            reminders = []
            for reminder_json in reminders_json:
                if isinstance(reminder_json, bytes):
                    reminder_json = reminder_json.decode('utf-8')
                reminders.append(json.loads(reminder_json))

            logger.info(f"Found {len(reminders)} due reminders")
            return reminders

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get due reminders: {e}", exc_info=True)
            return []

    async def execute_reminder(self, reminder: Dict[str, Any]) -> bool:
        """
        Execute a reminder by making outbound Twilio call

        Args:
            reminder: Reminder dict

        Returns:
            True if successful
        """
        try:
            phone_number = reminder["phone_number"]
            reminder_text = reminder["reminder_text"]

            # Make outbound Twilio call
            twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

            if not all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
                logger.error("Twilio credentials not configured")
                return False

            client = TwilioClient(twilio_account_sid, twilio_auth_token)

            # Create TwiML for reminder
            twiml_url = f"{os.getenv('PUBLIC_BASE_URL')}/reminder/twiml?text={reminder_text}"

            # Make call
            call = client.calls.create(
                to=phone_number,
                from_=twilio_phone_number,
                url=twiml_url,
                status_callback=f"{os.getenv('PUBLIC_BASE_URL')}/reminder/status",
                status_callback_event=["completed"]
            )

            logger.info(
                f"Reminder call initiated: {call.sid} to {phone_number} "
                f"for '{reminder_text}'"
            )

            # Remove from Redis sorted set
            await self.redis.zrem(self.reminders_key, json.dumps(reminder))

            return True

        except Exception as e:
            logger.error(f"Failed to execute reminder: {e}", exc_info=True)

            # Retry logic: increment retry count
            reminder["retry_count"] = reminder.get("retry_count", 0) + 1

            if reminder["retry_count"] < 3:
                # Retry in 5 minutes
                retry_time = datetime.utcnow() + timedelta(minutes=5)
                retry_score = retry_time.timestamp()

                await self.redis.zadd(
                    self.reminders_key,
                    {json.dumps(reminder): retry_score}
                )

                logger.info(f"Reminder scheduled for retry ({reminder['retry_count']}/3)")
            else:
                logger.error(f"Reminder failed after 3 retries, giving up")
                await self.redis.zrem(self.reminders_key, json.dumps(reminder))

            return False

    async def list_upcoming_reminders(self, phone_number: str) -> List[Dict[str, Any]]:
        """
        Get list of upcoming reminders for a user

        Args:
            phone_number: User's phone number

        Returns:
            List of upcoming reminders
        """
        try:
            # Get all future reminders
            now_timestamp = datetime.utcnow().timestamp()
            all_reminders_json = await self.redis.zrangebyscore(
                self.reminders_key,
                now_timestamp,
                "+inf",
                withscores=True
            )

            user_reminders = []
            for reminder_json, score in all_reminders_json:
                if isinstance(reminder_json, bytes):
                    reminder_json = reminder_json.decode('utf-8')

                reminder = json.loads(reminder_json)
                if reminder["phone_number"] == phone_number:
                    user_reminders.append(reminder)

            return user_reminders

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to list reminders: {e}", exc_info=True)
            return []


# Singleton instance
_reminder_scheduler: Optional[ReminderScheduler] = None


async def get_reminder_scheduler() -> ReminderScheduler:
    """
    Get or create reminder scheduler singleton

    Returns:
        ReminderScheduler instance
    """
    global _reminder_scheduler

    if _reminder_scheduler is None:
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        redis_client = await sub_mgr._get_client()
        _reminder_scheduler = ReminderScheduler(redis_client)

    return _reminder_scheduler


async def reminder_worker_loop():
    """
    Background worker that checks for due reminders every minute

    Run this in a separate asyncio task or as a cron job
    """
    logger.info("Reminder worker started")

    while True:
        try:
            scheduler = await get_reminder_scheduler()
            due_reminders = await scheduler.get_due_reminders()

            for reminder in due_reminders:
                await scheduler.execute_reminder(reminder)

            # Check every 30 seconds
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Reminder worker error: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait longer on error
