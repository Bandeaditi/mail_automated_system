"""
Pure LLM Chatbot - Updated with quick count feature
"""

import sys
import json
from colorama import init, Fore, Style

from core.models import Email, EmailBatch, Replyability, Action
from core.email_reader import EmailReader
from core.email_analyzer import EmailAnalyzer
from core.reply_generator import ReplyGenerator
from core.email_sender import EmailSender
from utils.email_json_saver import EmailJSONSaver
from utils.llm_client import llm_client
from config.settings import settings
from utils.logger import setup_logger

init(autoreset=True)
logger = setup_logger(__name__)


class PureAIChatbot:
    """100% LLM-powered chatbot"""
    
    def __init__(self, dry_run: bool = False):
        self.reader = EmailReader()
        self.analyzer = EmailAnalyzer()
        self.generator = ReplyGenerator()
        self.sender = EmailSender(dry_run=dry_run)
        self.json_saver = EmailJSONSaver()
        self.llm = llm_client
        self.dry_run = dry_run
        
        self.current_batch = None
        self.current_drafts = {}
        self.actionable_emails = []
        self.non_actionable_emails = []
    
    def run(self):
        """Main chatbot loop"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  AI EMAIL ASSISTANT")
        print(f"{Fore.CYAN}  Talk naturally - I understand everything (even typos!)")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        
        # Check config
        is_valid, errors = settings.validate()
        if not is_valid:
            print(f"{Fore.RED}Configuration error. Check .env file.{Style.RESET_ALL}")
            return
        
        # Check LLM
        print(f"{Fore.YELLOW}Starting AI...{Style.RESET_ALL}")
        test = self.llm.generate("Hi", max_tokens=5)
        if not test:
            print(f"{Fore.RED}AI not available. Run: ollama serve{Style.RESET_ALL}\n")
            return
        
        print(f"{Fore.GREEN}✓ AI ready{Style.RESET_ALL}\n")
        
        # Welcome
        print(f"{Fore.CYAN}Hi! I'm your AI email assistant.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Talk to me naturally - I understand typos too!{Style.RESET_ALL}\n")
        
        # Chat loop
        while True:
            user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}").strip()
            
            if not user_input:
                continue
            
            # Let AI understand and respond
            self._ai_understand_and_act(user_input)
            print()
    
    def _ai_understand_and_act(self, user_input: str):
        """Let AI understand and act"""
        
        # Build context
        context = self._build_context()
        
        # Ask AI what user wants
        prompt = f"""You are an email assistant. User said: "{user_input}"

Current state: {context}

Understand what user wants (even with typos) and return JSON.

Available actions:
- COUNT_EMAILS: Just count how many emails (no analysis)
- FETCH_EMAILS: Get and analyze emails
- SHOW_ALL: Show all emails
- SHOW_ACTIONABLE: Show emails needing action
- SHOW_URGENT: Show urgent emails
- GENERATE_REPLIES: Create reply drafts
- REPLY_TO_SPECIFIC: Reply to specific email (extract number)
- SEND_DRAFTS: Send draft replies
- SAVE_JSON: Save to JSON
- QUIT: Exit
- UNCLEAR: Don't understand

IMPORTANT: If user just wants to know "how many" or "count" → use COUNT_EMAILS (quick, no analysis)
If user wants to "check", "fetch", "analyze" → use FETCH_EMAILS (full analysis)

Format:
ACTION: [action]
PARAMETER: [number if needed, empty otherwise]
MESSAGE: [friendly response]

Examples:

User: "how many emails do i have"
ACTION: COUNT_EMAILS
PARAMETER: 
MESSAGE: Let me check how many emails you have...

User: "give me count of my mails"
ACTION: COUNT_EMAILS
PARAMETER: 
MESSAGE: Checking your email count...

User: "check my emails"
ACTION: FETCH_EMAILS
PARAMETER: 
MESSAGE: Sure! Fetching and analyzing your emails...

User: "get 50 emails"
ACTION: FETCH_EMAILS
PARAMETER: 50
MESSAGE: Getting 50 emails for analysis...

User: "show urgent"
ACTION: SHOW_URGENT
PARAMETER: 
MESSAGE: Here are your urgent emails:

User: "reply to 2"
ACTION: REPLY_TO_SPECIFIC
PARAMETER: 2
MESSAGE: Creating reply for email 2...

