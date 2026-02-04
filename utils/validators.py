"""
Validation utilities for email automation system.

WHY VALIDATORS?
- Security: Prevent injection attacks, malformed data
- Safety: Catch errors early before they cause problems
- Clarity: Explicit validation is self-documenting
- Reusability: Use same validation logic everywhere
"""

import re
from typing import Tuple, List
from email.utils import parseaddr


def validate_email_address(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.
    
    Returns:
        (is_valid, error_message)
    
    WHY NOT JUST REGEX?
    - Email validation is complex (RFC 5322)
    - Built-in parseaddr handles edge cases
    - Regex alone can have false positives/negatives
    """
    if not email or not email.strip():
        return False, "Email address is empty"
    
    email = email.strip()
    
    # Basic format check
    if '@' not in email:
        return False, "Email must contain @"
    
    # Use Python's email parser
    name, addr = parseaddr(email)
    
    if not addr:
        return False, "Invalid email format"
    
    # Check for valid domain
    if '.' not in addr.split('@')[1]:
        return False, "Email domain must contain a dot"
    
    return True, ""


def is_noreply_address(email: str) -> bool:
    """
    Check if email address is a no-reply address.
    
    WHY IMPORTANT?
    - Prevent sending emails to addresses that won't receive them
    - Save API calls and prevent bounce-backs
    - Better user experience (warn before attempting to reply)
    """
    noreply_patterns = [
        'noreply',
        'no-reply',
        'donotreply',
        'do-not-reply',
        'no_reply',
        'notifications',
        'mailer-daemon',
        'postmaster'
    ]
    
    email_lower = email.lower()
    return any(pattern in email_lower for pattern in noreply_patterns)


def validate_email_body(body: str, max_length: int = 100000) -> Tuple[bool, str]:
    """
    Validate email body content.
    
    Args:
        body: Email body text
        max_length: Maximum allowed length
    
    Returns:
        (is_valid, error_message)
    """
    if body is None:
        return False, "Email body is None"
    
    if not body.strip():
        return False, "Email body is empty"
    
    if len(body) > max_length:
        return False, f"Email body exceeds maximum length ({max_length} chars)"
    
    return True, ""


def validate_subject(subject: str, max_length: int = 500) -> Tuple[bool, str]:
    """
    Validate email subject line.
    
    Args:
        subject: Email subject
        max_length: Maximum allowed length
    
    Returns:
        (is_valid, error_message)
    """
    if subject is None:
        return False, "Subject is None"
    
    # Empty subject is technically valid
    if not subject.strip():
        return True, ""
    
    if len(subject) > max_length:
        return False, f"Subject exceeds maximum length ({max_length} chars)"
    
    # Check for suspicious patterns (potential injection)
    suspicious_patterns = ['\n', '\r', '\x00']
    for pattern in suspicious_patterns:
        if pattern in subject:
            return False, f"Subject contains suspicious character: {repr(pattern)}"
    
    return True, ""


def sanitize_email_body(body: str) -> str:
    """
    Sanitize email body for safe processing.
    
    WHY?
    - Remove potentially harmful content
    - Normalize whitespace
    - Make text LLM-friendly
    """
    if not body:
        return ""
    
    # Remove null bytes
    body = body.replace('\x00', '')
    
    # Normalize line endings
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    
    # Limit consecutive newlines (reduces token usage)
    body = re.sub(r'\n{4,}', '\n\n\n', body)
    
    # Remove excessive whitespace
    body = re.sub(r' {3,}', '  ', body)
    
    return body.strip()


def extract_reply_indicators(body: str) -> List[str]:
    """
    Extract indicators that suggest this email expects a reply.
    
    WHY?
    - Helps LLM make better replyability decisions
    - Can be used as features if we add ML later
    - Useful for debugging analysis results
    """
    indicators = []
    
    body_lower = body.lower()
    
    # Question indicators
    if '?' in body:
        indicators.append('contains_question')
    
    # Action request indicators
    action_phrases = [
        'please respond',
        'let me know',
        'get back to me',
        'reply by',
        'respond by',
        'your thoughts',
        'your feedback',
        'what do you think',
        'can you',
        'could you',
        'would you'
    ]
    
    for phrase in action_phrases:
        if phrase in body_lower:
            indicators.append(f'contains_phrase: {phrase}')
    
    return indicators


def check_reply_safety(from_address: str, subject: str, body: str) -> Tuple[bool, List[str]]:
    """
    Check if it's safe to reply to this email.
    
    Returns:
        (is_safe, list_of_warnings)
    
    WHY?
    - Prevent accidental replies to no-reply addresses
    - Catch potential phishing or spam
    - Protect user from embarrassing mistakes
    """
    warnings = []
    
    # Check for no-reply address
    if is_noreply_address(from_address):
        warnings.append("Sender is a no-reply address")
    
    # Check for suspicious subject patterns
    spam_indicators = [
        'viagra',
        'casino',
        'lottery',
        'nigerian prince',
        'click here now',
        'act now',
        'limited time'
    ]
    
    subject_lower = subject.lower()
    for indicator in spam_indicators:
        if indicator in subject_lower:
            warnings.append(f"Suspicious subject content: {indicator}")
    
    # Check for very short emails (might be automated)
    if len(body.strip()) < 50:
        warnings.append("Very short email body - might be automated")
    
    # All clear if no warnings
    is_safe = len(warnings) == 0
    
    return is_safe, warnings


def validate_reply_draft(draft: str, min_length: int = 20, max_length: int = 10000) -> Tuple[bool, str]:
    """
    Validate a generated reply draft.
    
    Returns:
        (is_valid, error_message)
    """
    if not draft or not draft.strip():
        return False, "Reply draft is empty"
    
    draft_length = len(draft.strip())
    
    if draft_length < min_length:
        return False, f"Reply draft too short ({draft_length} < {min_length} chars)"
    
    if draft_length > max_length:
        return False, f"Reply draft too long ({draft_length} > {max_length} chars)"
    
    return True, ""


# Example usage:
# from utils.validators import validate_email_address, is_noreply_address
# 
# valid, error = validate_email_address("user@example.com")
# if not valid:
#     print(f"Invalid email: {error}")
# 
# if is_noreply_address("noreply@example.com"):
#     print("This is a no-reply address!")
