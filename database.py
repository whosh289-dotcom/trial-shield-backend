import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "trial_shield.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Trials table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            sender_email TEXT,
            subject TEXT,
            trial_end_date TEXT NOT NULL,
            cost TEXT,
            cancel_url TEXT,
            status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'CANCELLED', 'EXPIRED'
            last_nagged_at TEXT,
            nag_count INTEGER DEFAULT 0,
            nag_intensity TEXT DEFAULT 'relentless', -- 'normal', 'aggressive', 'relentless'
            raw_snippet TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            cancelled_at TEXT
        )
    ''')

    # Nag notifications log
    c.execute('''
        CREATE TABLE IF NOT EXISTS nag_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id INTEGER,
            service_name TEXT,
            channel TEXT,
            message TEXT,
            urgency TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # System settings
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Seed default settings if empty
    defaults = {
        "desktop_notifications": "true",
        "voice_alerts": "true",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "webhook_url": "",
        "imap_server": "",
        "imap_user": "",
        "imap_password": "",
        "imap_port": "993",
        "imap_ssl": "true",
        "auto_scan_interval_seconds": "300",
        "global_nag_intensity": "relentless"
    }

    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))

    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM settings')
    rows = c.fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def add_trial(service_name, sender_email, subject, trial_end_date, cost=None, cancel_url=None, raw_snippet=None):
    conn = get_connection()
    c = conn.cursor()
    # Check if active trial for this service already exists
    c.execute('''
        SELECT id FROM trials 
        WHERE LOWER(service_name) = LOWER(?) AND status = 'ACTIVE'
    ''', (service_name,))
    existing = c.fetchone()
    
    if existing:
        # Update existing trial details
        c.execute('''
            UPDATE trials 
            SET trial_end_date = ?, cost = COALESCE(?, cost), cancel_url = COALESCE(?, cancel_url),
                subject = ?, raw_snippet = ?
            WHERE id = ?
        ''', (trial_end_date, cost, cancel_url, subject, raw_snippet, existing['id']))
        trial_id = existing['id']
    else:
        c.execute('''
            INSERT INTO trials (service_name, sender_email, subject, trial_end_date, cost, cancel_url, raw_snippet, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        ''', (service_name, sender_email, subject, trial_end_date, cost, cancel_url, raw_snippet))
        trial_id = c.lastrowid
        
    conn.commit()
    conn.close()
    return trial_id

def defuse_trial(service_name_or_keyword, cancellation_email_snippet=None):
    """
    Called when a cancellation confirmation email is detected.
    Finds matching ACTIVE trial and changes status to CANCELLED.
    """
    conn = get_connection()
    c = conn.cursor()
    keyword = f"%{service_name_or_keyword.strip()}%"
    c.execute('''
        SELECT id, service_name, trial_end_date, cost FROM trials
        WHERE (LOWER(service_name) LIKE LOWER(?) OR LOWER(sender_email) LIKE LOWER(?)) 
          AND status = 'ACTIVE'
    ''', (keyword, keyword))
    trials = c.fetchall()
    
    defused_ids = []
    now = datetime.now().isoformat()
    for t in trials:
        c.execute('''
            UPDATE trials 
            SET status = 'CANCELLED', cancelled_at = ?
            WHERE id = ?
        ''', (now, t['id']))
        defused_ids.append({
            "id": t['id'],
            "service_name": t['service_name'],
            "cost": t['cost']
        })
        
    conn.commit()
    conn.close()
    return defused_ids

def get_active_trials():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM trials 
        WHERE status = 'ACTIVE'
        ORDER BY trial_end_date ASC
    ''')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_all_trials():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM trials ORDER BY id DESC')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def mark_nagged(trial_id):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        UPDATE trials 
        SET last_nagged_at = ?, nag_count = nag_count + 1
        WHERE id = ?
    ''', (now, trial_id))
    conn.commit()
    conn.close()

def log_nag(trial_id, service_name, channel, message, urgency):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO nag_logs (trial_id, service_name, channel, message, urgency)
        VALUES (?, ?, ?, ?, ?)
    ''', (trial_id, service_name, channel, message, urgency))
    conn.commit()
    conn.close()

def get_recent_logs(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM nag_logs 
        ORDER BY id DESC 
        LIMIT ?
    ''', (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def delete_trial(trial_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM trials WHERE id = ?', (trial_id,))
    c.execute('DELETE FROM nag_logs WHERE trial_id = ?', (trial_id,))
    conn.commit()
    conn.close()

# Initialize upon import
init_db()
