import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        existing = conn.execute("SELECT id FROM user_profile WHERE id = 1").fetchone()
        if existing is None:
            default_name = os.getenv("USER_PROFILE_NAME", "SpendSense User").strip() or "SpendSense User"
            default_email = os.getenv("USER_PROFILE_EMAIL", "user@spendsense.local").strip() or "user@spendsense.local"
            conn.execute(
                "INSERT INTO user_profile (id, name, email, updated_at) VALUES (1, ?, ?, ?)",
                (default_name, default_email, datetime.utcnow().isoformat()),
            )
        conn.commit()
