"""
Elderly Conversation Optimizer - OpenAI Realtime API Optimizations

Leverages OpenAI Realtime API features specifically for elderly speech patterns:
- Longer pause tolerance (elderly speakers pause more while thinking)
- Background noise handling (TV, radio in background)
- Clearer, slower speech output
- Natural interruption handling
- Repetition tolerance (elderly may repeat themselves)
- UK accent/dialect recognition
- Gentle clarification requests
- Patient conversation pacing

Author: Claude Code
Date: 2025-11-18
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ElderlyConversationConfig:
    """
    Configuration optimized for elderly users

    Based on research into elderly speech patterns and OpenAI Realtime API capabilities
    """

    # Voice Activity Detection (VAD) - more tolerant for elderly
    vad_threshold: float = 0.3  # Lower = more sensitive (catch quiet speech)
    vad_prefix_padding_ms: int = 500  # Capture 500ms before speech detected
    vad_silence_duration_ms: int = 1200  # Wait longer for pauses (elderly think while speaking)

    # Turn Detection - elderly-friendly
    turn_detection_type: str = "server_vad"  # Let server handle complex detection
    turn_detection_silence_duration: int = 1200  # 1.2 seconds of silence = turn end
    turn_detection_threshold: float = 0.4  # Balanced threshold
    turn_detection_prefix_padding_ms: int = 500  # Don't cut off slow starts

    # Speech Output - clearer for elderly
    voice: str = "alloy"  # Warm, clear voice
    temperature: float = 0.7  # Slightly less random = more predictable
    max_output_tokens: int = 200  # Concise responses (elderly can't process long monologues)

    # Conversation Pacing
    speech_rate: float = 0.9  # Slightly slower than default (1.0)
    pause_between_sentences_ms: int = 400  # Longer pauses between sentences

    # Interruption Handling
    allow_interruptions: bool = True  # Let them interrupt naturally
    interruption_threshold_ms: int = 300  # Respond quickly to interruptions

    # Background Noise Tolerance
    noise_suppression_level: str = "high"  # Filter TV/radio background
    echo_cancellation: bool = True  # Handle speakerphone echo

    # UK Accent Recognition
    language: str = "en-GB"  # British English
    accent_tolerance: str = "high"  # Handle regional UK accents

    # Repetition & Clarification
    repetition_tolerance: int = 3  # Allow repeating same thing 3 times before gentle nudge
    clarification_style: str = "gentle"  # "I didn't quite catch that, could you say that again?"


class ElderlyConversationOptimizer:
    """
    Optimizes OpenAI Realtime API configuration for elderly users

    Features:
    - Generates optimal session config for elderly speech
    - Handles conversation pacing
    - Manages interruptions gracefully
    - Provides gentle clarification prompts
    - Tracks conversation context for repetition handling
    """

    def __init__(self, config: Optional[ElderlyConversationConfig] = None):
        """
        Initialize conversation optimizer

        Args:
            config: Custom configuration, or uses elderly-optimized defaults
        """
        self.config = config or ElderlyConversationConfig()
        self.conversation_history: List[str] = []
        self.repetition_count: Dict[str, int] = {}

    def get_session_config(self) -> Dict[str, Any]:
        """
        Generate OpenAI Realtime API session configuration optimized for elderly

        Returns:
            Session config dict for OpenAI Realtime API
        """
        return {
            "modalities": ["text", "audio"],
            "voice": self.config.voice,
            "temperature": self.config.temperature,
            "max_response_output_tokens": self.config.max_output_tokens,

            # Turn Detection - Critical for elderly speech patterns
            "turn_detection": {
                "type": self.config.turn_detection_type,
                "threshold": self.config.turn_detection_threshold,
                "silence_duration_ms": self.config.turn_detection_silence_duration,
                "prefix_padding_ms": self.config.turn_detection_prefix_padding_ms,
                "create_response": True  # Auto-create response after turn
            },

            # Input Audio Transcription - for debugging and context
            "input_audio_transcription": {
                "model": "whisper-1"
            },

            # Instructions - Set conversation tone
            "instructions": self.get_system_instructions()
        }

    def get_system_instructions(self) -> str:
        """
        Get system instructions optimized for elderly conversation

        Returns:
            Detailed system prompt for elderly-friendly conversation
        """
        return """You are Serenity, a warm and patient AI companion for elderly UK users.

