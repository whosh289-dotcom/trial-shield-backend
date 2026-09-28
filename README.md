# 🛡️ Trial Shield — Relentless Subscription Watchdog

> **Never get accidentally billed for a forgotten free trial again.**

Unlike passive subscription trackers that show a quiet dashboard you forget to check, **Trial Shield** acts as an active watchdog:
1. **Scans your inbox** for emails warning that a free trial is ending or a renewal charge is upcoming.
2. **Begins relentlessly nagging you** across desktop notifications, audio alarms, Telegram, or Discord.
3. **Escalates frequency** as the expiration deadline gets closer (e.g., from once a day to every 15 minutes in the final hours).
4. **The Defusal Loop**: Keeps pestering you **until** it detects your cancellation confirmation email (*"Your subscription has been canceled"*). Only then does the shield stand down.

---

## ⚡ Quick Start

```bash
cd /Users/bhaviksakarkar/Documents/Antigravity/trial-shield
```

### 1. Launch the Web Dashboard
```bash
python3 server.py
```
Open **[http://localhost:5055](http://localhost:5055)** in your browser to view:
- **Active Watchlist Radar**: Real-time countdown to charges, renewal fees, and nag frequencies.
- **Interactive Simulator**: Test incoming trial emails and cancellation emails with 1-click presets.
- **Defused Archive**: View money saved from confirmed cancellations.
- **Nag Audit Log**: Complete history of every alert dispatched.

### 2. Or Use the Interactive CLI
```bash
python3 cli.py
```

---

## 📬 Automated Inbox Sync (Gmail / Outlook)

Trial Shield includes a built-in IMAP scanner:
1. Open the **Email & Nag Settings** tab in the web dashboard (or configure via `database.py`).
2. Enter your email provider:
   - **Gmail**: Server `imap.gmail.com`, Port `993`
   - Use an **App Password** (generate in *Google Account > Security > 2-Step Verification > App Passwords*).
3. Trial Shield periodically checks your inbox in the background for:
   - Trial end / upcoming charge notices -> adds them to the nag queue.
   - Cancellation receipts -> automatically defuses and stops nagging!

---

## 🔔 Escalation Schedule

| Time Remaining Until Charge | Urgency Level | Relentless Nag Frequency | Mac Sound |
| :--- | :--- | :--- | :--- |
| **> 3 Days** | `NORMAL` | Every 12 hours | *Sosumi* |
| **24h – 72h** | `MEDIUM` | Every 3 hours | *Ping* |
| **6h – 24h** | `HIGH` | Every 60 minutes | *Basso* |
| **< 6 Hours** | `CRITICAL` | **Every 15 minutes + Voice Warning** | *Basso / Speech* |
| **Cancellation Verified** | `DEFUSED` | **Silenced & Stood Down** | *Hero (Victory)* |

---

## 🛠️ Multi-Channel Alert Support
- **Native macOS Notifications**: Popups with system sounds using `osascript`.
- **macOS Voice Speech**: Speaks audible warnings when &lt; 6 hours remain using `say`.
- **Telegram Bot**: Pushes instant telegram alerts with direct links to cancellation pages.
- **Discord / Slack Webhooks**: Posts alerts to your private channel.
