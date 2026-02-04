"""
LLM Prompt Templates for Email Analysis and Reply Generation.

WHY SEPARATE FILE FOR PROMPTS?
- Prompt engineering is iterative - keeping prompts in one place makes tuning easier
- Non-technical users can modify prompts without touching code
- Version control shows prompt changes clearly
- Easy A/B testing of different prompt strategies
"""


# ==============================================================================
# EMAIL ANALYSIS PROMPT - IMPROVED WITH BETTER URGENCY DETECTION
# ==============================================================================

ANALYSIS_PROMPT = """You are an expert email analyst helping a busy professional prioritize their inbox.

Analyze the following email and provide a structured assessment.

EMAIL DETAILS:
---
From: {from_address}
To: {to_address}
Subject: {subject}
Date: {date}
Body:
{body}
---

ANALYSIS TASK:
Evaluate this email on THREE dimensions:

1. IMPORTANCE (Choose ONE):

   CRITICAL - Use for emails with ANY of these:
   - Contains words: "urgent", "asap", "immediately", "emergency", "critical"
   - Requests documents or information needed TODAY or within 24 hours
   - Payment issues, account problems, security alerts
   - System outages, critical bugs, service disruptions
   - Angry customers, escalated issues, complaints
   - Legal matters, compliance issues
   - Boss/executive asking for something
   - Deadline mentioned within 24 hours
   
   HIGH - Use for emails with ANY of these:
   - Requests documents or information within 2-3 days
   - Meeting requests or schedule confirmations
   - Important project updates requiring input
   - Client/customer requests (non-urgent)
   - Action items with deadlines this week
   - Questions that need answers soon
   - Follow-ups on pending matters
   - Stakeholder communications
   
   NORMAL - Use for:
   - Regular work correspondence
   - FYI updates that don't require action
   - Team announcements
   - Status reports
   - Routine questions
   - General information sharing
   
   LOW - Use for:
   - Newsletters, marketing emails
   - Social media notifications
   - Automated reports
   - Promotional content
   - Non-work related emails

   IMPORTANT RULES:
   - If email contains "urgent", "asap", "immediately" → Always CRITICAL
   - If email requests documents/files/information → At least HIGH
   - If email asks questions needing answers → At least HIGH
   - If email has a deadline → Match importance to deadline urgency
   - When in doubt between two levels, choose the HIGHER importance

2. REPLYABILITY (Choose ONE):
   
   YES - Email expects or would benefit from a response:
   - Asks questions
   - Requests information or documents
   - Needs confirmation or acknowledgment
   - Requires a decision or input
   - Has action items for you
   
   NO - Email doesn't need a response:
   - From no-reply addresses
   - Newsletters, marketing, notifications
   - FYI-only emails with no questions
   - Automated system emails

3. ACTION (Choose ONE):
   
   REPLY - Should draft a response:
   - Email asks questions
   - Requests information or documents
   - Needs confirmation
   - Requires your input or decision
   
   READ_ONLY - Just needs to be read:
   - FYI emails with useful information
   - Updates that don't require response
   - Information to be aware of
   
   TRACK - Needs follow-up but no immediate action:
   - Waiting for someone else
   - Future deadline (>3 days)
   - Needs monitoring
   
   IGNORE - Can be safely ignored:
   - Marketing, spam
   - Irrelevant automated emails
   - Social media notifications

RESPONSE FORMAT:
You MUST respond in EXACTLY this format (no other text):

IMPORTANCE: [CRITICAL/HIGH/NORMAL/LOW]
REPLYABILITY: [YES/NO]
ACTION: [REPLY/READ_ONLY/TRACK/IGNORE]
REASONING: [One sentence explaining your assessment, mentioning key factors like urgency words, requests, or deadlines]

EXAMPLES:

Example 1 (Document Request - Urgent):
Email: "Hi, I need the Q4 report urgently for the board meeting tomorrow. Can you send it ASAP?"
Response:
IMPORTANCE: CRITICAL
REPLYABILITY: YES
ACTION: REPLY
REASONING: Contains "urgent" and "ASAP" with document request needed for tomorrow's meeting.

Example 2 (Document Request - Non-urgent):
Email: "Hey, when you get a chance, could you send me last month's sales figures? No rush."
Response:
IMPORTANCE: HIGH
REPLYABILITY: YES
ACTION: REPLY
REASONING: Requests information/documents but no immediate deadline, still needs response.

Example 3 (Question Needing Answer):
Email: "Quick question - what time is the client call on Friday?"
Response:
IMPORTANCE: HIGH
REPLYABILITY: YES
ACTION: REPLY
REASONING: Direct question requiring answer for upcoming meeting coordination.

Example 4 (Urgent Problem):
Email: "URGENT: Customer is reporting they cannot access their account and losing money."
Response:
IMPORTANCE: CRITICAL
REPLYABILITY: YES
ACTION: REPLY
REASONING: Marked urgent, customer issue affecting service and causing financial impact.

Example 5 (Newsletter):
Email: "Weekly Newsletter - Top 10 Marketing Tips"
Response:
IMPORTANCE: LOW
REPLYABILITY: NO
ACTION: IGNORE
REASONING: Marketing newsletter with no action required.

Example 6 (Deadline Tomorrow):
Email: "Reminder: Your presentation is due tomorrow for the stakeholder meeting."
Response:
IMPORTANCE: CRITICAL
REPLYABILITY: NO
ACTION: READ_ONLY
REASONING: Deadline within 24 hours requires immediate action but email is just a reminder.

Example 7 (Request with This Week Deadline):
Email: "Can you review this proposal by Friday? Need your feedback before we submit."
Response:
IMPORTANCE: HIGH
REPLYABILITY: YES
ACTION: REPLY
REASONING: Requests review/feedback with deadline this week, needs confirmation.

Example 8 (Boss Request):
Email from boss: "Please prepare the budget analysis when you have time."
Response:
IMPORTANCE: HIGH
REPLYABILITY: YES
ACTION: REPLY
REASONING: Request from supervisor requires acknowledgment even without specific deadline.

Now analyze the email above. Pay special attention to:
- Urgency indicators (urgent, asap, immediately, emergency)
- Document/information requests
- Questions that need answers
- Deadlines mentioned
- Who the sender is (boss, client, team member)"""


