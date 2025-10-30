import logging
from twilio.twiml.voice_response import Gather, VoiceResponse
from langdetect import detect

EXIT_PHRASES: list[str] = [
    "exit", "quit", "stop", "goodbye", "bye",
    "start over", "main menu", "go back", "return",
    "talk about something else", "something else", "change the topic", "leave", "new topic"
]

def log_message(level: str, message: str) -> None:
    """
    Logs a message with the specified level.

    Args:
        level (str): The log level (e.g., "info", "error").
        message (str): The message to log.

    Returns:
        None
    """
    logger = logging.getLogger("serenity_ai")
    log_levels = {
        "info": logging.INFO,
        "error": logging.ERROR,
        "debug": logging.DEBUG,
        "warning": logging.WARNING,
    }
    logger.log(log_levels.get(level, logging.INFO), message)

def clean_input(text: str) -> str:
    """
    Cleans and normalizes user input for consistent handling.
    Removes symbols and the word 'serenity' if mentioned.
    """
    if not text:
        return ""
    text = text.replace("Serenity", "").replace("serenity", "")
    return text.strip().lower()

def detect_exit_command(text: str) -> bool:
    """
    Detects if user is trying to switch topics or exit the current module.
    """
    if not text:
        return False
    lowered: str = text.strip().lower()
    return any(phrase in lowered for phrase in EXIT_PHRASES)

def handle_exit_if_detected(response: VoiceResponse, text: str, request: dict, voice: str, redirect_url: str = "/conversation") -> bool:
    """
    If exit phrase detected, respond and redirect. Returns True if exit was handled.
    """
    if detect_exit_command(text):
        response.say("No problem. What would you like to talk about instead?", voice=voice)
        append_gather_to_response(response, action=redirect_url, language="en-GB", speech_timeout="auto")
        return True
    return False

def append_gather_to_response(response: VoiceResponse, action: str, language: str = "en-GB", speech_timeout: str = "auto", prompt: str = None) -> None:
    if prompt:
        response.say(prompt, language=language)
    response.append(Gather(
        input="speech",
        action=action,
        language=language,
        speechTimeout=speech_timeout
    ))

def detect_confusion_or_frustration(text: str) -> str | None:
    """
    Detects confusion or frustration in user input.
    Returns 'confusion', 'frustration', or None.
    """
    confusion_phrases: list[str] = ["don't understand", "confused", "what do you mean"]
    frustration_phrases: list[str] = ["this is annoying", "not helpful", "wasting my time"]

    if any(phrase in text.lower() for phrase in confusion_phrases):
        return "confusion"
    if any(phrase in text.lower() for phrase in frustration_phrases):
        return "frustration"
    return None

def detect_language(text: str) -> str:
    """
    Detects the language of the given text.
    :param text: The input text to analyze.
    :return: The detected language code (e.g., "en", "es").
    """
    try:
        return detect(text)
    except Exception as e:
        log_message("error", f"Language detection failed: {e}")
        return "unknown"
