import os
from dotenv import load_dotenv

# --- Load environment variables from .env file ---
load_dotenv()

# --- DEBUG: Print loaded env variables (only use for development) ---
if os.getenv("ENV") == "development":  # Only print in development mode
    print("✅ CONFIG LOADED")
    print("GOOGLE_APPLICATION_CREDENTIALS:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

# --- Central configuration class for global access ---
class Config:
    """
    Loads and stores all external API keys and environment-based configuration
    variables required for the Serenity AI platform.
    """

    REQUIRED_KEYS = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "STRIPE_SECRET_KEY",  # Required for Twilio Pay integration
        "GROQ_API_KEY",  # Required for LLM (Groq Llama 3.1 70B) - fallback only
        "DEEPGRAM_API_KEY",  # Required for STT (Deepgram Nova-2) - fallback only
        "OPENAI_API_KEY",  # Required for OpenAI Realtime API (primary voice AI)
        "DATABASE_URL",  # Required for PostgreSQL conversation logging
        "REDIS_URL",  # Required for subscription management and caching
    ]

    # --- Google Cloud ---
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # --- AI Services (Optimized Stack) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI Realtime API (primary voice AI)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Llama 3.1 70B - fallback if OpenAI unavailable
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")  # Nova-2 STT - fallback if OpenAI unavailable
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Optional fallback
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")  # Optional: Brave Search API for Web Search MCP

    # --- Twilio ---
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    
    # --- Stripe (for Twilio Pay) ---
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")  # Optional, only for web dashboard
    
    # --- Pricing Configuration ---
    PRICE_PER_HOUR = float(os.getenv("PRICE_PER_HOUR", "6.00"))  # £6.00/hour default (£0.10/min)
    FREE_TRIAL_MINUTES = int(os.getenv("FREE_TRIAL_MINUTES", "5"))  # 5 minutes free trial
    PAYMENT_PROMPT_AT_MINUTES = int(os.getenv("PAYMENT_PROMPT_AT_MINUTES", "4"))  # Ask at 4:30 (4.5 min)
    CURRENCY = os.getenv("CURRENCY", "GBP")
    TWILIO_PAY_CONNECTOR_NAME = os.getenv("TWILIO_PAY_CONNECTOR_NAME", "Serenity AI Stripe")

    # --- Voice Configuration (4 Chirp3 HD voices) ---
    CHIRP3_VOICES = {
        "leda": "en-GB-Chirp3-HD-Leda",    # Warm female (primary companion)
        "puck": "en-GB-Chirp3-HD-Puck",    # Friendly male (storyteller)
        "seren": "en-GB-Chirp3-HD-Seren",  # Gentle female (grief/sadness)
        "aoife": "en-GB-Chirp3-HD-Aoife",  # Cheerful female (excitement/joy)
    }
    DEFAULT_VOICE = "leda"
    
    # --- Redis (for subscription tracking) ---
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # --- PostgreSQL (for conversation logging and training data) ---
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/serenityai")

    # --- Google Custom Search (used in web search or fact-finding modules) ---
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

    # --- Google Maps Places API ---
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    # --- OpenWeatherMap API (for weather endpoint) ---
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    # --- NewsAPI (for UK news headlines in function calling) ---
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Required for get_uk_news tool

    @staticmethod
    def validate_required_keys():
        """
        Validates that all required keys are set in the environment.
        Raises an exception if any key is missing.
        """
        missing_keys = [key for key in Config.REQUIRED_KEYS if not os.getenv(key)]
        if missing_keys:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_keys)}")

# Validate required keys during startup
Config.validate_required_keys()
