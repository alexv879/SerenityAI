# SerenityAI - Docker Setup Guide

Complete Docker environment for local development and production deployment.

## Quick Start

### 1. Prerequisites

- Docker Desktop or Docker Engine 20.10+
- Docker Compose V2
- Make (optional, for convenience)

### 2. Setup Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Start Services

**Option A: Using Make (recommended)**
```bash
make up          # Start in production mode
make up-dev      # Start in development mode (hot-reload)
make tools       # Start with pgAdmin and Redis Commander
```

**Option B: Using Docker Compose directly**
```bash
docker-compose up -d                                    # Production
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up  # Development
```

### 4. Verify Services

```bash
make health      # Check health status
make metrics     # View service metrics
```

Services will be available at:
- **SerenityAI API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **pgAdmin** (with --profile tools): http://localhost:5050
- **Redis Commander** (with --profile tools): http://localhost:8081

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     SerenityAI Stack                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   FastAPI    │  │  PostgreSQL  │  │    Redis     │  │
│  │     App      │  │   Database   │  │    Cache     │  │
│  │   (Python)   │  │              │  │              │  │
│  │              │  │  - Logs      │  │  - Sessions  │  │
│  │  Port 8000   │  │  - Users     │  │  - Cache     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Optional Tools (--profile tools):                      │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │   pgAdmin    │  │    Redis     │                    │
│  │              │  │  Commander   │                    │
│  │  Port 5050   │  │  Port 8081   │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

## Services

### 1. SerenityAI App (FastAPI)
- **Port**: 8000
- **Container**: serenity-app
- **Health**: http://localhost:8000/health

Features:
- Multi-worker Uvicorn server (4 workers)
- Automatic health checks
- Hot-reload in development mode
- Non-root user for security

### 2. PostgreSQL Database
- **Port**: 5432
- **Container**: serenity-postgres
- **Database**: serenityai
- **User**: postgres
- **Password**: serenity_dev_password (development)

Tables:
- `conversations` - Call metadata
- `conversation_turns` - Message history
- `function_call_logs` - Tool execution logs
- `user_preferences` - GDPR-compliant user data
- `subscription_events` - Payment lifecycle

### 3. Redis Cache
- **Port**: 6379
- **Container**: serenity-redis
- **Password**: serenity_redis_password

Use cases:
- Subscription tracking
- API response caching (40% cost reduction)
- Rate limiting
- Circuit breaker state

### 4. pgAdmin (Optional)
- **Port**: 5050
- **Container**: serenity-pgadmin
- **URL**: http://localhost:5050
- **Email**: admin@serenityai.local
- **Password**: admin

Enable with `--profile tools` flag.

### 5. Redis Commander (Optional)
- **Port**: 8081
- **Container**: serenity-redis-commander
- **URL**: http://localhost:8081

Enable with `--profile tools` flag.

---

## Common Commands

### Service Management

```bash
# Start services
make up              # Production mode
make up-dev          # Development mode with hot-reload
make tools           # Start with management tools

# Stop services
make down            # Stop all containers
make restart         # Restart services

# View logs
make logs            # All services
make logs-app        # App only
docker-compose logs -f postgres  # Specific service
```

### Database Operations

```bash
# Access database
make db-shell        # PostgreSQL CLI
make db-init         # Run initialization script
make db-reset        # Reset database (WARNING: deletes data)
make db-backup       # Backup to ./backups/

# Manual queries
docker-compose exec postgres psql -U postgres -d serenityai -c "SELECT COUNT(*) FROM conversations;"
```

### Redis Operations

```bash
# Access Redis
make redis-shell     # Redis CLI

# Manual commands in Redis CLI
redis-cli -a serenity_redis_password
> KEYS *
> GET subscription:+447411123456
> FLUSHDB  # WARNING: clears all data
```

### Application Shell

```bash
# Access app container
make shell

# Inside container:
python -c "from utils.cache import get_cache_manager; import asyncio; asyncio.run(get_cache_manager().get_stats())"
```

### Health Monitoring

```bash
# Check health
make health          # Basic + detailed health
make metrics         # Service metrics including:
                     # - Database pool stats
                     # - Cache hit/miss rates
                     # - Circuit breaker states

# Individual endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/live
curl http://localhost:8000/metrics
```

---

## Development Workflow

### 1. Start Development Environment

```bash
# Terminal 1: Start services with hot-reload
make up-dev

# Terminal 2: View logs
make logs-app
```

