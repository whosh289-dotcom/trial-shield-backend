import re
import datetime
from email.utils import parseaddr
from urllib.parse import urlparse

# Keywords indicating a trial is about to end or an upcoming charge
TRIAL_EXPIRY_KEYWORDS = [
    r"trial\s+(?:is\s+)?(?:about\s+to\s+)?end(?:ing|s)?",
    r"trial\s+(?:will\s+)?expire[s]?",
    r"free\s+trial\s+(?:is\s+)?ending",
    r"free\s+trial\s+expires",
    r"end\s+of\s+(?:your\s+)?(?:free\s+)?trial",
    r"trial\s+period\s+is\s+(?:almost\s+)?over",
    r"upcoming\s+(?:subscription\s+)?(?:charge|renewal|payment|bill)",
    r"your\s+subscription\s+will\s+(?:automatically\s+)?renew",
    r"you\s+will\s+be\s+charged",
    r"first\s+charge\s+(?:will\s+be|on)",
    r"auto-renew(?:al)?\s+(?:is\s+scheduled|notice)",
    r"membership\s+renews\s+on",
    r"days\s+left\s+in\s+your\s+(?:free\s+)?trial"
]

# Keywords indicating the user successfully cancelled
CANCELLATION_KEYWORDS = [
    r"subscription\s+(?:has\s+been\s+)?cancel(?:l)?ed",
    r"cancellation\s+confirm(?:ed|ation)",
    r"confirm(?:ing)?\s+your\s+cancellation",
    r"we('re| are)\s+sorry\s+to\s+see\s+you\s+go",
    r"we('re| are)\s+sorry\s+you('re| are)\s+leaving",
    r"your\s+(?:free\s+)?trial\s+has\s+been\s+cancel(?:l)?ed",
    r"auto-renew(?:al)?\s+(?:has\s+been\s+)?(?:turned\s+off|cancel(?:l)?ed)",
    r"membership\s+cancel(?:l)?ed",
    r"account\s+cancel(?:l)?ed",
    r"successful\s+cancellation",
    r"you\s+have\s+successfully\s+cancel(?:l)?ed"
]

MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def extract_service_name(from_header, subject="", body=""):
    """
    Extracts the clean brand / service name from sender or subject.
    e.g. 'Netflix <info@mailer.netflix.com>' -> 'Netflix'
         'Adobe Billing <billing@adobe.com>' -> 'Adobe'
    """
    name, email_addr = parseaddr(from_header or "")
    
    # 1. Clean display name
    clean_name = re.sub(r'(support|billing|notifications?|mailer|team|account|info|no-?reply|customer\s+service|services?|auto)', '', name, flags=re.I).strip()
    if clean_name and len(clean_name) > 2:
        return clean_name
        
    # 2. Extract from email domain
    if email_addr and '@' in email_addr:
        domain = email_addr.split('@')[1]
        parts = domain.split('.')
        if len(parts) >= 2:
            # e.g. mailer.netflix.com -> netflix
            brand = parts[-2]
            if brand not in ('gmail', 'yahoo', 'outlook', 'hotmail', 'protonmail', 'icloud', 'mail'):
                return brand.capitalize()
                
    # 3. Look in subject line (e.g. "Your Spotify Premium trial")
    subject_match = re.search(r'Your\s+([A-Za-z0-9\+\s]+?)\s+(?:free\s+trial|subscription|membership|account)', subject, re.I)
    if subject_match:
        s_name = subject_match.group(1).strip()
        if len(s_name) > 2 and len(s_name) < 25:
            return s_name

    return name or "Subscription Service"