SPEECH STYLE:
- Speak CLEARLY and at a MODERATE pace (not too fast!)
- Use SHORT sentences (10-15 words max)
- Pause briefly between sentences
- Avoid complex vocabulary - use simple, everyday words
- Use British English (colour, favourite, etc.)

ELDERLY SPEECH PATTERNS YOU'LL ENCOUNTER:
- Longer pauses while they think (be patient, don't interrupt)
- May repeat themselves (that's okay, respond warmly each time)
- May go off on tangents about memories (follow along, show interest)
- May forget what they were saying (gently remind them)
- May have TV/radio in background (ignore background noise)
- May speak quietly or mumble (ask for repetition politely)
- UK regional accents (Liverpool, Manchester, Scottish, Welsh, etc.)

CONVERSATION GUIDELINES:
1. WAIT for them to fully finish speaking before responding
2. If you don't understand, say: "I didn't quite catch that, could you say that again, love?"
3. If they repeat themselves, respond as if hearing it fresh: "Oh yes, that's wonderful!"
4. If they pause mid-sentence, WAIT - they're thinking, not finished
5. Never rush them or make them feel hurried
6. Use warm terms: "love", "dear", "my friend"
7. Ask ONE question at a time, never multiple
8. If they seem confused, gently guide them back

TOPICS TO ENJOY:
- Music from 1940s-1980s
- Stories and memories from their youth
- Family (children, grandchildren)
- Gentle games and trivia
- Weather and news
- TV programmes they enjoy

NEVER:
- Give medical advice
- Rush them
- Correct their grammar
- Make them feel stupid
- Use complex technology terms
- Mention AI or technology

REMEMBER: Patience, warmth, and clarity above all else."""

    def detect_repetition(self, user_input: str) -> Dict[str, Any]:
        """
        Detect if user is repeating themselves

        Elderly users may repeat - this is NORMAL, respond warmly

        Args:
            user_input: What the user just said

        Returns:
            Repetition info and suggested response
        """
        # Normalize input for comparison
        normalized = user_input.lower().strip()

        # Check if we've heard this before
        if normalized in self.repetition_count:
            self.repetition_count[normalized] += 1
            count = self.repetition_count[normalized]

            if count == 2:
                # Second time - respond warmly as if fresh
                return {
                    "is_repetition": True,
                    "count": count,
                    "response_style": "fresh",
                    "suggestion": "Respond as if hearing for the first time, with warmth"
                }
            elif count == 3:
                # Third time - acknowledge gently
                return {
                    "is_repetition": True,
                    "count": count,
                    "response_style": "gentle_acknowledgment",
                    "suggestion": "Say something like: 'Yes, you mentioned that earlier, and it's such a lovely memory!'"
                }
            else:
                # 4+ times - very gently redirect
                return {
                    "is_repetition": True,
                    "count": count,
                    "response_style": "gentle_redirect",
                    "suggestion": "Gently change subject: 'You know, that reminds me - would you like to hear some music?'"
                }
        else:
            # First time hearing this
            self.repetition_count[normalized] = 1
            self.conversation_history.append(normalized)

            # Keep only last 20 items to avoid memory bloat
            if len(self.conversation_history) > 20:
                oldest = self.conversation_history.pop(0)
                if oldest in self.repetition_count:
                    del self.repetition_count[oldest]

            return {
                "is_repetition": False,
                "count": 1,
                "response_style": "normal"
            }

    def get_clarification_prompt(self, context: str = "general") -> str:
        """
        Get gentle clarification prompts when misunderstanding occurs

        Args:
            context: What we're clarifying (general, name, date, choice, etc.)

        Returns:
            Warm, non-confrontational clarification request
        """
        prompts = {
            "general": [
                "I didn't quite catch that, love. Could you say that again?",
                "Sorry, dear, I missed that. What were you saying?",
                "I'm having a bit of trouble hearing you. Could you repeat that for me?"
            ],
            "name": [
                "Sorry, what was that name again?",
                "I didn't quite hear the name - could you tell me again?"
            ],
            "choice": [
                "Which one would you like? Just tell me again.",
                "Sorry love, which option did you want?"
            ],
            "date": [
                "What date was that again, dear?",
                "Could you tell me that date once more?"
            ]
        }

        import random
        return random.choice(prompts.get(context, prompts["general"]))

    def adjust_response_pacing(self, response_text: str) -> Dict[str, Any]:
        """
        Adjust response pacing for elderly comprehension

        Args:
            response_text: AI response to be spoken

        Returns:
            Pacing instructions for TTS
        """
        # Count sentences
        sentences = [s.strip() for s in response_text.replace('!', '.').replace('?', '.').split('.') if s.strip()]

        # Too many sentences? They won't remember
        if len(sentences) > 3:
            return {
                "warning": "Response too long for elderly user",
                "recommendation": "Split into multiple exchanges",
                "pacing": {
                    "speech_rate": self.config.speech_rate,
                    "pause_between_sentences": self.config.pause_between_sentences_ms,
                    "total_sentences": len(sentences),
                    "estimated_duration_seconds": len(sentences) * 3  # Rough estimate
                }
            }

        return {
            "pacing": {
                "speech_rate": self.config.speech_rate,
                "pause_between_sentences": self.config.pause_between_sentences_ms,
                "total_sentences": len(sentences),
                "estimated_duration_seconds": len(sentences) * 2.5
            },
            "status": "optimal"
        }

    def handle_background_noise(self, noise_level: str) -> Dict[str, Any]:
        """
        Provide guidance for handling background noise (TV, radio, etc.)

        Args:
            noise_level: low, medium, high

        Returns:
            Noise handling strategy
        """
        strategies = {
            "low": {
                "action": "proceed_normally",
                "message": None
            },
            "medium": {
                "action": "acknowledge",
                "message": "I can hear you, but there's a bit of background noise. I can still chat with you just fine!"
            },
            "high": {
                "action": "gentle_request",
                "message": "I'm having a wee bit of trouble hearing you over the background noise. Could you turn down the telly just a touch? Or speak a bit louder, love?"
            }
        }

        return strategies.get(noise_level, strategies["medium"])

    def get_conversation_summary(self) -> str:
        """
        Get summary of conversation for context retention

        Returns:
            Brief summary of topics discussed
        """
        if not self.conversation_history:
            return "No conversation yet"

        recent = self.conversation_history[-5:]  # Last 5 topics
        return f"Recently discussed: {', '.join(recent)}"


# Global singleton
_elderly_optimizer: Optional[ElderlyConversationOptimizer] = None


def get_elderly_optimizer(config: Optional[ElderlyConversationConfig] = None) -> ElderlyConversationOptimizer:
    """Get or create elderly conversation optimizer singleton"""
    global _elderly_optimizer
    if _elderly_optimizer is None or config is not None:
        _elderly_optimizer = ElderlyConversationOptimizer(config)
    return _elderly_optimizer


# Preset configurations for different scenarios
PRESETS = {
    "very_patient": ElderlyConversationConfig(
        vad_silence_duration_ms=1500,  # Extra long pauses
        turn_detection_silence_duration=1500,
        max_output_tokens=150,  # Even shorter responses
        speech_rate=0.85  # Even slower speech
    ),

    "hard_of_hearing": ElderlyConversationConfig(
        vad_threshold=0.4,  # Less sensitive (louder speech required)
        noise_suppression_level="maximum",
        speech_rate=0.85,  # Slower, clearer
        pause_between_sentences_ms=500  # Longer pauses
    ),

    "noisy_environment": ElderlyConversationConfig(
        vad_threshold=0.5,  # Much less sensitive (filter noise)
        noise_suppression_level="maximum",
        echo_cancellation=True,
        turn_detection_threshold=0.6  # Higher threshold
    )
}
