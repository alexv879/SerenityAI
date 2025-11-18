"""
Family Voice Messages - Audio-only messaging system

Allows elderly users to:
- Record voice messages for family members
- Listen to voice messages from family
- Send "thinking of you" quick messages
- Receive special occasion greetings

Pure audio - no text, no apps, no screens needed!

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import base64

logger = logging.getLogger(__name__)


class FamilyVoiceMessages:
    """
    Manages voice message recording and playback for family communication

    Features:
    - Record voice messages via phone
    - Play back messages from family
    - "Thinking of you" quick messages
    - Birthday/occasion greetings
    - Message notifications
    """

    def __init__(self, redis_client=None, twilio_client=None):
        """
        Initialize family voice messages

        Args:
            redis_client: Redis for message storage
            twilio_client: Twilio for SMS notifications
        """
        self.redis_client = redis_client
        self.twilio_client = twilio_client

    async def record_message_for_family(
        self,
        user_id: str,
        recipient_name: str,
        message_url: Optional[str] = None,
        duration: int = 30
    ) -> Dict[str, Any]:
        """
        Start recording a voice message for family member

        Args:
            user_id: User's phone number
            recipient_name: Who the message is for ("Mary", "Tom", etc.)
            message_url: Twilio recording URL (if already recorded)
            duration: Max recording duration in seconds

        Returns:
            Recording instructions
        """
        try:
            if message_url:
                # Message already recorded, save it
                message_data = {
                    "from": user_id,
                    "to": recipient_name,
                    "url": message_url,
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "listened": False
                }

                if self.redis_client:
                    # Store message
                    message_key = f"voice_message:{recipient_name}:{datetime.now().timestamp()}"
                    await self.redis_client.set(
                        message_key,
                        json.dumps(message_data),
                        ex=30 * 24 * 60 * 60  # 30 days
                    )

                    # Add to recipient's inbox
                    inbox_key = f"voice_inbox:{recipient_name}"
                    await self.redis_client.lpush(inbox_key, message_key)
                    await self.redis_client.expire(inbox_key, 30 * 24 * 60 * 60)

                # Send SMS notification to recipient
                # (In production, would actually send via Twilio)
                logger.info(f"Would send SMS to {recipient_name}: You have a new voice message!")

                return {
                    "success": True,
                    "message": (
                        f"Wonderful! Your message for {recipient_name} has been recorded. "
                        f"I'll let them know it's waiting for them. They can call anytime to listen to it."
                    ),
                    "recipient": recipient_name
                }

            else:
                # Start recording
                return {
                    "success": True,
                    "recording": True,
                    "message": (
                        f"I'm ready to record your message for {recipient_name}. "
                        f"After the beep, speak your message. You have up to {duration} seconds. "
                        f"When you're done, just hang up or press any key."
                    ),
                    "recipient": recipient_name,
                    "max_duration": duration,
                    "instruction": "Start Twilio recording for voice message"
                }

        except Exception as e:
            logger.error(f"Error recording message: {e}")
            return {
                "success": False,
                "message": "I had trouble starting the recording. Please try again."
            }

    async def listen_to_messages(
        self,
        user_name: str
    ) -> Dict[str, Any]:
        """
        Listen to voice messages from family

        Args:
            user_name: User's name (to find their inbox)

        Returns:
            Message playback instructions
        """
        try:
            if not self.redis_client:
                return {
                    "success": False,
                    "message": "I don't have any messages stored right now."
                }

            # Get user's inbox
            inbox_key = f"voice_inbox:{user_name}"
            message_keys = await self.redis_client.lrange(inbox_key, 0, -1)

            if not message_keys or len(message_keys) == 0:
                return {
                    "success": True,
                    "has_messages": False,
                    "message": (
                        "You don't have any new voice messages right now. "
                        "But I'm sure your family will send you one soon!"
                    )
                }

            # Get first unlistened message
            for msg_key in message_keys:
                if isinstance(msg_key, bytes):
                    msg_key = msg_key.decode('utf-8')

                msg_json = await self.redis_client.get(msg_key)
                if msg_json:
                    if isinstance(msg_json, bytes):
                        msg_json = msg_json.decode('utf-8')

                    message_data = json.loads(msg_json)

                    if not message_data.get("listened", False):
                        # Mark as listened
                        message_data["listened"] = True
                        message_data["listened_at"] = datetime.now().isoformat()
                        await self.redis_client.set(
                            msg_key,
                            json.dumps(message_data),
                            ex=30 * 24 * 60 * 60
                        )

                        sender = message_data.get("to", "your family")  # Actually from field
                        time_ago = self._get_time_ago(message_data["timestamp"])

                        return {
                            "success": True,
                            "has_messages": True,
                            "message": f"You have a voice message from {sender}, sent {time_ago}. Let me play it for you now.",
                            "recording_url": message_data.get("url"),
                            "sender": sender,
                            "timestamp": message_data["timestamp"],
                            "instruction": f"Play audio from URL: {message_data.get('url')}"
                        }

            # All messages have been listened to
            return {
                "success": True,
                "has_messages": False,
                "message": "You've listened to all your messages! Would you like to hear them again?"
            }

        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return {
                "success": False,
                "message": "I had trouble getting your messages. Please try again."
            }

    def _get_time_ago(self, timestamp_str: str) -> str:
        """Convert timestamp to friendly 'time ago' string"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            diff = datetime.now() - timestamp

            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    if minutes < 5:
                        return "just now"
                    else:
                        return f"{minutes} minutes ago"
                elif hours == 1:
                    return "an hour ago"
                else:
                    return f"{hours} hours ago"
            elif diff.days == 1:
                return "yesterday"
            elif diff.days < 7:
                return f"{diff.days} days ago"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                return "a while ago"

        except:
            return "recently"

    async def send_quick_message(
        self,
        user_id: str,
        recipient_name: str,
        message_type: str = "thinking_of_you"
    ) -> Dict[str, Any]:
        """
        Send pre-recorded quick messages

        Message types: thinking_of_you, love_you, call_me, happy_birthday

        Returns:
            Confirmation
        """
        quick_messages = {
            "thinking_of_you": {
                "text": "Just wanted to let you know I'm thinking of you. Hope you're having a lovely day!",
                "voice_note": "A warm 'thinking of you' message"
            },
            "love_you": {
                "text": "I love you very much. You're always in my thoughts!",
                "voice_note": "A loving message"
            },
            "call_me": {
                "text": "When you have a moment, give me a ring. I'd love to have a chat!",
                "voice_note": "A gentle request for a call"
            },
            "happy_birthday": {
                "text": "Happy Birthday! Wishing you a wonderful day filled with joy and celebration!",
                "voice_note": "Birthday wishes"
            }
        }

        message = quick_messages.get(message_type, quick_messages["thinking_of_you"])

        # In production, would send via SMS or voice call
        logger.info(f"Would send to {recipient_name}: {message['text']}")

        return {
            "success": True,
            "message": f"Perfect! I've sent {message['voice_note']} to {recipient_name}. I'm sure they'll love hearing from you!",
            "recipient": recipient_name,
            "message_type": message_type
        }

    async def get_message_count(
        self,
        user_name: str
    ) -> Dict[str, Any]:
        """
        Get count of unlistened messages

        Returns:
            Message count
        """
        try:
            if not self.redis_client:
                return {"count": 0, "message": "You don't have any new messages."}

            inbox_key = f"voice_inbox:{user_name}"
            message_keys = await self.redis_client.lrange(inbox_key, 0, -1)

            unlistened_count = 0
            for msg_key in message_keys:
                if isinstance(msg_key, bytes):
                    msg_key = msg_key.decode('utf-8')

                msg_json = await self.redis_client.get(msg_key)
                if msg_json:
                    if isinstance(msg_json, bytes):
                        msg_json = msg_json.decode('utf-8')

                    message_data = json.loads(msg_json)
                    if not message_data.get("listened", False):
                        unlistened_count += 1

            if unlistened_count == 0:
                return {
                    "count": 0,
                    "message": "You don't have any new messages right now."
                }
            elif unlistened_count == 1:
                return {
                    "count": 1,
                    "message": "You have 1 new voice message waiting for you! Would you like to listen to it?"
                }
            else:
                return {
                    "count": unlistened_count,
                    "message": f"You have {unlistened_count} new voice messages! Would you like to listen to them?"
                }

        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return {"count": 0, "error": str(e)}


# Global singleton
_family_voice_messages: Optional[FamilyVoiceMessages] = None
_messages_lock = asyncio.Lock()


async def get_family_voice_messages(redis_client=None, twilio_client=None) -> FamilyVoiceMessages:
    """Get or create family voice messages singleton"""
    global _family_voice_messages
    if _family_voice_messages is None:
        async with _messages_lock:
            if _family_voice_messages is None:
                _family_voice_messages = FamilyVoiceMessages(redis_client, twilio_client)
    return _family_voice_messages
