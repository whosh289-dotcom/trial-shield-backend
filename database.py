import sqlite3
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger("Database")

# Determine Database Engine
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

def get_connection():
    if USE_POSTGRES:
        # Connect to Postgres
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        return conn
    else:
        # Connect to local SQLite
        conn = sqlite3.connect("trial_shield.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def execute(query, params=()):
    if USE_POSTGRES:
        # Convert SQLite ? placeholders to Postgres %s placeholders
        query = query.replace("?", "%s")
    
    conn = get_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    return [dict(row) for row in cur.fetchall()]
                # If returning id (INSERT RETURNING id)
                if "RETURNING" in query.upper():
                    res = cur.fetchone()
                    return res['id'] if res else None
                return cur.lastrowid
        else:
            cur = conn.cursor()
            cur.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cur.fetchall()]
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def init_db():
    queries = [
        """
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY,
            service_name TEXT NOT NULL,
            sender_email TEXT,
            subject TEXT,
            trial_end_date TEXT NOT NULL,
            cost TEXT,
            cancel_url TEXT,
            raw_snippet TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nag_logs (
            id INTEGER PRIMARY KEY,
            trial_id INTEGER,
            service_name TEXT,
            nag_type TEXT,
            nag_message TEXT,
            urgency TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    # In postgres, AUTOINCREMENT is SERIAL, INTEGER PRIMARY KEY works but SERIAL is better.
    # We will adjust the schema for postgres manually if needed, 
    # but Postgres actually supports CREATE TABLE ... (id SERIAL PRIMARY KEY)
    
    if USE_POSTGRES:
        queries = [q.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY").replace("CURRENT_TIMESTAMP", "CURRENT_TIMESTAMP") for q in queries]
        
    for q in queries:
        execute(q)

def add_trial(service_name, sender_email, subject, trial_end_date, cost, cancel_url, raw_snippet):
    # Check if already exists and active to avoid duplicates
    existing = execute("SELECT id FROM trials WHERE service_name = ? AND status = 'ACTIVE'", (service_name,))
    if existing:
        return existing[0]['id']

    query = """
        INSERT INTO trials (service_name, sender_email, subject, trial_end_date, cost, cancel_url, raw_snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    if USE_POSTGRES:
        query += " RETURNING id"
    return execute(query, (service_name, sender_email, subject, trial_end_date, cost, cancel_url, raw_snippet))

def get_active_trials():
    return execute("SELECT * FROM trials WHERE status = 'ACTIVE' ORDER BY trial_end_date ASC")

def get_all_trials():
    return execute("SELECT * FROM trials ORDER BY trial_end_date DESC")

def defuse_trial(trial_id):
    execute("UPDATE trials SET status = 'DEFUSED' WHERE id = ?", (trial_id,))

def delete_trial(trial_id):
    execute("DELETE FROM trials WHERE id = ?", (trial_id,))

def log_nag(trial_id, service_name, nag_type, nag_message, urgency):
    query = """
        INSERT INTO nag_logs (trial_id, service_name, nag_type, nag_message, urgency)
        VALUES (?, ?, ?, ?, ?)
    """
    execute(query, (trial_id, service_name, nag_type, nag_message, urgency))

def get_recent_logs(limit=20):
    return execute(f"SELECT * FROM nag_logs ORDER BY timestamp DESC LIMIT {limit}")

def set_setting(key, value):
    # SQLite UPSERT vs Postgres UPSERT
    if USE_POSTGRES:
        query = """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    else:
        query = """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """
    execute(query, (key, value))

def get_setting(key, default=None):
    res = execute("SELECT value FROM settings WHERE key = ?", (key,))
    if res:
        return res[0]['value']
    return default

def get_all_settings():
    res = execute("SELECT key, value FROM settings")
    return {row['key']: row['value'] for row in res}

# Initialize the schema
init_db()
