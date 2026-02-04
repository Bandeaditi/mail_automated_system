"""
Reply Generator - LLM-based draft reply generation.

KEY DESIGN:
- Human-in-the-loop (drafts must be approved)
- Safety checks (no-reply detection, validation)
- Context-aware generation
- Professional tone enforcement
"""

from typing import Optional
from core.models import Email, ReplyDraft, Replyability
from config.prompts import format_reply_prompt, parse_reply_response
from utils.llm_client import llm_client
from utils.logger import setup_logger, log_email_action
from utils.validators import check_reply_safety, validate_reply_draft

logger = setup_logger(__name__)


class ReplyGenerator:
    """
    Generates draft replies to emails using LLM.
    
    WHY LLM?
    - Understands context and tone
    - Can adapt to different email types
    - Provides reasoning for drafts
    - No templates needed
    """
    
    def __init__(self, llm_client_instance=None):
        """
        Initialize reply generator.
        
        Args:
            llm_client_instance: LLM client (defaults to singleton)
        """
        self.llm = llm_client_instance or llm_client
        logger.info("Initialized ReplyGenerator")
    
    def generate_reply(self, email: Email, context: str = "") -> ReplyDraft:
        """
        Generate a draft reply for an email.
        
        Args:
            email: Email to reply to
            context: Additional context for reply generation
        
        Returns:
            ReplyDraft object (may indicate should_reply=False)
        
        WHY ALWAYS RETURN DRAFT?
        - Consistent API (no None to check)
        - Draft can explain why NOT to reply
        - Warnings are captured in draft
        """
        logger.info(f"Generating reply for: '{email.subject}' from {email.from_address}")
        
        # Safety checks BEFORE calling LLM
        is_safe, warnings = check_reply_safety(
            email.from_address,
            email.subject,
            email.body
        )
        
        if not is_safe:
            logger.warning(f"Reply safety check failed: {warnings}")
            draft = ReplyDraft.create_noreply(email.subject)
            draft.warnings = warnings
            return draft
        
        # Check if email is marked as not replyable by analyzer
        if email.replyability == Replyability.NO:
            logger.info("Email marked as not replyable by analyzer")
            draft = ReplyDraft.create_noreply(email.subject)
            draft.reasoning = "Email analysis determined this doesn't need a reply"
            return draft
        
        # Generate reply using LLM
        draft = self._generate_draft_with_llm(email, context)
        
        # Add any warnings from safety check
        if warnings:
            draft.warnings.extend(warnings)
        
        log_email_action(
            logger, "REPLY GENERATED", 
            email.subject, email.from_address,
            f"Should reply: {draft.should_reply}"
        )
        
        return draft
    
    def _generate_draft_with_llm(self, email: Email, context: str) -> ReplyDraft:
        """
        Generate draft using LLM.
        
        Returns:
            ReplyDraft object
        
        WHY SEPARATE?
        - Isolates LLM interaction
        - Easier to test
        - Can be overridden
        """
        try:
            # Format prompt
            prompt = format_reply_prompt(
                from_addr=email.from_address,
                to_addr=email.to_address,
                subject=email.subject,
                body=email.body,
                context=context
            )
            
            # Call LLM
            llm_response = self.llm.generate(prompt, max_tokens=800)
            
            if not llm_response:
                logger.warning("LLM returned no response for reply generation")
                return self._create_fallback_draft(
                    email.subject,
                    "LLM failed to generate reply"
                )
            
            # Parse response
            parsed = parse_reply_response(llm_response)
            
            # Convert to ReplyDraft
            draft = self._parse_to_draft(parsed, email.subject)
            
            # Validate draft
            is_valid, error = validate_reply_draft(draft.body)
            if not is_valid:
                logger.warning(f"Generated draft validation failed: {error}")
                draft.warnings.append(f"Draft validation issue: {error}")
            
            logger.debug(f"Generated draft: {len(draft.body)} chars")
            
            return draft
        
        except Exception as e:
            logger.error(f"Error generating reply draft: {e}")
            return self._create_fallback_draft(
                email.subject,
                f"Error during generation: {str(e)}"
            )
    
    def _parse_to_draft(self, parsed: dict, original_subject: str) -> ReplyDraft:
        """
        Convert parsed LLM response to ReplyDraft.
        
        Args:
            parsed: Dict with parsed fields
            original_subject: Original email subject (fallback)
        
        Returns:
            ReplyDraft object
        """
        subject = parsed.get('subject') or f"Re: {original_subject}"
        body = parsed.get('body') or ""
        reasoning = parsed.get('reasoning') or "Generated by LLM"
        
        # Ensure subject starts with "Re: " if replying
        if not subject.startswith("Re: ") and not subject.startswith("RE: "):
            subject = f"Re: {subject}"
        
        should_reply = bool(body and len(body.strip()) > 20)
        
        warnings = []
        if not body:
            warnings.append("LLM did not generate email body")
            should_reply = False
        
        return ReplyDraft(
            body=body.strip(),
            subject=subject,
            reasoning=reasoning,
            should_reply=should_reply,
            warnings=warnings
        )
    
    def _create_fallback_draft(self, subject: str, reason: str) -> ReplyDraft:
        """
        Create a fallback draft when LLM fails.
        
        WHY?
        - System continues working even if LLM fails
        - User is informed about the issue
        - Can still manually write reply
        """
        return ReplyDraft(
            body="",
            subject=f"Re: {subject}",
            reasoning=reason,
            should_reply=False,
            warnings=[reason]
        )
    
    def generate_multiple_replies(self, emails: list[Email], 
                                  context: str = "",
                                  only_replyable: bool = True) -> dict[str, ReplyDraft]:
        """
        Generate drafts for multiple emails.
        
        Args:
            emails: List of emails to generate replies for
            context: Shared context for all replies
            only_replyable: Only generate for emails marked as replyable
        
        Returns:
            Dict mapping email UID to ReplyDraft
        
        WHY DICT?
        - Easy lookup by email ID
        - Preserves association with original email
        - Can be partial (some might fail)
        """
        drafts = {}
        
        # Filter emails if requested
        emails_to_process = emails
        if only_replyable:
            emails_to_process = [
                e for e in emails 
                if e.replyability == Replyability.YES
            ]
            logger.info(f"Generating replies for {len(emails_to_process)}/{len(emails)} replyable emails")
        else:
            logger.info(f"Generating replies for all {len(emails)} emails")
        
        for i, email in enumerate(emails_to_process, 1):
            if i % 5 == 0:
                logger.info(f"Progress: {i}/{len(emails_to_process)} replies generated")
            
            draft = self.generate_reply(email, context)
            drafts[email.uid] = draft
            
            # Store draft in email object for convenience
            email.draft_reply = draft.body
        
        logger.info(f"Completed generating {len(drafts)} reply drafts")
        
        return drafts
    
    def refine_draft(self, original_draft: str, refinement_instructions: str,
                    email_subject: str) -> ReplyDraft:
        """
        Refine an existing draft based on user instructions.
        
        Args:
            original_draft: The original draft text
            refinement_instructions: User's instructions for changes
            email_subject: Subject of original email
        
        Returns:
            Refined ReplyDraft
        
        WHY?
        - Allows iterative improvement
        - User can customize LLM output
        - Better than regenerating from scratch
        """
        try:
            refinement_prompt = f"""You are refining an email reply based on user feedback.

ORIGINAL DRAFT:
---
{original_draft}
---

USER FEEDBACK:
{refinement_instructions}

Please revise the draft according to the user's feedback. Maintain professional tone.

RESPONSE FORMAT:
BODY:
[The refined email body]
---
REASONING: [One sentence explaining the changes made]
"""
            
            llm_response = self.llm.generate(refinement_prompt, max_tokens=800)
            
            if not llm_response:
                logger.warning("LLM failed to refine draft")
                return self._create_fallback_draft(
                    email_subject,
                    "Failed to refine draft"
                )
            
            parsed = parse_reply_response(llm_response)
            draft = self._parse_to_draft(parsed, email_subject)
            
            logger.info("Successfully refined draft")
            return draft
        
        except Exception as e:
            logger.error(f"Error refining draft: {e}")
            return self._create_fallback_draft(
                email_subject,
                f"Refinement error: {str(e)}"
            )


# Example usage:
# from core.reply_generator import ReplyGenerator
# from core.email_reader import EmailReader
# from core.email_analyzer import EmailAnalyzer
# 
# reader = EmailReader()
# analyzer = EmailAnalyzer()
# generator = ReplyGenerator()
# 
# if reader.connect():
#     batch = reader.fetch_recent_emails(max_count=5)
#     if batch:
#         # Analyze first
#         analyzer.analyze_batch(batch.emails)
#         
#         # Generate replies for replyable emails
#         for email in batch.emails:
#             if email.replyability == Replyability.YES:
#                 draft = generator.generate_reply(email)
#                 
#                 if draft.should_reply:
#                     print(f"\nDraft for: {email.subject}")
#                     print(f"Subject: {draft.subject}")
#                     print(f"Body:\n{draft.body}")
#                     print(f"Reasoning: {draft.reasoning}")
#                 else:
#                     print(f"\nNo reply needed: {draft.reasoning}")
#     
#     reader.disconnect()
