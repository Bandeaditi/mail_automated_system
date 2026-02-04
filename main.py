"""
Email Chatbot Launcher

Run this to start the AI chatbot interface
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interface.chatbot import PureAIChatbot


def main():
    """Start the AI chatbot"""
    
    dry_run = '--dry-run' in sys.argv or '--test' in sys.argv
    
    try:
        chatbot = PureAIChatbot(dry_run=dry_run)
        chatbot.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