### 2. Make Code Changes

Files are mounted as volumes - changes reload automatically!

```python
# Edit endpoints/voice_entry.py
# Save file
# Server automatically restarts
```

### 3. Test Your Changes

```bash
# Run tests
make test

# Manual testing
curl -X POST http://localhost:8000/voice/entry \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=+447411123456"
```

### 4. Check Database

```bash
# View recent conversations
make db-shell
SELECT call_sid, phone_number, created_at, payment_status
FROM conversations
ORDER BY created_at DESC
LIMIT 10;
```

### 5. Monitor Cache

```bash
# View cache stats
curl http://localhost:8000/metrics | jq '.metrics.cache'

# Clear cache if needed
make redis-shell
FLUSHDB
```

---

## Production Deployment

### 1. Build Production Image

```bash
docker build -t serenityai:latest .
```

### 2. Configure Environment

Create production `.env` file with:
- Real API keys (not test keys)
- Strong database passwords
- Production Redis password
- PUBLIC_BASE_URL set to your domain
- STRIPE_WEBHOOK_SECRET from Stripe dashboard

### 3. Deploy to Railway/Render/AWS

**Railway:**
```bash
railway up
```

**Render:**
- Connect GitHub repository
- Set environment variables in dashboard
- Deploy from docker-compose.yml

**AWS ECS:**
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker tag serenityai:latest <account-id>.dkr.ecr.<region>.amazonaws.com/serenityai:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/serenityai:latest

# Deploy with ECS task definition
aws ecs update-service --cluster serenity --service serenity-app --force-new-deployment
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
make logs

# Check service health
docker-compose ps

# Restart specific service
docker-compose restart app
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose exec postgres pg_isready -U postgres

# Check connection from app
docker-compose exec app python -c "from utils.conversation_logger import get_conversation_logger; import asyncio; asyncio.run(get_conversation_logger())"
```

### Redis Connection Issues

```bash
# Verify Redis is running
docker-compose exec redis redis-cli -a serenity_redis_password ping

# Check connection from app
docker-compose exec app python -c "from utils.subscription_manager import get_subscription_manager; import asyncio; asyncio.run(get_subscription_manager())"
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
kill -9 <PID>

# Or change ports in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```

### Cache Issues

```bash
# Clear Redis cache
make redis-shell
FLUSHDB

# Restart Redis
docker-compose restart redis
```

---

## Backup & Restore

### Backup Database

```bash
# Automatic backup
make db-backup

# Manual backup
docker-compose exec -T postgres pg_dump -U postgres serenityai > backup.sql
```

### Restore Database

```bash
# From backup file
docker-compose exec -T postgres psql -U postgres serenityai < backup.sql

# From latest backup in ./backups/
docker-compose exec -T postgres psql -U postgres serenityai < backups/serenity_20251118_120000.sql
```

### Backup Redis Data

```bash
# Redis automatically persists to /data (mounted volume)
docker-compose exec redis redis-cli -a serenity_redis_password SAVE
docker cp serenity-redis:/data/dump.rdb ./backups/redis-backup.rdb
```

---

## Performance Tuning

### Increase Workers

```yaml
# docker-compose.yml
command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 8
```

### PostgreSQL Pool Size

```python
# utils/conversation_logger.py
self.pool = await asyncpg.create_pool(
    dsn=database_url,
    min_size=10,
    max_size=100  # Increase for more concurrent connections
)
```

### Redis Memory Limit

```yaml
# docker-compose.yml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## Security Checklist

- [ ] Change default passwords in production
- [ ] Use secrets management (AWS Secrets Manager, Railway secrets)
- [ ] Enable SSL/TLS for database connections
- [ ] Set `ENV=production` in production
- [ ] Never commit `.env` files (in `.gitignore`)
- [ ] Use non-root user in containers ✅
- [ ] Enable health checks ✅
- [ ] Set up firewall rules (only expose necessary ports)
- [ ] Regularly update base images
- [ ] Monitor logs for suspicious activity

---

## Next Steps

1. **Set up CI/CD**: Automate testing and deployment
2. **Add monitoring**: Integrate with Datadog, New Relic, or Prometheus
3. **Scale horizontally**: Add load balancer for multiple app instances
4. **Database replication**: Set up read replicas for scaling
5. **Redis cluster**: High availability Redis setup

For more information, see the main [README.md](README.md).
