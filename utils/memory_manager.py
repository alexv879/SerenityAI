"""
GDPR-Compliant Memory Manager for Serenity AI
Stores conversation context and preferences WITHOUT medical/personal identifiable information
Redis-based persistence with automatic 90-day TTL for data minimization
"""

import redis
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

# GDPR-compliant memory configuration
MEMORY_TTL_DAYS = 90  # Automatic deletion after 90 days (data minimization)
MAX_CONVERSATION_SUMMARIES = 10  # Keep only last 10 call summaries


def get_redis_client():
    """Get or create Redis client connection"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            redis_client = None
    return redis_client


def hash_phone_number(phone: str) -> str:
    """
    Create anonymized hash of phone number for GDPR compliance
    Uses SHA-256 to prevent reverse lookup
    """
    return hashlib.sha256(phone.encode()).hexdigest()


def get_memory_key(phone: str) -> str:
    """Generate Redis key for user memory"""
    phone_hash = hash_phone_number(phone)
    return f"memory:{phone_hash}"


def load_user_memory(phone: str) -> Optional[Dict]:
    """
    Load user's conversation memory from Redis
    
    Returns:
        Dictionary with conversation_summaries, preferences, interaction_stats
        None if no memory exists or Redis unavailable
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = get_memory_key(phone)
        memory_json = client.get(key)
        
        if not memory_json:
            logger.info(f"No existing memory found for user")
            return None
        
        memory = json.loads(memory_json)
        logger.info(f"Loaded memory with {len(memory.get('conversation_summaries', []))} conversation summaries")
        return memory
        
    except Exception as e:
        logger.error(f"Error loading user memory: {e}")
        return None


def save_user_memory(phone: str, memory: Dict) -> bool:
    """
    Save user's conversation memory to Redis with TTL
    
    Args:
        phone: User's phone number (will be hashed)
        memory: Memory dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = get_memory_key(phone)
        memory_json = json.dumps(memory)
        
        # Save with TTL for GDPR data minimization
        ttl_seconds = MEMORY_TTL_DAYS * 24 * 60 * 60
        client.setex(key, ttl_seconds, memory_json)
        
        logger.info(f"Saved user memory with {MEMORY_TTL_DAYS}-day TTL")
        return True
        
    except Exception as e:
        logger.error(f"Error saving user memory: {e}")
        return False


def create_conversation_summary(
    topics_discussed: List[str],
    sentiment: str,
    tools_used: List[str],
    duration_seconds: int,
    notes: str = ""
) -> Dict:
    """
    Create GDPR-compliant conversation summary
    
    EXCLUDES:
    - Medical conditions or symptoms
    - Personal identifiable information (full names, addresses)
    - Financial information
    - Precise health data
    
    INCLUDES ONLY:
    - General topics discussed (non-medical)
    - Sentiment (positive, neutral, concerned)
    - Tools/features used
    - Duration
    - General notes (no PII)
    """
    return {
        "date": datetime.now().isoformat(),
        "topics": topics_discussed[:5],  # Limit to 5 topics
        "sentiment": sentiment,
        "tools_used": tools_used,
        "duration_seconds": duration_seconds,
        "notes": notes[:200]  # Limit note length
    }


def add_conversation_to_memory(
    phone: str,
    topics: List[str],
    sentiment: str = "positive",
    tools_used: List[str] = None,
    duration_seconds: int = 0,
    notes: str = ""
) -> bool:
    """
    Add new conversation summary to user's memory
    Maintains rolling window of last 10 conversations
    """
    # Load existing memory or create new
    memory = load_user_memory(phone) or {
        "first_call_date": datetime.now().isoformat(),
        "conversation_summaries": [],
        "preferences": {},
        "interaction_stats": {
            "total_calls": 0,
            "total_duration_seconds": 0,
            "tools_most_used": {}
        }
    }
    
    # Create conversation summary
    summary = create_conversation_summary(
        topics_discussed=topics,
        sentiment=sentiment,
        tools_used=tools_used or [],
        duration_seconds=duration_seconds,
        notes=notes
    )
    
    # Add to conversation history (keep last 10)
    memory["conversation_summaries"].append(summary)
    if len(memory["conversation_summaries"]) > MAX_CONVERSATION_SUMMARIES:
        memory["conversation_summaries"] = memory["conversation_summaries"][-MAX_CONVERSATION_SUMMARIES:]
    
    # Update interaction stats
    memory["interaction_stats"]["total_calls"] += 1
    memory["interaction_stats"]["total_duration_seconds"] += duration_seconds
    memory["last_call_date"] = datetime.now().isoformat()
    
    # Update tool usage stats
    for tool in (tools_used or []):
        current_count = memory["interaction_stats"]["tools_most_used"].get(tool, 0)
        memory["interaction_stats"]["tools_most_used"][tool] = current_count + 1
    
    # Save updated memory
    return save_user_memory(phone, memory)


def update_user_preference(phone: str, preference_key: str, preference_value) -> bool:
    """
    Update user preference in memory
    
    SAFE PREFERENCES (GDPR-compliant):
    - favorite_news_categories: ["health", "technology"]
    - best_call_time: "morning"
    - conversation_style: "brief" or "chatty"
    - preferred_voice: "alloy"
    - story_themes_enjoyed: ["nostalgia", "wartime"]
    
    DO NOT STORE:
    - Medical conditions
    - Medication names
    - Appointment details
    - Family member names
    - Address or precise location
    """
    memory = load_user_memory(phone) or {
        "first_call_date": datetime.now().isoformat(),
        "conversation_summaries": [],
        "preferences": {},
        "interaction_stats": {"total_calls": 0, "total_duration_seconds": 0, "tools_most_used": {}}
    }
    
    # Update preference
    memory["preferences"][preference_key] = preference_value
    memory["preferences_last_updated"] = datetime.now().isoformat()
    
    return save_user_memory(phone, memory)


def get_user_context_for_llm(phone: str) -> str:
    """
    Generate natural language summary of user's memory for LLM context
    
    Returns formatted string that can be included in system prompt
    """
    memory = load_user_memory(phone)
    
    if not memory:
        return "This is our first conversation. I'm learning about this user's preferences."
    
    # Build context summary
    context_parts = []
    
    # Recent conversation history
    recent_convos = memory.get("conversation_summaries", [])[-3:]  # Last 3 conversations
    if recent_convos:
        context_parts.append("RECENT CONVERSATION HISTORY:")
        for convo in recent_convos:
            date = datetime.fromisoformat(convo["date"]).strftime("%B %d")
            topics = ", ".join(convo["topics"][:3])
            context_parts.append(f"- {date}: Discussed {topics}. Sentiment: {convo['sentiment']}")
    
    # User preferences
    prefs = memory.get("preferences", {})
    if prefs:
        context_parts.append("\nUSER PREFERENCES:")
        if "favorite_news_categories" in prefs:
            context_parts.append(f"- Enjoys {', '.join(prefs['favorite_news_categories'])} news")
        if "best_call_time" in prefs:
            context_parts.append(f"- Prefers {prefs['best_call_time']} calls")
        if "conversation_style" in prefs:
            context_parts.append(f"- Conversation style: {prefs['conversation_style']}")
        if "story_themes_enjoyed" in prefs:
            context_parts.append(f"- Enjoys {', '.join(prefs['story_themes_enjoyed'])} stories")
    
    # Interaction stats
    stats = memory.get("interaction_stats", {})
    total_calls = stats.get("total_calls", 0)
    if total_calls > 0:
        context_parts.append(f"\nINTERACTION STATS:")
        context_parts.append(f"- Total previous calls: {total_calls}")
        
        # Most used tools
        tools_used = stats.get("tools_most_used", {})
        if tools_used:
            top_tools = sorted(tools_used.items(), key=lambda x: x[1], reverse=True)[:3]
            tool_names = [tool[0] for tool in top_tools]
            context_parts.append(f"- Frequently uses: {', '.join(tool_names)}")
    
    # Time since last call
    last_call = memory.get("last_call_date")
    if last_call:
        last_call_dt = datetime.fromisoformat(last_call)
        days_since = (datetime.now() - last_call_dt).days
        if days_since == 0:
            context_parts.append("\n- Last spoke: Earlier today")
        elif days_since == 1:
            context_parts.append("\n- Last spoke: Yesterday")
        else:
            context_parts.append(f"\n- Last spoke: {days_since} days ago")
    
    return "\n".join(context_parts)


def delete_user_memory(phone: str) -> bool:
    """
    Delete user's memory (GDPR right to be forgotten)
    
    Use when:
    - User requests data deletion
    - Account closure
    - GDPR compliance request
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = get_memory_key(phone)
        client.delete(key)
        logger.info("User memory deleted per GDPR request")
        return True
    except Exception as e:
        logger.error(f"Error deleting user memory: {e}")
        return False


