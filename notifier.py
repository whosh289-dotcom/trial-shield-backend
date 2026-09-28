import json
import logging
import queue
from database import log_nag

logger = logging.getLogger("Notifier")

# Global queue for Server-Sent Events (SSE) to the browser
browser_alert_queue = queue.Queue()

def dispatch_nag(trial_id, service_name, time_left_str, cost, cancel_url, urgency="CRITICAL"):
    """
    Dispatches a nag alert exclusively to connected browsers via SSE & Web Push.
    """
    title = f"🛡️ TRIAL SHIELD: {service_name.upper()} RENEWING!"
    
    short_msg = f"{service_name} trial ends in {time_left_str}! Cancel now ({cost or 'Upcoming charge'})"

    # Browser Push Notification via SSE
    browser_alert_queue.put({
        "title": title,
        "body": short_msg,
        "urgency": urgency,
        "url": cancel_url
    })

    log_nag(trial_id, service_name, "Browser Push", short_msg, urgency)

def notify_defused(service_name, cost=""):
    """
    Notifies that the trial has been successfully defused!
    """
    title = f"🛡️ TRIAL DEFUSED: {service_name}"
    msg = f"🎉 Cancellation confirmed for {service_name}! Shield has stopped nagging."
    
    browser_alert_queue.put({
        "title": title,
        "body": msg,
        "urgency": "DEFUSED",
        "url": None
    })
