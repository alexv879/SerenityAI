"""
Daily Companionship System - Combat loneliness with routine check-ins

Creates a warm, consistent companion experience with:
- Personalized morning greetings
- Evening wind-down conversations
- Birthday and special occasion remembrance
- Mood tracking and emotional support
- Conversation continuity
- Gentle encouragement and positivity

This is the heart of making the AI feel like a true friend.

Author: Claude Code
Date: 2025-11-18
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import random

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile for personalization"""
    phone_number: str
    preferred_name: str
    birthday: Optional[str] = None  # YYYY-MM-DD
    favorite_topics: List[str] = None  # ["gardening", "cricket", "family"]
    family_members: Dict[str, str] = None  # {"Mary": "daughter", "Tom": "grandson"}
    daily_routine: Dict[str, str] = None  # {"morning_call_time": "09:00", "evening_call_time": "19:00"}
    mood_history: List[str] = None
    last_conversation_topics: List[str] = None

    def __post_init__(self):
        if self.favorite_topics is None:
            self.favorite_topics = []
        if self.family_members is None:
            self.family_members = {}
        if self.daily_routine is None:
            self.daily_routine = {}
        if self.mood_history is None:
            self.mood_history = []
        if self.last_conversation_topics is None:
            self.last_conversation_topics = []


