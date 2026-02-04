# Email Automation System

An intelligent, LLM-powered email management system that analyzes, prioritizes, and helps you respond to emails efficiently.

## 🎯 Features

- **Smart Analysis**: Uses LLM to understand email importance and required actions
- **Priority Sorting**: Automatically sorts emails by importance (CRITICAL → HIGH → NORMAL → LOW)
- **Reply Generation**: Drafts professional replies using AI
- **Human-in-the-Loop**: Requires explicit approval before sending any email
- **Safety First**: Detects no-reply addresses, validates recipients, rate limits sends
- **Explainable**: LLM provides reasoning for every decision
- **Graceful Degradation**: Works even if LLM fails (falls back to safe defaults)

## 🏗️ Architecture

```
Email Pipeline:
Gmail (IMAP) → Reader → Analyzer → Prioritizer → CLI Interface
                           ↓                          ↓
                    Reply Generator  ←────────  Human Review
                           ↓
                    Gmail (SMTP)
```

### Components

1. **Email Reader** (`core/email_reader.py`): Fetches emails via IMAP
2. **Email Analyzer** (`core/email_analyzer.py`): LLM-based analysis
3. **Reply Generator** (`core/reply_generator.py`): Drafts replies with LLM
4. **Email Sender** (`core/email_sender.py`): Sends approved replies via SMTP
5. **CLI Interface** (`interface/cli.py`): User interaction layer

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **LLM-based (no ML models)** | No training needed, context-aware, explainable |
| **Human approval required** | Safety, compliance, accountability |
| **IMAP/SMTP (not APIs)** | Standard protocols, works with any provider |
| **Modular architecture** | Easy to test, extend, and maintain |
| **Graceful degradation** | System works even if LLM fails |
| **CLI first** | Faster to build, foundation for future UI |

## 📋 Prerequisites

- **Python 3.8+**
- **Gmail account** with 2FA enabled
- **Gmail App Password** (not your regular password)
- **Ollama** with a language model (e.g., llama2)

## 🚀 Installation

### 1. Clone or Download

```bash
cd email_automation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication if not already enabled
3. Go to "App passwords"
4. Create a new app password for "Mail"
5. Save this 16-character password (you'll use it in .env)

### 4. Install and Setup Ollama

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from: https://ollama.ai

# Start Ollama service
ollama serve

# Pull a model (in a new terminal)
ollama pull llama2
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required settings in `.env`:**

```env
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

LLM_MODEL=llama2
LLM_API_URL=http://localhost:11434/api/generate
```

## 💻 Usage

### Basic Usage

```bash
# Start the system
python main.py

# Or with dry-run mode (won't actually send emails)
python main.py --dry-run
```

### Workflow

1. **Fetch and Analyze Emails**
   - Choose option 1 from main menu
   - System fetches recent emails
   - LLM analyzes each email for importance and actionability
   - Results are displayed sorted by importance

2. **Review Emails**
   - Choose option 2 to see prioritized list
   - View detailed information about any email
   - See LLM's analysis reasoning

3. **Generate Reply Drafts**
   - Choose option 3
   - System generates drafts for replyable emails
   - LLM creates professional, context-aware responses

4. **Review and Send**
   - Choose option 4
   - Review each draft
   - Approve/reject individual drafts
   - System sends only approved replies

### Example Session

```
MAIN MENU
1. Fetch and analyze emails
2. Show email list (sorted by importance)
3. Generate reply drafts
4. Review and send replies
5. Show statistics
6. Show settings
q. Quit

Choose an option: 1

Fetching emails...
✓ Fetched 10 emails
Analyzing emails with LLM...
✓ Analysis complete!

Quick Summary:
  CRITICAL: 1
  HIGH: 3
  NORMAL: 4
  LOW: 2
  Replyable: 5
```

## 🔧 Configuration

### Email Settings

```env
# IMAP (for reading)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# SMTP (for sending)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# How many emails to fetch
MAX_EMAILS_TO_FETCH=50
EMAIL_CHECK_FOLDER=INBOX
```

### LLM Settings

```env
# Which model to use
LLM_MODEL=llama2

# Where Ollama is running
LLM_API_URL=http://localhost:11434/api/generate

# Request timeout (seconds)
LLM_TIMEOUT=60
```

### System Settings

```env
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

## 🛡️ Security Considerations

### Credentials

- **Never commit `.env`** to version control
- Use Gmail App Passwords, not your main password
- Rotate app passwords periodically
- Store `.env` securely with proper file permissions:
  ```bash
  chmod 600 .env
  ```

### Email Sending Safety

- ✅ Human approval required for all sends
- ✅ No-reply address detection
- ✅ Rate limiting (2 second minimum between sends)
- ✅ Recipient validation
- ✅ Dry-run mode for testing
- ✅ Comprehensive logging of all operations

### LLM Privacy

- Ollama runs locally (no cloud APIs)
- Email content never leaves your machine
- You control the LLM and its data

## 🧪 Testing

### Dry-Run Mode

Test the system without actually sending emails:

```bash
python main.py --dry-run
```

In dry-run mode:
- ✅ Emails are fetched and analyzed
- ✅ Reply drafts are generated
- ✅ All operations logged
- ❌ No emails are actually sent