# ==============================================================================
# REPLY GENERATION PROMPT - IMPROVED
# ==============================================================================

REPLY_GENERATION_PROMPT = """You are a professional email writing assistant.

Generate a polite, professional reply to the following email.

ORIGINAL EMAIL:
---
From: {from_address}
To: {to_address}
Subject: {subject}
Body:
{body}
---

CONTEXT:
{context}

REPLY GUIDELINES:

1. ACKNOWLEDGE URGENCY:
   - If email says "urgent/asap/immediately" → Start with "I understand the urgency..."
   - If requesting documents → Acknowledge the request clearly

2. BE SPECIFIC:
   - If they need documents → State which documents and when you'll send them
   - If they ask questions → Answer each question directly
   - If they need action → Confirm what you'll do and by when

3. PROVIDE TIMELINE:
   - If urgent → "I'll get this to you within [X hours]"
   - If high priority → "I'll have this ready by [specific date/time]"
   - If need more time → "I'll need until [date] to complete this properly"

4. PROFESSIONAL TONE:
   - Be warm but professional
   - Show you understand their needs
   - Be helpful and solution-oriented
   - Keep it concise (2-4 paragraphs max)

5. CLEAR NEXT STEPS:
   - State exactly what you'll do
   - Give specific timeframes
   - Offer alternatives if needed

6. IF UNSURE:
   - Don't make commitments you can't keep
   - Use: "Let me check and get back to you by [time]"
   - Or: "I'll look into this and update you soon"

RESPONSE FORMAT:
You MUST respond in EXACTLY this format:

SUBJECT: [Reply subject line - typically "Re: {original_subject}"]
---
BODY:
[The reply email body - be specific about what you'll do and when]
---
REASONING: [One sentence explaining your approach to the reply]

EXAMPLES:

Example 1 (Urgent Document Request):
Original: "Hi, I need the Q4 report urgently for the board meeting tomorrow. Can you send it ASAP?"

SUBJECT: Re: Q4 Report Needed Urgently
---
BODY:
Hi,

I understand the urgency and will get you the Q4 report right away. I'm finalizing the last section now and will send it to you within the next 2 hours.

Is there any specific format you need it in for the board meeting? Let me know if you need anything else.

Best regards
---
REASONING: Acknowledged urgency, gave specific timeline (2 hours), offered to help with formatting.

Example 2 (Document Request - Non-urgent):
Original: "Hey, when you get a chance, could you send me last month's sales figures? No rush."

SUBJECT: Re: Last Month's Sales Figures
---
BODY:
Hi,

Absolutely! I'll pull together last month's sales figures and send them over by end of day tomorrow.

If you need them sooner or in any specific format, just let me know.

Best regards
---
REASONING: Confirmed request, provided clear timeline, offered flexibility.

Example 3 (Multiple Questions):
Original: "Quick questions: 1) What time is the client call Friday? 2) Do we need to prepare slides? 3) Who else is joining?"

SUBJECT: Re: Client Call Details
---
BODY:
Hi,

Here are the answers to your questions:

1) The client call is Friday at 2 PM EST
2) Yes, please prepare 5-10 slides covering our Q1 results
3) Sarah and Mike from the sales team will also be joining

I'll send out a calendar invite with the call link shortly. Let me know if you need anything else!

Best regards
---
REASONING: Answered each question directly and clearly, offered to send additional information.

Example 4 (Need More Time):
Original: "Can you complete the analysis by end of today? Need it for tomorrow's meeting."

SUBJECT: Re: Analysis Timeline
---
BODY:
Hi,

Thank you for reaching out. To ensure the analysis is thorough and accurate, I'll need until tomorrow morning (9 AM) to complete it properly. This will still give you time to review before the meeting.

If this timeline doesn't work, I can provide a preliminary version today with a full analysis tomorrow. Let me know which you prefer.

Best regards
---
REASONING: Provided realistic timeline, explained reasoning, offered alternative solution.

Now generate a professional reply to the email above. Remember to:
- Acknowledge any urgency
- Be specific about what you'll do
- Provide clear timelines
- Answer all questions directly"""


