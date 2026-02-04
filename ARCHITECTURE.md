# Architecture Deep Dive

This document explains the technical architecture, design decisions, and implementation details of the Email Automation System.

## 🎯 Design Principles

### 1. Modularity

**Every component is independent and replaceable.**

```python
# Each module has a clear interface
class EmailReader:
    def connect() -> bool
    def fetch_recent_emails() -> EmailBatch
    def disconnect()

class EmailAnalyzer:
    def analyze_email(email: Email) -> Email
    def analyze_batch(emails: List[Email]) -> List[Email]
```

**Why?**
- Easy to test components in isolation
- Can swap implementations (e.g., different email providers)
- Team can work on different modules simultaneously
- Changes in one module don't break others

### 2. Fail-Safe Design

**System degrades gracefully when components fail.**

```python
def _get_llm_analysis(self, email: Email) -> Analysis:
    try:
        # Try to get LLM analysis
        llm_response = self.llm.generate(prompt)
        return self._parse_response(llm_response)
    except Exception as e:
        logger.error(f"LLM failed: {e}")
        # Return safe fallback instead of crashing
        return Analysis.create_fallback("LLM error")
```

**Fallback behavior:**
- LLM fails → Use NORMAL importance, READ_ONLY action
- IMAP fails → Clear error message, don't proceed
- SMTP fails → Log error, don't mark as sent
- Parsing fails → Safe defaults, warnings logged

### 3. Explainability

**Every decision includes reasoning.**

```python
@dataclass
class Analysis:
    importance: Importance
    replyability: Replyability
    action: Action
    reasoning: str  # WHY was this decision made?
```

**Why?**
- Users understand system behavior
- Debugging is easier
- Can improve prompts based on reasoning quality
- Builds trust in automation

### 4. Safety First

**Multiple layers of protection against mistakes.**

1. **Prevention**: Validate before acting
2. **Detection**: Check for dangerous patterns
3. **Control**: Require human approval
4. **Audit**: Log all operations
5. **Recovery**: Dry-run mode for testing

### 5. Type Safety

**Use Python type hints everywhere.**

```python
def send_reply(self, 
               original_email: Email, 
               reply_draft: ReplyDraft,
               approved: bool = False) -> Tuple[bool, str]:
```

**Benefits:**
- IDE autocomplete and error detection
- Self-documenting code
- Catch errors at development time
- Easier refactoring

## 🏗️ Component Architecture

### Data Flow

```
┌─────────────┐
│    Gmail    │
│   (IMAP)    │
└──────┬──────┘
       │ fetch
       ▼
┌─────────────┐
│Email Reader │──────┐
└─────────────┘      │
                     │ EmailBatch
                     ▼
              ┌─────────────┐
              │   Models    │
              │  (Email,    │
              │  Analysis)  │
              └──────┬──────┘
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
┌─────────────┐            ┌──────────────┐
│  Analyzer   │◄───────────│ LLM Client   │
└──────┬──────┘            └──────────────┘
       │ analyzed emails
       ▼
┌─────────────┐
│     CLI     │
│  Interface  │
└──────┬──────┘
       │ user selects emails to reply to
       ▼
┌─────────────┐
│   Reply     │◄───────────┐
│  Generator  │            │ LLM Client
└──────┬──────┘            │
       │ drafts            │
       ▼                   │
┌─────────────┐            │
│     CLI     │            │
│   Review    │────────────┘
└──────┬──────┘
       │ approved drafts
       ▼
┌─────────────┐
│Email Sender │
│   (SMTP)    │
└──────┬──────┘
       │ send
       ▼
┌─────────────┐
│    Gmail    │
│   (SMTP)    │
└─────────────┘
```

### Core Models

```python
# Immutable data structures
@dataclass
class Email:
    """Represents an email message."""
    uid: str
    from_address: str
    to_address: str
    subject: str
    body: str
    date: datetime
    
    # Analysis results (mutable)
    importance: Importance = Importance.UNKNOWN
    replyability: Replyability = Replyability.UNKNOWN
    action: Action = Action.UNKNOWN
    
    # Generated reply (mutable)
    draft_reply: Optional[str] = None

@dataclass
class Analysis:
    """LLM analysis result."""
    importance: Importance
    replyability: Replyability
    action: Action
    reasoning: str
    confidence: str

@dataclass
class ReplyDraft:
    """Generated reply draft."""
    body: str
    subject: str
    reasoning: str
    should_reply: bool
    warnings: List[str]
```

**Design notes:**
- Email object holds both content AND analysis (keeps related data together)
- Separate Analysis class for clean LLM response parsing
- ReplyDraft includes warnings (safety considerations)
- All classes use dataclasses (automatic __init__, __repr__, etc.)

