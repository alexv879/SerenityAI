from fastapi import APIRouter, Response
from twilio.twiml.voice_response import VoiceResponse

router = APIRouter()

VOICE = "Polly.Amy-Neural"


@router.post("/news")
async def news_stub() -> Response:
    vr = VoiceResponse()
    vr.say("Here's a quick update. Live news will be available soon.", voice=VOICE)
    vr.pause(length=1)
    vr.say("Would you like the weather or to chat instead?", voice=VOICE)
    vr.redirect("/voice/entry")
    return Response(content=str(vr), media_type="application/xml")


@router.post("/weather")
async def weather_stub() -> Response:
    vr = VoiceResponse()
    vr.say("Today's weather: a placeholder forecast for now.", voice=VOICE)
    vr.pause(length=1)
    vr.say("Would you like some company to chat now?", voice=VOICE)
    vr.redirect("/voice/entry")
    return Response(content=str(vr), media_type="application/xml")
