import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table_name: str, column_name: str, alter_sql: str):
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not any(col["name"] == column_name for col in cols):
        conn.execute(alter_sql)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                account_details TEXT,
                password_hash TEXT NOT NULL,
                auth_token TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "users", "phone", "ALTER TABLE users ADD COLUMN phone TEXT")
        _ensure_column(
            conn,
            "users",
            "account_details",
            "ALTER TABLE users ADD COLUMN account_details TEXT",
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        _ensure_column(
            conn,
            "expenses",
            "user_id",
            "ALTER TABLE expenses ADD COLUMN user_id INTEGER",
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                amount REAL NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, month),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()