### Email Reader

**Responsibility**: Fetch emails from Gmail via IMAP

```python
class EmailReader:
    def connect(self) -> bool:
        """Establish IMAP connection."""
        
    def fetch_recent_emails(self, max_count: int) -> EmailBatch:
        """Fetch and parse emails."""
        
    def _fetch_single_email(self, email_id: bytes) -> Email:
        """Parse individual email."""
        
    def _extract_body(self, email_message) -> str:
        """Handle multipart, HTML, attachments."""
```

**Key features:**
- Read-only connection (safer)
- Handles multipart emails
- Strips HTML tags
- Decodes various encodings
- Extracts threading headers

**Error handling:**
- IMAP connection errors → Return False from connect()
- Individual email parsing errors → Skip email, log warning
- Malformed headers → Use safe defaults

### Email Analyzer

**Responsibility**: Analyze emails using LLM

```python
class EmailAnalyzer:
    def analyze_email(self, email: Email) -> Email:
        """Analyze single email, mutate with results."""
        
    def analyze_batch(self, emails: List[Email]) -> List[Email]:
        """Analyze multiple emails with progress tracking."""
        
    def _get_llm_analysis(self, email: Email) -> Analysis:
        """Call LLM and parse response."""
        
    def _parse_to_analysis(self, parsed: dict) -> Analysis:
        """Convert LLM output to Analysis object."""
```

**LLM interaction:**
```python
# Format prompt
prompt = format_analysis_prompt(
    from_addr=email.from_address,
    to_addr=email.to_address,
    subject=email.subject,
    date=email.date,
    body=email.body
)

# Call LLM
response = self.llm.generate(prompt, max_tokens=300)

# Parse structured response
parsed = parse_analysis_response(response)

# Convert to enums
analysis = self._parse_to_analysis(parsed)
```

**Fallback strategy:**
```python
if llm_fails:
    return Analysis(
        importance=Importance.NORMAL,  # Safe default
        replyability=Replyability.UNKNOWN,
        action=Action.READ_ONLY,  # Read but don't auto-reply
        reasoning="LLM analysis unavailable"
    )
```

### Reply Generator

**Responsibility**: Generate draft replies using LLM

```python
class ReplyGenerator:
    def generate_reply(self, email: Email, context: str) -> ReplyDraft:
        """Generate single draft with safety checks."""
        
    def generate_multiple_replies(self, emails: List[Email]) -> dict:
        """Batch generation for efficiency."""
        
    def refine_draft(self, original: str, instructions: str) -> ReplyDraft:
        """Iterative improvement of drafts."""
```

**Safety pipeline:**
```python
# 1. Check if address is no-reply
if email.is_noreply():
    return ReplyDraft.create_noreply()

# 2. Check replyability from analyzer
if email.replyability == Replyability.NO:
    return draft_with_explanation()

# 3. Run safety validation
is_safe, warnings = check_reply_safety(email)
if not is_safe:
    draft.warnings = warnings
    draft.should_reply = False

# 4. Generate with LLM
draft = self._generate_draft_with_llm(email)

# 5. Validate output
is_valid, error = validate_reply_draft(draft.body)
if not is_valid:
    draft.warnings.append(error)
```

### Email Sender

**Responsibility**: Send approved replies via SMTP

```python
class EmailSender:
    def send_reply(self, 
                   email: Email, 
                   draft: ReplyDraft,
                   approved: bool) -> Tuple[bool, str]:
        """Send with explicit approval requirement."""
        
    def send_batch(self, 
                   emails_and_drafts: List[Tuple],
                   approved_uids: Set[str]) -> dict:
        """Batch send with per-email approval."""
```

**Safety checks:**
```python
def _validate_send_request(self, email, draft):
    # 1. Validate recipient email format
    if not validate_email_address(email.from_address):
        return False, "Invalid email"
    
    # 2. Check for no-reply
    if is_noreply_address(email.from_address):
        return False, "No-reply address"
    
    # 3. Validate subject
    if not validate_subject(draft.subject):
        return False, "Invalid subject"
    
    # 4. Check body length
    if len(draft.body) < 10:
        return False, "Body too short"
    
    return True, ""
```

**Rate limiting:**
```python
class EmailSender:
    min_send_interval = 2.0  # seconds
    
    def _check_rate_limit(self) -> bool:
        if self.last_send_time is None:
            return True
        
        elapsed = time.time() - self.last_send_time
        return elapsed >= self.min_send_interval
```

### LLM Client

**Responsibility**: Abstract LLM interaction

