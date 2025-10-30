# SerenityAI - Elderly Voice Companion

**AI-powered voice companion service designed specifically for elderly users in the UK**

## Overview

SerenityAI is a sophisticated voice-based AI assistant that provides companionship, information, and support to elderly users through simple phone calls. No apps, no complicated technology - just call and talk.

### Key Features

- **24/7 Voice Companionship**: Always available for conversation and support
- **Natural Conversations**: Powered by OpenAI Realtime API with low-latency audio streaming
- **UK-Focused Services**: Integration with NHS, Age UK, and local services
- **Simple Access**: Just a phone call - no apps or tech skills required
- **Privacy-First**: GDPR compliant with phone number hashing and PII anonymization
- **Flexible Pricing**: 5-minute free trial, then £6/hour pay-as-you-go

## Technology Stack

### Core Framework
- **FastAPI**: Modern async web framework
- **Python 3.9+**: Primary development language
- **Uvicorn/Gunicorn**: Production-grade ASGI server

### AI & Voice Services
- **OpenAI Realtime API**: Primary voice AI (GPT-4 Turbo with audio)
- **Google Cloud Text-to-Speech**: Chirp3 HD voices (4 UK voices)
- **Groq (Llama 3.1 70B)**: Fallback LLM (75% faster, 85% cheaper)
- **Deepgram Nova-2**: Fallback STT (70% faster, 28% cheaper)

### Communication & Payments
- **Twilio**: Voice telephony infrastructure
- **Stripe**: Payment processing via Twilio Pay

### Data Storage
- **PostgreSQL**: Conversation logging and training data (asyncpg)
- **Redis**: Subscription management and caching

### Integration Framework
- **Model Context Protocol (MCP)**: Standardized tool integration
  - Web Search MCP Server (Brave API / DuckDuckGo)
  - NHS Healthcare MCP Server
  - Age UK Services MCP Server

## Project Structure

```
D:\SerenityAI/
├── main.py                      # FastAPI application entry point
├── config.py                    # Centralized configuration
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Production Docker image
├── Dockerfile.production        # Optimized production build
│
├── endpoints/                   # FastAPI routers
│   ├── voice_entry.py          # Call entry point (/voice/entry)
│   ├── conversation_handler.py # Main conversation logic (/voice/chat)
│   ├── realtime_voice_handler.py # OpenAI Realtime WebSocket
│   ├── payment_handler.py      # Twilio Pay integration
│   ├── news_weather.py         # News & weather endpoints
│   └── stripe_webhook.py       # Stripe webhook handler
│
├── utils/                       # Core utilities
│   ├── subscription_manager.py # Redis-based subscription tracking
│   ├── conversation_logger.py  # PostgreSQL conversation storage
│   ├── openai_realtime_client.py # OpenAI Realtime API client
│   ├── mcp_client.py           # MCP client manager
│   ├── mcp_initialization.py   # MCP server startup
│   ├── tool_executor.py        # Function calling handler
│   ├── groq_client.py          # Groq LLM client (fallback)
│   ├── audio_transcoding.py    # Audio format conversion
│   ├── memory_manager.py       # User memory & context
│   ├── story_library.py        # Story generation
│   ├── analytics_logger.py     # Usage analytics
│   ├── helpers.py              # General utilities
│   ├── personality_selector.py # Voice personality matching
│   └── logging.py              # Logging configuration
│
├── mcp_servers/                 # MCP server implementations
│   ├── web_search_server.py    # Web search (Brave/DuckDuckGo)
│   ├── nhs_healthcare_server.py # NHS service lookup
│   └── age_uk_services_server.py # Age UK befriending services
│
├── config/                      # Configuration files
│   ├── system_prompts.py       # AI system prompts
│   ├── tool_definitions.py     # Function calling schemas
│   └── realtime_config.py      # OpenAI Realtime settings
│
├── prompts/                     # Prompt templates
│   └── templates.json          # TwiML and prompt templates
│
├── tests/                       # Test suite
│   ├── test_voice_entry.py
│   └── test_payment_handler.py
│
├── documents/                   # Internal documentation (not on GitHub)
│   ├── README.md
│   ├── architecture-overview.md
│   ├── quickstart.md
│   ├── action-items.md
│   ├── patches/                # Critical bug fix patches
│   └── [50+ internal docs]
│
└── scripts/                     # Utility scripts (not on GitHub)
    ├── test_mcp_integration.py
    ├── check_name_usage.py
    └── find_*_name.py
```

## Installation

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 12+
- Redis 6+
- Twilio account with phone number
- OpenAI API key
- Stripe account
- Google Cloud account (for TTS/STT fallback)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/SerenityAI.git
cd SerenityAI
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy example and edit
cp .env.example .env
```

Required environment variables:

```env
# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# OpenAI
OPENAI_API_KEY=sk-...

# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+44...

# Stripe
STRIPE_SECRET_KEY=sk_...

# AI Services (Fallback)
GROQ_API_KEY=gsk_...
DEEPGRAM_API_KEY=...
GEMINI_API_KEY=...  # Optional

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/serenityai
REDIS_URL=redis://localhost:6379

# Optional APIs
BRAVE_API_KEY=...  # For web search (falls back to DuckDuckGo)
NEWS_API_KEY=...   # For UK news
OPENWEATHER_API_KEY=...  # For weather
GOOGLE_MAPS_API_KEY=...  # For location services
```

### 5. Initialize Database

```bash
# Create PostgreSQL database
createdb serenityai

# Run migrations (if migration scripts exist)
# python scripts/migrate.py
```

### 6. Start Redis

```bash
redis-server
```

### 7. Run Application

```bash
# Development mode (with auto-reload)
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

### Making a Call

