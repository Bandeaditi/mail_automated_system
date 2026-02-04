"""
Logging configuration for the email automation system.

WHY CENTRALIZED LOGGING?
- Consistent log format across all modules
- Easy to change log level without touching each file
- Can add file logging, remote logging, etc. in one place
- Helps debug issues in production
"""

import logging
import sys
from datetime import datetime
from config.settings import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Create a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
    
    Returns:
        Configured logger instance
    
    WHY FUNCTION?
    - Each module gets its own logger with the module name
    - Makes it easy to filter logs by component
    - Consistent formatting everywhere
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured (prevents duplicate handlers)
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
        
        # Console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Format: [2024-01-15 10:30:45] [INFO] [module_name] Message
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger


def log_email_action(logger: logging.Logger, action: str, email_subject: str, 
                     email_from: str, details: str = ""):
    """
    Log an email-related action with consistent formatting.
    
    WHY HELPER FUNCTION?
    - Consistent log format for email operations
    - Easy to grep logs for specific email actions
    - Can be extended to log to database or external service
    """
    log_message = f"{action} | Subject: '{email_subject}' | From: {email_from}"
    if details:
        log_message += f" | {details}"
    
    logger.info(log_message)


def log_llm_call(logger: logging.Logger, operation: str, success: bool, 
                 duration_ms: float, error: str = ""):
    """
    Log LLM API calls for monitoring and debugging.
    
    WHY? Track LLM performance, failures, and costs.
    """
    status = "SUCCESS" if success else "FAILED"
    log_message = f"LLM {operation} | Status: {status} | Duration: {duration_ms:.2f}ms"
    
    if error:
        log_message += f" | Error: {error}"
        logger.error(log_message)
    else:
        logger.info(log_message)


# Example usage:
# from utils.logger import setup_logger
# logger = setup_logger(__name__)
# logger.info("Starting email analysis")
