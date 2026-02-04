"""
LLM-Based Email Analyzer - Uses AI model for intelligent analysis
"""

from core.models import Email, Analysis, Importance, Replyability, Action
from utils.llm_client import llm_client
from utils.logger import setup_logger

logger = setup_logger(__name__)


class EmailAnalyzer:
    """
    Uses LLM (AI model) to analyze emails intelligently.
    
    WHY USE LLM?
    - Understands context and nuance
    - Better than simple keyword matching
    - Can detect urgency from tone and content
    - Learns patterns humans understand
    """
    
    def __init__(self, llm_client_instance=None):
        self.llm = llm_client_instance or llm_client
        logger.info("LLM-Based Analyzer initialized")
    
    def analyze_email(self, email: Email) -> Email:
        """
        Analyze email using LLM.
        
        The LLM reads the email and decides:
        1. Is action needed?
        2. How urgent is it?
        3. Why?
        """
        logger.info(f"Analyzing with LLM: {email.subject}")
        
        # Check no-reply first (no need for LLM)
        if email.is_noreply():
            email.replyability = Replyability.NO
            email.action = Action.READ_ONLY
            email.importance = Importance.LOW
            email.analysis_reasoning = "No-reply address"
            email.urgency_score = 0
            return email
        
        # Ask LLM to analyze
        analysis_result = self._ask_llm_to_analyze(email)
        
        # Apply LLM results to email
        email.replyability = analysis_result['replyability']
        email.action = analysis_result['action']
        email.importance = analysis_result['importance']
        email.urgency_score = analysis_result['urgency_score']
        email.analysis_reasoning = analysis_result['reasoning']
        
        logger.info(f"LLM result: {email.action.name}, urgency: {email.urgency_score}")
        
        return email
    
    def _ask_llm_to_analyze(self, email: Email) -> dict:
        """
        Ask the LLM to analyze the email.
        
        Returns dict with analysis results.
        """
        # Create prompt for LLM
        prompt = f"""Analyze this email and tell me:
1. Does it need a response/action from me?
2. How urgent is it (0-100)?
3. Why?

EMAIL:
From: {email.from_address}
Subject: {email.subject}
Body: {email.body[:1000]}

Respond in this exact format:
ACTIONABLE: YES or NO
URGENCY: [number 0-100]
REASONING: [one sentence why]

Examples:

Email: "Can you send the Q4 report urgently?"
ACTIONABLE: YES
URGENCY: 85
REASONING: Requests document with urgent keyword

Email: "FYI - New policy update"
ACTIONABLE: NO
URGENCY: 20
REASONING: Just information, no action needed

Email: "Please review this by tomorrow"
ACTIONABLE: YES
URGENCY: 70
REASONING: Requests review with deadline

Now analyze the email above:"""
        
        try:
            # Call LLM
            response = self.llm.generate(prompt, max_tokens=200)
            
            if not response:
                logger.warning("LLM returned empty, using fallback")
                return self._fallback_analysis()
            
            # Parse LLM response
            result = self._parse_llm_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._fallback_analysis()
    
    def _parse_llm_response(self, response: str) -> dict:
        """Parse the LLM's response."""
        
        actionable = False
        urgency = 50
        reasoning = "Standard email"
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('ACTIONABLE:'):
                value = line.split(':', 1)[1].strip().upper()
                actionable = (value == 'YES')
            
            elif line.startswith('URGENCY:'):
                try:
                    urgency = int(line.split(':', 1)[1].strip())
                    urgency = max(0, min(100, urgency))  # Keep in 0-100 range
                except:
                    urgency = 50
            
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
        
        # Convert to our enums
        if actionable:
            replyability = Replyability.YES
            action = Action.REPLY
        else:
            replyability = Replyability.NO
            action = Action.READ_ONLY
        
        # Set importance based on urgency score
        if urgency >= 80:
            importance = Importance.CRITICAL
        elif urgency >= 60:
            importance = Importance.HIGH
        elif urgency >= 30:
            importance = Importance.NORMAL
        else:
            importance = Importance.LOW
        
        return {
            'replyability': replyability,
            'action': action,
            'importance': importance,
            'urgency_score': urgency,
            'reasoning': reasoning
        }
    
    def _fallback_analysis(self) -> dict:
        """
        Fallback if LLM fails.
        Uses simple keyword check.
        """
        return {
            'replyability': Replyability.UNKNOWN,
            'action': Action.READ_ONLY,
            'importance': Importance.NORMAL,
            'urgency_score': 50,
            'reasoning': 'LLM unavailable - default analysis'
        }
    
    def analyze_batch(self, emails: list[Email], show_progress: bool = True) -> list[Email]:
        """Analyze multiple emails using LLM."""
        total = len(emails)
        logger.info(f"Analyzing {total} emails with LLM")
        
        for i, email in enumerate(emails, 1):
            if show_progress:
                print(f"  [{i}/{total}] Asking LLM about: {email.subject[:50]}...")
            
            self.analyze_email(email)
        
        logger.info(f"Completed LLM analysis of {total} emails")
        return emails
