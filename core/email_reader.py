"""
Email Reader - IMAP-based email fetching from Gmail.

WHY IMAP?
- Standard protocol, works with any email provider
- Can mark emails as read/unread
- Access to folder structure
- No need to download entire mailbox

KEY DESIGN DECISIONS:
- Read-only by default (safer)
- Graceful degradation on errors
- Structured email objects for easy processing
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Optional
import re

from core.models import Email, EmailBatch
from config.settings import settings
from utils.logger import setup_logger
from utils.validators import sanitize_email_body

logger = setup_logger(__name__)


class EmailReader:
    """
    IMAP-based email reader for Gmail.
    
    WHY CLASS?
    - Maintains connection state
    - Handles authentication once
    - Can implement connection pooling
    - Easy to mock in tests
    """
    
    def __init__(self, email_address: str = None, password: str = None,
                 server: str = None, port: int = None):
        """
        Initialize email reader.
        
        Args:
            email_address: Gmail address (defaults to settings)
            password: App password (defaults to settings)
            server: IMAP server (defaults to settings)
            port: IMAP port (defaults to settings)
        """
        self.email_address = email_address or settings.GMAIL_EMAIL
        self.password = password or settings.GMAIL_APP_PASSWORD
        self.server = server or settings.IMAP_SERVER
        self.port = port or settings.IMAP_PORT
        
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        
        logger.info(f"Initialized EmailReader for {self.email_address}")
    
    def connect(self) -> bool:
        """
        Establish connection to IMAP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.server}:{self.port}")
            
            # Create SSL connection
            self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            
            # Login
            self.connection.login(self.email_address, self.password)
            
            logger.info("Successfully connected to email server")
            return True
        
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication error: {e}")
            logger.error("Check your email and app password in .env file")
            return False
        
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
    
    def fetch_recent_emails(self, folder: str = None, 
                           max_count: int = None) -> Optional[EmailBatch]:
        """
        Fetch recent emails from specified folder.
        
        Args:
            folder: Email folder (defaults to INBOX)
            max_count: Maximum number of emails to fetch
        
        Returns:
            EmailBatch object or None if fetch fails
        """
        folder = folder or settings.EMAIL_CHECK_FOLDER
        max_count = max_count or settings.MAX_EMAILS_TO_FETCH
        
        if not self.connection:
            logger.error("Not connected to email server")
            return None
        
        try:
            # Select folder
            logger.info(f"Selecting folder: {folder}")
            status, messages = self.connection.select(folder, readonly=True)
            
            if status != 'OK':
                logger.error(f"Failed to select folder: {folder}")
                return None
            
            # Search for all emails (can be filtered later)
            logger.info("Searching for emails...")
            status, message_ids = self.connection.search(None, 'ALL')
            
            if status != 'OK':
                logger.error("Failed to search emails")
                return None
            
            # Get list of email IDs
            email_ids = message_ids[0].split()
            total_emails = len(email_ids)
            
            logger.info(f"Found {total_emails} emails in {folder}")
            
            # Get most recent emails (IMAP returns oldest first, so reverse)
            email_ids = email_ids[-max_count:]
            email_ids.reverse()  # Most recent first
            
            # Fetch emails
            emails = []
            for i, email_id in enumerate(email_ids, 1):
                logger.info(f"Fetching email {i}/{len(email_ids)}")
                
                email_obj = self._fetch_single_email(email_id)
                if email_obj:
                    emails.append(email_obj)
            
            logger.info(f"Successfully fetched {len(emails)} emails")
            
            return EmailBatch(
                emails=emails,
                fetched_at=datetime.now(),
                total_count=total_emails
            )
        
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return None
    
    def _fetch_single_email(self, email_id: bytes) -> Optional[Email]:
        """
        Fetch and parse a single email.
        
        Args:
            email_id: IMAP email ID
        
        Returns:
            Email object or None if parsing fails
        
        WHY SEPARATE METHOD?
        - Easier to test individual email parsing
        - Can be reused for fetching specific emails
        - Cleaner error handling
        """
        try:
            # Fetch email data
            status, msg_data = self.connection.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                logger.warning(f"Failed to fetch email {email_id}")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            to_addr = self._decode_header(email_message.get('To', ''))
            date_str = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', '')
            in_reply_to = email_message.get('In-Reply-To', '')
            references = email_message.get('References', '')
            
            # Parse date
            email_date = self._parse_date(date_str)
            
            # Extract body
            body = self._extract_body(email_message)
            body = sanitize_email_body(body)
            
            # Create Email object
            return Email(
                uid=email_id.decode(),
                from_address=from_addr,
                to_address=to_addr,
                subject=subject,
                body=body,
                date=email_date,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references
            )
        
        except Exception as e:
            logger.error(f"Error parsing email {email_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """
        Decode email header (handles encoding like UTF-8, base64).
        
        WHY?
        - Email headers can be encoded in various formats
        - Must decode properly to avoid garbled text
        """
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        decoded_string = ""
        
        for content, encoding in decoded_parts:
            if isinstance(content, bytes):
                try:
                    decoded_string += content.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded_string += content.decode('utf-8', errors='ignore')
            else:
                decoded_string += str(content)
        
        return decoded_string.strip()
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse email date string to datetime object.
        
        Returns:
            datetime object, or current time if parsing fails
        """
        if not date_str:
            return datetime.now()
        
        try:
            # Use email.utils.parsedate_to_datetime for RFC 2822 format
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.now()
    
    def _extract_body(self, email_message) -> str:
        """
        Extract email body text.
        
        WHY COMPLEX?
        - Emails can be multipart (HTML + plain text)
        - Need to handle attachments
        - Must prefer plain text over HTML
        - HTML needs to be stripped of tags
        """
        body = ""
        
        if email_message.is_multipart():
            # Process multipart email
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break  # Prefer plain text
                    except Exception as e:
                        logger.warning(f"Error decoding plain text part: {e}")
                
                elif content_type == 'text/html' and not body:
                    # Use HTML if plain text not available
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            body = self._strip_html(html_content)
                    except Exception as e:
                        logger.warning(f"Error decoding HTML part: {e}")
        else:
            # Single part email
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8', errors='ignore')
                    
                    if email_message.get_content_type() == 'text/html':
                        body = self._strip_html(content)
                    else:
                        body = content
            except Exception as e:
                logger.warning(f"Error decoding single part email: {e}")
        
        return body.strip()
    
    def _strip_html(self, html: str) -> str:
        """
        Strip HTML tags and extract text.
        
        WHY NOT USE LIBRARY?
        - Simple regex is sufficient for basic stripping
        - Reduces dependencies
        - Good enough for LLM processing
        """
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&amp;', '&')
        html = html.replace('&quot;', '"')
        
        # Clean up whitespace
        html = re.sub(r'\s+', ' ', html)
        
        return html.strip()


# Example usage:
# from core.email_reader import EmailReader
# 
# reader = EmailReader()
# if reader.connect():
#     batch = reader.fetch_recent_emails(max_count=10)
#     if batch:
#         print(f"Fetched {len(batch.emails)} emails")
#         for email in batch.emails:
#             print(f"- {email.subject} from {email.from_address}")
#     reader.disconnect()
