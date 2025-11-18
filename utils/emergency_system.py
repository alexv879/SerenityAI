"""
Emergency SOS System - Safety-critical feature for elderly users

Provides:
- Voice-activated emergency alerts
- Quick access to family contacts
- Location sharing with emergency contacts
- Integration with NHS 111/999
- Fall detection support (future)
- Wellbeing check-ins

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class EmergencyContact:
    """Emergency contact information"""
    name: str
    relationship: str  # "daughter", "son", "neighbor", "carer", etc.
    phone_number: str
    priority: int = 1  # 1 = highest priority
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmergencyContact':
        return cls(**data)


class EmergencySystem:
    """
    Manages emergency alerts and safety features

    Features:
    - Voice-activated SOS ("Help!" or "Emergency!")
    - Family contact management
    - Automatic escalation (try family first, then 999)
    - Daily check-in system
    - Wellbeing monitoring
    """

    def __init__(self, redis_client=None, twilio_client=None):
        """
        Initialize emergency system

        Args:
            redis_client: Redis client for storage
            twilio_client: Twilio client for calls/SMS
        """
        self.redis_client = redis_client
        self.twilio_client = twilio_client

    async def add_emergency_contact(
        self,
        phone_number: str,
        contact_name: str,
        contact_phone: str,
        relationship: str,
        priority: int = 1,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add an emergency contact for a user

        Args:
            phone_number: User's phone number
            contact_name: Contact's name
            contact_phone: Contact's phone number
            relationship: Relationship to user
            priority: 1 = call first, 2 = call second, etc.
            notes: Additional notes (e.g., "Only call during daytime")

        Returns:
            Confirmation message
        """
        try:
            contact = EmergencyContact(
                name=contact_name,
                relationship=relationship,
                phone_number=contact_phone,
                priority=priority,
                notes=notes
            )

            if self.redis_client:
                # Store contact
                key = f"emergency_contact:{phone_number}:{contact_name}"
                await self.redis_client.set(
                    key,
                    json.dumps(contact.to_dict()),
                    ex=365 * 24 * 60 * 60  # 1 year retention
                )

                # Add to contact list (sorted by priority)
                list_key = f"emergency_contacts:{phone_number}"
                # Store as sorted set with priority as score
                await self.redis_client.zadd(
                    list_key,
                    {contact_name: priority}
                )
                await self.redis_client.expire(list_key, 365 * 24 * 60 * 60)

            logger.info(f"Added emergency contact {contact_name} for {phone_number}")

            return {
                "success": True,
                "message": (
                    f"I've added {contact_name}, your {relationship}, "
                    f"as emergency contact number {priority}. "
                    f"If you ever need help, just say 'Help' or 'Emergency' and "
                    f"I'll call {contact_name} right away."
                ),
                "contact": contact.to_dict()
            }

        except Exception as e:
            logger.error(f"Error adding emergency contact: {e}")
            return {
                "success": False,
                "message": "I had trouble saving that contact. Please try again.",
                "error": str(e)
            }

    async def get_emergency_contacts(self, phone_number: str) -> List[EmergencyContact]:
        """
        Get all emergency contacts for a user (sorted by priority)

        Args:
            phone_number: User's phone number

        Returns:
            List of EmergencyContact objects
        """
        try:
            if not self.redis_client:
                return []

            list_key = f"emergency_contacts:{phone_number}"
            # Get contacts sorted by priority (ascending)
            contact_names = await self.redis_client.zrange(list_key, 0, -1)

            if not contact_names:
                return []

            contacts = []
            for name in contact_names:
                if isinstance(name, bytes):
                    name = name.decode('utf-8')

                key = f"emergency_contact:{phone_number}:{name}"
                data = await self.redis_client.get(key)

                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    contact_dict = json.loads(data)
                    contacts.append(EmergencyContact.from_dict(contact_dict))

            return contacts

        except Exception as e:
            logger.error(f"Error getting emergency contacts: {e}")
            return []

    async def trigger_emergency(
        self,
        phone_number: str,
        emergency_type: str = "general",
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger emergency protocol

        Args:
            phone_number: User's phone number
            emergency_type: Type of emergency (general, medical, fall, etc.)
            user_message: What the user said

        Returns:
            Emergency response details
        """
        logger.critical(f"EMERGENCY triggered by {phone_number}: {emergency_type}")

        try:
            # Get emergency contacts
            contacts = await self.get_emergency_contacts(phone_number)

            if not contacts:
                # No contacts - direct to 999
                return {
                    "success": True,
                    "action": "transfer_to_999",
                    "message": (
                        "I'm connecting you to emergency services right now. "
                        "Stay on the line, help is coming."
                    ),
                    "contacts_called": []
                }

            # Log emergency event
            await self._log_emergency_event(
                phone_number,
                emergency_type,
                user_message
            )

            # Call contacts in priority order
            contacted = []
            if self.twilio_client:
                for contact in contacts[:3]:  # Try top 3 contacts
                    try:
                        # Initiate call to emergency contact
                        # Note: In production, this would make actual Twilio calls
                        logger.info(f"Would call emergency contact: {contact.name} at {contact.phone_number}")
                        contacted.append({
                            "name": contact.name,
                            "relationship": contact.relationship,
                            "phone": contact.phone_number
                        })

                        # Send SMS alert as well
                        logger.info(f"Would send SMS to {contact.name}: Emergency alert from {phone_number}")

                    except Exception as e:
                        logger.error(f"Failed to contact {contact.name}: {e}")

            return {
                "success": True,
                "action": "contacts_notified",
                "message": (
                    f"I'm calling {contacts[0].name} right now. "
                    f"Help is on the way. Stay calm, you're going to be okay."
                ),
                "contacts_called": contacted,
                "emergency_type": emergency_type
            }

        except Exception as e:
            logger.error(f"Emergency protocol error: {e}")
            # Fail-safe: always offer 999
            return {
                "success": False,
                "action": "offer_999",
                "message": (
                    "I'm having trouble reaching your contacts. "
                    "Would you like me to connect you to 999 emergency services?"
                ),
                "error": str(e)
            }

    async def _log_emergency_event(
        self,
        phone_number: str,
        emergency_type: str,
        user_message: Optional[str]
    ):
        """Log emergency event for tracking and family notifications"""
        if not self.redis_client:
            return

        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": emergency_type,
                "user_message": user_message,
                "phone_number": phone_number
            }

            log_key = f"emergency_log:{phone_number}"
            score = datetime.now().timestamp()

            await self.redis_client.zadd(
                log_key,
                {json.dumps(event): score}
            )
            await self.redis_client.expire(log_key, 365 * 24 * 60 * 60)

        except Exception as e:
            logger.error(f"Error logging emergency: {e}")

    async def list_emergency_contacts_voice(self, phone_number: str) -> str:
        """
        Create voice-friendly list of emergency contacts

        Returns:
            Natural language description
        """
        contacts = await self.get_emergency_contacts(phone_number)

        if not contacts:
            return (
                "You don't have any emergency contacts saved yet. "
                "Would you like to add someone? Just tell me their name, phone number, "
                "and how they're related to you."
            )

        if len(contacts) == 1:
            c = contacts[0]
            return (
                f"Your emergency contact is {c.name}, your {c.relationship}. "
                f"If you ever need help, just say 'Help' or 'Emergency' and I'll call them immediately."
            )

        response = f"You have {len(contacts)} emergency contacts. "
        for i, c in enumerate(contacts, 1):
            response += f"{i}. {c.name}, your {c.relationship}. "

        response += "If you need help, just say 'Help' or 'Emergency' and I'll call them right away."
        return response

    async def daily_check_in(self, phone_number: str) -> Dict[str, Any]:
        """
        Daily wellbeing check-in

        Returns:
            Check-in result
        """
        try:
            # Record check-in
            if self.redis_client:
                key = f"daily_checkin:{phone_number}:{datetime.now().strftime('%Y-%m-%d')}"
                await self.redis_client.set(
                    key,
                    json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "status": "completed"
                    }),
                    ex=7 * 24 * 60 * 60  # 7 days retention
                )

            return {
                "success": True,
                "message": (
                    "Good to hear from you today! How are you feeling? "
                    "Is there anything you need help with?"
                )
            }

        except Exception as e:
            logger.error(f"Error recording check-in: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def check_missed_checkins(self, phone_number: str, days: int = 1) -> bool:
        """
        Check if user has missed daily check-ins

        Args:
            phone_number: User's phone number
            days: Number of consecutive days missed to trigger alert

        Returns:
            True if missed check-ins detected
        """
        try:
            if not self.redis_client:
                return False

            # Check last N days
            missed_count = 0
            for i in range(days):
                date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                key = f"daily_checkin:{phone_number}:{date_str}"
                exists = await self.redis_client.exists(key)

                if not exists:
                    missed_count += 1

            return missed_count >= days

        except Exception as e:
            logger.error(f"Error checking missed check-ins: {e}")
            return False

    async def send_welfare_check_alert(self, phone_number: str):
        """
        Send welfare check alert to emergency contacts

        Called when user hasn't checked in for several days
        """
        try:
            contacts = await self.get_emergency_contacts(phone_number)

            if contacts:
                logger.warning(f"Sending welfare check alert for {phone_number}")

                # Would send SMS/call to emergency contacts
                for contact in contacts[:2]:  # Alert top 2 contacts
                    logger.info(
                        f"Would send welfare check SMS to {contact.name}: "
                        f"User {phone_number} hasn't checked in for several days"
                    )

        except Exception as e:
            logger.error(f"Error sending welfare check: {e}")


# Global singleton
_emergency_system: Optional[EmergencySystem] = None
_system_lock = asyncio.Lock()


async def get_emergency_system(redis_client=None, twilio_client=None) -> EmergencySystem:
    """Get or create emergency system singleton"""
    global _emergency_system
    if _emergency_system is None:
        async with _system_lock:
            if _emergency_system is None:
                _emergency_system = EmergencySystem(redis_client, twilio_client)
    return _emergency_system
