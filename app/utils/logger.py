"""
Logging configuration for PRGate
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create formatters
formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

# Define log levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Default log level from environment
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
log_level = LOG_LEVELS.get(DEFAULT_LOG_LEVEL, logging.INFO)


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """Setup a logger with file and console handlers"""
    
    logger = logging.getLogger(name)
    level_value = LOG_LEVELS.get(level.lower() if level else DEFAULT_LOG_LEVEL, log_level)
    logger.setLevel(level_value)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler (for terminal output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level_value)
    logger.addHandler(console_handler)
    
    # File handler (for persistent logs)
    log_file = LOG_DIR / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10_485_760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level_value)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger"""
    return setup_logger(name)


# Pre-configured loggers for different components
webhook_logger = get_logger("webhook")
review_logger = get_logger("review")
database_logger = get_logger("database")
github_logger = get_logger("github")
cache_logger = get_logger("cache")
error_logger = get_logger("error")
llm_logger = get_logger("llm")
pr_fetcher_logger = get_logger("pr_fetcher")

# Special audit logger for security events
audit_logger = get_logger("audit")
audit_logger.setLevel(logging.INFO)


def log_performance(operation: str, start_time: datetime, **kwargs):
    """Log performance metrics"""
    duration = (datetime.utcnow() - start_time).total_seconds()
    audit_logger.info(f"Performance - {operation}: {duration:.3f}s", extra=kwargs)
    return duration