# ==============================================================================
# PROMPT HELPER FUNCTIONS
# ==============================================================================

def format_analysis_prompt(from_addr: str, to_addr: str, subject: str, 
                          date: str, body: str) -> str:
    """
    Format the analysis prompt with email details.
    
    WHY FUNCTION? Keeps prompts DRY and allows validation of inputs.
    """
    # Truncate body if too long (LLMs have context limits)
    max_body_length = 2000
    if len(body) > max_body_length:
        body = body[:max_body_length] + "\n\n[... email truncated for length ...]"
    
    return ANALYSIS_PROMPT.format(
        from_address=from_addr,
        to_address=to_addr,
        subject=subject,
        date=date,
        body=body
    )


def format_reply_prompt(from_addr: str, to_addr: str, subject: str, 
                       body: str, context: str = "") -> str:
    """
    Format the reply generation prompt with email details.
    
    Args:
        context: Additional context about the recipient or situation
    """
    max_body_length = 2000
    if len(body) > max_body_length:
        body = body[:max_body_length] + "\n\n[... email truncated for length ...]"
    
    if not context:
        context = "No additional context provided."
    
    # Keep original subject for reply
    original_subject = subject.replace("Re: ", "").replace("RE: ", "")
    
    return REPLY_GENERATION_PROMPT.format(
        from_address=from_addr,
        to_address=to_addr,
        subject=subject,
        body=body,
        context=context,
        original_subject=original_subject
    )


# ==============================================================================
# RESPONSE PARSING HELPERS
# ==============================================================================

def parse_analysis_response(response: str) -> dict:
    """
    Parse the structured LLM response for email analysis.
    
    Returns:
        Dict with keys: importance, replyability, action, reasoning
        Returns None values if parsing fails (caller handles fallback)
    """
    result = {
        'importance': None,
        'replyability': None,
        'action': None,
        'reasoning': None
    }
    
    lines = response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('IMPORTANCE:'):
            result['importance'] = line.split(':', 1)[1].strip()
        elif line.startswith('REPLYABILITY:'):
            result['replyability'] = line.split(':', 1)[1].strip()
        elif line.startswith('ACTION:'):
            result['action'] = line.split(':', 1)[1].strip()
        elif line.startswith('REASONING:'):
            result['reasoning'] = line.split(':', 1)[1].strip()
    
    return result


def parse_reply_response(response: str) -> dict:
    """
    Parse the structured LLM response for reply generation.
    
    Returns:
        Dict with keys: subject, body, reasoning
        Returns None values if parsing fails
    """
    result = {
        'subject': None,
        'body': None,
        'reasoning': None
    }
    
    # Split on the separator
    parts = response.split('---')
    
    for i, part in enumerate(parts):
        part = part.strip()
        
        if part.startswith('SUBJECT:'):
            result['subject'] = part.split(':', 1)[1].strip()
        elif part.startswith('BODY:'):
            result['body'] = part.split(':', 1)[1].strip()
        elif part.startswith('REASONING:'):
            result['reasoning'] = part.split(':', 1)[1].strip()
        elif 'BODY' not in part and i > 0:  # Sometimes body is after ---
            if result['body'] is None and len(part) > 50:  # Reasonable body length
                result['body'] = part
    
    return result
