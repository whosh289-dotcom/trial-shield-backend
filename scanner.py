import imaplib
import email
from email.header import decode_header
import datetime
import logging
from database import add_trial, defuse_trial, get_setting, get_all_settings
from detector import analyze_email
from notifier import notify_defused

logger = logging.getLogger("Scanner")

def decode_mime_words(s):
    if not s:
        return ""
    decoded = decode_header(s)
    parts = []
    for content, encoding in decoded:
        if isinstance(content, bytes):
            try:
                parts.append(content.decode(encoding or 'utf-8', errors='replace'))
            except Exception:
                parts.append(content.decode('latin1', errors='replace'))
        else:
            parts.append(str(content))
    return "".join(parts)

def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                if content_type in ["text/plain", "text/html"]:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body += payload.decode(charset, errors='replace') + "\n"
                        except Exception:
                            body += payload.decode('latin1', errors='replace') + "\n"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            try:
                body = payload.decode(charset, errors='replace')
            except Exception:
                body = payload.decode('latin1', errors='replace')
    return body

def process_raw_email(from_header, subject, body):
    """
    Parses a single email and updates Trial Shield state accordingly.
    """
    analysis = analyze_email(from_header, subject, body)
    
    if analysis['type'] == 'TRIAL_EXPIRING':
        trial_id = add_trial(
            service_name=analysis['service_name'],
            sender_email=analysis.get('sender_email', ''),
            subject=analysis.get('subject', ''),
            trial_end_date=analysis['trial_end_date'],
            cost=analysis.get('cost'),
            cancel_url=analysis.get('cancel_url'),
            raw_snippet=analysis.get('raw_snippet')
        )
        return {
            "status": "TRIAL_DETECTED",
            "trial_id": trial_id,
            "data": analysis
        }
        
    elif analysis['type'] == 'CANCELLATION_CONFIRMED':
        defused = defuse_trial(analysis['service_name'])
        if defused:
            for item in defused:
                notify_defused(item['service_name'], item['cost'])
            return {
                "status": "TRIAL_DEFUSED",
                "defused_trials": defused,
                "data": analysis
            }
        else:
            return {
                "status": "NO_MATCHING_ACTIVE_TRIAL",
                "service_name": analysis['service_name'],
                "data": analysis
            }

    return {"status": "IRRELEVANT"}

def scan_imap():
    """
    Connects to the configured IMAP server and checks recent messages.
    """
    settings = get_all_settings()
    server = settings.get("imap_server")
    user = settings.get("imap_user")
    password = settings.get("imap_password")
    port = int(settings.get("imap_port", 993))
    use_ssl = settings.get("imap_ssl", "true") == "true"

    if not server or not user or not password:
        return {"error": "IMAP credentials not configured"}

    results = []
    try:
        mail = imaplib.IMAP4_SSL(server, port) if use_ssl else imaplib.IMAP4(server, port)
        mail.login(user, password)
        mail.select("inbox")

        # Search for recent messages in the last 7 days
        since_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
        status, data = mail.search(None, f'(SINCE "{since_date}")')
        
        if status != "OK":
            mail.logout()
            return {"error": "Failed to search inbox"}

        msg_ids = data[0].split()
        # Check up to 50 most recent messages
        for num in reversed(msg_ids[-50:]):
            res, msg_data = mail.fetch(num, '(RFC822)')
            if res != 'OK':
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            from_h = decode_mime_words(msg.get("From", ""))
            subject = decode_mime_words(msg.get("Subject", ""))
            body = get_email_body(msg)

            processed = process_raw_email(from_h, subject, body)
            if processed['status'] in ('TRIAL_DETECTED', 'TRIAL_DEFUSED'):
                results.append(processed)

        mail.logout()
        return {"success": True, "processed_count": len(results), "events": results}

    except Exception as e:
        logger.error(f"IMAP scan failed: {e}")
        return {"error": str(e)}
