"""
Save analyzed emails to JSON format
"""

import json
import os
from datetime import datetime
from typing import List
from core.models import Email, EmailBatch
from utils.logger import setup_logger

logger = setup_logger(__name__)


class EmailJSONSaver:
    """
    Saves analyzed emails to JSON files.
    
    WHY JSON?
    - Easy to read
    - Can be used by other programs
    - Good for backups
    - Can import into databases
    """
    
    def __init__(self, output_dir: str = "analyzed_emails"):
        """
        Initialize saver.
        
        Args:
            output_dir: Where to save JSON files
        """
        self.output_dir = output_dir
        
        # Create directory if doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created directory: {output_dir}")
    
    def save_batch(self, batch: EmailBatch, filename: str = None) -> str:
        """
        Save all emails to JSON.
        
        Args:
            batch: EmailBatch with analyzed emails
            filename: Custom filename (optional)
        
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emails_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Separate actionable and non-actionable
        actionable = []
        non_actionable = []
        
        for email in batch.emails:
            email_dict = self._email_to_dict(email)
            
            if email_dict['actionable']:
                actionable.append(email_dict)
            else:
                non_actionable.append(email_dict)
        
        # Sort actionable by urgency
        actionable.sort(key=lambda e: e['urgency_score'], reverse=True)
        
        # Create JSON structure
        data = {
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_emails': len(batch.emails),
            'actionable_count': len(actionable),
            'non_actionable_count': len(non_actionable),
            'actionable_emails': actionable,
            'non_actionable_emails': non_actionable
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(batch.emails)} emails to {filepath}")
        print(f"\n✓ Saved analysis to: {filepath}")
        
        return filepath
    
    def _email_to_dict(self, email: Email) -> dict:
        """Convert Email object to dictionary."""
        return {
            'from': email.from_address,
            'to': email.to_address,
            'subject': email.subject,
            'date': email.date.strftime('%Y-%m-%d %H:%M:%S'),
            'actionable': email.action.name == 'REPLY',
            'urgency_score': getattr(email, 'urgency_score', 0),
            'importance': email.importance.name,
            'action': email.action.name,
            'reasoning': email.analysis_reasoning,
            'body': email.body
        }
    
    def save_actionable_only(self, batch: EmailBatch, filename: str = None) -> str:
        """
        Save only actionable emails (ones that need response).
        
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"actionable_emails_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Get only actionable emails
        actionable = [
            self._email_to_dict(email)
            for email in batch.emails
            if email.action.name == 'REPLY'
        ]
        
        # Sort by urgency
        actionable.sort(key=lambda e: e['urgency_score'], reverse=True)
        
        data = {
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(actionable),
            'emails': actionable
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(actionable)} actionable emails to {filepath}")
        print(f"\n✓ Saved actionable emails to: {filepath}")
        
        return filepath
    
    def load_from_json(self, filepath: str) -> dict:
        """
        Load emails from JSON file.
        
        Args:
            filepath: Path to JSON file
        
        Returns:
            Dictionary with email data
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {data.get('total_emails', 0)} emails from {filepath}")
        
        return data
