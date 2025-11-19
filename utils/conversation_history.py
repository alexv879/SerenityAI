"""
Conversation History Manager - Redis-based conversation memory

Stores recent conversation context in Redis for continuity across calls.
Critical for elderly users who expect the AI to remember previous conversations.

Features:
- Stores last N conversation turns
- TTL-based expiration (24 hours default)
- Phone number based storage
- GDPR-compliant (automatic expiration)

Author: Claude Code
Date: 2025-11-19
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ConversationHistory:
    """
    Manages conversation history in Redis for context continuity

    Usage:
        history = await get_conversation_history()
        await history.add_turn(phone_number, "user", "Hello, how are you?")
        await history.add_turn(phone_number, "assistant", "I'm well, thank you!")
        context = await history.get_recent_turns(phone_number, limit=10)
    """

    def __init__(self, redis_client: redis.Redis, ttl_hours: int = 24, max_turns: int = 50):
        """
        Initialize conversation history manager

        Args:
            redis_client: Redis async client
            ttl_hours: How long to keep conversation history (hours)
            max_turns: Maximum number of turns to keep per user
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_hours * 3600
        self.max_turns = max_turns

    def _get_key(self, phone_number: str) -> str:
        """Get Redis key for phone number"""
        return f"conversation_history:{phone_number}"

    async def add_turn(
        self,
        phone_number: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a conversation turn to history

        Args:
            phone_number: User's phone number
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (function calls, timestamps, etc.)

        Returns:
            True if successful
        """
        try:
            key = self._get_key(phone_number)

            turn = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            # Add to Redis list (most recent at the end)
            await self.redis.rpush(key, json.dumps(turn))

            # Trim to max_turns
            await self.redis.ltrim(key, -self.max_turns, -1)

            # Set expiration
            await self.redis.expire(key, self.ttl_seconds)

            logger.debug(f"Added {role} turn to history for {phone_number}")
            return True

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to add conversation turn: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding conversation turn: {e}", exc_info=True)
            return False

    async def get_recent_turns(
        self,
        phone_number: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation turns for context

        Args:
            phone_number: User's phone number
            limit: Maximum number of turns to retrieve

        Returns:
            List of conversation turns (oldest first)
        """
        try:
            key = self._get_key(phone_number)

            # Get last N turns
            turns_json = await self.redis.lrange(key, -limit, -1)

            if not turns_json:
                return []

            turns = []
            for turn_json in turns_json:
                if isinstance(turn_json, bytes):
                    turn_json = turn_json.decode('utf-8')
                turns.append(json.loads(turn_json))

            logger.debug(f"Retrieved {len(turns)} turns for {phone_number}")
            return turns

        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get conversation history: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting conversation history: {e}", exc_info=True)
            return []

    async def get_formatted_context(
        self,
        phone_number: str,
        limit: int = 10,
        include_timestamps: bool = False
    ) -> str:
        """
        Get conversation history formatted for AI context

        Args:
            phone_number: User's phone number
            limit: Maximum number of turns
            include_timestamps: Include timestamps in output

        Returns:
            Formatted conversation history string
        """
        turns = await self.get_recent_turns(phone_number, limit)

        if not turns:
            return "No previous conversation history."

        lines = []
        for turn in turns:
            role = turn['role'].capitalize()
            content = turn['content']

            if include_timestamps:
                timestamp = turn['timestamp']
                lines.append(f"[{timestamp}] {role}: {content}")
            else:
                lines.append(f"{role}: {content}")

        return "\n".join(lines)

    async def clear_history(self, phone_number: str) -> bool:
        """
        Clear conversation history for a user (GDPR compliance)

        Args:
            phone_number: User's phone number

        Returns:
            True if successful
        """
        try:
            key = self._get_key(phone_number)
            await self.redis.delete(key)
            logger.info(f"Cleared conversation history for {phone_number}")
            return True

        except redis.RedisError as e:
            logger.error(f"Failed to clear conversation history: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing conversation history: {e}", exc_info=True)
            return False

    async def get_last_conversation_time(self, phone_number: str) -> Optional[datetime]:
        """
        Get timestamp of last conversation turn

        Args:
            phone_number: User's phone number

        Returns:
            Datetime of last turn, or None if no history
        """
        try:
            turns = await self.get_recent_turns(phone_number, limit=1)
            if turns:
                timestamp_str = turns[0]['timestamp']
                return datetime.fromisoformat(timestamp_str)
            return None

        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse last conversation time: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting last conversation time: {e}", exc_info=True)
            return None

    async def get_conversation_summary(self, phone_number: str) -> Dict[str, Any]:
        """
        Get summary statistics about conversation history

        Args:
            phone_number: User's phone number

        Returns:
            Summary dict with turn count, last conversation time, etc.
        """
        try:
            key = self._get_key(phone_number)
            turn_count = await self.redis.llen(key)
            last_time = await self.get_last_conversation_time(phone_number)

            ttl = await self.redis.ttl(key)
            expires_in_hours = ttl / 3600 if ttl > 0 else None

            return {
                "phone_number": phone_number,
                "turn_count": turn_count,
                "last_conversation": last_time.isoformat() if last_time else None,
                "expires_in_hours": round(expires_in_hours, 1) if expires_in_hours else None,
                "max_turns": self.max_turns
            }

        except redis.RedisError as e:
            logger.error(f"Failed to get conversation summary: {e}", exc_info=True)
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting conversation summary: {e}", exc_info=True)
            return {"error": str(e)}


# Singleton instance
_conversation_history: Optional[ConversationHistory] = None


async def get_conversation_history() -> ConversationHistory:
    """
    Get or create conversation history singleton

    Returns:
        ConversationHistory instance
    """
    global _conversation_history

    if _conversation_history is None:
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        redis_client = await sub_mgr._get_client()
        _conversation_history = ConversationHistory(redis_client)

    return _conversation_history
