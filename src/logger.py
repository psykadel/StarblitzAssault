"""Centralized logging utility for the game."""

import logging
import os
from typing import Optional

from config.config import LOG_LEVEL


def setup_logger(log_level: int = LOG_LEVEL) -> None:
    """Set up the root logger with file and console handlers.

    Args:
        log_level: Logging level to use (default: LOG_LEVEL from config)
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove all existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # File handler for persistent logs
    log_file_path = os.path.join(log_dir, "application.log")
    file_handler = logging.FileHandler(log_file_path)
    file_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # Console handler for real-time logs
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger instance with the specified name.

    Args:
        name: Logger name, typically the module name.

    Returns:
        logging.Logger: Logger instance for the given name.
    """
    return logging.getLogger(name)


# Initialize logging configuration on import
setup_logger()