def extract_cost(text):
    """
    Finds cost mentioned in text (e.g., $19.99, £9.99, €24.00, ₹699, $9.99/month)
    """
    patterns = [
        r'([$€£₹]\s*\d+(?:\.\d{2})?(?:\s*\/\s*(?:month|mo|year|yr|week))?)',
        r'(\d+(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|CAD|AUD)(?:\s*\/\s*(?:month|mo|year|yr))?)',
        r'(?:charge|billed|renewed\s+for|cost)\s*(?:of)?\s*([$€£₹]?\s*\d+(?:\.\d{2})?)'
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            val = m.group(1).strip()
            if any(char.isdigit() for char in val):
                return val
    return None

def extract_cancel_url(text):
    """
    Finds direct cancellation or account management links.
    """
    urls = re.findall(r'https?://[^\s<>"\')]+', text)
    for url in urls:
        low = url.lower()
        if any(term in low for term in ['cancel', 'manage', 'subscription', 'billing', 'account', 'membership', 'unsubscribe']):
            # Filter out generic tracking or image urls
            if not any(ext in low for ext in ['.png', '.jpg', '.gif', '.css', '.js']):
                return url
    return None

def extract_date(text):
    """
    Attempts to parse date of expiry from text.
    Handles 'September 30, 2026', 'on Sep 28', 'in 3 days', 'tomorrow', '2026-09-30'.
    """
    now = datetime.datetime.now()
    
    # Check 'in X days'
    in_days_match = re.search(r'in\s+(\d+)\s+days?', text, re.I)
    if in_days_match:
        days = int(in_days_match.group(1))
        target = now + datetime.timedelta(days=days)
        return target.strftime("%Y-%m-%d 23:59:59")
        
    if re.search(r'\btomorrow\b', text, re.I):
        target = now + datetime.timedelta(days=1)
        return target.strftime("%Y-%m-%d 23:59:59")

    if re.search(r'\btoday\b', text, re.I):
        target = now + datetime.timedelta(hours=6)
        return target.strftime("%Y-%m-%d %H:%M:%S")

    # Check ISO format YYYY-MM-DD
    iso_match = re.search(r'\b(20\d\d)[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b', text)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        return f"{y:04d}-{m:02d}-{d:02d} 23:59:59"

    # Check "September 30, 2026" or "Sep 30" or "30 Sep 2026"
    month_regex = r'(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)'
    date_match = re.search(rf'\b({month_regex})\s+([0-3]?\d)(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b', text, re.I)
    if date_match:
        m_str = date_match.group(1).lower()
        d_str = date_match.group(2)
        y_str = date_match.group(3) or str(now.year)
        m_num = MONTHS.get(m_str, now.month)
        d_num = int(d_str)
        y_num = int(y_str)
        # If the date appears to be in the past this year, it might be next year
        try:
            parsed = datetime.datetime(y_num, m_num, d_num, 23, 59, 59)
            if parsed < now and not date_match.group(3):
                parsed = datetime.datetime(y_num + 1, m_num, d_num, 23, 59, 59)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Default fallback: 3 days from now
    fallback = now + datetime.timedelta(days=3)
    return fallback.strftime("%Y-%m-%d 23:59:59")

def analyze_email(from_header, subject, body):
    """
    Analyzes an email to determine if it is:
    - 'TRIAL_EXPIRING': A subscription trial warning or upcoming charge notice
    - 'CANCELLATION_CONFIRMED': Confirmation that a subscription was canceled
    - 'IRRELEVANT': Neither
    """
    full_text = f"{subject}\n{body}"
    
    # 1. Check for cancellation confirmation
    is_cancellation = False
    for pat in CANCELLATION_KEYWORDS:
        if re.search(pat, full_text, re.I):
            is_cancellation = True
            break
            
    if is_cancellation:
        service = extract_service_name(from_header, subject, body)
        return {
            "type": "CANCELLATION_CONFIRMED",
            "service_name": service,
            "sender_email": parseaddr(from_header)[1],
            "raw_snippet": full_text[:400]
        }
        
    # 2. Check for trial expiration / upcoming renewal
    is_trial_ending = False
    for pat in TRIAL_EXPIRY_KEYWORDS:
        if re.search(pat, full_text, re.I):
            is_trial_ending = True
            break
            
    if is_trial_ending:
        service = extract_service_name(from_header, subject, body)
        end_date = extract_date(full_text)
        cost = extract_cost(full_text)
        cancel_url = extract_cancel_url(full_text)
        
        return {
            "type": "TRIAL_EXPIRING",
            "service_name": service,
            "sender_email": parseaddr(from_header)[1],
            "subject": subject,
            "trial_end_date": end_date,
            "cost": cost or "Unknown",
            "cancel_url": cancel_url,
            "raw_snippet": full_text[:400]
        }

    return {"type": "IRRELEVANT"}
