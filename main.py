import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Suppress TensorFlow warnings

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Routers available in repository
from endpoints.voice_entry import router as voice_entry_router
from endpoints.payment_handler import router as payment_router  # Payment endpoints
from endpoints.news_weather import router as news_weather_router
from endpoints.stripe_webhook import router as stripe_webhook_router
from endpoints.conversation_handler import router as conversation_router
from endpoints.realtime_voice_handler import router as realtime_voice_router  # OpenAI Realtime WebSocket
from endpoints.health import router as health_router  # Health check and metrics endpoints

# Optional/absent modules are guarded to avoid startup failures
try:
    from utils.rate_limiter import rate_limit_middleware  # type: ignore
except Exception:  # Module may be missing; use no-op
    async def rate_limit_middleware(app: FastAPI):
        return None

from utils.logging import log_message

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform startup tasks
    await rate_limit_middleware(app)

    # Initialize conversation logger (PostgreSQL)
    try:
        # Delay import to avoid early Config validation during module import
        from utils.conversation_logger import get_conversation_logger
        conversation_logger = await get_conversation_logger()
        log_message("info", "Conversation logger initialized")
    except Exception as e:
        log_message("error", f"Failed to initialize conversation logger: {e}")

    yield

    # Perform shutdown tasks
    try:
        from utils.conversation_logger import get_conversation_logger
        conversation_logger = await get_conversation_logger()
        await conversation_logger.close()
        log_message("info", "Conversation logger closed")
    except Exception:
        pass
    
    # Close Redis connection
    try:
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        await sub_mgr.close()
        log_message("info", "Subscription manager closed")
    except Exception:
        pass

    # Close Groq client HTTP connections
    try:
        from utils.groq_client import get_groq_client
        groq_client = await get_groq_client()
        await groq_client.close()
        log_message("info", "Groq client closed")
    except Exception:
        pass

    # Shutdown MCP servers
    try:
        from utils.mcp_initialization import shutdown_mcp_servers
        await shutdown_mcp_servers()
        log_message("info", "MCP servers shut down")
    except Exception as e:
        log_message("error", f"MCP shutdown error: {e}")

app = FastAPI(lifespan=lifespan)

# Include only routers that exist in this repo to ensure app starts
app.include_router(voice_entry_router)  # /voice/entry, /voice/route, /prefs/voice
app.include_router(conversation_router) # /voice/chat, /twilio/status-callback
app.include_router(realtime_voice_router) # /voice/stream (WebSocket for OpenAI Realtime)
app.include_router(payment_router)      # /payment/*
app.include_router(news_weather_router) # /news, /weather
app.include_router(stripe_webhook_router) # /stripe/webhook
app.include_router(health_router)       # /health, /health/detailed, /health/ready, /health/live, /metrics

@app.get("/")
def root():
    return {"message": "Serenity AI is running!"}

# Remove unused stub endpoints that return JSON (violates voice-only policy)
# If these are needed, they should return TwiML XML

# Entry point for the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