```python
class LLMClient:
    def generate(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate text, return None on failure."""
        
    def check_connection(self) -> bool:
        """Pre-flight check before processing."""
```

**Why abstraction?**
- Easy to swap LLM providers
- Centralized error handling
- Can add caching, retry logic
- Isolates Ollama-specific code

**Error handling:**
```python
try:
    response = requests.post(
        self.api_url,
        json=payload,
        timeout=self.timeout
    )
    response.raise_for_status()
    return response.json()['response']
    
except requests.exceptions.Timeout:
    log_error("Timeout")
    return None
    
except requests.exceptions.ConnectionError:
    log_error("Cannot connect - is Ollama running?")
    return None
    
except Exception as e:
    log_error(f"Unexpected: {e}")
    return None
```

## 📝 Prompt Engineering

### Analysis Prompt Structure

```
[System Role] You are an expert email analyst

[Task Description] Analyze the following email

[Email Content]
From: ...
To: ...
Subject: ...
Body: ...

[Instructions]
Evaluate on THREE dimensions:
1. IMPORTANCE (with criteria)
2. REPLYABILITY (with criteria)
3. ACTION (with criteria)

[Output Format]
IMPORTANCE: [value]
REPLYABILITY: [value]
ACTION: [value]
REASONING: [explanation]

[Examples]
Example 1: ...
Example 2: ...
```

**Why this structure?**
- Clear role definition
- Explicit task
- Structured output for parsing
- Examples for few-shot learning
- Reasoning for explainability

### Reply Generation Prompt Structure

```
[System Role] You are a professional email assistant

[Original Email]
From: ...
Subject: ...
Body: ...

[Context]
Additional information...

[Guidelines]
1. Be professional
2. Address main points
3. Keep concise
4. Match tone
...

[Output Format]
SUBJECT: ...
---
BODY:
...
---
REASONING: ...
```

**Design principles:**
- Explicit formatting for parsing
- Guidelines prevent common mistakes
- Context injection for personalization
- Reasoning for debugging

### Prompt Iteration

**How to improve prompts:**

1. **Collect examples of failures**
   ```
   Email: [content]
   Expected: HIGH importance
   Got: NORMAL importance
   Why wrong: [reasoning]
   ```

2. **Add to prompt examples**
   ```python
   ANALYSIS_PROMPT += """
   Example N (High Importance):
   [corrected example]
   """
   ```

3. **Adjust criteria**
   ```python
   # Before: "Important requests"
   # After: "Urgent requests from stakeholders"
   ```

4. **Test on diverse emails**
   - Newsletters
   - Customer support
   - Internal communications
   - Automated notifications

## 🔄 Error Handling Strategy

### Levels of Error Handling

1. **Component Level**: Try-catch in each method
2. **Module Level**: Validate inputs, sanitize outputs
3. **System Level**: Graceful degradation, fallbacks
4. **User Level**: Clear error messages, recovery options

### Example: Complete Error Path

```python
# User action
user_chooses_to_fetch_emails()

# CLI handles UI errors
try:
    reader.connect()
except KeyboardInterrupt:
    show_message("Interrupted by user")
    return

# Reader handles connection errors
def connect(self):
    try:
        self.connection = imaplib.IMAP4_SSL(server, port)
        return True
    except imaplib.IMAP4.error:
        logger.error("Authentication failed")
        return False  # Don't crash, return status
    except Exception as e:
        logger.error(f"Unexpected: {e}")
        return False

# CLI shows appropriate message
if not reader.connect():
    print("Failed to connect. Check credentials in .env")
    return  # Don't proceed
```

### Error Recovery

**Principle**: System should always be in consistent state

```python
# Bad: Partial state
reader.connect()
batch = reader.fetch_emails()  # Could fail here
reader.disconnect()  # Might not run!

# Good: Try-finally ensures cleanup
try:
    if reader.connect():
        batch = reader.fetch_emails()
    else:
        batch = None
finally:
    reader.disconnect()  # Always runs
```

## 🧪 Testing Strategy

### Unit Testing

**Test each component independently:**

```python
def test_email_analyzer_fallback():
    """Analyzer should use fallback when LLM fails."""
    
    # Mock LLM to return None
    mock_llm = Mock()
    mock_llm.generate.return_value = None
    
    analyzer = EmailAnalyzer(llm_client_instance=mock_llm)
    email = create_test_email()
    
    result = analyzer.analyze_email(email)
    
    # Should use fallback, not crash
    assert result.importance == Importance.NORMAL
    assert "fallback" in result.analysis_reasoning.lower()
```

### Integration Testing

**Test component interactions:**

