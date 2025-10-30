from fastapi import Request
from twilio.twiml.voice_response import VoiceResponse

from utils.general_utils import detect_language
from utils.tts_handler import stream_text_to_speech

# -------------------------------------------------------------------
# Helpers for speaking responses with TTS and language detection
# -------------------------------------------------------------------

def get_voice_for_language(lang_code: str) -> str:
    """
    Returns the appropriate voice for the given language code.

    Args:
        lang_code (str): The language code (e.g., 'en', 'es').

    Returns:
        str: The voice identifier for the language.
    """
    language_voice_map = {
        "en": "en-GB-Chirp3-HD-Leda",
        "es": "es-ES-Standard-A",
        "fr": "fr-FR-Standard-A",
        "de": "de-DE-Standard-A",
        "it": "it-IT-Standard-A",
        "pt": "pt-PT-Standard-A"
    }
    return language_voice_map.get(lang_code, "en-GB-Chirp3-HD-Leda")


def get_absolute_base_url(request_obj: Request) -> str:
    """
    Constructs the absolute base URL from the given request object.

    Args:
        request_obj (Request): The FastAPI request object.

    Returns:
        str: The absolute base URL.
    """
    base_url = str(request_obj.base_url)
    return base_url if base_url.endswith("/") else base_url + "/"


def say_google(twiml_response: VoiceResponse, text: str, request_obj: Request, voice: str = "en-GB-Chirp3-HD-Leda"):
    """
    Adds a TTS response to the Twilio VoiceResponse object.

    Args:
        twiml_response (VoiceResponse): The Twilio VoiceResponse object.
        text (str): The text to be spoken.
        request_obj (Request): The FastAPI request object.
        voice (str, optional): The voice identifier. Defaults to "en-GB-Chirp3-HD-Leda".
    """
    try:
        lang_code = detect_language(text)
        voice = get_voice_for_language(lang_code)

        cleaned_text = text.strip().replace("I'm sorry", "Apologies")
        stream_url = f"{get_absolute_base_url(request_obj)}stream_tts?text={cleaned_text}&voice={voice}"
        twiml_response.play(stream_url)
    except Exception as e:
        print(f"[ERROR] say_google failed: {e}")
        twiml_response.say("Sorry, I had trouble responding just now.")


# Optional alias to allow future voice selection by name
say_google_with_voice = say_google
