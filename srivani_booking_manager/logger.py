"""
SRIVANI BOOKING MANAGER - Production Structured Logging Engine
Provides rotating log files with PII sanitization, structured formatting, and error tracking.
"""
import logging
from logging.handlers import RotatingFileHandler
import re
from pathlib import Path
from config import DATA_DIR

LOGS_DIR = DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "srivani_manager.log"

class PIISanitizingFormatter(logging.Formatter):
    """Sanitizes sensitive details such as 12-digit numbers, passwords, OTPs from logs."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # Redact any 12-digit Aadhaar-like numbers
        msg = re.sub(r"\b\d{8}(\d{4})\b", r"XXXX-XXXX-\1", msg)
        # Redact potential password/pin references
        msg = re.sub(r"(password|pin|otp)\s*[:=]\s*[^\s,;]+", r"\1=******", msg, flags=re.IGNORECASE)
        return msg

_logger = None

def get_logger(name: str = "srivani_manager") -> logging.Logger:
    """Return configured structured logger instance."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # File handler: 5MB per file, keeping last 5 backups
        file_handler = RotatingFileHandler(
            str(LOG_FILE),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        formatter = PIISanitizingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Stream handler for console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _logger = logger
    return _logger
