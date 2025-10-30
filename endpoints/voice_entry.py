from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

router = APIRouter()

VOICE = "Polly.Amy-Neural"

@router.post("/voice/entry")
async def voice_entry(_: Request) -> Response:
    """Warm welcome with a simple menu; voice-only TwiML."""
    vr = VoiceResponse()
    vr.say("Hello, it's Serenity. I'm here to chat and help.", voice=VOICE)
    vr.pause(length=1)
    vr.say("You can say: news, weather, chat, pay, preferences, or help.", voice=VOICE)
    vr.pause(length=1)
    gather = Gather(input="speech", action="/voice/route", language="en-GB", speech_timeout="auto")
    gather.say("What would you like to do?", voice=VOICE)
    vr.append(gather)
    # Fallback if no input
    vr.say("I didn't catch that. I'll say goodbye for now.", voice=VOICE)
    vr.hangup()
    return Response(content=str(vr), media_type="application/xml")

@router.post("/voice/route")
async def voice_route(request: Request) -> Response:
    """Route based on simple spoken keywords; all responses as TwiML."""
    form = await request.form()
    speech = (form.get("SpeechResult") or "").lower()

    vr = VoiceResponse()

    if any(k in speech for k in ["news", "headlines", "today"]):
        vr.say("Here's a quick update. I don't have the news connected yet, but I can tell you a brief headline placeholder.", voice=VOICE)
        vr.pause(length=1)
        vr.say("Would you like weather or to chat instead?", voice=VOICE)
        vr.redirect("/voice/entry")
        return Response(content=str(vr), media_type="application/xml")

    if any(k in speech for k in ["weather", "forecast"]):
        vr.say("Today's weather: this is a placeholder forecast. We'll add live weather soon.", voice=VOICE)
        vr.pause(length=1)
        vr.say("Would you like some company to chat now?", voice=VOICE)
        vr.redirect("/voice/entry")
        return Response(content=str(vr), media_type="application/xml")

    if any(k in speech for k in ["pay", "payment", "subscribe", "card"]):
        vr.say("I'll help you with payment now.", voice=VOICE)
        vr.redirect("/payment/trigger")
        return Response(content=str(vr), media_type="application/xml")

    if any(k in speech for k in ["preference", "voice", "slow", "faster", "quieter", "louder"]):
        vr.redirect("/prefs/voice")
        return Response(content=str(vr), media_type="application/xml")

    if any(k in speech for k in ["help", "doctor", "emergency", "nhs", "n h s", "one one one", "111"]):
        vr.say("If it's medical, you can dial one one one for NHS one one one.", voice=VOICE)
        vr.pause(length=1)
        vr.say("For scams, never share your PIN or bank password. I will never ask for it.", voice=VOICE)
        vr.redirect("/voice/entry")
        return Response(content=str(vr), media_type="application/xml")

    # Default: redirect to actual AI conversation handler
    vr.say("Lovely. Let's have a chat then.", voice=VOICE)
    vr.redirect("/voice/chat")
    return Response(content=str(vr), media_type="application/xml")

@router.post("/prefs/voice")
async def prefs_voice(_: Request) -> Response:
    vr = VoiceResponse()
    vr.say("Okay. I'll remember your voice preference next time.", voice=VOICE)
    vr.pause(length=1)
    vr.say("What would you like to do now? You can say: news, weather, chat, pay, or help.", voice=VOICE)
    vr.redirect("/voice/entry")
    return Response(content=str(vr), media_type="application/xml")
