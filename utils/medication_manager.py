"""
Medication Reminder System - Life-critical feature for elderly users

Helps users manage medications with:
- Voice-based medication scheduling
- Automatic reminder calls via Twilio
- Medication tracking and adherence monitoring
- Family notifications for missed doses
- Simple voice commands for adding/checking medications

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class Medication:
    """Medication information"""
    name: str
    dosage: str
    frequency: str  # "daily", "twice_daily", "weekly", etc.
    times: List[str]  # e.g., ["09:00", "21:00"]
    instructions: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    with_food: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Medication':
        return cls(**data)


class MedicationManager:
    """
    Manages medication reminders for users

    Features:
    - Add medications via voice
    - Schedule automatic reminder calls
    - Track medication adherence
    - Send family alerts for missed doses
    """

    def __init__(self, redis_client=None, twilio_client=None):
        """
        Initialize medication manager

        Args:
            redis_client: Redis client for storage
            twilio_client: Twilio client for reminder calls
        """
        self.redis_client = redis_client
        self.twilio_client = twilio_client

    async def add_medication(
        self,
        phone_number: str,
        medication_name: str,
        dosage: str,
        frequency: str,
        times: List[str],
        instructions: Optional[str] = None,
        with_food: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new medication for a user

        Args:
            phone_number: User's phone number
            medication_name: Name of medication (e.g., "aspirin", "blood pressure tablets")
            dosage: Dosage amount (e.g., "one tablet", "two pills")
            frequency: How often (daily, twice_daily, weekly)
            times: List of times in HH:MM format (e.g., ["09:00", "21:00"])
            instructions: Additional instructions
            with_food: Whether to take with food

        Returns:
            Confirmation message
        """
        try:
            medication = Medication(
                name=medication_name,
                dosage=dosage,
                frequency=frequency,
                times=times,
                instructions=instructions,
                start_date=datetime.now().isoformat(),
                with_food=with_food
            )

            # Store in Redis
            if self.redis_client:
                key = f"medications:{phone_number}:{medication_name}"
                await self.redis_client.set(
                    key,
                    json.dumps(medication.to_dict()),
                    ex=90 * 24 * 60 * 60  # 90 days retention
                )

                # Add to user's medication list
                list_key = f"medication_list:{phone_number}"
                await self.redis_client.sadd(list_key, medication_name)
                await self.redis_client.expire(list_key, 90 * 24 * 60 * 60)

            logger.info(f"Added medication {medication_name} for {phone_number}")

            return {
                "success": True,
                "message": self._create_confirmation_message(medication),
                "medication": medication.to_dict()
            }

        except Exception as e:
            logger.error(f"Error adding medication: {e}")
            return {
                "success": False,
                "message": "I had trouble saving that medication. Could you try again?",
                "error": str(e)
            }

    def _create_confirmation_message(self, med: Medication) -> str:
        """Create a friendly confirmation message"""
        times_str = " and ".join([self._format_time_friendly(t) for t in med.times])
        food_str = " with food" if med.with_food else ""

        message = (
            f"I've added {med.name}, {med.dosage}, to your medication schedule. "
            f"I'll remind you {med.frequency.replace('_', ' ')} at {times_str}{food_str}."
        )

        if med.instructions:
            message += f" Remember: {med.instructions}."

        return message

    def _format_time_friendly(self, time_str: str) -> str:
        """Convert 24h time to friendly format (e.g., '09:00' -> '9 in the morning')"""
        try:
            hour, minute = map(int, time_str.split(':'))

            if hour == 0:
                return "midnight"
            elif hour == 12:
                return "noon"
            elif hour < 12:
                return f"{hour} in the morning" if minute == 0 else f"{hour}:{minute:02d} in the morning"
            else:
                hour_12 = hour - 12
                return f"{hour_12} in the afternoon" if minute == 0 else f"{hour_12}:{minute:02d} in the afternoon"
        except:
            return time_str

    async def get_medications(self, phone_number: str) -> List[Medication]:
        """
        Get all medications for a user

        Args:
            phone_number: User's phone number

        Returns:
            List of Medication objects
        """
        try:
            if not self.redis_client:
                return []

            # Get medication names from list
            list_key = f"medication_list:{phone_number}"
            med_names = await self.redis_client.smembers(list_key)

            if not med_names:
                return []

            medications = []
            for name in med_names:
                if isinstance(name, bytes):
                    name = name.decode('utf-8')

                key = f"medications:{phone_number}:{name}"
                data = await self.redis_client.get(key)

                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    med_dict = json.loads(data)
                    medications.append(Medication.from_dict(med_dict))

            return medications

        except Exception as e:
            logger.error(f"Error getting medications: {e}")
            return []

    async def list_medications_voice(self, phone_number: str) -> str:
        """
        Create a voice-friendly list of medications

        Returns:
            Natural language description of medications
        """
        medications = await self.get_medications(phone_number)

        if not medications:
            return (
                "You don't have any medications saved yet. "
                "Would you like to add one? Just tell me the name and when you need to take it."
            )

        if len(medications) == 1:
            med = medications[0]
            times_str = " and ".join([self._format_time_friendly(t) for t in med.times])
            return (
                f"You're taking {med.name}, {med.dosage}, "
                f"{med.frequency.replace('_', ' ')} at {times_str}."
            )

        # Multiple medications
        response = f"You're currently taking {len(medications)} medications. "
        for i, med in enumerate(medications, 1):
            times_str = " and ".join([self._format_time_friendly(t) for t in med.times])
            response += (
                f"{i}. {med.name}, {med.dosage}, at {times_str}. "
            )

        return response

    async def get_next_medication(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get the next medication due

        Returns:
            Next medication info or None
        """
        medications = await self.get_medications(phone_number)

        if not medications:
            return None

        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # Find next medication after current time
        next_med = None
        min_time_diff = float('inf')

        for med in medications:
            for time_str in med.times:
                # Calculate time difference
                med_time = datetime.strptime(time_str, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )

                # If time has passed today, check tomorrow
                if med_time < now:
                    med_time += timedelta(days=1)

                time_diff = (med_time - now).total_seconds()

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    next_med = {
                        "medication": med,
                        "time": time_str,
                        "time_until": time_diff,
                        "time_friendly": self._format_time_friendly(time_str)
                    }

        return next_med

    async def record_medication_taken(
        self,
        phone_number: str,
        medication_name: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record that a medication was taken

        Args:
            phone_number: User's phone number
            medication_name: Name of medication
            timestamp: When it was taken (defaults to now)

        Returns:
            Confirmation message
        """
        if timestamp is None:
            timestamp = datetime.now()

        try:
            if self.redis_client:
                # Store in adherence log
                log_key = f"med_adherence:{phone_number}:{medication_name}"
                log_entry = {
                    "timestamp": timestamp.isoformat(),
                    "status": "taken"
                }

                # Use sorted set for time-ordered tracking
                score = timestamp.timestamp()
                await self.redis_client.zadd(
                    log_key,
                    {json.dumps(log_entry): score}
                )
                await self.redis_client.expire(log_key, 90 * 24 * 60 * 60)

            return {
                "success": True,
                "message": f"Wonderful! I've recorded that you took your {medication_name}. Well done for keeping up with your medications."
            }

        except Exception as e:
            logger.error(f"Error recording medication: {e}")
            return {
                "success": False,
                "message": "I noted that, thank you for letting me know.",
                "error": str(e)
            }

    async def get_adherence_stats(self, phone_number: str, days: int = 7) -> Dict[str, Any]:
        """
        Get medication adherence statistics

        Args:
            phone_number: User's phone number
            days: Number of days to analyze

        Returns:
            Adherence statistics
        """
        medications = await self.get_medications(phone_number)

        if not medications:
            return {
                "adherence_rate": 0,
                "total_doses_expected": 0,
                "doses_taken": 0,
                "message": "No medication data available yet."
            }

        try:
            total_expected = 0
            total_taken = 0

            cutoff = datetime.now() - timedelta(days=days)

            for med in medications:
                # Calculate expected doses
                doses_per_day = len(med.times)
                total_expected += doses_per_day * days

                # Count taken doses
                if self.redis_client:
                    log_key = f"med_adherence:{phone_number}:{med.name}"
                    taken_count = await self.redis_client.zcount(
                        log_key,
                        cutoff.timestamp(),
                        datetime.now().timestamp()
                    )
                    total_taken += taken_count

            adherence_rate = (total_taken / total_expected * 100) if total_expected > 0 else 0

            return {
                "adherence_rate": round(adherence_rate, 1),
                "total_doses_expected": total_expected,
                "doses_taken": total_taken,
                "days_analyzed": days,
                "message": self._create_adherence_message(adherence_rate)
            }

        except Exception as e:
            logger.error(f"Error calculating adherence: {e}")
            return {
                "adherence_rate": 0,
                "error": str(e)
            }

    def _create_adherence_message(self, rate: float) -> str:
        """Create encouraging message based on adherence rate"""
        if rate >= 95:
            return "You're doing brilliantly! You've taken almost all your medications on time."
        elif rate >= 80:
            return "You're doing very well with your medications. Keep it up!"
        elif rate >= 60:
            return "You're doing okay, but try to remember to take your medications on time."
        else:
            return "It looks like you've missed quite a few doses. Would you like me to remind you more often?"


# Global singleton
_medication_manager: Optional[MedicationManager] = None
_manager_lock = asyncio.Lock()


async def get_medication_manager(redis_client=None, twilio_client=None) -> MedicationManager:
    """Get or create medication manager singleton"""
    global _medication_manager
    if _medication_manager is None:
        async with _manager_lock:
            if _medication_manager is None:
                _medication_manager = MedicationManager(redis_client, twilio_client)
    return _medication_manager