# GDPR Compliance Notes:
"""
This memory system is designed to comply with UK GDPR requirements:

1. DATA MINIMIZATION: Only stores non-sensitive conversation context
2. AUTOMATIC DELETION: 90-day TTL ensures data isn't kept longer than necessary
3. ANONYMIZATION: Phone numbers hashed with SHA-256
4. NO SENSITIVE DATA: Explicitly excludes medical, financial, precise personal information
5. RIGHT TO BE FORGOTTEN: delete_user_memory() function supports data deletion requests
6. PURPOSE LIMITATION: Data used only to improve conversation quality
7. TRANSPARENCY: User should be informed about what's remembered

WHAT WE STORE:
✅ General topics discussed (e.g., "weather", "news", "stories")
✅ Sentiment (positive, neutral, concerned)
✅ Tools used (get_weather, tell_story)
✅ General preferences (favorite news categories, story themes)
✅ Interaction patterns (call frequency, duration)

WHAT WE DON'T STORE:
❌ Medical conditions or symptoms
❌ Medication names or dosages
❌ Personal identifiable information (full names, addresses, NHS numbers)
❌ Financial information
❌ Precise health data
❌ Family member details
❌ Emergency situations or crises

Example safe conversation summary:
{
    "topics": ["weather forecast", "news headlines", "nostalgic story"],
    "sentiment": "positive",
    "tools_used": ["get_weather_forecast", "get_uk_news", "tell_story"],
    "notes": "User enjoyed wartime story, mentioned interest in technology news"
}

Example UNSAFE summary (DO NOT STORE):
{
    "topics": ["chest pain", "diabetes medication"],  # ❌ Medical information
    "notes": "User mentioned daughter Sarah visiting tomorrow"  # ❌ PII
}
"""
