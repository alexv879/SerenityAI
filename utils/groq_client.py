"""
Groq LLM Client - Llama 3.1 70B Integration
Fast, cost-effective conversation generation
"""

import asyncio
import os
import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Async client for Groq Cloud API (Llama 3.1 70B)
    
    Pricing: ~$0.59/1M tokens (85% cheaper than Gemini)
    Speed: ~330 tokens/sec (75% faster than Gemini)
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-70b-versatile"
        self.max_tokens = 150  # Keep responses concise for voice
        self.temperature = 0.8  # Warm, natural conversation
    
    async def generate_response(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate AI response for user input
        
        Args:
            user_input: What the user said
            conversation_history: Previous turns [{"role": "user/assistant", "content": "..."}]
            system_prompt: Optional system instructions
            
        Returns:
            AI response text (voice-optimized, concise)
        """
        try:
            # Build messages
            messages = []
            
            # System prompt
            if not system_prompt:
                system_prompt = (
                    "You are Serenity, a warm and friendly AI companion for elderly UK users. "
                    "Keep responses SHORT (1-2 sentences), conversational, and empathetic. "
                    "Use British English. Ask follow-up questions to keep them engaged. "
                    "If they mention loneliness, health concerns, or family, respond with gentle care."
                )
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-6:])  # Keep last 6 turns for context
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Call Groq API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                    }
                )
                response.raise_for_status()
                
            data = response.json()
            ai_response = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"Groq response generated ({len(ai_response)} chars)")
            return ai_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API error: {e.response.status_code} - {e.response.text}")
            return "I'm having a bit of trouble thinking right now. Could you say that again?"
            
        except Exception as e:
            logger.error(f"Groq client error: {e}")
            return "Sorry, I didn't catch that. What were you saying?"


# Global singleton
_groq_client: Optional[GroqClient] = None
_groq_client_lock = asyncio.Lock()


async def get_groq_client() -> GroqClient:
    """Get or create Groq client singleton (thread-safe)"""
    global _groq_client
    if _groq_client is None:
        async with _groq_client_lock:
            if _groq_client is None:  # Double-check after acquiring lock
                _groq_client = GroqClient()
    return _groq_client