Now process: "{user_input}"
"""
        
        try:
            # Ask AI
            ai_response = self.llm.generate(prompt, max_tokens=200)
            
            if not ai_response:
                print(f"{Fore.CYAN}Assistant: Sorry, can you rephrase?{Style.RESET_ALL}")
                return
            
            # Parse
            decision = self._parse_ai_decision(ai_response)
            
            # Show message
            print(f"{Fore.CYAN}Assistant: {decision['message']}{Style.RESET_ALL}")
            
            # Execute
            self._execute_action(decision)
            
        except Exception as e:
            logger.error(f"AI error: {e}")
            print(f"{Fore.RED}Assistant: Oops, something went wrong!{Style.RESET_ALL}")
    
    def _parse_ai_decision(self, ai_response: str) -> dict:
        """Parse AI decision"""
        
        action = "UNCLEAR"
        parameter = ""
        message = "I'm not sure what you mean."
        
        lines = ai_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('ACTION:'):
                action = line.split(':', 1)[1].strip()
            elif line.startswith('PARAMETER:'):
                parameter = line.split(':', 1)[1].strip()
            elif line.startswith('MESSAGE:'):
                message = line.split(':', 1)[1].strip()
        
        return {
            'action': action,
            'parameter': parameter,
            'message': message
        }
    
    def _execute_action(self, decision: dict):
        """Execute action"""
        
        action = decision['action']
        parameter = decision['parameter']
        
        if action == 'COUNT_EMAILS':
            self._count_emails_only()
        
        elif action == 'FETCH_EMAILS':
            count = int(parameter) if parameter.isdigit() else 20
            self._fetch_emails(count)
        
        elif action == 'SHOW_ALL':
            self._show_all_emails()
        
        elif action == 'SHOW_ACTIONABLE':
            self._show_actionable()
        
        elif action == 'SHOW_URGENT':
            self._show_urgent()
        
        elif action == 'GENERATE_REPLIES':
            self._generate_all_replies()
        
        elif action == 'REPLY_TO_SPECIFIC':
            num = int(parameter) if parameter.isdigit() else 0
            self._reply_to_specific(num)
        
        elif action == 'SEND_DRAFTS':
            self._send_drafts()
        
        elif action == 'SAVE_JSON':
            self._save_json()
        
        elif action == 'QUIT':
            print(f"\n{Fore.CYAN}Assistant: Goodbye!{Style.RESET_ALL}\n")
            sys.exit(0)
    
    def _build_context(self) -> str:
        """Build context"""
        
        parts = []
        
        if self.current_batch:
            parts.append(f"Emails loaded: {len(self.current_batch.emails)}")
            parts.append(f"Actionable: {len(self.actionable_emails)}")
        else:
            parts.append("No emails loaded")
        
        if self.current_drafts:
            parts.append(f"Drafts: {len(self.current_drafts)}")
        
        return ", ".join(parts)
    
    def _count_emails_only(self):
        """Quick count - no analysis"""
        
        # Connect
        if not self.reader.connect():
            print(f"{Fore.RED}Assistant: Can't connect to Gmail.{Style.RESET_ALL}")
            return
        
        # Just count, don't fetch
        try:
            import imaplib
            status, messages = self.reader.mail.search(None, 'ALL')
            
            if status == 'OK':
                email_ids = messages[0].split()
                count = len(email_ids)
                
                print(f"\n{Fore.GREEN}✓ You have {count} emails in your inbox{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Assistant: Couldn't count emails{Style.RESET_ALL}")
        
        except Exception as e:
            print(f"{Fore.RED}Assistant: Error counting emails{Style.RESET_ALL}")
        
        finally:
            self.reader.disconnect()
    
    def _fetch_emails(self, count: int):
        """Fetch and analyze"""
        
        # Connect
        if not self.reader.connect():
            print(f"{Fore.RED}Assistant: Can't connect.{Style.RESET_ALL}")
            return
        
        # Fetch
        self.current_batch = self.reader.fetch_recent_emails(max_count=count)
        self.reader.disconnect()
        
        if not self.current_batch or not self.current_batch.emails:
            print(f"{Fore.CYAN}Assistant: No emails found.{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}Assistant: Analyzing {len(self.current_batch.emails)} emails...{Style.RESET_ALL}\n")
        
        # Analyze
        self.analyzer.analyze_batch(self.current_batch.emails, show_progress=False)
        
        # Separate
        self.actionable_emails = [e for e in self.current_batch.emails if e.action == Action.REPLY]
        self.non_actionable_emails = [e for e in self.current_batch.emails if e.action != Action.REPLY]
        
        # Sort
        self.actionable_emails.sort(key=lambda e: getattr(e, 'urgency_score', 0), reverse=True)
        
        # Save
        self.json_saver.save_batch(self.current_batch)
        
        print(f"\n{Fore.GREEN}✓ Done!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {len(self.actionable_emails)} need your action{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  {len(self.non_actionable_emails)} are FYI{Style.RESET_ALL}")
    
    def _show_all_emails(self):
        """Show all"""
        
        if not self.current_batch:
            print(f"{Fore.CYAN}Assistant: No emails loaded.{Style.RESET_ALL}")
            return
        
        if self.actionable_emails:
            print(f"\n{Fore.RED}ACTIONABLE ({len(self.actionable_emails)}):{Style.RESET_ALL}\n")
            self._display_emails(self.actionable_emails)
        
        if self.non_actionable_emails:
            print(f"\n{Fore.BLUE}FYI ({len(self.non_actionable_emails)}):{Style.RESET_ALL}\n")
            self._display_emails(self.non_actionable_emails)
    
    def _show_actionable(self):
        """Show actionable"""
        
        if not self.actionable_emails:
            print(f"{Fore.GREEN}Assistant: No emails need response!{Style.RESET_ALL}")
            return
        
        print()
        self._display_emails(self.actionable_emails)
    
    def _show_urgent(self):
        """Show urgent"""
        
        urgent = [e for e in self.actionable_emails if getattr(e, 'urgency_score', 0) >= 70]
        
        if not urgent:
            print(f"{Fore.GREEN}Assistant: No urgent emails!{Style.RESET_ALL}")
            return
        
        print()
        self._display_emails(urgent)
    
    def _display_emails(self, emails: list):
        """Display list"""
        
        for i, email in enumerate(emails, 1):
            score = getattr(email, 'urgency_score', 0)
            
            if score >= 80:
                marker = "🔴"
                color = Fore.RED
            elif score >= 60:
                marker = "🟡"
                color = Fore.YELLOW
            else:
                marker = "🟢"
                color = Fore.GREEN
            
            print(f"{color}{marker} [{i}] {email.subject}{Style.RESET_ALL}")
            print(f"    From: {email.from_address}")
            print(f"    {email.analysis_reasoning}")
            print()
    
    def _generate_all_replies(self):
        """Generate replies"""
        
        if not self.actionable_emails:
            print(f"{Fore.CYAN}Assistant: No emails to reply to.{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}Assistant: Creating {len(self.actionable_emails)} replies...{Style.RESET_ALL}\n")
        
        self.current_drafts = self.generator.generate_multiple_replies(
            self.actionable_emails,
            only_replyable=True
        )
        
        successful = sum(1 for d in self.current_drafts.values() if d.should_reply)
        print(f"{Fore.GREEN}✓ Generated {successful} drafts!{Style.RESET_ALL}")
    
    def _reply_to_specific(self, num: int):
        """Reply to specific"""
        
        if num < 1 or num > len(self.actionable_emails):
            print(f"{Fore.CYAN}Assistant: Invalid email number.{Style.RESET_ALL}")
            return
        
        email = self.actionable_emails[num - 1]
        
        print(f"{Fore.CYAN}Assistant: Creating reply...{Style.RESET_ALL}\n")
        
        draft = self.generator.generate_reply(email)
        
        if draft and draft.should_reply:
            print(f"{Fore.CYAN}Draft:{Style.RESET_ALL}")
            print("-" * 60)
            print(draft.body)
            print("-" * 60)
            
            send = input(f"\n{Fore.GREEN}Send? (yes/no): {Style.RESET_ALL}").strip().lower()
            
            if send in ['yes', 'y']:
                self.current_drafts[email.uid] = draft
                print(f"{Fore.GREEN}✓ Saved!{Style.RESET_ALL}")
    
    def _send_drafts(self):
        """Send drafts"""
        
        if not self.current_drafts:
            print(f"{Fore.CYAN}Assistant: No drafts.{Style.RESET_ALL}")
            return
        
        print(f"{Fore.YELLOW}Assistant: Sending {len(self.current_drafts)} emails.{Style.RESET_ALL}")
        
        confirm = input(f"{Fore.GREEN}Confirm? (yes): {Style.RESET_ALL}").strip().lower()
        
        if confirm in ['yes', 'y']:
            emails_with_drafts = [
                (e, self.current_drafts[e.uid])
                for e in self.actionable_emails
                if e.uid in self.current_drafts
            ]
            
            approved = set(e.uid for e, _ in emails_with_drafts)
            
            results = self.sender.send_batch(emails_with_drafts, approved)
            
            successful = sum(1 for s, _ in results.values() if s)
            print(f"{Fore.GREEN}✓ Sent {successful}!{Style.RESET_ALL}")
    
    def _save_json(self):
        """Save JSON"""
        
        if not self.current_batch:
            print(f"{Fore.CYAN}Assistant: No emails to save.{Style.RESET_ALL}")
            return
        
        self.json_saver.save_batch(self.current_batch)
        print(f"{Fore.GREEN}✓ Saved!{Style.RESET_ALL}")


def main():
    dry_run = '--dry-run' in sys.argv
    
    try:
        chatbot = PureAIChatbot(dry_run=dry_run)
        chatbot.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.CYAN}Bye!{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
