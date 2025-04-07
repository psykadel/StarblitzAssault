"""Centralized logging utility for the game."""

import os
import logging
import sys
from typing import Optional

# Import the LOG_LEVEL from game config
from config.config import LOG_LEVEL

# Configure the root logger
def setup_logger(log_level: int = LOG_LEVEL) -> None:
    """Set up the logger with file and console handlers.
    
    Args:
        log_level: The logging level to use (default: from game_config.LOG_LEVEL)
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers (to avoid duplicates if called multiple times)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and configure file handler
    log_file_path = os.path.join(log_dir, 'application.log')
    file_handler = logging.FileHandler(log_file_path)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: The logger name, typically the module name
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name)

# Set up the logger when this module is imported
setup_logger() 