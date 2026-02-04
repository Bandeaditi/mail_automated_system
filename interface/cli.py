"""
CLI with LLM Analysis and JSON saving
"""

import sys
from colorama import init, Fore, Style

from core.models import Email, EmailBatch, Replyability, Action
from core.email_reader import EmailReader
from core.email_analyzer import EmailAnalyzer
from core.reply_generator import ReplyGenerator
from core.email_sender import EmailSender
from utils.email_json_saver import EmailJSONSaver
from config.settings import settings
from utils.logger import setup_logger

init(autoreset=True)
logger = setup_logger(__name__)


class EmailCLI:
    """CLI with LLM analysis and JSON saving"""
    
    def __init__(self, dry_run: bool = False):
        self.reader = EmailReader()
        self.analyzer = EmailAnalyzer()  # Uses LLM now!
        self.generator = ReplyGenerator()
        self.sender = EmailSender(dry_run=dry_run)
        self.json_saver = EmailJSONSaver()
        self.dry_run = dry_run
        
        self.current_batch = None
        self.current_drafts = {}
    
    def run(self):
        """Main loop"""
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}  EMAIL AUTOMATION")
        print(f"{Fore.CYAN}  ✓ Uses AI Model (LLM) for analysis")
        print(f"{Fore.CYAN}  ✓ Saves results to JSON")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        
        # Check config
        is_valid, errors = settings.validate()
        if not is_valid:
            print(f"{Fore.RED}Configuration errors:{Style.RESET_ALL}")
            for error in errors:
                print(f"  - {error}")
            return
        
        print(f"{Fore.GREEN}✓ Configuration loaded{Style.RESET_ALL}")
        
        # Check if LLM is available
        print(f"{Fore.YELLOW}Checking LLM (AI model)...{Style.RESET_ALL}")
        test_response = self.analyzer.llm.generate("test", max_tokens=5)
        if test_response:
            print(f"{Fore.GREEN}✓ LLM is ready{Style.RESET_ALL}\n")
        else:
            print(f"{Fore.RED}✗ LLM not available{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Make sure Ollama is running: ollama serve{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}And model is installed: ollama pull llama2{Style.RESET_ALL}\n")
            return
        
        # Main menu
        while True:
            print(f"\n{Fore.CYAN}{'='*50}")
            print(f"MENU")
            print(f"{'='*50}{Style.RESET_ALL}")
            print("1. Fetch and analyze emails (using AI)")
            print("2. Show analyzed emails")
            print("3. Save analysis to JSON")
            print("4. Generate replies (using AI)")
            print("5. Send replies")
            print("q. Quit")
            
            choice = input(f"\n{Fore.GREEN}Choose: {Style.RESET_ALL}").strip()
            
            if choice == '1':
                self._fetch_and_analyze()
            elif choice == '2':
                self._show_emails()
            elif choice == '3':
                self._save_to_json()
            elif choice == '4':
                self._generate_replies()
            elif choice == '5':
                self._send_replies()
            elif choice == 'q':
                print("\nBye!")
                break
            
            input(f"\n{Fore.CYAN}Press Enter...{Style.RESET_ALL}")
    
    def _fetch_and_analyze(self):
        """Fetch and analyze with LLM"""
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"FETCH & ANALYZE (Using AI Model)")
        print(f"{'='*50}{Style.RESET_ALL}\n")
        
        # Get count
        count_input = input(f"How many emails? (default 20): ").strip()
        max_count = int(count_input) if count_input.isdigit() else 20
        
        # Connect
        print(f"\n{Fore.YELLOW}Connecting to Gmail...{Style.RESET_ALL}")
        if not self.reader.connect():
            print(f"{Fore.RED}✗ Connection failed{Style.RESET_ALL}")
            print("Check your .env file settings")
            return
        
        print(f"{Fore.GREEN}✓ Connected{Style.RESET_ALL}")
        
        # Fetch
        print(f"{Fore.YELLOW}Fetching {max_count} emails...{Style.RESET_ALL}")
        self.current_batch = self.reader.fetch_recent_emails(max_count=max_count)
        self.reader.disconnect()
        
        if not self.current_batch or not self.current_batch.emails:
            print(f"{Fore.RED}No emails found{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}✓ Fetched {len(self.current_batch.emails)} emails{Style.RESET_ALL}")
        
        # Analyze with LLM
        print(f"\n{Fore.YELLOW}Analyzing with AI model...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}This uses the LLM to understand each email{Style.RESET_ALL}\n")
        
        self.analyzer.analyze_batch(self.current_batch.emails, show_progress=True)
        
        print(f"\n{Fore.GREEN}✓ AI analysis complete!{Style.RESET_ALL}")
        
        # Auto-save to JSON
        print(f"\n{Fore.YELLOW}Auto-saving to JSON...{Style.RESET_ALL}")
        self.json_saver.save_batch(self.current_batch)
        
        # Show results
        self._show_emails()
    
    def _show_emails(self):
        """Show analyzed emails"""
        if not self.current_batch:
            print(f"\n{Fore.YELLOW}No emails loaded. Fetch first (option 1){Style.RESET_ALL}")
            return
        
        emails = self.current_batch.emails
        
        # Separate
        actionable = []
        non_actionable = []
        
        for email in emails:
            if email.action == Action.REPLY:
                actionable.append(email)
            else:
                non_actionable.append(email)
        
        # Sort actionable by urgency (LLM-determined)
        actionable.sort(key=lambda e: getattr(e, 'urgency_score', 0), reverse=True)
        
        # Display
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"YOUR EMAILS (Analyzed by AI)")
        print(f"{'='*80}{Style.RESET_ALL}\n")
        
        print(f"Total: {len(emails)} emails")
        print(f"  → {Fore.RED}{len(actionable)} NEED YOUR ACTION{Style.RESET_ALL}")
        print(f"  → {Fore.BLUE}{len(non_actionable)} just information{Style.RESET_ALL}")
        
        # Show actionable first
        if actionable:
            print(f"\n{Fore.RED}{'='*80}")
            print(f"📌 ACTIONABLE - NEED YOUR ACTION")
            print(f"(AI sorted by urgency - most urgent first)")
            print(f"{'='*80}{Style.RESET_ALL}\n")
            
            for i, email in enumerate(actionable, 1):
                score = getattr(email, 'urgency_score', 0)
                
                if score >= 80:
                    marker = "🔴"
                    urgency = "VERY URGENT"
                    color = Fore.RED
                elif score >= 60:
                    marker = "🟡"
                    urgency = "URGENT"
                    color = Fore.YELLOW
                elif score >= 40:
                    marker = "🟢"
                    urgency = "MODERATE"
                    color = Fore.GREEN
                else:
                    marker = "🔵"
                    urgency = "NORMAL"
                    color = Fore.BLUE
                
                print(f"{color}{marker} [{i}] {urgency} (AI score: {score}/100){Style.RESET_ALL}")
                print(f"   From: {email.from_address}")
                print(f"   Subject: {email.subject}")
                print(f"   AI reasoning: {email.analysis_reasoning}")
                print()
        else:
            print(f"\n{Fore.GREEN}✓ No actionable emails!{Style.RESET_ALL}\n")
        
        # Show non-actionable
        if non_actionable:
            print(f"\n{Fore.BLUE}{'='*80}")
            print(f"📖 NON-ACTIONABLE - JUST INFORMATION")
            print(f"{'='*80}{Style.RESET_ALL}\n")
            
            for i, email in enumerate(non_actionable, 1):
                print(f"{Fore.BLUE}[{i}]{Style.RESET_ALL}")
                print(f"   From: {email.from_address}")
                print(f"   Subject: {email.subject}")
                print(f"   AI reasoning: {email.analysis_reasoning}")
                print()
        
        # View details
        if actionable:
            print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            view = input(f"View full email? Enter number (or Enter to skip): ").strip()
            
            if view.isdigit():
                idx = int(view) - 1
                if 0 <= idx < len(actionable):
                    self._show_full_email(actionable[idx])
    
    def _show_full_email(self, email: Email):
        """Show full email"""
        score = getattr(email, 'urgency_score', 0)
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"FULL EMAIL")
        print(f"{'='*80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}AI Urgency Score:{Style.RESET_ALL} {score}/100")
        print(f"{Fore.YELLOW}From:{Style.RESET_ALL} {email.from_address}")
        print(f"{Fore.YELLOW}Subject:{Style.RESET_ALL} {email.subject}")
        print(f"{Fore.YELLOW}Date:{Style.RESET_ALL} {email.date.strftime('%Y-%m-%d %H:%M')}")
        print(f"{Fore.YELLOW}AI Analysis:{Style.RESET_ALL} {email.analysis_reasoning}")
        
        print(f"\n{Fore.YELLOW}Body:{Style.RESET_ALL}")
        print("-" * 80)
        print(email.body)
        print("-" * 80)
    
    def _save_to_json(self):
        """Save analyzed emails to JSON"""
        if not self.current_batch:
            print(f"\n{Fore.YELLOW}No emails to save. Fetch first (option 1){Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"SAVE TO JSON")
        print(f"{'='*50}{Style.RESET_ALL}\n")
        
        print("What to save?")
        print("1. All emails (actionable + non-actionable)")
        print("2. Only actionable emails")
        
        choice = input(f"\n{Fore.GREEN}Choose: {Style.RESET_ALL}").strip()
        
        if choice == '1':
            filepath = self.json_saver.save_batch(self.current_batch)
            print(f"\n{Fore.GREEN}✓ Saved all emails to: {filepath}{Style.RESET_ALL}")
        
        elif choice == '2':
            filepath = self.json_saver.save_actionable_only(self.current_batch)
            print(f"\n{Fore.GREEN}✓ Saved actionable emails to: {filepath}{Style.RESET_ALL}")
        
        else:
            print(f"{Fore.RED}Invalid choice{Style.RESET_ALL}")
    
    def _generate_replies(self):
        """Generate replies using LLM"""
        if not self.current_batch:
            print(f"\n{Fore.YELLOW}No emails loaded{Style.RESET_ALL}")
            return
        
        actionable = [e for e in self.current_batch.emails if e.action == Action.REPLY]
        
        if not actionable:
            print(f"\n{Fore.YELLOW}No actionable emails{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.YELLOW}Generating replies with AI for {len(actionable)} emails...{Style.RESET_ALL}\n")
        
        self.current_drafts = self.generator.generate_multiple_replies(
            actionable,
            only_replyable=True
        )
        
        successful = sum(1 for d in self.current_drafts.values() if d.should_reply)
        print(f"\n{Fore.GREEN}✓ AI generated {successful} reply drafts{Style.RESET_ALL}")
    
    def _send_replies(self):
        """Send replies"""
        if not self.current_drafts:
            print(f"\n{Fore.YELLOW}No drafts. Generate first (option 4){Style.RESET_ALL}")
            return
        
        emails_with_drafts = [
            (e, self.current_drafts[e.uid])
            for e in self.current_batch.emails
            if e.uid in self.current_drafts and self.current_drafts[e.uid].should_reply
        ]
        
        if not emails_with_drafts:
            print(f"\n{Fore.YELLOW}No drafts ready{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"REVIEW AI-GENERATED DRAFTS")
        print(f"{'='*80}{Style.RESET_ALL}\n")
        
        approved = set()
        
        for i, (email, draft) in enumerate(emails_with_drafts, 1):
            print(f"\n{Fore.YELLOW}[{i}/{len(emails_with_drafts)}]{Style.RESET_ALL}")
            print(f"To: {email.from_address}")
            print(f"Subject: {draft.subject}")
            print(f"\n{Fore.CYAN}AI Draft:{Style.RESET_ALL}")
            print("-" * 80)
            print(draft.body)
            print("-" * 80)
            
            response = input(f"\n{Fore.GREEN}Send? (y/n/s=skip): {Style.RESET_ALL}").strip().lower()
            
            if response == 'y':
                approved.add(email.uid)
                print(f"{Fore.GREEN}✓ Approved{Style.RESET_ALL}")
            elif response == 's':
                break
        
        if not approved:
            print(f"\n{Fore.YELLOW}Nothing approved{Style.RESET_ALL}")
            return
        
        confirm = input(f"\n{Fore.GREEN}Send {len(approved)} emails? Type 'yes': {Style.RESET_ALL}").strip().lower()
        
        if confirm == 'yes':
            print(f"\n{Fore.YELLOW}Sending...{Style.RESET_ALL}")
            results = self.sender.send_batch(emails_with_drafts, approved)
            
            successful = sum(1 for s, _ in results.values() if s)
            print(f"\n{Fore.GREEN}✓ Sent {successful}/{len(results)}{Style.RESET_ALL}")


def main():
    dry_run = '--dry-run' in sys.argv
    
    try:
        cli = EmailCLI(dry_run=dry_run)
        cli.run()
    except KeyboardInterrupt:
        print("\n\nBye!")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