1. **Dial the Twilio number**: Call the configured Twilio phone number
2. **Greeting**: You'll hear: "Hello, it's Serenity. I'm here to chat and help."
3. **Free Trial**: First 5 minutes are free
4. **Payment**: After 4:30, you'll be prompted to pay £6 for another hour
5. **Continue**: Keep chatting as long as you like!

### Available Features

- **General Conversation**: Chat about anything
- **Information Lookup**: Ask about weather, news, facts
- **Local Services**: Find NHS services, chiropodists, Age UK support
- **Storytelling**: Request stories on any topic
- **Memory**: The AI remembers your preferences across calls

### Example Conversations

```
User: "What's the weather like today?"
AI: "Let me check that for you... [fetches weather]"

User: "I need to find a chiropodist near me"
AI: "I can help with that. What's your postcode?"

User: "Can you tell me a story about the countryside?"
AI: "Of course! Once upon a time in the rolling hills..."
```

## API Endpoints

### Voice Endpoints

- `POST /voice/entry` - Initial call entry point (Twilio webhook)
- `POST /voice/chat` - Main conversation handler (Twilio webhook)
- `WS /voice/stream` - OpenAI Realtime WebSocket connection

### Payment Endpoints

- `POST /payment/start` - Initiate Twilio Pay
- `POST /payment/callback` - Payment result webhook

### Utility Endpoints

- `GET /news` - Get UK news headlines
- `GET /weather` - Get weather forecast
- `POST /stripe/webhook` - Stripe event webhook

### Status Endpoints

- `GET /` - Health check

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_voice_entry.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Testing MCP Integration

```bash
python scripts/test_mcp_integration.py
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t serenityai:latest .

# Run container
docker run -p 8000:8000 --env-file .env serenityai:latest
```

### Production Deployment (Railway/Heroku)

1. Set all environment variables in platform settings
2. Configure PostgreSQL and Redis add-ons
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### Environment-Specific Configuration

```bash
# Set environment
export ENV=production  # or development, staging

# Production: Disable debug logging
export TF_CPP_MIN_LOG_LEVEL=2
```

## Architecture

### High-Level Flow

```
┌─────────────┐
│   User      │
│   (Phone)   │
└──────┬──────┘
       │ Call
       ▼
┌─────────────────────────────────────────────┐
│              Twilio                         │
│  (Voice Gateway + Media Streams)           │
└──────┬──────────────────────────────────────┘
       │ HTTP Webhooks / WebSocket
       ▼
┌─────────────────────────────────────────────┐
│           SerenityAI FastAPI                │
│  ┌────────────────────────────────────┐     │
│  │  Voice Entry → Conversation Handler│     │
│  └──────┬─────────────────────────────┘     │
│         │                                    │
│         ▼                                    │
│  ┌─────────────────────────────────────┐    │
│  │  OpenAI Realtime API               │    │
│  │  (WebSocket Audio Streaming)        │    │
│  └──────┬──────────────────────────────┘    │
│         │                                    │
│         ▼                                    │
│  ┌─────────────────────────────────────┐    │
│  │  MCP Servers (Tools)               │    │
│  │  - Web Search                       │    │
│  │  - NHS Services                     │    │
│  │  - Age UK                          │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
       │           │
       ▼           ▼
┌──────────┐  ┌─────────┐
│PostgreSQL│  │  Redis  │
│(Logs)    │  │(Subs)   │
└──────────┘  └─────────┘
```

### Key Design Patterns

- **Async/Await**: All I/O operations are async for high concurrency
- **Singleton Pattern**: Shared resources (DB, Redis, MCP) use thread-safe singletons
- **Dependency Injection**: FastAPI dependencies for clean separation
- **MCP Protocol**: Standardized tool integration
- **GDPR Compliance**: Phone number hashing, PII anonymization, explicit consent

## Security & Compliance

### Security Features

- ✅ Phone number hashing (SHA-256)
- ✅ PII anonymization in logs
- ✅ Twilio webhook signature verification
- ✅ Stripe webhook signature verification
- ✅ Environment variable validation
- ✅ No API keys in code
- ✅ Encrypted connections (HTTPS/WSS)

### GDPR Compliance

- ✅ Explicit consent collection
- ✅ Data anonymization
- ✅ Right to deletion
- ✅ 7-year data retention (HMRC requirement)
- ✅ Secure data storage (PostgreSQL)

### Known Issues & Roadmap

See `documents/action-items.md` for detailed tracking.

**Critical Issues Fixed**:
- ✅ Thread-safe singleton patterns
- ✅ Redis connection initialization
- ✅ Database/Redis added to required keys
- ✅ Organized documentation and scripts

**Remaining Issues**:
- ⚠️ Subscription schema inconsistency (trial vs. paid)
- ⚠️ SQL injection risk in conversation_logger.py (line 331)
- ⚠️ Missing reconnection logic for WebSocket drops
- ⚠️ No rate limiting on expensive API calls

See detailed analysis in code review report.

## Contributing

This is a private project. For authorized contributors:

1. Create a feature branch
2. Make changes with tests
3. Submit pull request
4. Ensure all tests pass
5. Get code review approval

## License

Proprietary. All rights reserved.

## Support

For issues or questions:
- Check `documents/` folder for detailed documentation
- Review `documents/quickstart.md` for setup help
- Check `documents/troubleshooting.md` for common issues

## Acknowledgments

- **OpenAI**: Realtime API for natural voice conversations
- **Twilio**: Voice telephony infrastructure
- **Anthropic**: Model Context Protocol (MCP) design
- **Google Cloud**: Text-to-Speech and Speech-to-Text services
- **NHS & Age UK**: Service data and APIs

---

**SerenityAI** - Bringing companionship and support to elderly users through the power of AI 🤖❤️
