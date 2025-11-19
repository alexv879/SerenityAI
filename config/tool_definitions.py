"""
Tool/function definitions for OpenAI Realtime API
Defines capabilities for news, weather, knowledge, reminders, appointments
"""

# Complete tool catalog for OpenAI Realtime function calling
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_uk_news",
        "description": "Get latest UK news headlines. Use when user asks 'what's in the news', 'tell me the headlines', or similar.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["general", "health", "technology", "business", "entertainment", "sports"],
                    "description": "News category to fetch",
                    "default": "general"
                },
                "max_headlines": {
                    "type": "integer",
                    "description": "Maximum number of headlines to retrieve (1-10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "get_weather_forecast",
        "description": "Get UK weather forecast for user's location. Use when user asks about weather, rain, temperature, or forecast.",
        "parameters": {
            "type": "object",
            "properties": {
                "postcode": {
                    "type": "string",
                    "description": "UK postcode (optional, uses user's saved location if not provided)",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to forecast (1-5)",
                    "default": 1,
                    "enum": [1, 3, 5]
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "wikipedia_search",
        "description": "Search Wikipedia for information on a topic. Use for factual questions about people, places, events, or concepts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'Winston Churchill', 'Big Ben', 'World War 2')"
                },
                "sentences": {
                    "type": "integer",
                    "description": "Number of sentences to retrieve from Wikipedia summary",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "on_this_day",
        "description": "Get historical events that happened on today's date. Use when user asks 'what happened on this day', 'on this day in history', etc.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "set_reminder",
        "description": "Set a reminder for the user (medication, appointment, important task). User will receive a phone call at the scheduled time.",
        "parameters": {
            "type": "object",
            "properties": {
                "reminder_text": {
                    "type": "string",
                    "description": "What to remind the user about (e.g., 'Take your blood pressure medication', 'Call the dentist')"
                },
                "when": {
                    "type": "string",
                    "description": "When to send the reminder. Examples: 'in 30 minutes', 'in 2 hours', 'tomorrow at 2 PM', 'at 9 AM'"
                }
            },
            "required": ["reminder_text", "when"]
        }
    },
    {
        "type": "function",
        "name": "recall_user_context",
        "description": "Load previous conversation history and user preferences from memory. Use at the start of each call to personalize the interaction. Returns topics discussed, user preferences, and general context.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "tell_story",
        "description": "Tell the user a story from the classic collection. Perfect for entertainment, reminiscence, or bedtime. Stories include British classics, wartime memories, seaside holidays, and gentle tales from the 1940s-1960s era.",
        "parameters": {
            "type": "object",
            "properties": {
                "theme": {
                    "type": "string",
                    "enum": ["classic", "nostalgia", "bedtime", "wartime", "seaside", "village", "nature", "gentle_humor"],
                    "description": "Story theme to tell",
                    "default": "classic"
                },
                "length": {
                    "type": "string",
                    "enum": ["short", "medium", "long"],
                    "description": "Story length (short: 2-3 min, medium: 5-7 min, long: 10+ min)",
                    "default": "medium"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "tell_joke",
        "description": "Tell a clean, elderly-appropriate joke. Perfect for brightening the mood and bringing laughter to the conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "style": {
                    "type": "string",
                    "enum": ["gentle", "witty", "wordplay", "british_humor"],
                    "description": "Style of humor",
                    "default": "gentle"
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "switch_mode",
        "description": "Switch Serenity's conversation mode to change personality and voice style. Companion (default), Storytelling (expressive theatrical voice), or Newsreader (authoritative clear voice).",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["companion", "storytelling", "newsreader"],
                    "description": "Mode to switch to"
                }
            },
            "required": ["mode"]
        }
    }
]

# Tool definitions optimized for elderly users (simplified descriptions)
ELDERLY_OPTIMIZED_TOOLS = [
    {
        "type": "function",
        "name": "get_uk_news",
        "description": "Get today's news headlines from the UK",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["general", "health"],
                    "default": "general"
                }
            }
        }
    },
    {
        "type": "function",
        "name": "get_weather_forecast",
        "description": "Check the weather forecast",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "default": 1,
                    "enum": [1, 3]
                }
            }
        }
    },
    {
        "type": "function",
        "name": "set_reminder",
        "description": "Set a reminder to call back later",
        "parameters": {
            "type": "object",
            "properties": {
                "reminder_text": {"type": "string"},
                "when": {"type": "string"}
            },
            "required": ["reminder_text", "when"]
        }
    }
]
