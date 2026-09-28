import threading
import time
from datetime import datetime, timedelta
import logging
from database import get_active_trials, mark_nagged, get_setting
from notifier import dispatch_nag
from scanner import scan_imap

logger = logging.getLogger("NagEngine")

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    if total_seconds <= 0:
        return "NOW (Expired / Charged)"
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    mins = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)

def calculate_nag_parameters(trial_end_str, intensity="relentless"):
    """
    Returns (interval_minutes, urgency, time_left_str, is_due)
    """
    try:
        end_dt = datetime.fromisoformat(trial_end_str.replace(" ", "T"))
    except Exception:
        # Fallback date parse
        try:
            end_dt = datetime.strptime(trial_end_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            end_dt = datetime.now() + timedelta(days=1)
            
    now = datetime.now()
    diff = end_dt - now
    total_seconds = diff.total_seconds()
    time_left_str = format_timedelta(diff)

    # Determine interval based on urgency & intensity
    if total_seconds <= 0:
        # Past due
        interval = 10 if intensity == "relentless" else 30
        urgency = "CRITICAL"
    elif total_seconds < 6 * 3600:
        # Less than 6 hours
        interval = 15 if intensity == "relentless" else 30
        urgency = "CRITICAL"
    elif total_seconds < 24 * 3600:
        # Less than 24 hours
        interval = 60 if intensity == "relentless" else 120
        urgency = "HIGH"
    elif total_seconds < 72 * 3600:
        # Less than 3 days
        interval = 180 if intensity == "relentless" else 360
        urgency = "MEDIUM"
    else:
        # More than 3 days
        interval = 720 if intensity == "relentless" else 1440
        urgency = "NORMAL"

    return interval, urgency, time_left_str

class NagEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                logger.info("Nag Engine started successfully.")

    def stop(self):
        with self._lock:
            self.running = False

    def trigger_immediate_nag(self, trial_id):
        """
        Forces an immediate nag for a specific trial regardless of schedule.
        """
        trials = get_active_trials()
        target = next((t for t in trials if t['id'] == trial_id), None)
        if not target:
            return False
            
        interval, urgency, time_left_str = calculate_nag_parameters(
            target['trial_end_date'],
            target.get('nag_intensity', 'relentless')
        )
        dispatch_nag(
            trial_id=target['id'],
            service_name=target['service_name'],
            time_left_str=time_left_str,
            cost=target.get('cost'),
            cancel_url=target.get('cancel_url'),
            urgency=urgency
        )
        mark_nagged(target['id'])
        return True

    def _check_trials(self):
        active_trials = get_active_trials()
        now = datetime.now()

        for trial in active_trials:
            interval_mins, urgency, time_left_str = calculate_nag_parameters(
                trial['trial_end_date'],
                trial.get('nag_intensity', 'relentless')
            )
            
            should_nag = False
            if not trial['last_nagged_at']:
                should_nag = True
            else:
                try:
                    last_nag = datetime.fromisoformat(trial['last_nagged_at'].replace(" ", "T"))
                    elapsed = (now - last_nag).total_seconds() / 60.0
                    if elapsed >= interval_mins:
                        should_nag = True
                except Exception:
                    should_nag = True

            if should_nag:
                logger.info(f"Nagging user for {trial['service_name']} (Urgency: {urgency}, Left: {time_left_str})")
                dispatch_nag(
                    trial_id=trial['id'],
                    service_name=trial['service_name'],
                    time_left_str=time_left_str,
                    cost=trial.get('cost'),
                    cancel_url=trial.get('cancel_url'),
                    urgency=urgency
                )
                mark_nagged(trial['id'])

    def _run_loop(self):
        last_imap_check = 0
        while self.running:
            try:
                # 1. Check active trials and nag if interval reached
                self._check_trials()

                # 2. Check IMAP periodically if configured
                now_sec = time.time()
                imap_interval = int(get_setting("auto_scan_interval_seconds", "300"))
                if now_sec - last_imap_check >= imap_interval:
                    last_imap_check = now_sec
                    # Non-blocking scan attempt
                    threading.Thread(target=scan_imap, daemon=True).start()

            except Exception as e:
                logger.error(f"Error in nag loop: {e}")

            # Sleep 15 seconds between loop checks
            time.sleep(15)

nag_engine = NagEngine()
