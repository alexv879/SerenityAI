<div align="center">

# 🎙️ SerenityAI - Elderly Voice Companion

**AI-powered voice companion service designed specifically for elderly users in the UK**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenAI Realtime](https://img.shields.io/badge/OpenAI-Realtime%20API-412991.svg)](https://platform.openai.com/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

[![Twilio](https://img.shields.io/badge/Twilio-Voice%20API-F22F46.svg)](https://www.twilio.com/)
[![Stripe](https://img.shields.io/badge/Stripe-Payments-008CDD.svg)](https://stripe.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-316192.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-6+-DC382D.svg)](https://redis.io/)

[Features](#key-features) • [Tech Stack](#technology-stack) • [Installation](#installation) • [Usage](#usage) • [Architecture](#architecture)

---

</div>

## 🌟 Overview

SerenityAI is a sophisticated voice-based AI assistant that provides companionship, information, and support to elderly users through simple phone calls. No apps, no complicated technology - just call and talk.

> **🎯 Mission**: Making technology accessible and beneficial for elderly users through natural voice conversations.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🗣️ **24/7 Voice Companionship** | Always available for conversation and support |
| 🤖 **Natural Conversations** | Powered by OpenAI Realtime API with low-latency audio streaming |
| 🏥 **UK-Focused Services** | Integration with NHS, Age UK, and local services |
| 📞 **Simple Access** | Just a phone call - no apps or tech skills required |
| 🔒 **Privacy-First** | GDPR compliant with phone number hashing and PII anonymization |
| 💰 **Flexible Pricing** | 5-minute free trial, then £6/hour pay-as-you-go |
| 🔧 **12 Built-in Tools** | Web search, NHS lookup, weather, news, reminders, and more |
| 🎭 **Emotion-Aware** | 4 voice personalities that adapt to user's emotional state |

## 🛠️ Technology Stack

<table>
<tr>
<td width="50%">

### Core Framework
- **FastAPI** - Modern async web framework
- **Python 3.9+** - Primary language
- **Uvicorn/Gunicorn** - ASGI server

### AI & Voice Services
- **OpenAI Realtime API** - Primary voice AI
- **Google Chirp3 HD** - TTS (4 UK voices)
- **Groq (Llama 3.1 70B)** - Fallback LLM
- **Deepgram Nova-2** - Fallback STT

</td>
<td width="50%">

### Communication & Payments
- **Twilio** - Voice telephony
- **Stripe** - Payment processing

### Data Storage
- **PostgreSQL** - Conversation logs
- **Redis** - Subscriptions & caching

### Integration Framework
- **Model Context Protocol (MCP)** 
  - Web Search Server
  - NHS Healthcare Server
  - Age UK Services Server

</td>
</tr>
</table>

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

## 🚀 Quick Start

### Prerequisites

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-316192?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-6+-DC382D?logo=redis&logoColor=white)

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

## 📞 Usage

### Making a Call

```mermaid
graph LR
    A[📱 Dial Number] --> B[🎙️ Greeting]
    B --> C[⏱️ 5 Min Free Trial]
    C --> D{Continue?}
    D -->|Yes| E[💳 Pay £6/hour]
    D -->|No| F[👋 Goodbye]
    E --> G[💬 Chat Unlimited]
```

1. **Dial the Twilio number**: Call the configured Twilio phone number
2. **Greeting**: You'll hear: "Hello, it's Serenity. I'm here to chat and help."
3. **Free Trial**: First 5 minutes are free
4. **Payment**: After 4:30, you'll be prompted to pay £6 for another hour
5. **Continue**: Keep chatting as long as you like!

### 💡 Available Features

<table>
<tr>
<td width="50%">

#### 🗣️ Conversation
- General chat and companionship
- Emotion detection and empathy
- Memory across calls
- Story generation

#### 🔍 Information
- Web search (Brave/DuckDuckGo)
- UK news headlines
- Weather forecasts
- General knowledge

</td>
<td width="50%">

#### 🏥 Healthcare & Services
- NHS service finder
- Age UK befriending services
- Local chiropodist search
- Medication reminders

#### 🎭 Personalization
- 4 voice personalities
- Context-aware responses
- Preference learning
- Emotional adaptation

</td>
</tr>
</table>

### 💬 Example Conversations

```plaintext
👤 User: "What's the weather like today?"
🤖 AI: "Let me check that for you... It's partly cloudy with a high of 18°C..."

👤 User: "I need to find a chiropodist near me"
🤖 AI: "I can help with that. What's your postcode?"

👤 User: "Can you tell me a story about the countryside?"
🤖 AI: "Of course! Once upon a time in the rolling hills of Yorkshire..."

👤 User: "I'm feeling a bit lonely today"
🤖 AI: "I'm here with you. Would you like to chat about what's on your mind?"
```

## 📡 API Endpoints

<details>
<summary><b>Voice Endpoints</b></summary>

- `POST /voice/entry` - Initial call entry point (Twilio webhook)
- `POST /voice/chat` - Main conversation handler (Twilio webhook)
- `WS /voice/stream` - OpenAI Realtime WebSocket connection
- `GET /voice/stream/health` - WebSocket health check

</details>

<details>
<summary><b>Payment Endpoints</b></summary>

- `POST /payment/start` - Initiate Twilio Pay
- `POST /payment/callback` - Payment result webhook

</details>

<details>
<summary><b>MCP Endpoints</b></summary>

- `GET /mcp/health` - MCP server status (3 servers, 12 tools)

</details>

<details>
<summary><b>Utility Endpoints</b></summary>

- `GET /news` - Get UK news headlines
- `GET /weather` - Get weather forecast
- `POST /stripe/webhook` - Stripe event webhook
- `GET /` - Health check

</details>

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

## 🚀 Deployment

### 🐳 Docker Deployment

<table>
<tr>
<td width="50%">

**Development**
```bash
# Build image
docker build -t serenityai:dev .

# Run with hot reload
docker run -p 8000:8000 \
  -v $(pwd):/app \
  --env-file .env \
  serenityai:dev
```

</td>
<td width="50%">

**Production**
```bash
# Build production image
docker build -f Dockerfile.production \
  -t serenityai:latest .

# Run with resource limits
docker run -p 8000:8000 \
  --memory="2g" \
  --cpus="1.5" \
  --env-file .env.production \
  serenityai:latest
```

</td>
</tr>
</table>

### ☁️ Cloud Platform Deployment

<table>
<tr>
<td width="33%">

**🚄 Railway**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway up
```

**Auto-deploy**: Connect GitHub for CD

</td>
<td width="33%">

**🟣 Heroku**
```bash
# Create app
heroku create serenityai

# Add buildpack
heroku buildpacks:set heroku/python

# Deploy
git push heroku main
```

**Scale**: `heroku ps:scale web=2`

</td>
<td width="33%">

**🔵 Azure**
```bash
# Create resource group
az group create -n serenityai-rg

# Deploy container
az container create \
  --resource-group serenityai-rg \
  --name serenityai \
  --image serenityai:latest
```

**Database**: Use Azure PostgreSQL

</td>
</tr>
</table>

### ⚙️ Production Configuration

| Setting | Development | Production |
|---------|-------------|------------|
| **Workers** | 1 | 4+ (CPU cores × 2) |
| **Logging** | DEBUG | INFO |
| **SSL** | Optional | Required (Let's Encrypt) |
| **Database Pool** | 5 connections | 20+ connections |
| **Redis** | Local | Cloud (ElastiCache/Azure) |
| **Monitoring** | Console logs | CloudWatch/Azure Monitor |

### 🔐 Security Checklist

- [ ] All API keys in environment variables
- [ ] Database SSL/TLS enabled
- [ ] Redis password authentication
- [ ] Webhook signature verification
- [ ] Rate limiting enabled
- [ ] CORS configured for production domains
- [ ] Firewall rules (only ports 80/443)
- [ ] Regular security updates



## 🏗️ Architecture

### System Architecture

```mermaid
graph TB
    subgraph "User Layer"
        A[📱 Phone Call<br/>via Twilio]
    end
    
    subgraph "Communication Layer"
        B[🌐 FastAPI Server<br/>Twilio Webhooks]
        C[🔌 WebSocket<br/>OpenAI Realtime]
    end
    
    subgraph "AI Layer"
        D[🤖 OpenAI GPT-4<br/>Realtime API]
        E[🧠 AI Processing<br/>Vision, Tools, Functions]
    end
    
    subgraph "Integration Layer"
        F[🔧 MCP Server<br/>3 Servers, 12 Tools]
        G[💳 Stripe<br/>Payment Processing]
        H[📰 News API<br/>UK Headlines]
        I[🌤️ Weather API<br/>Forecast]
    end
    
    subgraph "Data Layer"
        J[(📊 PostgreSQL<br/>Call Records, Users)]
        K[(🔴 Redis<br/>Sessions, Cache)]
        L[📝 Logs<br/>CloudWatch]
    end
    
    A -->|Voice| B
    B <-->|Audio Stream| C
    C <-->|Realtime| D
    D <--> E
    E <--> F
    B --> G
    F --> H
    F --> I
    B --> J
    B --> K
    B --> L
    
    style A fill:#e1f5ff
    style D fill:#fff4e6
    style F fill:#f3e5f5
    style J fill:#e8f5e9
    style K fill:#ffebee
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

## 🤝 Contributing

This is a private project. For authorized contributors:

<table>
<tr>
<td width="50%">

### 📝 Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make Changes**
   - Follow code style guidelines
   - Add tests for new features
   - Update documentation

3. **Run Tests**
   ```bash
   pytest
   flake8 .
   mypy .
   ```

4. **Submit PR**
   - Clear description
   - Link related issues
   - Request review

</td>
<td width="50%">

### 📋 Code Standards

**Python Style**:
- Follow PEP 8
- Type hints required
- Docstrings for functions
- Max line length: 120

**Commit Messages**:
```
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
refactor: improve code
```

**Testing**:
- Minimum 80% coverage
- Unit + integration tests
- Mock external services

</td>
</tr>
</table>

### 🐛 Issue Reporting

Found a bug? Please include:
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python version)
- Relevant logs



## 📄 License

**Proprietary License** - All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

---

## 🆘 Support

<table>
<tr>
<td width="50%">

### 📚 Documentation
- **Setup Guide**: `documents/quickstart.md`
- **Troubleshooting**: `documents/troubleshooting.md`
- **API Reference**: `documents/api-reference.md`
- **Architecture**: `documents/architecture.md`

</td>
<td width="50%">

### 🔧 Common Issues
- **Voice not working**: Check Twilio webhooks
- **Payment failing**: Verify Stripe keys
- **MCP errors**: Restart MCP servers
- **Database errors**: Check PostgreSQL connection

</td>
</tr>
</table>

### 📞 Contact

For issues, questions, or support:
- 📧 Email: support@serenityai.com
- 📖 Docs: `/documents/` folder
- 🐛 Issues: GitHub Issues (authorized users)

---

## 🙏 Acknowledgments

<table>
<tr>
<td width="25%" align="center">
<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/openai/openai-original.svg" width="40"/><br/>
<b>OpenAI</b><br/>
Realtime API
</td>
<td width="25%" align="center">
<img src="https://www.vectorlogo.zone/logos/twilio/twilio-icon.svg" width="40"/><br/>
<b>Twilio</b><br/>
Voice Infrastructure
</td>
<td width="25%" align="center">
<img src="https://www.vectorlogo.zone/logos/stripe/stripe-icon.svg" width="40"/><br/>
<b>Stripe</b><br/>
Payment Processing
</td>
<td width="25%" align="center">
<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/google/google-original.svg" width="40"/><br/>
<b>Google Cloud</b><br/>
Speech Services
</td>
</tr>
<tr>
<td colspan="2" align="center">
<b>NHS & Age UK</b><br/>
Service data and APIs for healthcare information
</td>
<td colspan="2" align="center">
<b>Anthropic</b><br/>
Model Context Protocol (MCP) design and specification
</td>
</tr>
</table>

---

<div align="center">

**🤖 SerenityAI** - Bringing companionship and support to elderly users through the power of AI ❤️

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue?logo=python&logoColor=white)](https://python.org)
[![Powered by OpenAI](https://img.shields.io/badge/Powered%20by-OpenAI-412991?logo=openai&logoColor=white)](https://openai.com)
[![Built with FastAPI](https://img.shields.io/badge/Built%20with-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

⭐ Star this repo if you find it useful! | 📧 [Contact Us](mailto:support@serenityai.com)

</div>
