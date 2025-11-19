"""
Conversation Handler - Core AI Chat Logic
Handles back-and-forth conversation with trial enforcement
"""

from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import json
from datetime import datetime

from utils.groq_client import get_groq_client
from utils.subscription_manager import get_subscription_manager
from utils.conversation_history import get_conversation_history
from utils.logging import log_message

router = APIRouter()

VOICE = "Polly.Amy-Neural"


@router.post("/voice/chat")
async def handle_conversation(request: Request) -> Response:
    """
    Main conversation loop - accepts user speech, generates AI response
    
    Flow:
    1. Check subscription/trial status
    2. Get user input from SpeechResult
    3. Generate AI response via Groq
    4. Return TwiML with response + Gather for next turn
    """
    form = await request.form()
    phone = form.get("From")
    call_sid = form.get("CallSid")
    user_speech = form.get("SpeechResult", "").strip()
    
    vr = VoiceResponse()
    
    # Check if user can use AI (trial/subscription check)
    sub_mgr = await get_subscription_manager()
    
    # Get or create subscription
    subscription = await sub_mgr.get_subscription(phone)
    if not subscription:
        # First-time caller, create trial
        await sub_mgr.create_trial(phone, call_sid)
        log_message("info", f"[{phone}] New caller, trial started")
    
    # Check if allowed to continue
    can_continue = await sub_mgr.can_use_ai(phone)
    if not can_continue:
        # Trial expired or subscription inactive
        vr.say(
            "Your free trial has ended. To continue chatting, I'll need to collect payment.",
            voice=VOICE
        )
        vr.redirect("/payment/trigger")
        return Response(content=str(vr), media_type="application/xml")
    
    # Handle empty/no input
    if not user_speech:
        vr.say("I didn't hear anything. What's on your mind?", voice=VOICE)
        gather = Gather(
            input="speech",
            action="/voice/chat",
            language="en-GB",
            speech_timeout="auto"
        )
        gather.say("I'm listening.", voice=VOICE)
        vr.append(gather)
        return Response(content=str(vr), media_type="application/xml")
    
    # Log user input
    log_message("info", f"[{phone}] User: {user_speech[:50]}...")

    # Get conversation history from Redis for context continuity
    conversation_context = None
    try:
        history_mgr = await get_conversation_history()
        recent_turns = await history_mgr.get_recent_turns(phone, limit=10)
        if recent_turns:
            # Format for AI context
            conversation_context = await history_mgr.get_formatted_context(phone, limit=10)
            log_message("info", f"[{phone}] Loaded {len(recent_turns)} previous turns from history")
    except Exception as e:
        log_message("warning", f"[{phone}] Failed to load conversation history: {e}")
        conversation_context = None

    # Generate AI response
    try:
        groq_client = await get_groq_client()
        ai_response = await groq_client.generate_response(
            user_input=user_speech,
            conversation_history=conversation_context
        )

        log_message("info", f"[{phone}] AI: {ai_response[:50]}...")

    except (ConnectionError, TimeoutError) as e:
        log_message("error", f"[{phone}] AI API connection failed: {e}")
        ai_response = "I'm having trouble connecting. Could you try again in a moment, love?"
    except Exception as e:
        log_message("error", f"[{phone}] AI generation failed: {e}", exc_info=True)
        ai_response = "I'm having a spot of trouble. Could you say that again, love?"

    # Store this conversation turn in history for context continuity
    try:
        history_mgr = await get_conversation_history()
        await history_mgr.add_turn(phone, "user", user_speech)
        await history_mgr.add_turn(phone, "assistant", ai_response)
        log_message("debug", f"[{phone}] Conversation turn saved to history")
    except Exception as e:
        log_message("warning", f"[{phone}] Failed to save conversation history: {e}")
    
    # Update trial usage (rough estimate: 0.5 min per turn)
    # TODO: Track actual call duration via status callback
    if subscription and subscription.get("subscription_status") == "trial":
        current_usage = subscription.get("minutes_used_in_trial", 0)
        await sub_mgr.update_trial_usage(phone, current_usage + 0.5)
    
    # Return TwiML with AI response + Gather for next turn
    vr.say(ai_response, voice=VOICE)
    
    # Continue conversation
    gather = Gather(
        input="speech",
        action="/voice/chat",
        language="en-GB",
        speech_timeout="auto",
        timeout=10
    )
    gather.say("", voice=VOICE)  # Silent prompt (AI already spoke)
    vr.append(gather)
    
    # Fallback if user goes silent
    vr.say("Are you still there? If you'd like to chat more, just say hello.", voice=VOICE)
    vr.redirect("/voice/entry")
    
    return Response(content=str(vr), media_type="application/xml")


@router.post("/twilio/status-callback")
async def call_status_callback(request: Request) -> Response:
    """
    Twilio status callback - logs call end and duration
    
    Set in Twilio Console or via statusCallback parameter in <Dial>
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    phone = form.get("From")
    duration = form.get("CallDuration")  # In seconds
    
    if call_status == "completed" and duration:
        duration_minutes = int(duration) / 60.0
        
        sub_mgr = await get_subscription_manager()
        await sub_mgr.log_call(phone, call_sid, duration_minutes)
        
        log_message("info", f"[{phone}] Call ended: {duration_minutes:.1f} min")
    
    # Return empty 200 (Twilio doesn't need TwiML for status callbacks)
    return Response(status_code=200)
