"""
Audio transcoding utilities for Twilio ↔ OpenAI Realtime
Twilio uses μ-law (mulaw) 8kHz, OpenAI uses PCM16 24kHz
"""

import audioop
import base64
import logging

logger = logging.getLogger(__name__)


def mulaw_to_pcm16_24khz(mulaw_base64: str) -> bytes:
    """
    Convert Twilio's μ-law 8kHz to OpenAI's PCM16 24kHz
    
    Args:
        mulaw_base64: Base64-encoded μ-law audio from Twilio Media Streams
        
    Returns:
        PCM16 24kHz mono audio bytes for OpenAI Realtime
        
    Example:
        >>> mulaw_data = "AWD//wMA..."  # From Twilio
        >>> pcm_audio = mulaw_to_pcm16_24khz(mulaw_data)
        >>> # Send to OpenAI Realtime
    """
    try:
        # Decode base64
        mulaw_data = base64.b64decode(mulaw_base64)
        
        # μ-law to linear PCM (16-bit, 8kHz)
        pcm_8khz = audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit width
        
        # Resample 8kHz → 24kHz (3x upsampling)
        pcm_24khz, _ = audioop.ratecv(
            pcm_8khz,
            2,      # sample width (16-bit = 2 bytes)
            1,      # mono channel
            8000,   # input sample rate
            24000,  # output sample rate
            None    # no state (stateless conversion)
        )
        
        return pcm_24khz
        
    except Exception as e:
        logger.error(f"mulaw → PCM16 transcoding failed: {e}")
        # Return silence (zero-filled PCM16)
        return b'\x00' * (len(mulaw_base64) * 3 * 2)  # 3x upsampling, 2 bytes per sample


def pcm16_24khz_to_mulaw(pcm_data: bytes) -> str:
    """
    Convert OpenAI's PCM16 24kHz to Twilio's μ-law 8kHz
    
    Args:
        pcm_data: PCM16 24kHz mono audio bytes from OpenAI Realtime
        
    Returns:
        Base64-encoded μ-law 8kHz audio for Twilio Media Streams
        
    Example:
        >>> pcm_audio = openai_response.audio  # From OpenAI
        >>> mulaw_data = pcm16_24khz_to_mulaw(pcm_audio)
        >>> # Send to Twilio via WebSocket
    """
    try:
        # Resample 24kHz → 8kHz (3x downsampling)
        pcm_8khz, _ = audioop.ratecv(
            pcm_data,
            2,      # sample width (16-bit = 2 bytes)
            1,      # mono channel
            24000,  # input sample rate
            8000,   # output sample rate
            None    # no state
        )
        
        # Linear PCM to μ-law
        mulaw_data = audioop.lin2ulaw(pcm_8khz, 2)
        
        # Base64 encode for JSON transmission
        mulaw_base64 = base64.b64encode(mulaw_data).decode('utf-8')
        
        return mulaw_base64
        
    except Exception as e:
        logger.error(f"PCM16 → mulaw transcoding failed: {e}")
        # Return empty audio
        return ""


def get_audio_chunk_size(duration_ms: int = 20, sample_rate: int = 24000, 
                          sample_width: int = 2, channels: int = 1) -> int:
    """
    Calculate audio chunk size in bytes for a given duration
    
    Args:
        duration_ms: Duration in milliseconds (default 20ms - common chunk size)
        sample_rate: Sample rate in Hz (default 24000 for OpenAI)
        sample_width: Bytes per sample (default 2 for PCM16)
        channels: Number of audio channels (default 1 for mono)
        
    Returns:
        Chunk size in bytes
        
    Example:
        >>> chunk_size = get_audio_chunk_size(20, 24000, 2, 1)
        >>> print(chunk_size)  # 960 bytes (20ms of PCM16 24kHz mono)
    """
    samples_per_second = sample_rate
    samples_in_chunk = int((duration_ms / 1000.0) * samples_per_second)
    bytes_in_chunk = samples_in_chunk * sample_width * channels
    return bytes_in_chunk


# Constants for common audio configurations
TWILIO_CHUNK_SIZE = get_audio_chunk_size(20, 8000, 1, 1)  # 160 bytes (mulaw 8kHz)
OPENAI_CHUNK_SIZE = get_audio_chunk_size(20, 24000, 2, 1)  # 960 bytes (PCM16 24kHz)

logger.info(
    f"Audio transcoding configured: "
    f"Twilio chunk={TWILIO_CHUNK_SIZE}B (mulaw 8kHz), "
    f"OpenAI chunk={OPENAI_CHUNK_SIZE}B (PCM16 24kHz)"
)
