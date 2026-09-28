import unittest
import os
import tempfile
import json
import io
import threading
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

import database
import detector
import scanner
import nag_engine
import notifier
import auditor
import server

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        database.DB_PATH = self.temp_db.name
        database.init_db()

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)

    def test_settings(self):
        database.set_setting("test_key", "test_val")
        self.assertEqual(database.get_setting("test_key"), "test_val")
        settings = database.get_all_settings()
        self.assertIn("test_key", settings)
        self.assertEqual(settings["test_key"], "test_val")

    def test_add_and_get_trial(self):
        end_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        trial_id = database.add_trial(
            service_name="Netflix",
            sender_email="billing@netflix.com",
            subject="Trial Ending Soon",
            trial_end_date=end_date,
            cost="$15.99/mo",
            cancel_url="https://netflix.com/cancel"
        )
        self.assertIsNotNone(trial_id)

        active = database.get_active_trials()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["service_name"], "Netflix")
        self.assertEqual(active[0]["status"], "ACTIVE")

        # Update existing trial
        new_end_date = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
        updated_id = database.add_trial(
            service_name="netflix",
            sender_email="billing@netflix.com",
            subject="Updated Trial",
            trial_end_date=new_end_date,
            cost="$19.99/mo"
        )
        self.assertEqual(trial_id, updated_id)
        active_after = database.get_active_trials()
        self.assertEqual(len(active_after), 1)
        self.assertEqual(active_after[0]["cost"], "$19.99/mo")

    def test_defuse_trial(self):
        end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        database.add_trial(
            service_name="Spotify",
            sender_email="support@spotify.com",
            subject="Trial notice",
            trial_end_date=end_date,
            cost="$9.99"
        )
        active = database.get_active_trials()
        self.assertEqual(len(active), 1)

        defused = database.defuse_trial("Spotify")
        self.assertEqual(len(defused), 1)
        self.assertEqual(defused[0]["service_name"], "Spotify")

        active_after = database.get_active_trials()
        self.assertEqual(len(active_after), 0)

        all_trials = database.get_all_trials()
        self.assertEqual(len(all_trials), 1)
        self.assertEqual(all_trials[0]["status"], "CANCELLED")

    def test_nag_logging(self):
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        trial_id = database.add_trial("Adobe", "billing@adobe.com", "Sub", end_date)
        database.mark_nagged(trial_id)
        active = database.get_active_trials()
        self.assertEqual(active[0]["nag_count"], 1)
        self.assertIsNotNone(active[0]["last_nagged_at"])

        database.log_nag(trial_id, "Adobe", "Browser Push", "Test message", "HIGH")
        logs = database.get_recent_logs(10)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["service_name"], "Adobe")
        self.assertEqual(logs[0]["urgency"], "HIGH")

    def test_delete_trial(self):
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        trial_id = database.add_trial("Hulu", "billing@hulu.com", "Sub", end_date)
        database.delete_trial(trial_id)
        self.assertEqual(len(database.get_all_trials()), 0)


class TestDetector(unittest.TestCase):
    def test_extract_service_name(self):
        name = detector.extract_service_name("Adobe Billing <billing@adobe.com>", "Your trial is ending")
        self.assertEqual(name, "Adobe")

        name2 = detector.extract_service_name("Netflix <info@mailer.netflix.com>", "Upcoming charge")
        self.assertEqual(name2, "Netflix")

    def test_extract_cost(self):
        cost1 = detector.extract_cost("You will be charged $54.99/mo starting tomorrow.")
        self.assertIn("54.99", cost1)

        cost2 = detector.extract_cost("Subscription fee of £9.99 per month")
        self.assertIn("9.99", cost2)

    def test_extract_cancel_url(self):
        text = "Visit https://account.adobe.com/plans/cancel to cancel your membership."
        url = detector.extract_cancel_url(text)
        self.assertEqual(url, "https://account.adobe.com/plans/cancel")

    def test_analyze_email_expiring(self):
        email_from = "Adobe CC <billing@adobe.com>"
        subject = "Action Required: Your Adobe Creative Cloud trial is ending"
        body = "Your free trial ends tomorrow. You will be charged $54.99/mo unless you cancel at https://account.adobe.com/cancel."
        result = detector.analyze_email(email_from, subject, body)
        self.assertEqual(result["type"], "TRIAL_EXPIRING")
        self.assertEqual(result["service_name"], "Adobe CC")
        self.assertIn("54.99", result["cost"])

    def test_analyze_email_cancellation(self):
        email_from = "Netflix Support <support@netflix.com>"
        subject = "Confirmation: Your subscription has been canceled"
        body = "We're sorry to see you go! Your Netflix subscription has been canceled."
        result = detector.analyze_email(email_from, subject, body)
        self.assertEqual(result["type"], "CANCELLATION_CONFIRMED")
        self.assertEqual(result["service_name"], "Netflix")

    def test_analyze_email_irrelevant(self):
        email_from = "Friend <friend@example.com>"
        subject = "Dinner tonight?"
        body = "Hey, are we still meeting at 7pm?"
        result = detector.analyze_email(email_from, subject, body)
        self.assertEqual(result["type"], "IRRELEVANT")


class TestAuditor(unittest.TestCase):
    def test_detect_recurring_charges_monthly(self):
        transactions = [
            {"date": "2026-07-01", "description": "NETFLIX COM RECURRING", "amount": 15.99},
            {"date": "2026-08-01", "description": "NETFLIX COM RECURRING", "amount": 15.99},
            {"date": "2026-09-01", "description": "NETFLIX COM RECURRING", "amount": 15.99},
            {"date": "2026-08-15", "description": "GROCERY STORE ONE TIME", "amount": 45.20}
        ]
        detected = auditor.detect_recurring_charges(transactions)
        self.assertEqual(len(detected), 1)
        self.assertEqual(detected[0]["interval"], "Monthly")
        self.assertEqual(detected[0]["cost"], 15.99)


