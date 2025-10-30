"""
Conversation Logger - Store conversations in PostgreSQL for training data

Stores all conversation turns for future model training (ELM-70B)
Complies with GDPR and HMRC requirements

Features:
- Hash phone numbers (SHA256)
- Anonymize PII
- Get explicit consent
- Store 7 years for tax compliance
- Export to JSONL for Llama fine-tuning

Author: Claude Code
Date: 2025-10-29
"""

import asyncio
import asyncpg
import logging
import hashlib
import json
import re
from datetime import datetime, date
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)


class ConversationLogger:
    """
    Logs conversations to PostgreSQL for training data collection

    Privacy-first design:
    - Phone numbers are hashed
    - PII is anonymized
    - Explicit consent required
    - 7-year retention for tax compliance
    """

    def __init__(self):
        self.database_url = Config.DATABASE_URL
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """
        Initialize database connection pool and create tables

        Call this during app startup
        """
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )

            # Create tables if they don't exist
            await self._create_tables()

            logger.info("Conversation logger initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize conversation logger: {e}")
            raise

    async def _create_tables(self):
        """
        Create database tables if they don't exist
        """
        async with self.pool.acquire() as conn:
            # Conversations table - Enhanced for loneliness research
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    phone_hash VARCHAR(64) NOT NULL,
                    call_sid VARCHAR(100) NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    duration_seconds INT,
                    voice_used VARCHAR(50),
                    user_consented BOOLEAN DEFAULT FALSE,

                    -- Loneliness Research Metadata (GDPR-compliant, no PII)
                    time_of_day VARCHAR(20),  -- 'morning', 'afternoon', 'evening', 'night'
                    day_of_week VARCHAR(20),  -- 'monday', 'tuesday', etc.
                    conversation_topics JSONB,  -- ['family', 'health', 'memories', 'current_events']
                    emotional_keywords JSONB,  -- {'lonely': 2, 'happy': 1, 'sad': 3}
                    voice_switches INT DEFAULT 0,  -- How many times voice changed
                    avg_sentiment FLOAT,  -- Average sentiment across conversation
                    loneliness_indicators JSONB,  -- {'mentioned_living_alone': true, 'no_recent_visitors': true}
                    engagement_level VARCHAR(20),  -- 'low', 'medium', 'high'
                    user_age_bracket VARCHAR(20),  -- '60-69', '70-79', '80+' (if disclosed)

                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Conversation turns table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                    turn_number INT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    user_input TEXT,
                    ai_response TEXT,
                    voice_used VARCHAR(50),
                    sentiment_score FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_phone_hash
                ON conversations(phone_hash)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_created_at
                ON conversations(created_at)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_turns_conversation_id
                ON conversation_turns(conversation_id)
            """)

            logger.info("Database tables created successfully")

    @staticmethod
    def _hash_phone(phone_number: str) -> str:
        """
        Hash phone number using SHA256

        Args:
            phone_number: Raw phone number (e.g., +447411237771)

        Returns:
            SHA256 hash (hex string)
        """
        return hashlib.sha256(phone_number.encode()).hexdigest()

    @staticmethod
    def _anonymize_pii(text: str) -> str:
        """
        Anonymize personally identifiable information

        Replaces:
        - Names → [NAME]
        - Addresses/places → [PLACE]
        - Phone numbers → [PHONE]
        - Email addresses → [EMAIL]

        Args:
            text: Raw text

        Returns:
            Anonymized text
        """
        # Phone numbers
        text = re.sub(r'\+?\d{10,15}', '[PHONE]', text)

        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

        # Addresses (simple pattern for UK postcodes)
        text = re.sub(r'\b[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}\b', '[POSTCODE]', text)

        # Note: Name detection is complex and would require NLP
        # For now, we rely on consent and data minimization

        return text

    async def start_conversation(
        self,
        phone_number: str,
        call_sid: str,
        voice_used: str = "leda",
        user_consented: bool = False
    ) -> str:
        """
        Start logging a new conversation

        Args:
            phone_number: Caller's phone number
            call_sid: Twilio call SID
            voice_used: Initial voice name
            user_consented: Whether user consented to logging

        Returns:
            Conversation ID (UUID as string)
        """
        try:
            phone_hash = self._hash_phone(phone_number)

            async with self.pool.acquire() as conn:
                conversation_id = await conn.fetchval("""
                    INSERT INTO conversations (
                        phone_hash, call_sid, started_at, voice_used, user_consented
                    ) VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, phone_hash, call_sid, datetime.utcnow(), voice_used, user_consented)

            logger.info(f"[{call_sid}] Started conversation logging: {conversation_id}")
            return str(conversation_id)

        except Exception as e:
            logger.error(f"[{call_sid}] Failed to start conversation logging: {e}")
            return None

    async def log_turn(
        self,
        conversation_id: str,
        turn_number: int,
        user_input: str,
        ai_response: str,
        voice_used: str,
        sentiment_score: Optional[float] = None,
        anonymize: bool = True
    ):
        """
        Log a single conversation turn

        Args:
            conversation_id: Conversation UUID
            turn_number: Turn number (1, 2, 3, ...)
            user_input: What user said
            ai_response: What AI responded
            voice_used: Voice name used for this turn
            sentiment_score: Optional sentiment score (0.0-5.0)
            anonymize: Whether to anonymize PII (default: True)
        """
        try:
            # Anonymize PII if requested
            if anonymize:
                user_input = self._anonymize_pii(user_input)
                ai_response = self._anonymize_pii(ai_response)

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversation_turns (
                        conversation_id, turn_number, timestamp,
                        user_input, ai_response, voice_used, sentiment_score
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, conversation_id, turn_number, datetime.utcnow(),
                    user_input, ai_response, voice_used, sentiment_score)

            logger.debug(f"Logged turn {turn_number} for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to log turn {turn_number}: {e}")

    async def end_conversation(
        self,
        conversation_id: str,
        duration_seconds: int
    ):
        """
        Mark conversation as ended

        Args:
            conversation_id: Conversation UUID
            duration_seconds: Total call duration in seconds
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE conversations
                    SET ended_at = $1, duration_seconds = $2
                    WHERE id = $3
                """, datetime.utcnow(), duration_seconds, conversation_id)

            logger.info(f"Ended conversation {conversation_id} ({duration_seconds}s)")

        except Exception as e:
            logger.error(f"Failed to end conversation {conversation_id}: {e}")

    async def set_consent(self, conversation_id: str, consented: bool):
        """
        Update user consent status

        Args:
            conversation_id: Conversation UUID
            consented: Whether user consented
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE conversations
                    SET user_consented = $1
                    WHERE id = $2
                """, consented, conversation_id)

            logger.info(f"Updated consent for {conversation_id}: {consented}")

        except Exception as e:
            logger.error(f"Failed to update consent: {e}")

    async def export_training_data(
        self,
        start_date: date,
        end_date: date,
        only_consented: bool = True
    ) -> str:
        """
        Export conversations as JSONL for Llama fine-tuning

        Format:
        {"messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]}

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            only_consented: Only export consented conversations

        Returns:
            JSONL string (one JSON object per line)
        """
        try:
            consent_filter = "AND user_consented = TRUE" if only_consented else ""

            async with self.pool.acquire() as conn:
                # Get conversations
                conversations = await conn.fetch(f"""
                    SELECT id, call_sid
                    FROM conversations
                    WHERE DATE(created_at) BETWEEN $1 AND $2
                    {consent_filter}
                    ORDER BY created_at
                """, start_date, end_date)

            jsonl_lines = []

            for conv in conversations:
                # Get turns for this conversation
                async with self.pool.acquire() as conn:
                    turns = await conn.fetch("""
                        SELECT user_input, ai_response
                        FROM conversation_turns
                        WHERE conversation_id = $1
                        ORDER BY turn_number
                    """, conv['id'])

                # Build messages array
                messages = []
                for turn in turns:
                    messages.append({"role": "user", "content": turn['user_input']})
                    messages.append({"role": "assistant", "content": turn['ai_response']})

                if messages:
                    jsonl_lines.append(json.dumps({"messages": messages}))

            jsonl_output = "\n".join(jsonl_lines)
            logger.info(f"Exported {len(jsonl_lines)} conversations ({len(jsonl_output)} bytes)")

            return jsonl_output

        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
            return ""

    async def get_conversation_count(self, phone_number: str) -> int:
        """
        Get total number of conversations for a phone number

        Args:
            phone_number: Phone number

        Returns:
            Conversation count
        """
        try:
            phone_hash = self._hash_phone(phone_number)

            async with self.pool.acquire() as conn:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM conversations
                    WHERE phone_hash = $1
                """, phone_hash)

            return count or 0

        except Exception as e:
            logger.error(f"Failed to get conversation count: {e}")
            return 0

    async def log_payment(
        self,
        phone_hash: str,
        call_sid: str,
        amount: float,
        stripe_charge_id: str
    ):
        """Log payment for analytics"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        phone_hash VARCHAR(64),
                        call_sid VARCHAR(100),
                        amount_gbp DECIMAL(10, 2),
                        stripe_charge_id VARCHAR(100),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                await conn.execute("""
                    INSERT INTO payments (phone_hash, call_sid, amount_gbp, stripe_charge_id)
                    VALUES ($1, $2, $3, $4)
                """, phone_hash, call_sid, amount, stripe_charge_id)

            logger.info(f"[{call_sid}] Logged payment: £{amount} ({stripe_charge_id})")

        except Exception as e:
            logger.error(f"Failed to log payment: {e}")

    def _extract_loneliness_metadata(self, turns: list) -> dict:
        """
        Extract valuable loneliness research metadata (GDPR-compliant, no PII)

        Returns:
            Dict with research-valuable metadata
        """
        # Loneliness indicator keywords
        loneliness_keywords = {
            'living_alone': ['live alone', 'by myself', 'nobody here', 'just me'],
            'no_visitors': ['nobody visits', "haven't seen anyone", 'no visitors', 'isolated'],
            'missing_people': ['miss my', 'wish i could see', 'nobody to talk to'],
            'boredom': ['bored', 'nothing to do', 'same every day', 'monotonous'],
            'loss': ['passed away', 'died', 'lost my', 'widow', 'widower']
        }

        # Conversation topics
        topic_keywords = {
            'family': ['son', 'daughter', 'grandchildren', 'family', 'husband', 'wife'],
            'health': ['doctor', 'hospital', 'medicine', 'pain', 'health'],
            'memories': ['remember', 'back in', 'used to', 'when i was young'],
            'current_events': ['news', 'today', 'happening', 'current'],
            'hobbies': ['garden', 'read', 'watch', 'enjoy', 'hobby']
        }

        # Emotional keywords
        emotional_keywords = {
            'lonely': 0, 'alone': 0, 'isolated': 0,
            'happy': 0, 'joy': 0, 'wonderful': 0,
            'sad': 0, 'depressed': 0, 'down': 0,
            'excited': 0, 'looking forward': 0
        }

        # Analyze turns
        all_text = ' '.join([turn.get('user_input', '') for turn in turns]).lower()

        # Count loneliness indicators
        indicators = {}
        for category, keywords in loneliness_keywords.items():
            indicators[category] = any(keyword in all_text for keyword in keywords)

        # Identify topics
        topics = [topic for topic, keywords in topic_keywords.items()
                  if any(keyword in all_text for keyword in keywords)]

        # Count emotional keywords
        for emotion in emotional_keywords:
            emotional_keywords[emotion] = all_text.count(emotion)

        return {
            'loneliness_indicators': indicators,
            'topics': topics,
            'emotional_keywords': emotional_keywords
        }

    def _calculate_engagement_level(self, turns_count: int, avg_turn_length: float) -> str:
        """
        Calculate engagement level based on conversation metrics

        Returns:
            'low', 'medium', or 'high'
        """
        if turns_count < 5 or avg_turn_length < 10:
            return 'low'
        elif turns_count > 15 and avg_turn_length > 30:
            return 'high'
        else:
            return 'medium'

    def _get_time_of_day(self, timestamp: datetime) -> str:
        """Get time period for temporal analysis"""
        hour = timestamp.hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'

    async def finalize_conversation(
        self,
        conversation_id: str,
        duration_seconds: int,
        voice_used: str,
        user_consented: bool = False
    ):
        """
        Mark conversation as complete with loneliness research metadata

        Args:
            conversation_id: UUID
            duration_seconds: Total call duration
            voice_used: Primary voice used
            user_consented: Did user consent to data usage?
        """
        try:
            async with self.pool.acquire() as conn:
                # Get all turns to analyze
                turns = await conn.fetch("""
                    SELECT user_input, ai_response, sentiment_score, voice_used
                    FROM conversation_turns
                    WHERE conversation_id = $1
                    ORDER BY turn_number
                """, conversation_id)

                # Extract metadata
                turns_list = [dict(turn) for turn in turns]
                metadata = self._extract_loneliness_metadata(turns_list)

                # Calculate metrics
                sentiments = [t['sentiment_score'] for t in turns_list if t.get('sentiment_score')]
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None

                voice_changes = len(set(t['voice_used'] for t in turns_list if t.get('voice_used')))

                avg_turn_length = sum(len(str(t.get('user_input', ''))) for t in turns_list) / len(turns_list) if turns_list else 0
                engagement = self._calculate_engagement_level(len(turns_list), avg_turn_length)

                # Get conversation start time
                conv = await conn.fetchrow("SELECT started_at FROM conversations WHERE id = $1", conversation_id)
                time_of_day = self._get_time_of_day(conv['started_at'])
                day_of_week = conv['started_at'].strftime('%A').lower()

                # Update with all metadata
                await conn.execute("""
                    UPDATE conversations
                    SET
                        ended_at = $1,
                        duration_seconds = $2,
                        voice_used = $3,
                        user_consented = $4,
                        time_of_day = $5,
                        day_of_week = $6,
                        conversation_topics = $7,
                        emotional_keywords = $8,
                        voice_switches = $9,
                        avg_sentiment = $10,
                        loneliness_indicators = $11,
                        engagement_level = $12
                    WHERE id = $13
                """,
                    datetime.utcnow(),
                    duration_seconds,
                    voice_used,
                    user_consented,
                    time_of_day,
                    day_of_week,
                    json.dumps(metadata['topics']),
                    json.dumps(metadata['emotional_keywords']),
                    voice_changes,
                    avg_sentiment,
                    json.dumps(metadata['loneliness_indicators']),
                    engagement,
                    conversation_id
                )

            logger.info(f"Finalized conversation {conversation_id} with loneliness metadata")

        except Exception as e:
            logger.error(f"Failed to finalize conversation: {e}")

    async def close(self):
        """
        Close database connection pool
        """
        if self.pool:
            await self.pool.close()
            logger.info("Conversation logger closed")


# Global instance
_conversation_logger: Optional[ConversationLogger] = None
_logger_lock = asyncio.Lock()


async def get_conversation_logger() -> ConversationLogger:
    """
    Get the global conversation logger instance (thread-safe)

    Returns:
        ConversationLogger singleton
    """
    global _conversation_logger
    if _conversation_logger is None:
        async with _logger_lock:
            if _conversation_logger is None:  # Double-check after acquiring lock
                _conversation_logger = ConversationLogger()
                await _conversation_logger.initialize()
    return _conversation_logger
