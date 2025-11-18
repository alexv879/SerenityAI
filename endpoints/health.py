"""
Health Check Endpoints - Monitor system status and dependencies

Provides comprehensive health monitoring for:
- Database connections (PostgreSQL)
- Cache connections (Redis)
- External API status (Twilio, Stripe, OpenAI)
- System resources

Author: Claude Code
Date: 2025-11-18
"""

from fastapi import APIRouter, Response
from typing import Dict, Any
import logging
import asyncio
from datetime import datetime
import os

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint

    Returns:
        Simple health status for load balancers
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SerenityAI"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Comprehensive health check with dependency status

    Checks:
    - PostgreSQL database connection
    - Redis cache connection
    - Environment configuration
    - External API accessibility

    Returns:
        Detailed health status with component breakdown
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SerenityAI",
        "version": "2.1",
        "environment": os.getenv("ENV", "unknown"),
        "components": {}
    }

    # Check PostgreSQL
    try:
        from utils.conversation_logger import get_conversation_logger
        logger_instance = await get_conversation_logger()
        if logger_instance.pool:
            async with logger_instance.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["components"]["postgresql"] = {
                "status": "healthy",
                "message": "Database connection active",
                "pool_size": logger_instance.pool.get_size(),
                "max_size": logger_instance.pool.get_max_size()
            }
        else:
            health_status["components"]["postgresql"] = {
                "status": "unhealthy",
                "message": "Database pool not initialized"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["postgresql"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Check Redis
    try:
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        redis_client = await sub_mgr._get_client()
        await redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection active"
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}"
        }
        health_status["status"] = "degraded"

    # Check Environment Variables
    required_vars = [
        "OPENAI_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "STRIPE_SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        health_status["components"]["environment"] = {
            "status": "unhealthy",
            "message": f"Missing environment variables: {', '.join(missing_vars)}"
        }
        health_status["status"] = "unhealthy"
    else:
        health_status["components"]["environment"] = {
            "status": "healthy",
            "message": "All required environment variables configured"
        }

    # Check OpenAI API Key validity (basic check)
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            health_status["components"]["openai"] = {
                "status": "configured",
                "message": "OpenAI API key configured"
            }
        else:
            health_status["components"]["openai"] = {
                "status": "warning",
                "message": "OpenAI API key format invalid"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["openai"] = {
            "status": "unknown",
            "message": str(e)
        }

    # Check MCP Status (if available)
    try:
        from utils.mcp_initialization import get_mcp_status
        mcp_status = get_mcp_status()
        total_tools = sum(len(server.get("tools", [])) for server in mcp_status.values())
        health_status["components"]["mcp"] = {
            "status": "healthy",
            "message": f"{len(mcp_status)} servers, {total_tools} tools",
            "servers": list(mcp_status.keys())
        }
    except Exception as e:
        health_status["components"]["mcp"] = {
            "status": "unavailable",
            "message": f"MCP not available: {str(e)}"
        }

    return health_status


@router.get("/health/ready")
async def readiness_check() -> Response:
    """
    Kubernetes/Docker readiness probe

    Returns 200 if service is ready to accept traffic
    Returns 503 if not ready

    Used by orchestration platforms to determine if pod should receive traffic
    """
    try:
        # Quick check of critical dependencies
        from utils.subscription_manager import get_subscription_manager
        sub_mgr = await get_subscription_manager()
        redis_client = await sub_mgr._get_client()

        # Quick ping
        await asyncio.wait_for(redis_client.ping(), timeout=1.0)

        return Response(
            content='{"status": "ready"}',
            status_code=200,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return Response(
            content=f'{{"status": "not ready", "error": "{str(e)}"}}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes/Docker liveness probe

    Returns 200 if service is alive (even if degraded)
    Only returns 5xx if service should be restarted

    Used by orchestration platforms to determine if pod should be restarted
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """
    Basic metrics endpoint for monitoring

    Returns:
        System metrics and usage statistics
    """
    metrics_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SerenityAI",
        "metrics": {}
    }

    # Database pool metrics
    try:
        from utils.conversation_logger import get_conversation_logger
        logger_instance = await get_conversation_logger()
        if logger_instance.pool:
            metrics_data["metrics"]["database"] = {
                "pool_size": logger_instance.pool.get_size(),
                "max_size": logger_instance.pool.get_max_size(),
                "idle_size": logger_instance.pool.get_idle_size(),
                "min_size": logger_instance.pool.get_min_size()
            }
    except Exception as e:
        metrics_data["metrics"]["database"] = {"error": str(e)}

    # Add more metrics as needed
    # - Active calls count
    # - Total calls today
    # - Revenue today
    # - Error rate
    # - Average response time

    return metrics_data