### Manual Testing

1. Send yourself a test email
2. Run the system with `--dry-run`
3. Verify analysis and draft generation
4. Remove `--dry-run` flag
5. Send a real reply to yourself

## 📊 Analysis Categories

### Importance Levels

| Level | Description | Examples |
|-------|-------------|----------|
| **CRITICAL** | Urgent, requires immediate attention | Payment failures, security alerts, urgent client issues |
| **HIGH** | Important but not urgent | Meeting requests, stakeholder emails, time-sensitive tasks |
| **NORMAL** | Regular correspondence | Standard work emails, routine requests |
| **LOW** | Can be deferred | Newsletters, notifications, social media updates |

### Recommended Actions

| Action | Description |
|--------|-------------|
| **REPLY** | Should generate and send a response |
| **READ_ONLY** | Just needs to be read and acknowledged |
| **TRACK** | Needs follow-up but no immediate action |
| **IGNORE** | Can be safely ignored or archived |

## 🔍 Troubleshooting

### LLM Connection Failed

**Problem**: "Cannot connect to LLM service"

**Solutions**:
1. Start Ollama: `ollama serve`
2. Pull model: `ollama pull llama2`
3. Check API URL in `.env`
4. Try different port if 11434 is in use

### IMAP Authentication Failed

**Problem**: "IMAP authentication error"

**Solutions**:
1. Verify Gmail App Password (not regular password)
2. Enable 2FA on Google Account
3. Generate new App Password
4. Check email address in `.env`

### SMTP Send Failed

**Problem**: "SMTP authentication failed"

**Solutions**:
1. Same App Password for IMAP and SMTP
2. Check SMTP server and port
3. Ensure "Less secure app access" is NOT needed (App Passwords bypass this)

### Empty Email Bodies

**Problem**: Emails fetched but bodies are empty

**Solutions**:
1. Check internet connection
2. Verify IMAP permissions
3. Try fetching fewer emails
4. Check Gmail storage quota

## 🚀 Future Enhancements

### Planned Features

- [ ] **Web UI**: Browser-based interface
- [ ] **Email Threading**: Better conversation tracking
- [ ] **Custom Filters**: User-defined importance rules
- [ ] **Draft Editing**: Inline editing of generated replies
- [ ] **Scheduled Sending**: Schedule replies for later
- [ ] **Multi-Account**: Support multiple email accounts
- [ ] **Email Templates**: Pre-defined response templates
- [ ] **Attachment Handling**: Process and respond to attachments
- [ ] **Calendar Integration**: Auto-schedule meetings
- [ ] **Learning Mode**: Improve prompts based on user feedback

### Extension Points

The system is designed for easy extension:

1. **Custom LLM Providers**: Implement `LLMClient` interface
2. **Different Email Providers**: Extend `EmailReader` and `EmailSender`
3. **Alternative Interfaces**: Create new interface modules (web, desktop)
4. **Additional Analyzers**: Add rule-based or ML analyzers alongside LLM
5. **Plugin System**: Load custom analysis logic at runtime

## 📝 Code Structure

```
email_automation/
│
├── config/                    # Configuration management
│   ├── settings.py           # Environment variables and validation
│   └── prompts.py            # LLM prompt templates
│
├── core/                      # Core business logic
│   ├── models.py             # Data structures (Email, Analysis, etc.)
│   ├── email_reader.py       # IMAP email fetching
│   ├── email_analyzer.py     # LLM-based analysis
│   ├── reply_generator.py    # LLM-based reply drafting
│   └── email_sender.py       # SMTP email sending
│
├── utils/                     # Utilities
│   ├── llm_client.py         # LLM interaction
│   ├── validators.py         # Input validation
│   └── logger.py             # Logging configuration
│
├── interface/                 # User interfaces
│   └── cli.py                # Command-line interface
│
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Example configuration
└── README.md                 # This file
```

## 🤝 Contributing

Contributions are welcome! This is a modular system designed for easy extension.

### Adding New Features

1. Follow existing code structure
2. Add docstrings explaining "WHY" not just "WHAT"
3. Handle errors gracefully
4. Add logging for important operations
5. Update README with new features

### Code Style

- Clear variable names
- Type hints for functions
- Docstrings for all modules/classes/functions
- Comments explain reasoning, not mechanics

## 📄 License

This is an educational project. Feel free to use and modify as needed.

## ⚠️ Disclaimer

- This system sends real emails. Test thoroughly with `--dry-run` first.
- Always review drafts before sending.
- The LLM may occasionally generate inappropriate content - human review is essential.
- Not responsible for emails sent by this system.

## 💡 Tips

1. **Start Small**: Test with 5-10 emails first
2. **Use Dry-Run**: Always test new configurations with `--dry-run`
3. **Review Drafts**: Never blindly send LLM-generated content
4. **Check Logs**: Logs provide detailed operation history
5. **Tune Prompts**: Modify `config/prompts.py` to improve analysis
6. **Monitor Costs**: While Ollama is free, be mindful of compute resources

## 📞 Support

For issues and questions:
1. Check this README thoroughly
2. Review error logs
3. Test with `--dry-run` mode
4. Verify all prerequisites are installed

---

**Built with** ❤️ **for efficient email management**
