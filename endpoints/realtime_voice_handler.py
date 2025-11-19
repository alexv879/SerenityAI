"""
WebSocket endpoint handler for Twilio → OpenAI Realtime integration
Handles bidirectional audio streaming with function calling
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from config.system_prompts import ELDERLY_COMPANION_PROMPT
from config.tool_definitions import TOOL_DEFINITIONS
from utils.openai_realtime_client import OpenAIRealtimeClient
from utils.tool_executor import ToolExecutor
from utils.audio_transcoding import mulaw_to_pcm16_24khz, pcm16_24khz_to_mulaw
from utils.elderly_conversation_optimizer import get_elderly_optimizer
from utils.mcp_initialization import (
    initialize_mcp_servers,
    get_mcp_tools_for_openai,
    shutdown_mcp_servers
)
import config

logger = logging.getLogger(__name__)

router = APIRouter()

# MCP initialization flag and lock
_mcp_initialized = False
_mcp_init_lock = asyncio.Lock()


async def ensure_mcp_initialized() -> bool:
    """
    Thread-safe MCP initialization
    Ensures only one initialization happens even with concurrent calls
    """
    global _mcp_initialized
    
    if _mcp_initialized:
        return True
    
    async with _mcp_init_lock:
        # Double-check after acquiring lock
        if _mcp_initialized:
            return True
        
        logger.info("🚀 Initializing MCP servers...")
        try:
            import config as cfg
            brave_api_key = getattr(cfg, 'BRAVE_API_KEY', None)
            success = await initialize_mcp_servers(brave_api_key=brave_api_key)
            
            if success:
                _mcp_initialized = True
                logger.info("✅ MCP servers initialized successfully")
            else:
                logger.warning("⚠️  MCP servers failed to initialize - continuing with built-in tools only")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ MCP initialization error: {e}", exc_info=True)
            return False


class RealtimeSession:
    """
    Manages a single Twilio → OpenAI Realtime session
    Handles audio transcoding and function calling
    """
    
    def __init__(
        self,
        twilio_ws: WebSocket,
        openai_api_key: str,
        call_sid: str,
        stream_sid: Optional[str] = None
    ):
        self.twilio_ws = twilio_ws
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.started = False

        # Initialize elderly conversation optimizer with custom settings
        # Optimizes for: longer pauses, UK accents, background noise, repetition tolerance
        self.elderly_optimizer = get_elderly_optimizer()
        elderly_config = self.elderly_optimizer.get_session_config()

        # Combine built-in tools with MCP tools
        all_tools = TOOL_DEFINITIONS.copy()

        # Add MCP tools if initialized
        global _mcp_initialized
        if _mcp_initialized:
            mcp_tools = get_mcp_tools_for_openai()
            all_tools.extend(mcp_tools)
            logger.info(f"Loaded {len(mcp_tools)} MCP tools + {len(TOOL_DEFINITIONS)} built-in tools")
        else:
            logger.info(f"Using {len(TOOL_DEFINITIONS)} built-in tools (MCP not initialized)")

        # Initialize OpenAI Realtime client with elderly-optimized settings
        self.openai_client = OpenAIRealtimeClient(
            api_key=openai_api_key,
            model="gpt-4o-realtime-preview",  # Full model for best quality
            voice=elderly_config.get("voice", "alloy"),  # Warm, clear voice for elderly
            instructions=elderly_config.get("instructions"),  # Elderly-optimized system prompt
            tools=all_tools,  # Built-in + MCP tools
            turn_detection=elderly_config.get("turn_detection"),  # Longer pauses (1.2s) for elderly speech
            max_response_tokens=elderly_config.get("max_response_output_tokens", 200),  # Concise responses
            enable_noise_reduction=True  # Filter TV/background noise
        )

        logger.info(
            f"🎯 Elderly-optimized session initialized: "
            f"pause_tolerance={elderly_config.get('turn_detection', {}).get('silence_duration_ms')}ms, "
            f"voice={elderly_config.get('voice')}, "
            f"max_tokens={elderly_config.get('max_response_output_tokens')}"
        )
        
        # Initialize tool executor
        self.tool_executor = ToolExecutor(
            news_api_key=config.NEWS_API_KEY,
            weather_api_key=config.OPENWEATHER_API_KEY
        )
        
        # Set up callbacks
        self.openai_client.on_audio_delta = self.handle_openai_audio
        self.openai_client.on_function_call = self.handle_function_call
        self.openai_client.on_audio_transcript = self.handle_ai_transcript
        
        # Tracking
        self.user_transcript = ""
        self.ai_transcript = ""
        
    async def start(self):
        """Start OpenAI Realtime session"""
        connected = await self.openai_client.connect()
        
        if not connected:
            logger.error("Failed to connect to OpenAI Realtime API")
            return False
        
        # Start listening to OpenAI events
        self.openai_listen_task = asyncio.create_task(self.openai_client.listen())
        
        self.started = True
        logger.info(f"Realtime session started for call {self.call_sid}")
        return True
    
    async def handle_twilio_message(self, message: Dict):
        """
        Handle incoming message from Twilio Media Streams
        
        Args:
            message: Twilio message dict
        """
        event_type = message.get("event")
        
        if event_type == "start":
            self.stream_sid = message.get("start", {}).get("streamSid")
            logger.info(f"Media stream started: {self.stream_sid}")
            
        elif event_type == "media":
            # Audio from user (mulaw 8kHz from Twilio)
            media = message.get("media", {})
            mulaw_audio = media.get("payload")
            
            if mulaw_audio:
                # Transcode mulaw 8kHz → PCM16 24kHz
                pcm16_audio = mulaw_to_pcm16_24khz(mulaw_audio)
                
                if pcm16_audio:
                    # Send to OpenAI
                    await self.openai_client.send_audio(pcm16_audio)
        
        elif event_type == "stop":
            logger.info(f"Media stream stopped: {self.stream_sid}")
            await self.cleanup()
    
    async def handle_openai_audio(self, pcm16_audio: bytes):
        """
        Handle audio response from OpenAI (PCM16 24kHz)
        Transcode and send to Twilio
        
        Args:
            pcm16_audio: Raw PCM16 audio from OpenAI
        """
        # Transcode PCM16 24kHz → mulaw 8kHz
        mulaw_audio = pcm16_24khz_to_mulaw(pcm16_audio)
        
        if mulaw_audio:
            # Send to Twilio
            twilio_message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {
                    "payload": mulaw_audio
                }
            }
            
            try:
                await self.twilio_ws.send_json(twilio_message)
            except Exception as e:
                logger.error(f"Error sending audio to Twilio: {e}")
    
    async def handle_function_call(
        self,
        call_id: str,
        function_name: str,
        arguments: Dict
    ) -> Dict:
        """
        Handle function call from OpenAI
        Execute tool and return result
        
        Args:
            call_id: Function call ID
            function_name: Name of function to call
            arguments: Function arguments
            
        Returns:
            Function result
        """
        logger.info(f"Executing function: {function_name}({arguments})")
        
        try:
            # Execute tool
            result = await self.tool_executor.execute(function_name, arguments)
            
            logger.info(f"Function result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": str(e)}
    
    async def handle_ai_transcript(self, transcript_delta: str):
        """
        Handle AI's speech transcript (for logging)
        
        Args:
            transcript_delta: Incremental transcript text
        """
        self.ai_transcript += transcript_delta
        logger.debug(f"AI: {transcript_delta}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.openai_client.connected:
            await self.openai_client.disconnect()
        
        logger.info(f"Session cleaned up for call {self.call_sid}")
        
        # Log conversation for analytics
        if self.user_transcript or self.ai_transcript:
            logger.info(f"Conversation summary:\nUser: {self.user_transcript}\nAI: {self.ai_transcript}")


@router.websocket("/voice/stream")
async def realtime_voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams → OpenAI Realtime
    
    Query params expected from Twilio:
    - CallSid: Unique call identifier
    """
    await websocket.accept()
    
    # Extract call info from query params
    call_sid = websocket.query_params.get("CallSid", "unknown")
    
    logger.info(f"WebSocket connection established for call {call_sid}")
    
    # Initialize MCP servers if not already done (thread-safe)
    await ensure_mcp_initialized()
    
    # Get OpenAI API key
    openai_api_key = config.OPENAI_API_KEY
    
    if not openai_api_key:
        logger.error("OpenAI API key not configured")
        await websocket.close(code=1008, reason="OpenAI API key not configured")
        return
    
    # Create realtime session
    session = RealtimeSession(
        twilio_ws=websocket,
        openai_api_key=openai_api_key,
        call_sid=call_sid
    )
    
    # Start OpenAI connection
    started = await session.start()
    
    if not started:
        logger.error("Failed to start OpenAI Realtime session")
        await websocket.close(code=1011, reason="Failed to connect to OpenAI")
        return
    
    try:
        # Listen for messages from Twilio
        while True:
            try:
                message = await websocket.receive_json()
                await session.handle_twilio_message(message)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from Twilio: {e}")
                continue
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call {call_sid}")
        
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        
    finally:
        # Clean up
        await session.cleanup()
        
        try:
            await websocket.close()
        except:
            pass


@router.get("/voice/stream/health")
async def stream_health_check():
    """Health check endpoint for WebSocket route"""
    return {
        "status": "healthy",
        "endpoint": "/voice/stream",
        "protocol": "WebSocket",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/mcp/health")
async def mcp_health_check():
    """Health check for all MCP servers"""
    from utils.mcp_initialization import get_mcp_status
    
    try:
        status = get_mcp_status()
        
        if not status:
            return {
                "status": "not_initialized",
                "servers": {},
                "total_tools": 0,
                "message": "MCP servers not yet initialized"
            }
        
        all_healthy = all(
            server.get("status") == "running" 
            for server in status.values()
        )
        
        total_tools = sum(len(s.get("tools", [])) for s in status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "servers": status,
            "total_tools": total_tools,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"MCP health check error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