```python
def test_full_pipeline():
    """Test complete email → analysis → reply → send flow."""
    
    # Use real components but mock external services
    reader = EmailReader()
    analyzer = EmailAnalyzer()
    generator = ReplyGenerator()
    sender = EmailSender(dry_run=True)  # Don't actually send
    
    # Mock IMAP to return test email
    with mock_imap():
        batch = reader.fetch_recent_emails()
    
    # Analyze
    analyzer.analyze_batch(batch.emails)
    
    # Generate reply
    draft = generator.generate_reply(batch.emails[0])
    
    # Send (dry-run)
    success, msg = sender.send_reply(
        batch.emails[0], 
        draft, 
        approved=True
    )
    
    assert success
```

### Manual Testing Checklist

- [ ] Fetch emails with valid credentials
- [ ] Handle invalid credentials gracefully
- [ ] Analyze emails with LLM running
- [ ] Analyze emails with LLM stopped
- [ ] Generate replies for various email types
- [ ] Review and approve drafts
- [ ] Send in dry-run mode
- [ ] Send real email to self
- [ ] Handle no-reply addresses
- [ ] Rate limiting works
- [ ] All logging works
- [ ] Configuration validation works

## 📊 Performance Considerations

### Bottlenecks

1. **LLM Calls**: 2-10 seconds per email
   - Solution: Batch processing, progress indicators
   - Future: Parallel processing, caching

2. **IMAP Fetching**: ~0.5 seconds per email
   - Solution: Fetch in batches, limit max count
   - Future: Incremental fetching, caching

3. **SMTP Sending**: ~1-2 seconds per email + rate limit
   - Solution: Batch sending with progress
   - Current limit: 2 seconds between sends

### Optimization Opportunities

```python
# Current: Sequential
for email in emails:
    analysis = analyzer.analyze_email(email)  # 5 sec each
# Total: 5 * N seconds

# Future: Parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(analyzer.analyze_email, email) 
               for email in emails]
    analyses = [f.result() for f in futures]
# Total: ~5 * N/3 seconds
```

**Considerations for parallelization:**
- LLM might have rate limits
- Need to manage concurrent connections
- Error handling becomes more complex
- Current sequential approach is simpler and safer

## 🔮 Extension Points

### Adding New LLM Providers

```python
class OpenAILLMClient(LLMClient):
    """Alternative LLM using OpenAI API."""
    
    def generate(self, prompt: str, max_tokens: int) -> Optional[str]:
        # OpenAI-specific implementation
        pass

# Usage
from custom_llm import OpenAILLMClient
analyzer = EmailAnalyzer(llm_client_instance=OpenAILLMClient())
```

### Adding Email Providers

```python
class OutlookReader(EmailReader):
    """Read from Outlook/Microsoft 365."""
    
    def connect(self) -> bool:
        # Outlook-specific connection
        pass
```

### Adding Interfaces

```python
# interface/web.py
class EmailWebUI:
    """Flask/FastAPI web interface."""
    
    def __init__(self):
        self.reader = EmailReader()
        self.analyzer = EmailAnalyzer()
        # ...
    
    @app.route('/emails')
    def list_emails():
        # Web endpoint
        pass
```

### Adding Analysis Methods

```python
class HybridAnalyzer(EmailAnalyzer):
    """Combine LLM with rule-based analysis."""
    
    def analyze_email(self, email: Email) -> Email:
        # Get LLM analysis
        llm_analysis = super().analyze_email(email)
        
        # Apply rules
        if "urgent" in email.subject.lower():
            email.importance = max(email.importance, Importance.HIGH)
        
        return email
```

## 📚 Lessons Learned

### What Works Well

1. **Modular architecture**: Easy to test and extend
2. **Fail-safe design**: System doesn't crash on errors
3. **Explicit approval**: Users trust the system
4. **Comprehensive logging**: Easy to debug issues
5. **Type hints**: Catch errors early

### What Could Be Improved

1. **LLM prompt caching**: Avoid redundant similar requests
2. **Parallel processing**: Speed up batch operations
3. **Email threading detection**: Better conversation grouping
4. **Draft editing**: Allow inline edits in CLI
5. **Configuration UI**: Easier than editing .env

### Design Trade-offs

| Choice | Benefit | Cost |
|--------|---------|------|
| LLM-based | No training, context-aware | Slower than rules |
| Local LLM | Privacy, no API costs | Setup complexity |
| CLI first | Fast development | Less user-friendly |
| Sequential | Simple, predictable | Slower for batches |
| Explicit approval | Safe, compliant | More user interaction |

---

This architecture balances **simplicity**, **safety**, and **extensibility**. It's production-ready while remaining easy for junior developers to understand and modify.