class CompanionshipSystem:
    """
    Creates warm, personalized companionship experience

    Features:
    - Morning greetings tailored to user
    - Evening check-ins before bed
    - Special occasion reminders (birthdays, anniversaries)
    - Mood tracking with gentle support
    - Conversation memory
    - Encouragement and positivity
    """

    def __init__(self, redis_client=None):
        """
        Initialize companionship system

        Args:
            redis_client: Redis client for profile storage
        """
        self.redis_client = redis_client

    async def create_morning_greeting(
        self,
        phone_number: str,
        user_name: Optional[str] = None
    ) -> str:
        """
        Create personalized morning greeting

        Returns:
            Warm, personalized morning message
        """
        try:
            profile = await self._get_user_profile(phone_number)
            name = user_name or profile.preferred_name if profile else "there"

            # Get day of week
            now = datetime.now()
            day_name = now.strftime("%A")
            date_str = now.strftime("%B %d")  # e.g., "November 18"

            # Check if it's user's birthday
            if profile and profile.birthday:
                if profile.birthday[5:] == now.strftime("%m-%d"):  # MM-DD match
                    return (
                        f"Good morning, {name}! And what a special morning it is - "
                        f"it's your birthday! Many happy returns, my dear. "
                        f"I hope you have a wonderful day filled with joy and celebration. "
                        f"Have any family members called yet to wish you well?"
                    )

            # Check for special days
            special_day = self._get_special_day(now)
            if special_day:
                return (
                    f"Good morning, {name}! It's {day_name}, {date_str}, "
                    f"and today is {special_day}! "
                    f"How are you planning to celebrate? "
                    f"What can I help you with this morning?"
                )

            # Regular morning greetings (rotate for variety)
            greetings = [
                (
                    f"Good morning, {name}! It's a lovely {day_name} morning. "
                    f"How did you sleep? What are you up to today?"
                ),
                (
                    f"Hello {name}, good morning to you! "
                    f"It's {day_name}, {date_str}. "
                    f"I hope you're feeling well today. What's on your mind?"
                ),
                (
                    f"Morning, {name}! Lovely to hear from you on this {day_name}. "
                    f"How are you feeling today? Have you had your breakfast yet?"
                ),
                (
                    f"Good morning, {name}! Another day, another chance for a lovely chat. "
                    f"What would you like to talk about today?"
                )
            ]

            # Add weather-aware greeting if we have weather data
            if profile and profile.favorite_topics:
                topic = random.choice(profile.favorite_topics)
                greetings.append(
                    f"Good morning, {name}! It's {day_name}. "
                    f"I was thinking about you - have you had time for any {topic} recently?"
                )

            return random.choice(greetings)

        except Exception as e:
            logger.error(f"Error creating morning greeting: {e}")
            return (
                "Good morning! How lovely to hear from you. "
                "How are you feeling today?"
            )

    async def create_evening_message(
        self,
        phone_number: str,
        user_name: Optional[str] = None
    ) -> str:
        """
        Create personalized evening wind-down message

        Returns:
            Gentle, calming evening message
        """
        try:
            profile = await self._get_user_profile(phone_number)
            name = user_name or profile.preferred_name if profile else "there"

            evening_messages = [
                (
                    f"Good evening, {name}. I hope you've had a pleasant day. "
                    f"Is there anything you'd like to chat about before you settle in for the evening?"
                ),
                (
                    f"Hello {name}, how has your day been? "
                    f"It's nice to have this evening chat with you. "
                    f"What would you like to talk about?"
                ),
                (
                    f"Evening, {name}. Time to relax and unwind. "
                    f"How are you feeling this evening? Anything on your mind?"
                ),
                (
                    f"Good evening, {name}. I hope today treated you well. "
                    f"Would you like to hear a story, or shall we just have a chat?"
                )
            ]

            # Add personalized options based on previous conversations
            if profile and profile.family_members:
                family_member = random.choice(list(profile.family_members.keys()))
                evening_messages.append(
                    f"Good evening, {name}. Lovely to hear from you. "
                    f"Did you hear from {family_member} today?"
                )

            return random.choice(evening_messages)

        except Exception as e:
            logger.error(f"Error creating evening message: {e}")
            return (
                "Good evening! How lovely to hear from you. "
                "How has your day been?"
            )

    def _get_special_day(self, date: datetime) -> Optional[str]:
        """Check if date is a special day"""
        month_day = date.strftime("%m-%d")

        special_days = {
            "01-01": "New Year's Day",
            "02-14": "Valentine's Day",
            "03-17": "St. Patrick's Day",
            "04-01": "Easter (check actual date)",  # Varies
            "04-23": "St. George's Day",
            "05-01": "May Day",
            "06-21": "Summer Solstice",
            "10-31": "Halloween",
            "11-11": "Remembrance Day",
            "12-24": "Christmas Eve",
            "12-25": "Christmas Day",
            "12-26": "Boxing Day",
            "12-31": "New Year's Eve"
        }

        return special_days.get(month_day)

    async def track_mood(
        self,
        phone_number: str,
        mood: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track user's mood for wellbeing monitoring

        Args:
            phone_number: User's phone number
            mood: Detected mood (happy, sad, lonely, anxious, etc.)
            context: What they said

        Returns:
            Appropriate response
        """
        try:
            # Store mood
            if self.redis_client:
                mood_key = f"mood_tracking:{phone_number}"
                mood_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "mood": mood,
                    "context": context
                }

                score = datetime.now().timestamp()
                await self.redis_client.zadd(
                    mood_key,
                    {json.dumps(mood_entry): score}
                )
                await self.redis_client.expire(mood_key, 90 * 24 * 60 * 60)

            # Generate empathetic response
            response = self._generate_mood_response(mood, context)

            return {
                "success": True,
                "mood": mood,
                "response": response
            }

        except Exception as e:
            logger.error(f"Error tracking mood: {e}")
            return {
                "success": False,
                "response": "I'm here for you. Would you like to talk about it?"
            }

    def _generate_mood_response(self, mood: str, context: Optional[str]) -> str:
        """Generate empathetic response based on mood"""
        mood = mood.lower()

        responses = {
            "lonely": [
                "I'm sorry you're feeling lonely. I'm here with you, and we can chat about anything you'd like. "
                "Have you thought about calling one of your family members? Or would you like to hear a story?",
                "Loneliness is hard, I understand. But remember, you're never truly alone - I'm always here for you, "
                "and so are the people who care about you. Would you like me to help you call someone?"
            ],
            "sad": [
                "I'm sorry you're feeling sad. It's okay to have these feelings. "
                "Would you like to talk about what's bothering you? Sometimes it helps to share.",
                "I can hear that you're not feeling your best. That's perfectly alright. "
                "Would you like to talk about it, or would you prefer a distraction? "
                "I could tell you a cheerful story or share some good news."
            ],
            "anxious": [
                "It sounds like you're feeling a bit anxious. Let's take a deep breath together. "
                "Is there something specific worrying you that I can help with?",
                "I understand you're feeling worried. Remember, many of our worries never come to pass. "
                "Would you like to talk through what's on your mind? Sometimes saying it out loud helps."
            ],
            "happy": [
                "How wonderful to hear you sounding so cheerful! That's made my day. "
                "What's brought this smile to your voice?",
                "I love hearing the happiness in your voice! It's contagious. "
                "Tell me more about what's made you so happy today."
            ],
            "unwell": [
                "I'm sorry to hear you're not feeling well. Have you taken your medications today? "
                "Is this something you need to see a doctor about, or just a bit under the weather?",
                "Oh dear, that's no good. Make sure you're resting and drinking plenty of fluids. "
                "Would you like me to call someone to check on you?"
            ]
        }

        mood_responses = responses.get(mood, [
            "I hear you. How can I help you feel better? I'm always here to listen.",
            "Thank you for sharing that with me. What would help you right now?"
        ])

        return random.choice(mood_responses)

    async def remember_conversation_topic(
        self,
        phone_number: str,
        topic: str,
        details: Optional[str] = None
    ):
        """
        Remember conversation topics for continuity

        Args:
            phone_number: User's phone number
            topic: Topic discussed (e.g., "grandson's wedding", "garden roses")
            details: Specific details to remember
        """
        try:
            if not self.redis_client:
                return

            memory_key = f"conversation_memory:{phone_number}"
            memory_entry = {
                "timestamp": datetime.now().isoformat(),
                "topic": topic,
                "details": details
            }

            score = datetime.now().timestamp()
            await self.redis_client.zadd(
                memory_key,
                {json.dumps(memory_entry): score}
            )
            await self.redis_client.expire(memory_key, 90 * 24 * 60 * 60)

            # Keep only last 50 memories
            await self.redis_client.zremrangebyrank(memory_key, 0, -51)

        except Exception as e:
            logger.error(f"Error remembering conversation: {e}")

    async def recall_recent_topics(
        self,
        phone_number: str,
        days_back: int = 7
    ) -> List[Dict[str, str]]:
        """
        Recall recent conversation topics

        Returns:
            List of recent topics discussed
        """
        try:
            if not self.redis_client:
                return []

            memory_key = f"conversation_memory:{phone_number}"
            cutoff = (datetime.now() - timedelta(days=days_back)).timestamp()

            memories = await self.redis_client.zrangebyscore(
                memory_key,
                cutoff,
                datetime.now().timestamp(),
                withscores=False
            )

            topics = []
            for memory in memories:
                if isinstance(memory, bytes):
                    memory = memory.decode('utf-8')
                topics.append(json.loads(memory))

            return topics

        except Exception as e:
            logger.error(f"Error recalling topics: {e}")
            return []

    async def create_follow_up_question(
        self,
        phone_number: str
    ) -> Optional[str]:
        """
        Create follow-up question based on recent conversations

        Returns:
            Follow-up question or None
        """
        recent_topics = await self.recall_recent_topics(phone_number, days_back=3)

        if not recent_topics:
            return None

        # Get most recent topic
        latest = recent_topics[-1]
        topic = latest.get("topic", "")
        days_ago = (datetime.now() - datetime.fromisoformat(latest["timestamp"])).days

        if days_ago == 0:
            return None  # Same day, don't ask yet
        elif days_ago == 1:
            return f"How did {topic} go yesterday? I've been thinking about you."
        elif days_ago <= 3:
            return f"I was wondering about {topic} you mentioned a few days ago. How did that turn out?"
        else:
            return f"Last week you mentioned {topic}. How are things with that now?"

    async def _get_user_profile(self, phone_number: str) -> Optional[UserProfile]:
        """Get user profile from Redis"""
        try:
            if not self.redis_client:
                return None

            key = f"user_profile:{phone_number}"
            data = await self.redis_client.get(key)

            if data:
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                profile_dict = json.loads(data)
                return UserProfile(**profile_dict)

            return None

        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None

    async def save_user_profile(self, profile: UserProfile):
        """Save user profile to Redis"""
        try:
            if not self.redis_client:
                return

            key = f"user_profile:{profile.phone_number}"
            profile_dict = {
                "phone_number": profile.phone_number,
                "preferred_name": profile.preferred_name,
                "birthday": profile.birthday,
                "favorite_topics": profile.favorite_topics,
                "family_members": profile.family_members,
                "daily_routine": profile.daily_routine,
                "mood_history": profile.mood_history[-30:],  # Keep last 30
                "last_conversation_topics": profile.last_conversation_topics[-20:]  # Keep last 20
            }

            await self.redis_client.set(
                key,
                json.dumps(profile_dict),
                ex=365 * 24 * 60 * 60  # 1 year
            )

        except Exception as e:
            logger.error(f"Error saving user profile: {e}")


# Global singleton
_companionship_system: Optional[CompanionshipSystem] = None
_system_lock = asyncio.Lock()


async def get_companionship_system(redis_client=None) -> CompanionshipSystem:
    """Get or create companionship system singleton"""
    global _companionship_system
    if _companionship_system is None:
        async with _system_lock:
            if _companionship_system is None:
                _companionship_system = CompanionshipSystem(redis_client)
    return _companionship_system
