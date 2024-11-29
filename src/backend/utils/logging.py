"""
Logging configuration for the backend.

This module sets up structured logging with different handlers and formatters
for console and file output.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILENAME = LOGS_DIR / f"chatbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


class ContextFormatter(logging.Formatter):
    """Custom formatter that handles missing context gracefully."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with context if available."""
        if not hasattr(record, "context"):
            record.context = "{}"
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up logging configuration with console and file handlers.

    Args:
        level: The logging level to use. Defaults to logging.INFO.
    """
    console_formatter = ContextFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = ContextFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(context)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=10485760,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(file_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


class StructuredLogger:
    """
    A logger that adds structured context to log messages.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize the structured logger.

        Args:
            name: The name of the logger.
        """
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        """
        Set context values for subsequent log messages.

        Args:
            **kwargs: Key-value pairs to add to the context.
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context values."""
        self.context.clear()

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        """
        Internal method to handle logging with context.

        Args:
            level: The logging level.
            msg: The message to log.
            **kwargs: Additional context for this specific log message.
        """
        context = {**self.context, **kwargs}
        self.logger.log(level, msg, extra={"context": str(context)})

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log an info message with context."""
        self._log(logging.INFO, msg, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log a debug message with context."""
        self._log(logging.DEBUG, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log a warning message with context."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log an error message with context."""
        self._log(logging.ERROR, msg, **kwargs)
