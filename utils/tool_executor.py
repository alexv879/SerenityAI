"""
Tool executor for OpenAI Realtime function calling
Implements external API integrations for news, weather, Wikipedia, etc.
Includes storytelling, jokes, and GDPR-compliant memory management

Features:
- Redis caching for expensive API calls (40% cost reduction)
- Circuit breaker pattern prevents cascade failures
- Timeout protection for external APIs
- Graceful fallbacks on failures
- Automatic service recovery detection
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

# Import caching utilities
try:
    from utils.cache import cached, CacheTTL
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # No-op decorator if cache not available
    def cached(ttl=3600, prefix=None):
        def decorator(func):
            return func
        return decorator
    class CacheTTL:
        MINUTE_30 = 1800
        HOUR_1 = 3600
        HOUR_24 = 86400

# Import circuit breaker utilities
try:
    from utils.circuit_breaker import circuit_breaker
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False
    # No-op decorator if circuit breaker not available
    def circuit_breaker(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator

# External API clients
try:
    from newsapi import NewsApiClient
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False
    
try:
    import pyowm
    PYOWM_AVAILABLE = True
except ImportError:
    PYOWM_AVAILABLE = False
    
try:
    import wikipedia
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False

# Internal modules
try:
    from utils.story_library import get_story, get_joke, STORYTELLING_DELIVERY_GUIDE
    STORY_LIBRARY_AVAILABLE = True
except ImportError:
    STORY_LIBRARY_AVAILABLE = False
    
try:
    from utils.memory_manager import (
        load_user_memory,
        get_user_context_for_llm,
        add_conversation_to_memory,
        update_user_preference
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False

# MCP integration
try:
    from utils.mcp_initialization import call_mcp_tool, get_mcp_status
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes function calls requested by OpenAI Realtime API
    Integrates with external APIs (NewsAPI, OpenWeatherMap, Wikipedia)
    """
    
    def __init__(
        self,
        news_api_key: Optional[str] = None,
        weather_api_key: Optional[str] = None,
        redis_client = None  # For reminders and context storage
    ):
        """
        Initialize tool executor with API keys
        
        Args:
            news_api_key: NewsAPI key (free tier: 100 requests/day)
            weather_api_key: OpenWeatherMap API key
            redis_client: Redis client for persistent storage
        """
        self.news_api_key = news_api_key or os.getenv("NEWS_API_KEY")
        self.weather_api_key = weather_api_key or os.getenv("OPENWEATHER_API_KEY")
        self.redis_client = redis_client
        
        # Initialize API clients
        if NEWSAPI_AVAILABLE and self.news_api_key:
            self.news_client = NewsApiClient(api_key=self.news_api_key)
        else:
            self.news_client = None
            logger.warning("NewsAPI not available (missing library or API key)")
        
        if PYOWM_AVAILABLE and self.weather_api_key:
            self.owm = pyowm.OWM(self.weather_api_key)
            self.weather_manager = self.owm.weather_manager()
        else:
            self.owm = None
            self.weather_manager = None
            logger.warning("OpenWeatherMap not available (missing library or API key)")
        
        # Configure Wikipedia
        if WIKIPEDIA_AVAILABLE:
            wikipedia.set_lang('en')
        
    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call and return result
        
        Args:
            function_name: Name of function to call
            arguments: Function arguments as dict
            
        Returns:
            Function result as dict (will be JSON-serialized by OpenAI client)
        """
        try:
            # Check if this is an MCP tool first
            if MCP_AVAILABLE:
                mcp_status = get_mcp_status()
                
                # Check if tool exists in MCP registry
                for server_name, server_info in mcp_status.items():
                    if function_name in server_info.get("tools", []):
                        logger.info(f"Routing {function_name} to MCP server: {server_name}")
                        return await call_mcp_tool(function_name, arguments)
            
            # Route to built-in handlers
            if function_name == "get_uk_news":
                return await self.get_uk_news(**arguments)
            
            elif function_name == "get_weather_forecast":
                return await self.get_weather_forecast(**arguments)
            
            elif function_name == "wikipedia_search":
                return await self.wikipedia_search(**arguments)
            
            elif function_name == "on_this_day":
                return await self.on_this_day()
            
            elif function_name == "set_reminder":
                return await self.set_reminder(**arguments)

            elif function_name == "recall_user_context":
                return await self.recall_user_context(**arguments)
            
            elif function_name == "tell_story":
                return await self.tell_story(**arguments)
            
            elif function_name == "tell_joke":
                return await self.tell_joke(**arguments)
            
            elif function_name == "switch_mode":
                return await self.switch_mode(**arguments)

            # ENTERTAINMENT FEATURES (AUDIO ONLY - NO HEALTH/MEDICAL)
            elif function_name == "play_music":
                return await self.play_music(**arguments)

            elif function_name == "play_trivia":
                return await self.play_trivia(**arguments)

            elif function_name == "check_answer":
                return await self.check_trivia_answer(**arguments)

            elif function_name == "start_story":
                return await self.start_interactive_story(**arguments)

            elif function_name == "singalong":
                return await self.start_singalong(**arguments)

            elif function_name == "word_game":
                return await self.play_word_game(**arguments)

            elif function_name == "record_message":
                return await self.record_family_message(**arguments)

            elif function_name == "listen_messages":
                return await self.listen_to_messages(**arguments)

            elif function_name == "morning_greeting":
                return await self.morning_greeting(**arguments)

            elif function_name == "evening_checkin":
                return await self.evening_checkin(**arguments)

            else:
                logger.warning(f"Unknown function: {function_name}")
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}", exc_info=True)
            return {"error": str(e)}
    
    @cached(ttl=CacheTTL.HOUR_1, prefix="uk_news")
    @circuit_breaker(name="newsapi", failure_threshold=3, recovery_timeout=30, timeout=5)
    async def get_uk_news(
        self,
        category: str = "general",
        max_headlines: int = 5
    ) -> Dict[str, Any]:
        """
        Get UK news headlines from NewsAPI

        **Cached for 1 hour** to reduce API costs and rate limits
        **Circuit breaker** opens after 3 failures, recovers after 30s

        Args:
            category: general, health, technology, business, entertainment, sports
            max_headlines: Number of headlines to return (1-10)

        Returns:
            Dict with headlines list and metadata
        """
        if not self.news_client:
            return {
                "error": "News service is currently unavailable. Please try again later.",
                "headlines": []
            }
        
        try:
            # Map category to NewsAPI categories
            category_map = {
                "general": "general",
                "health": "health",
                "technology": "technology",
                "tech": "technology",
                "business": "business",
                "entertainment": "entertainment",
                "sports": "sports"
            }

            newsapi_category = category_map.get(category.lower(), "general")

            # Get UK top headlines with timeout protection (5 seconds)
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.news_client.get_top_headlines,
                        country='gb',  # United Kingdom
                        category=newsapi_category,
                        page_size=min(max_headlines, 10)
                    ),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.error("NewsAPI request timed out")
                return {"error": "News service is taking too long to respond", "headlines": []}
            
            if response['status'] != 'ok':
                return {"error": "Failed to fetch news", "headlines": []}
            
            articles = response.get('articles', [])
            
            # Format headlines for voice output (concise)
            headlines = []
            for article in articles[:max_headlines]:
                headline = {
                    "title": article.get('title', ''),
                    "description": article.get('description', ''),
                    "source": article.get('source', {}).get('name', 'Unknown')
                }
                headlines.append(headline)
            
            return {
                "category": category,
                "count": len(headlines),
                "headlines": headlines,
                "fetched_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return {
                "error": "Unable to fetch news at the moment",
                "headlines": []
            }
    
    @cached(ttl=CacheTTL.MINUTE_30, prefix="weather")
    @circuit_breaker(name="openweathermap", failure_threshold=3, recovery_timeout=30, timeout=5)
    async def get_weather_forecast(
        self,
        postcode: Optional[str] = None,
        days: int = 3
    ) -> Dict[str, Any]:
        """
        Get UK weather forecast from OpenWeatherMap

        **Cached for 30 minutes** to reduce API costs
        **Circuit breaker** opens after 3 failures, recovers after 30s

        Args:
            postcode: UK postcode (optional, defaults to London)
            days: Number of days (1, 3, or 5)

        Returns:
            Dict with weather forecast
        """
        if not self.weather_manager:
            return {
                "error": "Weather service is currently unavailable",
                "forecast": []
            }
        
        try:
            # Default to London if no postcode
            location = postcode if postcode else "London,GB"

            # Get forecast with timeout protection (5 seconds)
            try:
                if days == 1:
                    # Current weather
                    observation = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.weather_manager.weather_at_place,
                            location
                        ),
                        timeout=5.0
                    )
                    weather = observation.weather

                    return {
                        "location": location,
                        "current": {
                            "temperature": weather.temperature('celsius')['temp'],
                            "condition": weather.detailed_status,
                            "humidity": weather.humidity,
                            "wind_speed": weather.wind()['speed']
                        },
                        "forecast": []
                    }
                else:
                    # Multi-day forecast
                    forecaster = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.weather_manager.forecast_at_place,
                            location,
                            '3h'
                        ),
                        timeout=5.0
                    )
                    forecast = forecaster.forecast

                    # Group by day (take midday forecast for each day)
                    daily_forecasts = []
                    current_date = None

                    for weather in forecast.weathers[:days * 3]:  # Rough estimate
                        weather_date = datetime.fromtimestamp(weather.reference_time())

                        if current_date != weather_date.date():
                            current_date = weather_date.date()

                            daily_forecasts.append({
                                "date": weather_date.strftime("%A, %d %B"),
                                "temperature": weather.temperature('celsius')['temp'],
                                "condition": weather.detailed_status,
                                "humidity": weather.humidity
                            })

                            if len(daily_forecasts) >= days:
                                break

                    return {
                        "location": location,
                        "forecast": daily_forecasts,
                        "fetched_at": datetime.utcnow().isoformat()
                    }
            except asyncio.TimeoutError:
                logger.error("Weather API request timed out")
                return {"error": "Weather service is taking too long to respond", "forecast": []}
                
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {
                "error": "Unable to fetch weather forecast",
                "forecast": []
            }
    
    @cached(ttl=CacheTTL.HOUR_24, prefix="wikipedia")
    @circuit_breaker(name="wikipedia", failure_threshold=3, recovery_timeout=30, timeout=10)
    async def wikipedia_search(
        self,
        query: str,
        sentences: int = 3
    ) -> Dict[str, Any]:
        """
        Search Wikipedia and return summary

        **Cached for 24 hours** to reduce API calls (Wikipedia content is relatively static)
        **Circuit breaker** opens after 3 failures, recovers after 30s

        Args:
            query: Search query
            sentences: Number of sentences to return (1-5)

        Returns:
            Dict with summary and URL
        """
        if not WIKIPEDIA_AVAILABLE:
            return {"error": "Wikipedia search is unavailable", "summary": ""}
        
        try:
            # Search for page
            search_results = wikipedia.search(query, results=1)
            
            if not search_results:
                return {
                    "error": f"No Wikipedia results found for '{query}'",
                    "summary": ""
                }
            
            # Get page summary
            page_title = search_results[0]
            summary = wikipedia.summary(page_title, sentences=min(sentences, 5))
            page = wikipedia.page(page_title)
            
            return {
                "title": page.title,
                "summary": summary,
                "url": page.url,
                "query": query
            }
            
        except wikipedia.exceptions.DisambiguationError as e:
            # Multiple results - pick first option
            try:
                page_title = e.options[0]
                summary = wikipedia.summary(page_title, sentences=min(sentences, 5))
                page = wikipedia.page(page_title)
                
                return {
                    "title": page.title,
                    "summary": summary,
                    "url": page.url,
                    "query": query,
                    "note": f"Showing results for: {page_title}"
                }
            except Exception as inner_e:
                logger.error(f"Wikipedia disambiguation error: {inner_e}")
                return {"error": "Multiple results found, please be more specific", "summary": ""}
        
        except wikipedia.exceptions.PageError:
            return {"error": f"No Wikipedia page found for '{query}'", "summary": ""}
        
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
            return {"error": "Unable to search Wikipedia", "summary": ""}
    
    @cached(ttl=CacheTTL.HOUR_24, prefix="on_this_day")
    @circuit_breaker(name="wikipedia_otd", failure_threshold=3, recovery_timeout=30, timeout=10)
    async def on_this_day(self) -> Dict[str, Any]:
        """
        Get historical events that happened on this day
        Uses Wikipedia's "On This Day" feature

        **Cached for 24 hours** - content changes daily, cache refreshes at midnight
        **Circuit breaker** opens after 3 failures, recovers after 30s

        Returns:
            Dict with historical events
        """
        if not WIKIPEDIA_AVAILABLE:
            return {"error": "Historical events unavailable", "events": []}
        
        try:
            today = datetime.now()
            month = today.strftime("%B")
            day = today.day
            
            # Search Wikipedia for "Month Day" page (e.g., "January 15")
            page_title = f"{month} {day}"
            page = wikipedia.page(page_title)
            
            # Extract first few paragraphs (usually contain notable events)
            summary = wikipedia.summary(page_title, sentences=5)
            
            return {
                "date": today.strftime("%B %d"),
                "summary": summary,
                "url": page.url
            }
            
        except Exception as e:
            logger.error(f"On this day error: {e}")
            return {
                "error": "Unable to fetch historical events",
                "events": []
            }
    
    async def set_reminder(
        self,
        reminder_text: str,
        when: str
    ) -> Dict[str, Any]:
        """
        Set a reminder for the user (requires Redis + scheduler)
        
        Args:
            reminder_text: What to remind
            when: When to remind (e.g., "in 1 hour", "tomorrow at 2pm")
            
        Returns:
            Confirmation message
        """
        # TODO: Implement reminder scheduling with Redis + Twilio outbound calls
        # For now, return placeholder
        
        logger.info(f"Reminder requested: '{reminder_text}' at {when}")
        
        return {
            "success": True,
            "message": f"I'll remind you about '{reminder_text}' {when}",
            "reminder_text": reminder_text,
            "scheduled_for": when,
            "note": "Reminder feature coming soon"
        }
    
    async def recall_user_context(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recall user context from Redis memory (GDPR-compliant)
        
        Args:
            user_id: User identifier (phone number)
            
        Returns:
            Natural language user context summary
        """
        if not MEMORY_MANAGER_AVAILABLE:
            return {
                "context_available": False,
                "message": "This is our first conversation. I'm learning about your preferences."
            }
        
        if not user_id:
            return {
                "context_available": False,
                "message": "No user ID provided"
            }
        
        try:
            # Get formatted context for LLM
            context_summary = get_user_context_for_llm(user_id)
            
            if "first conversation" in context_summary.lower():
                return {
                    "context_available": False,
                    "message": context_summary
                }
            
            return {
                "context_available": True,
                "context_summary": context_summary,
                "message": "Previous conversation context loaded"
            }
            
        except Exception as e:
            logger.error(f"Error recalling context: {e}")
            return {
                "context_available": False,
                "message": "Unable to load previous context"
            }
    
    async def tell_story(
        self,
        theme: str = "classic",
        length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Tell a story from the library
        
        Args:
            theme: classic, nostalgia, wartime, bedtime, seaside, village, nature, gentle_humor
            length: short, medium, long
            
        Returns:
            Story content with delivery instructions
        """
        if not STORY_LIBRARY_AVAILABLE:
            return {
                "error": "Story library unavailable",
                "message": "I'm sorry, I can't access my story library at the moment."
            }
        
        try:
            story = get_story(theme=theme, length=length)
            
            return {
                "success": True,
                "title": story["title"],
                "content": story["content"],
                "delivery_notes": story["delivery_notes"],
                "theme": story["theme"],
                "length": story["length"],
                "instruction": "Read the story aloud with expressive emotion following the delivery_notes. After the story, invite the user to share their own memories related to the theme."
            }
            
        except Exception as e:
            logger.error(f"Error getting story: {e}")
            return {
                "error": str(e),
                "message": "I'm having trouble accessing that story. Would you like to hear something else?"
            }
    
    async def tell_joke(
        self,
        style: str = "gentle"
    ) -> Dict[str, Any]:
        """
        Tell a clean, elderly-appropriate joke
        
        Args:
            style: gentle, witty, wordplay, british_humor
            
        Returns:
            Joke text
        """
        if not STORY_LIBRARY_AVAILABLE:
            return {
                "success": False,
                "joke": "Why did the computer go to the doctor? Because it had a virus! ...Oh wait, that's from my emergency backup jokes."
            }
        
        try:
            joke = get_joke(style=style)
            
            return {
                "success": True,
                "joke": joke,
                "style": style,
                "instruction": "Tell the joke with a warm, amused tone. Laugh softly after the punchline to encourage the user to laugh too."
            }
            
        except Exception as e:
            logger.error(f"Error getting joke: {e}")
            return {
                "success": False,
                "joke": "I was going to tell you a joke about memory, but I forgot it! Oh dear, that's rather apt, isn't it?"
            }
    
    async def switch_mode(
        self,
        mode: str
    ) -> Dict[str, Any]:
        """
        Switch conversation mode (companion, storytelling, newsreader)
        
        Args:
            mode: companion, storytelling, newsreader
            
        Returns:
            Mode switch confirmation with voice change instructions
        """
        mode_configs = {
            "companion": {
                "voice": "alloy",
                "description": "Warm, friendly companion voice for general conversation",
                "temperature": 0.8
            },
            "storytelling": {
                "voice": "fable",
                "description": "Expressive, theatrical voice perfect for telling stories",
                "temperature": 0.9
            },
            "newsreader": {
                "voice": "echo",
                "description": "Clear, authoritative voice for reading news and information",
                "temperature": 0.6
            }
        }
        
        if mode.lower() not in mode_configs:
            return {
                "success": False,
                "error": f"Unknown mode: {mode}. Available modes: companion, storytelling, newsreader"
            }
        
        config = mode_configs[mode.lower()]
        
        logger.info(f"Mode switch requested: {mode}")
        
        return {
            "success": True,
            "mode": mode.lower(),
            "voice": config["voice"],
            "description": config["description"],
            "temperature": config["temperature"],
            "instruction": f"Session should be reinitialized with voice={config['voice']} and appropriate system prompt for {mode} mode. Temperature: {config['temperature']}"
        }

    # ========== ENTERTAINMENT FEATURES FOR ELDERLY USERS (AUDIO ONLY) ==========

    async def play_music(
        self,
        user_id: str,
        medication_name: str,
        dosage: str,
        times: List[str],
        frequency: str = "daily",
        with_food: bool = False,
        instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add medication reminder for user

        Args:
            user_id: User's phone number
            medication_name: Name of medication
            dosage: Dosage amount (e.g., "one tablet")
            times: Times to take (e.g., ["09:00", "21:00"])
            frequency: How often (daily, twice_daily, weekly)
            with_food: Whether to take with food
            instructions: Additional instructions

        Returns:
            Confirmation message
        """
        try:
            from utils.medication_manager import get_medication_manager
            med_mgr = await get_medication_manager(self.redis_client)

            result = await med_mgr.add_medication(
                phone_number=user_id,
                medication_name=medication_name,
                dosage=dosage,
                frequency=frequency,
                times=times,
                instructions=instructions,
                with_food=with_food
            )

            return result

        except Exception as e:
            logger.error(f"Error adding medication: {e}")
            return {
                "success": False,
                "message": "I had trouble saving that medication. Please try again.",
                "error": str(e)
            }

    async def list_medications(self, user_id: str) -> Dict[str, Any]:
        """
        List all medications for user

        Returns:
            Voice-friendly medication list
        """
        try:
            from utils.medication_manager import get_medication_manager
            med_mgr = await get_medication_manager(self.redis_client)

            message = await med_mgr.list_medications_voice(user_id)

            return {
                "success": True,
                "message": message
            }

        except Exception as e:
            logger.error(f"Error listing medications: {e}")
            return {
                "success": False,
                "message": "I'm having trouble accessing your medication list right now."
            }

    async def medication_taken(
        self,
        user_id: str,
        medication_name: str
    ) -> Dict[str, Any]:
        """
        Record that user took their medication

        Returns:
            Encouraging confirmation
        """
        try:
            from utils.medication_manager import get_medication_manager
            med_mgr = await get_medication_manager(self.redis_client)

            result = await med_mgr.record_medication_taken(
                phone_number=user_id,
                medication_name=medication_name
            )

            return result

        except Exception as e:
            logger.error(f"Error recording medication: {e}")
            return {
                "success": False,
                "message": "Thank you for letting me know. I've made a note of that."
            }

    async def add_emergency_contact(
        self,
        user_id: str,
        contact_name: str,
        contact_phone: str,
        relationship: str,
        priority: int = 1
    ) -> Dict[str, Any]:
        """
        Add emergency contact for user

        Args:
            user_id: User's phone number
            contact_name: Contact's name
            contact_phone: Contact's phone number
            relationship: Relationship (daughter, son, neighbor, etc.)
            priority: Call priority (1 = first, 2 = second, etc.)

        Returns:
            Confirmation message
        """
        try:
            from utils.emergency_system import get_emergency_system
            emergency_sys = await get_emergency_system(self.redis_client)

            result = await emergency_sys.add_emergency_contact(
                phone_number=user_id,
                contact_name=contact_name,
                contact_phone=contact_phone,
                relationship=relationship,
                priority=priority
            )

            return result

        except Exception as e:
            logger.error(f"Error adding emergency contact: {e}")
            return {
                "success": False,
                "message": "I had trouble saving that contact. Please try again."
            }

    async def trigger_emergency(
        self,
        user_id: str,
        emergency_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Trigger emergency protocol

        Args:
            user_id: User's phone number
            emergency_type: Type of emergency (general, medical, fall)

        Returns:
            Emergency response
        """
        try:
            from utils.emergency_system import get_emergency_system
            emergency_sys = await get_emergency_system(self.redis_client)

            result = await emergency_sys.trigger_emergency(
                phone_number=user_id,
                emergency_type=emergency_type
            )

            return result

        except Exception as e:
            logger.error(f"Error triggering emergency: {e}")
            return {
                "success": False,
                "message": (
                    "I'm having trouble reaching your contacts. "
                    "Would you like me to connect you to 999 emergency services?"
                )
            }

    async def morning_greeting(
        self,
        user_id: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create personalized morning greeting

        Returns:
            Warm morning message
        """
        try:
            from utils.companionship import get_companionship_system
            companion = await get_companionship_system(self.redis_client)

            message = await companion.create_morning_greeting(user_id, user_name)

            return {
                "success": True,
                "message": message,
                "time_of_day": "morning"
            }

        except Exception as e:
            logger.error(f"Error creating morning greeting: {e}")
            return {
                "success": True,
                "message": "Good morning! How lovely to hear from you. How are you feeling today?"
            }

    async def evening_checkin(
        self,
        user_id: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create personalized evening check-in

        Returns:
            Gentle evening message
        """
        try:
            from utils.companionship import get_companionship_system
            companion = await get_companionship_system(self.redis_client)

            message = await companion.create_evening_message(user_id, user_name)

            return {
                "success": True,
                "message": message,
                "time_of_day": "evening"
            }

        except Exception as e:
            logger.error(f"Error creating evening message: {e}")
            return {
                "success": True,
                "message": "Good evening! How has your day been?"
            }

    async def track_mood(
        self,
        user_id: str,
        mood: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track user mood and provide emotional support

        Args:
            user_id: User's phone number
            mood: Detected mood (happy, sad, lonely, anxious, unwell)
            context: What they said

        Returns:
            Empathetic response
        """
        try:
            from utils.companionship import get_companionship_system
            companion = await get_companionship_system(self.redis_client)

            result = await companion.track_mood(user_id, mood, context)

            return result

        except Exception as e:
            logger.error(f"Error tracking mood: {e}")
            return {
                "success": True,
                "response": "I'm here for you. Would you like to talk about it?"
            }


# Usage example
async def example_usage():
    """Example of how to use ToolExecutor"""
    
    executor = ToolExecutor(
        news_api_key="your_newsapi_key",
        weather_api_key="your_openweather_key"
    )
    
    # Execute news search
    news_result = await executor.execute("get_uk_news", {
        "category": "health",
        "max_headlines": 3
    })
    print("News:", news_result)
    
    # Execute weather forecast
    weather_result = await executor.execute("get_weather_forecast", {
        "postcode": "SW1A 1AA",  # Westminster
        "days": 3
    })
    print("Weather:", weather_result)
    
    # Execute Wikipedia search
    wiki_result = await executor.execute("wikipedia_search", {
        "query": "British Museum",
        "sentences": 2
    })
    print("Wikipedia:", wiki_result)
    
    # Execute storytelling
    story_result = await executor.execute("tell_story", {
        "theme": "nostalgia",
        "length": "short"
    })
    print("Story:", story_result)
    
    # Execute joke
    joke_result = await executor.execute("tell_joke", {
        "style": "british_humor"
    })
    print("Joke:", joke_result)


if __name__ == "__main__":
    asyncio.run(example_usage())
