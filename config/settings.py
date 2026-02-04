"""
Configuration management for the email automation system.

Centralizes all settings and provides validation.
WHY: Single source of truth for configuration prevents scattered magic values.
"""

import os
from typing import Optional

# Try to load dotenv, handle encoding errors gracefully
try:
    from dotenv import load_dotenv
    # Try different encodings
    try:
        load_dotenv(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            load_dotenv(encoding='utf-8-sig')
        except UnicodeDecodeError:
            try:
                load_dotenv(encoding='latin-1')
            except Exception as e:
                print(f"Warning: Could not load .env file due to encoding issues: {e}")
                print("Please ensure your .env file is saved as UTF-8 encoding")
                print("Continuing with environment variables only...")
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")


class Settings:
    """
    Configuration settings loaded from environment variables.
    
    WHY CLASS-BASED CONFIG?
    - Type hints for IDE support
    - Validation in one place
    - Easy to extend with computed properties
    - Can be mocked in tests
    """
    
    # Email Configuration
    GMAIL_EMAIL: str = os.getenv("GMAIL_EMAIL", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    
    # IMAP Settings
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    
    # SMTP Settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    
    # LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama2")
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:11434/api/generate")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    
    # System Settings
    MAX_EMAILS_TO_FETCH: int = int(os.getenv("MAX_EMAILS_TO_FETCH", "50"))
    EMAIL_CHECK_FOLDER: str = os.getenv("EMAIL_CHECK_FOLDER", "INBOX")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration settings.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if not cls.GMAIL_EMAIL:
            errors.append("GMAIL_EMAIL is not set")
        
        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD is not set")
        
        if "@" not in cls.GMAIL_EMAIL:
            errors.append("GMAIL_EMAIL is not a valid email address")
        
        if cls.LLM_TIMEOUT < 10:
            errors.append("LLM_TIMEOUT should be at least 10 seconds")
        
        if cls.MAX_EMAILS_TO_FETCH < 1:
            errors.append("MAX_EMAILS_TO_FETCH must be positive")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_display_config(cls) -> dict:
        """
        Get configuration for display (with sensitive data masked).
        
        WHY? Safe to print without exposing credentials.
        """
        return {
            "GMAIL_EMAIL": cls.GMAIL_EMAIL,
            "GMAIL_APP_PASSWORD": "***" if cls.GMAIL_APP_PASSWORD else "NOT SET",
            "IMAP_SERVER": cls.IMAP_SERVER,
            "IMAP_PORT": cls.IMAP_PORT,
            "SMTP_SERVER": cls.SMTP_SERVER,
            "SMTP_PORT": cls.SMTP_PORT,
            "LLM_MODEL": cls.LLM_MODEL,
            "LLM_API_URL": cls.LLM_API_URL,
            "MAX_EMAILS_TO_FETCH": cls.MAX_EMAILS_TO_FETCH,
            "EMAIL_CHECK_FOLDER": cls.EMAIL_CHECK_FOLDER,
        }


# Create a singleton instance
settings = Settings()
