import logging

# Configure logging
LOG_FILE = "application_logs.txt"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Write logs to a file
        logging.StreamHandler()         # Also output logs to the console
    ]
)

def log_message(level: str, message: str) -> None:
    """
    Logs a message with the specified level.

    Args:
        level (str): The log level (e.g., "info", "error").
        message (str): The message to log.

    Returns:
        None
    """
    logger = logging.getLogger("SerenityAI")
    if not logger.hasHandlers():  # Avoid duplicate handlers
        logger.addHandler(logging.FileHandler(LOG_FILE))
        logger.addHandler(logging.StreamHandler())
    if level == "info":
        logger.info(message)
    elif level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.debug(message)
