"""
Email Sender - SMTP-based email sending with safety checks.

KEY DESIGN:
- Requires explicit approval (no auto-send)
- Preserves email threading (In-Reply-To headers)
- Comprehensive logging
- Rate limiting to prevent abuse
- Dry-run mode for testing
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
from datetime import datetime

from core.models import Email, ReplyDraft
from config.settings import settings
from utils.logger import setup_logger, log_email_action
from utils.validators import validate_email_address, validate_subject, is_noreply_address

logger = setup_logger(__name__)


class EmailSender:
    """
    SMTP-based email sender with safety features.
    
    WHY SMTP?
    - Standard protocol, works with any provider
    - Can set custom headers (threading)
    - Full control over email composition
    
    SAFETY FEATURES:
    - Rate limiting (prevents spam)
    - No-reply detection
    - Validation before sending
    - Comprehensive logging
    - Dry-run mode for testing
    """
    
    def __init__(self, email_address: str = None, password: str = None,
                 smtp_server: str = None, smtp_port: int = None,
                 dry_run: bool = False):
        """
        Initialize email sender.
        
        Args:
            email_address: Gmail address (defaults to settings)
            password: App password (defaults to settings)
            smtp_server: SMTP server (defaults to settings)
            smtp_port: SMTP port (defaults to settings)
            dry_run: If True, don't actually send emails (for testing)
        """
        self.email_address = email_address or settings.GMAIL_EMAIL
        self.password = password or settings.GMAIL_APP_PASSWORD
        self.smtp_server = smtp_server or settings.SMTP_SERVER
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.dry_run = dry_run
        
        # Rate limiting: track sent emails
        self.sent_count = 0
        self.last_send_time = None
        self.min_send_interval = 2.0  # Minimum seconds between sends
        
        logger.info(f"Initialized EmailSender for {self.email_address}")
        if dry_run:
            logger.warning("DRY RUN MODE: Emails will not actually be sent")
    
    def send_reply(self, original_email: Email, reply_draft: ReplyDraft,
                   approved: bool = False) -> Tuple[bool, str]:
        """
        Send a reply to an email.
        
        Args:
            original_email: The email being replied to
            reply_draft: The draft reply to send
            approved: Whether user has approved this send (REQUIRED)
        
        Returns:
            (success, message)
        
        WHY REQUIRE APPROVAL?
        - Safety: prevents accidental sends
        - Compliance: user must explicitly approve
        - Audit trail: clear accountability
        """
        if not approved:
            logger.error("Attempted to send email without approval")
            return False, "Email must be explicitly approved before sending"
        
        logger.info(f"Preparing to send reply to: {original_email.from_address}")
        
        # Validation checks
        is_valid, error_msg = self._validate_send_request(
            original_email,
            reply_draft
        )
        
        if not is_valid:
            logger.error(f"Send validation failed: {error_msg}")
            return False, error_msg
        
        # Rate limiting check
        if not self._check_rate_limit():
            error_msg = "Rate limit exceeded. Please wait before sending another email."
            logger.warning(error_msg)
            return False, error_msg
        
        # Compose email
        message = self._compose_reply(original_email, reply_draft)
        
        # Send email
        if self.dry_run:
            logger.info("DRY RUN: Would have sent email")
            logger.info(f"To: {original_email.from_address}")
            logger.info(f"Subject: {reply_draft.subject}")
            logger.info(f"Body preview: {reply_draft.body[:100]}...")
            
            self._update_send_tracking()
            return True, "Email sent successfully (DRY RUN)"
        
        try:
            # Actually send the email
            success = self._send_via_smtp(message, original_email.from_address)
            
            if success:
                self._update_send_tracking()
                
                log_email_action(
                    logger, "EMAIL SENT",
                    original_email.subject,
                    original_email.from_address,
                    f"Reply sent successfully"
                )
                
                return True, "Email sent successfully"
            else:
                return False, "SMTP send failed"
        
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _validate_send_request(self, original_email: Email, 
                               reply_draft: ReplyDraft) -> Tuple[bool, str]:
        """
        Validate that it's safe to send this reply.
        
        Returns:
            (is_valid, error_message)
        """
        # Check recipient email
        is_valid_email, error = validate_email_address(original_email.from_address)
        if not is_valid_email:
            return False, f"Invalid recipient email: {error}"
        
        # Check for no-reply addresses
        if is_noreply_address(original_email.from_address):
            return False, "Cannot send to no-reply address"
        
        # Check subject
        is_valid_subject, error = validate_subject(reply_draft.subject)
        if not is_valid_subject:
            return False, f"Invalid subject: {error}"
        
        # Check body
        if not reply_draft.body or len(reply_draft.body.strip()) < 10:
            return False, "Reply body is too short or empty"
        
        # Check draft warnings
        if reply_draft.warnings:
            warning_str = "; ".join(reply_draft.warnings)
            logger.warning(f"Draft has warnings: {warning_str}")
            # Don't block send, but log warnings
        
        return True, ""
    
    def _check_rate_limit(self) -> bool:
        """
        Check if we can send another email (rate limiting).
        
        Returns:
            True if OK to send, False if rate limited
        
        WHY RATE LIMIT?
        - Prevent accidental spam
        - Comply with SMTP provider limits
        - Protect against bugs causing email floods
        """
        if self.last_send_time is None:
            return True
        
        time_since_last = time.time() - self.last_send_time
        
        if time_since_last < self.min_send_interval:
            return False
        
        return True
    
    def _update_send_tracking(self):
        """Update tracking for rate limiting."""
        self.sent_count += 1
        self.last_send_time = time.time()
        
        logger.debug(f"Emails sent this session: {self.sent_count}")
    
    def _compose_reply(self, original_email: Email, 
                      reply_draft: ReplyDraft) -> MIMEMultipart:
        """
        Compose email message with proper threading headers.
        
        WHY THREADING HEADERS?
        - Keeps replies in same conversation
        - Better user experience in email clients
        - Professional email behavior
        """
        message = MIMEMultipart('alternative')
        
        # Basic headers
        message['From'] = self.email_address
        message['To'] = original_email.from_address
        message['Subject'] = reply_draft.subject
        message['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Threading headers (keep conversation together)
        if original_email.message_id:
            message['In-Reply-To'] = original_email.message_id
            
            # References should include all previous message IDs
            references = []
            if original_email.references:
                references.append(original_email.references)
            references.append(original_email.message_id)
            message['References'] = ' '.join(references)
        
        # Email body
        body_text = MIMEText(reply_draft.body, 'plain', 'utf-8')
        message.attach(body_text)
        
        logger.debug("Composed email message with threading headers")
        
        return message
    
    def _send_via_smtp(self, message: MIMEMultipart, to_address: str) -> bool:
        """
        Actually send the email via SMTP.
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            
            # Create SMTP connection
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Upgrade to secure connection
                
                # Login
                logger.debug("Authenticating with SMTP server")
                server.login(self.email_address, self.password)
                
                # Send
                logger.debug(f"Sending email to {to_address}")
                server.send_message(message)
                
                logger.info("Email sent successfully via SMTP")
                return True
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            logger.error("Check your email and app password in .env file")
            return False
        
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {e}")
            return False
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def send_batch(self, emails_and_drafts: list[Tuple[Email, ReplyDraft]],
                   approved_uids: set[str]) -> dict:
        """
        Send multiple replies (only approved ones).
        
        Args:
            emails_and_drafts: List of (Email, ReplyDraft) tuples
            approved_uids: Set of email UIDs that are approved for sending
        
        Returns:
            Dict with results: {uid: (success, message)}
        
        WHY?
        - Efficient batch sending
        - Clear tracking of what was sent
        - User can approve subset of drafts
        """
        results = {}
        
        logger.info(f"Starting batch send: {len(approved_uids)}/{len(emails_and_drafts)} approved")
        
        for email, draft in emails_and_drafts:
            is_approved = email.uid in approved_uids
            
            if is_approved:
                success, message = self.send_reply(email, draft, approved=True)
                results[email.uid] = (success, message)
                
                # Rate limiting: wait between sends
                if success and not self.dry_run:
                    time.sleep(self.min_send_interval)
            else:
                logger.debug(f"Skipping unapproved email: {email.subject}")
        
        # Summary
        successful = sum(1 for s, _ in results.values() if s)
        logger.info(f"Batch send complete: {successful}/{len(results)} successful")
        
        return results
    
    def get_send_statistics(self) -> dict:
        """Get statistics about emails sent this session."""
        return {
            'total_sent': self.sent_count,
            'last_send_time': self.last_send_time,
            'dry_run': self.dry_run
        }


# Example usage:
# from core.email_sender import EmailSender
# from core.email_reader import EmailReader
# from core.reply_generator import ReplyGenerator
# 
# reader = EmailReader()
# generator = ReplyGenerator()
# sender = EmailSender(dry_run=True)  # Test without sending
# 
# if reader.connect():
#     batch = reader.fetch_recent_emails(max_count=1)
#     if batch and batch.emails:
#         email = batch.emails[0]
#         draft = generator.generate_reply(email)
#         
#         if draft.should_reply:
#             print(f"Draft: {draft.body}")
#             
#             # In real usage, ask user for approval
#             user_approved = input("Send this reply? (yes/no): ").lower() == 'yes'
#             
#             if user_approved:
#                 success, msg = sender.send_reply(email, draft, approved=True)
#                 print(f"Result: {msg}")
#     
#     reader.disconnect()
