import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import logging
import time

from database import (
    get_active_trials, get_all_trials, defuse_trial,
    get_all_settings, set_setting, get_recent_logs,
    delete_trial, add_trial
)
from scanner import process_raw_email, scan_imap
from nag_engine import nag_engine, calculate_nag_parameters
from notifier import browser_alert_queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Server")

PORT = 5055
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class TrialShieldHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/trials":
            all_trials = get_all_trials()
            # Enrich trials with time_left & urgency
            for t in all_trials:
                if t['status'] == 'ACTIVE':
                    interval, urgency, time_left = calculate_nag_parameters(t['trial_end_date'], t.get('nag_intensity', 'relentless'))
                    t['urgency'] = urgency
                    t['time_left_str'] = time_left
                    t['nag_interval_mins'] = interval
            self._send_json({"trials": all_trials})
            return

        elif path == "/api/logs":
            logs = get_recent_logs(50)
            self._send_json({"logs": logs})
            return

        elif path == "/api/settings":
            settings = get_all_settings()
            # Mask sensitive passwords in UI display
            if settings.get("imap_password"):
                settings["has_imap_password"] = True
                settings["imap_password"] = "••••••••"
            else:
                settings["has_imap_password"] = False
            self._send_json({"settings": settings})
            return
            
        elif path == "/api/auth/google":
            if not os.path.exists("client_secret.json"):
                # Serve an instruction page
                html = """
                <html>
                <body style="font-family:sans-serif; padding:40px; background:#0f172a; color:white; line-height:1.6;">
                    <h2>⚠️ Google OAuth Not Configured Yet</h2>
                    <p>To make "Sign in with Google" actually work, you need to tell Google about your app!</p>
                    <ol>
                        <li>Go to the <a href="https://console.cloud.google.com/" style="color:#38bdf8;">Google Cloud Console</a>.</li>
                        <li>Create a New Project.</li>
                        <li>Go to <b>APIs & Services > Credentials</b>.</li>
                        <li>Click <b>Create Credentials > OAuth client ID</b>.</li>
                        <li>Set Application type to <b>Web application</b>.</li>
                        <li>Add Authorized redirect URI: <code>http://localhost:5055/api/auth/google/callback</code></li>
                        <li>Click Download JSON, rename it to <b>client_secret.json</b>, and place it in this folder.</li>
                        <li>Restart the server.</li>
                    </ol>
                    <p><i>(Or, you can use the legacy App Password method if you prefer not to use OAuth!)</i></p>
                    <button onclick="window.history.back()" style="padding:10px 20px; background:#22c55e; border:none; border-radius:5px; color:white; cursor:pointer;">Go Back</button>
                </body>
                </html>
                """
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                return

            try:
                import google_auth_oauthlib.flow
                flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                    'client_secret.json',
                    scopes=['https://www.googleapis.com/auth/gmail.readonly']
                )
                flow.redirect_uri = 'http://localhost:5055/api/auth/google/callback'
                authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
                self.send_response(302)
                self.send_header("Location", authorization_url)
                self.end_headers()
            except ImportError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Please run: pip3 install google-auth-oauthlib")
            return

        elif path == "/api/auth/google/callback":
            try:
                import google_auth_oauthlib.flow
                flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                    'client_secret.json',
                    scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                    state=urllib.parse.parse_qs(parsed.query).get('state', [''])[0]
                )
                flow.redirect_uri = 'http://localhost:5055/api/auth/google/callback'
                # fetch token
                url = self.path
                flow.fetch_token(authorization_response="http://localhost:5055" + url)
                credentials = flow.credentials
                # Save to database
                set_setting('google_oauth_token', credentials.token)
                set_setting('google_oauth_refresh', credentials.refresh_token)
                
                self.send_response(302)
                self.send_header("Location", "/?google_auth_success=true")
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"OAuth Error: {str(e)}".encode('utf-8'))
            return

        elif path == "/api/stream":
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            try:
                while True:
                    while not browser_alert_queue.empty():
                        msg = browser_alert_queue.get()
                        data = json.dumps(msg)
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    time.sleep(1)
            except Exception as e:
                pass # Client disconnected
            return

        # Serve static files or fallback to index.html
        if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/simulate-email":
            from_h = payload.get("from", "")
            subject = payload.get("subject", "")
            body = payload.get("body", "")
            result = process_raw_email(from_h, subject, body)
            self._send_json(result)
            return

        elif path == "/api/trials":
            service_name = payload.get("service_name")
            trial_end_date = payload.get("trial_end_date")
            cost = payload.get("cost", "Unknown")
            cancel_url = payload.get("cancel_url", "")
            
            if not service_name or not trial_end_date:
                self._send_json({"error": "service_name and trial_end_date are required"}, status=400)
                return
                
            trial_id = add_trial(
                service_name=service_name,
                sender_email="Manual Entry",
                subject="Manual Entry",
                trial_end_date=trial_end_date,
                cost=cost,
                cancel_url=cancel_url,
                raw_snippet="Added manually via frontend"
            )
            self._send_json({"success": True, "trial_id": trial_id})
            return

        elif path == "/api/trials/nag":
            trial_id = payload.get("trial_id")
            success = nag_engine.trigger_immediate_nag(trial_id)
            self._send_json({"success": success})
            return

        elif path == "/api/trials/defuse":
            service_name = payload.get("service_name") or str(payload.get("trial_id"))
            defused = defuse_trial(service_name)
            self._send_json({"success": True, "defused": defused})
            return

        elif path == "/api/settings":
            for k, v in payload.items():
                # Don't overwrite password if masked
                if k == "imap_password" and v == "••••••••":
                    continue
                if k != "has_imap_password":
                    set_setting(k, str(v))
            self._send_json({"success": True})
            return

        elif path == "/api/test-notification":
            from notifier import browser_alert_queue
            browser_alert_queue.put({
                "title": "🛡️ Trial Shield Active",
                "body": "Browser alert test successful! Nagging watchdog is standing by.",
                "urgency": "NORMAL",
                "url": None
            })
            self._send_json({"success": True})
            return

        elif path == "/api/scan-imap":
            result = scan_imap()
            self._send_json(result)
            return
            
        elif path == "/api/audit/transactions":
            from auditor import detect_recurring_charges
            try:
                transactions = payload.get("transactions", [])
                detected = detect_recurring_charges(transactions)
                self._send_json({"detected": detected})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self._send_json({"error": "Not Found"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/trials/"):
            trial_id = int(path.split("/")[-1])
            delete_trial(trial_id)
            self._send_json({"success": True})
            return
        self._send_json({"error": "Not Found"}, status=404)

def run_server():
    nag_engine.start()
    ThreadingSimpleServer.allow_reuse_address = True
    with ThreadingSimpleServer(("", PORT), TrialShieldHandler) as httpd:
        print(f"🛡️  Trial Shield is running at: http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            nag_engine.stop()
            print("\nShutting down Trial Shield...")

if __name__ == "__main__":
    run_server()