class TestNagEngine(unittest.TestCase):
    def test_calculate_nag_parameters(self):
        # Critical (< 6h)
        soon = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        interval, urgency, _ = nag_engine.calculate_nag_parameters(soon, "relentless")
        self.assertEqual(urgency, "CRITICAL")
        self.assertEqual(interval, 15)

        # High (6h - 24h)
        high = (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")
        interval, urgency, _ = nag_engine.calculate_nag_parameters(high, "relentless")
        self.assertEqual(urgency, "HIGH")
        self.assertEqual(interval, 60)

        # Medium (24h - 72h)
        med = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        interval, urgency, _ = nag_engine.calculate_nag_parameters(med, "relentless")
        self.assertEqual(urgency, "MEDIUM")
        self.assertEqual(interval, 180)

        # Normal (> 72h)
        normal = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        interval, urgency, _ = nag_engine.calculate_nag_parameters(normal, "relentless")
        self.assertEqual(urgency, "NORMAL")
        self.assertEqual(interval, 720)


class MockSocket:
    def __init__(self, raw_http):
        self.rfile = io.BytesIO(raw_http)
        self.wfile = io.BytesIO()
    def makefile(self, mode, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        return self.wfile
    def sendall(self, data):
        self.wfile.write(data)

class DummyServer:
    def __init__(self):
        self.server_name = 'localhost'
        self.server_port = 5055

class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.temp_db.close()
        database.DB_PATH = cls.temp_db.name
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_db.name):
            os.remove(cls.temp_db.name)

    def _request(self, method, path, data=None):
        body_bytes = json.dumps(data).encode("utf-8") if data is not None else b""
        req_lines = [f"{method} {path} HTTP/1.1", "Host: localhost"]
        if data is not None:
            req_lines.append("Content-Type: application/json")
            req_lines.append(f"Content-Length: {len(body_bytes)}")
        raw = ("\r\n".join(req_lines) + "\r\n\r\n").encode("utf-8") + body_bytes
        sock = MockSocket(raw)
        server.TrialShieldHandler(sock, ("127.0.0.1", 12345), DummyServer())
        
        response_bytes = sock.wfile.getvalue()
        header_part, _, body_part = response_bytes.partition(b"\r\n\r\n")
        lines = header_part.decode("utf-8", errors="replace").split("\r\n")
        status_line = lines[0]
        status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 500
        parsed_body = json.loads(body_part.decode("utf-8")) if body_part else {}
        return status_code, parsed_body

    def _get(self, path):
        return self._request("GET", path)

    def _post(self, path, data):
        return self._request("POST", path, data)

    def _delete(self, path):
        return self._request("DELETE", path)

    def test_get_trials(self):
        status, data = self._get("/api/trials")
        self.assertEqual(status, 200)
        self.assertIn("trials", data)

    def test_get_settings(self):
        status, data = self._get("/api/settings")
        self.assertEqual(status, 200)
        self.assertIn("settings", data)

    def test_get_logs(self):
        status, data = self._get("/api/logs")
        self.assertEqual(status, 200)
        self.assertIn("logs", data)

    def test_simulate_email_and_defuse(self):
        # 1. Simulate incoming trial
        payload = {
            "from": "Spotify <support@spotify.com>",
            "subject": "Your Spotify trial is ending",
            "body": "Your free trial ends tomorrow. You will be charged $9.99/mo unless you cancel at https://spotify.com/cancel."
        }
        status, res = self._post("/api/simulate-email", payload)
        self.assertEqual(status, 200)
        self.assertEqual(res["status"], "TRIAL_DETECTED")
        trial_id = res["trial_id"]

        # Verify it shows up in active trials
        _, trials_res = self._get("/api/trials")
        active_ids = [t["id"] for t in trials_res["trials"] if t["status"] == "ACTIVE"]
        self.assertIn(trial_id, active_ids)

        # 2. Trigger nag
        status, nag_res = self._post("/api/trials/nag", {"trial_id": trial_id})
        self.assertEqual(status, 200)
        self.assertTrue(nag_res["success"])

        # 3. Defuse
        status, defuse_res = self._post("/api/trials/defuse", {"service_name": "Spotify"})
        self.assertEqual(status, 200)
        self.assertTrue(defuse_res["success"])

    def test_audit_transactions(self):
        payload = {
            "transactions": [
                {"date": "2026-07-01", "description": "CHATGPT PLUS", "amount": 20.00},
                {"date": "2026-08-01", "description": "CHATGPT PLUS", "amount": 20.00},
                {"date": "2026-09-01", "description": "CHATGPT PLUS", "amount": 20.00}
            ]
        }
        status, res = self._post("/api/audit/transactions", payload)
        self.assertEqual(status, 200)
        self.assertEqual(len(res["detected"]), 1)
        self.assertEqual(res["detected"][0]["cost"], 20.00)

    def test_manual_trial_creation(self):
        payload = {
            "service_name": "Canva Pro",
            "trial_end_date": "2026-10-15",
            "cost": "$12.99/mo",
            "cancel_url": "https://canva.com/cancel"
        }
        status, res = self._post("/api/trials", payload)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

class TestCLI(unittest.TestCase):
    def test_cli_alert_function(self):
        import cli
        # test_alert should execute without raising NameError or exception
        cli.test_alert()

if __name__ == "__main__":
    unittest.main()
