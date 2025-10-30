"""
Personality Selector - Dynamic voice selection based on context and sentiment

Selects between 4 Chirp3 HD voices:
- Leda: Warm female (primary companion)
- Puck: Friendly male (storyteller)
- Seren: Gentle female (grief/sadness)
- Aoife: Cheerful female (excitement/joy)

Selection logic:
1. User override (DTMF 1-4 or voice command)
2. Keywords (story, remember, etc.)
3. Sentiment analysis (sad → Seren, happy → Aoife)
4. Default → Leda

Author: Claude Code
Date: 2025-10-29
"""

import logging
from typing import Optional, List, Dict
from config import Config

logger = logging.getLogger(__name__)

# Voice configuration
CHIRP3_VOICES = Config.CHIRP3_VOICES
DEFAULT_VOICE = Config.DEFAULT_VOICE


class PersonalitySelector:
    """
    Intelligent voice selection for emotional appropriateness

    Uses keywords, sentiment, and user preferences to choose the right voice
    """

    # Keyword patterns for each voice
    STORYTELLING_KEYWORDS = [
        "story", "remember", "back in", "during the war",
        "when i was young", "in my day", "years ago",
        "tell me about", "what was it like", "reminisce"
    ]

    SADNESS_KEYWORDS = [
        "miss", "lonely", "sad", "grief", "lost", "passed away",
        "died", "funeral", "widow", "alone", "depressed"
    ]

    JOY_KEYWORDS = [
        "excited", "wonderful", "amazing", "fantastic",
        "love", "happy", "celebration", "birthday", "wedding"
    ]

    VOICE_COMMANDS = {
        "male voice": "puck",
        "female voice": "leda",
        "change voice": None,  # Triggers manual selection
        "different voice": None
    }

    def __init__(self):
        self.user_preferences: Dict[str, str] = {}  # phone_number → voice_name

    def select_voice(
        self,
        user_input: str,
        conversation_history: List[str] = None,
        sentiment_score: Optional[float] = None,
        phone_number: Optional[str] = None
    ) -> str:
        """
        Select the most appropriate voice based on context

        Priority:
        1. User override/preference
        2. Keywords in current input
        3. Sentiment score
        4. Default voice (Leda)

        Args:
            user_input: Current user input text
            conversation_history: Previous conversation turns
            sentiment_score: Sentiment score (0.0-5.0, None if not available)
            phone_number: User's phone number (for preferences)

        Returns:
            Voice name ('leda', 'puck', 'seren', 'aoife')
        """
        try:
            # Check for user preference
            if phone_number and phone_number in self.user_preferences:
                preferred_voice = self.user_preferences[phone_number]
                logger.info(f"Using user preference: {preferred_voice}")
                return preferred_voice

            # Check for voice change command
            user_lower = user_input.lower()
            for command, voice in self.VOICE_COMMANDS.items():
                if command in user_lower:
                    if voice:
                        logger.info(f"Voice command detected: {command} → {voice}")
                        if phone_number:
                            self.user_preferences[phone_number] = voice
                        return voice

            # Check for storytelling keywords → Puck (male storyteller)
            if any(keyword in user_lower for keyword in self.STORYTELLING_KEYWORDS):
                logger.info(f"Storytelling keywords detected → Puck")
                return "puck"

            # Check for sadness keywords → Seren (gentle female)
            if any(keyword in user_lower for keyword in self.SADNESS_KEYWORDS):
                logger.info(f"Sadness keywords detected → Seren")
                return "seren"

            # Check for joy keywords → Aoife (cheerful female)
            if any(keyword in user_lower for keyword in self.JOY_KEYWORDS):
                logger.info(f"Joy keywords detected → Aoife")
                return "aoife"

            # Use sentiment if available
            if sentiment_score is not None:
                voice = self._select_by_sentiment(sentiment_score)
                if voice != DEFAULT_VOICE:
                    logger.info(f"Sentiment {sentiment_score:.1f} → {voice}")
                    return voice

            # Default to Leda (warm companion)
            logger.debug(f"Using default voice: {DEFAULT_VOICE}")
            return DEFAULT_VOICE

        except Exception as e:
            logger.error(f"Error selecting voice: {e}, using default")
            return DEFAULT_VOICE

    def _select_by_sentiment(self, sentiment_score: float) -> str:
        """
        Select voice based on sentiment score

        Args:
            sentiment_score: Sentiment score (0.0 = very negative, 5.0 = very positive)

        Returns:
            Voice name
        """
        if sentiment_score < 2.5:
            # Very sad/negative → Seren (gentle, empathetic)
            return "seren"
        elif sentiment_score > 4.2:
            # Very happy/positive → Aoife (cheerful, energetic)
            return "aoife"
        else:
            # Neutral/moderate → Leda (warm, stable)
            return DEFAULT_VOICE

    def set_user_preference(self, phone_number: str, voice_name: str):
        """
        Save user's voice preference

        Args:
            phone_number: User's phone number
            voice_name: Preferred voice ('leda', 'puck', 'seren', 'aoife')
        """
        if voice_name in CHIRP3_VOICES:
            self.user_preferences[phone_number] = voice_name
            logger.info(f"Saved preference for {phone_number}: {voice_name}")
        else:
            logger.warning(f"Invalid voice name: {voice_name}")

    def clear_user_preference(self, phone_number: str):
        """
        Clear user's voice preference (reset to default)

        Args:
            phone_number: User's phone number
        """
        if phone_number in self.user_preferences:
            del self.user_preferences[phone_number]
            logger.info(f"Cleared preference for {phone_number}")

    def handle_dtmf_selection(self, dtmf_input: str) -> Optional[str]:
        """
        Handle DTMF (phone keypad) voice selection

        Press 1 = Leda (warm female)
        Press 2 = Puck (friendly male)
        Press 3 = Seren (gentle female)
        Press 4 = Aoife (cheerful female)

        Args:
            dtmf_input: DTMF digit pressed

        Returns:
            Voice name or None if invalid
        """
        dtmf_map = {
            "1": "leda",
            "2": "puck",
            "3": "seren",
            "4": "aoife"
        }

        voice = dtmf_map.get(dtmf_input)
        if voice:
            logger.info(f"DTMF {dtmf_input} → {voice}")
        else:
            logger.warning(f"Invalid DTMF input: {dtmf_input}")

        return voice

    def detect_manual_override(self, user_input: str) -> Optional[str]:
        """
        Detect if user wants to change voice manually

        Examples:
            "I'd like a male voice" → "puck"
            "Can you sound more cheerful?" → "aoife"
            "I need someone gentle" → "seren"

        Returns:
            Voice name or None
        """
        user_input_lower = user_input.lower()

        if any(phrase in user_input_lower for phrase in ["male voice", "man's voice", "gentleman"]):
            return "puck"

        if any(phrase in user_input_lower for phrase in ["cheerful", "happy", "energetic"]):
            return "aoife"

        if any(phrase in user_input_lower for phrase in ["gentle", "soft", "calm", "soothing"]):
            return "seren"

        if any(phrase in user_input_lower for phrase in ["warm", "motherly", "default"]):
            return "leda"

        return None

    def explain_voice_change(self, new_voice: str, old_voice: str) -> str:
        """
        Generate explanation when voice changes

        Returns:
            Natural explanation to include in response
        """
        if new_voice == old_voice:
            return ""

        explanations = {
            "leda": "",  # Default, no explanation needed
            "puck": "Let me tell you about that...",
            "seren": "*speaking gently*",
            "aoife": "*with excitement*"
        }

        return explanations.get(new_voice, "")

    def get_voice_description(self, voice_name: str) -> str:
        """
        Get human-readable description of a voice

        Args:
            voice_name: Voice name

        Returns:
            Description string
        """
        descriptions = {
            "leda": "Leda, a warm and caring female voice",
            "puck": "Puck, a friendly male voice great for storytelling",
            "seren": "Seren, a gentle and empathetic female voice",
            "aoife": "Aoife, a cheerful and energetic female voice"
        }
        return descriptions.get(voice_name, "the default voice")


# Global instance (singleton)
_personality_selector = PersonalitySelector()


def get_personality_selector() -> PersonalitySelector:
    """
    Get the global personality selector instance

    Returns:
        PersonalitySelector singleton
    """
    return _personality_selector


# Convenience function
def select_voice_for_context(
    user_input: str,
    sentiment_score: Optional[float] = None,
    phone_number: Optional[str] = None
) -> str:
    """
    Quick voice selection helper

    Args:
        user_input: User's input text
        sentiment_score: Optional sentiment score
        phone_number: Optional phone number for preferences

    Returns:
        Voice name ('leda', 'puck', 'seren', 'aoife')
    """
    selector = get_personality_selector()
    return selector.select_voice(user_input, sentiment_score=sentiment_score, phone_number=phone_number)
