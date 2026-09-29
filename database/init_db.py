"""
EcoTrack Database Initializer
Creates the SQLite database and all required tables.
Handles schema migrations safely without destroying existing data.

Supports two calculation modes:
  individual  — monthly activity inputs, direct monthly CO2e calculation
  industry    — daily activity inputs, aggregated into monthly totals
"""

import sqlite3
import os

# Path to the database file
DB_PATH = os.path.join(os.path.dirname(__file__), 'ecotrack.db')


def get_connection():
    """Return a connection to the EcoTrack SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows dict-style column access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn   = get_connection()
    cursor = conn.cursor()

    # --- Table: users ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            created_at TEXT    DEFAULT (datetime('now'))
        )
    """)

    # --- Table: footprint_records ---
    #
    # user_type : 'individual' | 'industry'
    # frequency : 'monthly'   | 'daily'
    # date      : YYYY-MM-DD  (for individual, set to first day of the month)
    # month     : YYYY-MM     (always derived from date)
    #
    # Individual records:
    #   user_type = 'individual', frequency = 'monthly'
    #   transport/electricity/fuel/waste = MONTHLY CO2e totals
    #
    # Industry records:
    #   user_type = 'industry', frequency = 'daily'
    #   transport/electricity/fuel/waste = DAILY CO2e values
    #   Monthly totals derived via SQL SUM GROUP BY month
    #
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS footprint_records (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            user_type     TEXT    NOT NULL DEFAULT 'industry',
            frequency     TEXT    NOT NULL DEFAULT 'daily',
            date          TEXT    NOT NULL,
            month         TEXT    NOT NULL,
            transport     REAL    NOT NULL DEFAULT 0,
            electricity   REAL    NOT NULL DEFAULT 0,
            fuel          REAL    NOT NULL DEFAULT 0,
            waste         REAL    NOT NULL DEFAULT 0,
            total         REAL    NOT NULL DEFAULT 0,
            data_quality  TEXT    NOT NULL DEFAULT 'Medium',
            quality_notes TEXT,
            created_at    TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, user_type, date)
        )
    """)

    # --- Table: emission_factors ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emission_factors (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            category       TEXT    NOT NULL,
            activity       TEXT    NOT NULL,
            unit           TEXT    NOT NULL,
            factor         REAL    NOT NULL,
            source         TEXT    NOT NULL,
            version        TEXT,
            effective_date TEXT
        )
    """)

    # --- Table: recommendations ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            category            TEXT    NOT NULL,
            recommendation_text TEXT    NOT NULL
        )
    """)

    # --- Table: goals ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            user_type    TEXT    NOT NULL DEFAULT 'individual',
            month        TEXT    NOT NULL,
            target_co2e  REAL    NOT NULL,
            created_at   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

    # Run schema migrations on existing databases
    migrate_db()

    print("[OK] Database initialized successfully.")
    print(f"   Location: {DB_PATH}")


def migrate_db():
    """
    Safely apply schema migrations to an existing database.
    Uses PRAGMA table_info to check before altering.
    All migrations are non-destructive — existing data is preserved.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    # Inspect existing columns
    cursor.execute("PRAGMA table_info(footprint_records)")
    existing_columns = [row["name"] for row in cursor.fetchall()]

    # --- Migration 1: Add 'date' column ---
    if "date" not in existing_columns:
        cursor.execute(
            "ALTER TABLE footprint_records ADD COLUMN date TEXT"
        )
        print("[OK] Migration: Added 'date' column to footprint_records.")
    else:
        print("[OK] Migration check: 'date' column already exists - skipped.")

    # --- Migration 2: Add 'user_type' column ---
    # Default 'industry' preserves backward compatibility with existing daily records.
    if "user_type" not in existing_columns:
        cursor.execute(
            "ALTER TABLE footprint_records ADD COLUMN user_type TEXT NOT NULL DEFAULT 'industry'"
        )
        print("[OK] Migration: Added 'user_type' column (default: industry).")
    else:
        print("[OK] Migration check: 'user_type' column already exists - skipped.")

    # --- Migration 3: Add 'frequency' column ---
    # Default 'daily' preserves backward compatibility with existing daily records.
    if "frequency" not in existing_columns:
        cursor.execute(
            "ALTER TABLE footprint_records ADD COLUMN frequency TEXT NOT NULL DEFAULT 'daily'"
        )
        print("[OK] Migration: Added 'frequency' column (default: daily).")
    else:
        print("[OK] Migration check: 'frequency' column already exists - skipped.")

    # --- Migration 4: Inspect goals table columns ---
    cursor.execute("PRAGMA table_info(goals)")
    goals_columns = [row["name"] for row in cursor.fetchall()]

    if "user_type" not in goals_columns:
        cursor.execute(
            "ALTER TABLE goals ADD COLUMN user_type TEXT NOT NULL DEFAULT 'individual'"
        )
        print("[OK] Migration: Added 'user_type' column to goals table.")
    else:
        print("[OK] Migration check: goals 'user_type' column already exists - skipped.")

    # --- Migration 5: UNIQUE index on (user_id, user_type, date) ---
    # Allows one record per user per type per date.
    # Drop old index if it exists (old index was on user_id, date only).
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_footprint_user_date")
    except Exception:
        pass

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_footprint_user_type_date
        ON footprint_records(user_id, user_type, date)
    """)
    print("[OK] Migration check: UNIQUE index on (user_id, user_type, date) ensured.")

    conn.commit()
    conn.close()


def seed_default_user():
    """Insert a default demo user if no users exist."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Demo User", "demo@ecotrack.app")
        )
        conn.commit()
        print("[OK] Default demo user created.")

    conn.close()


if __name__ == "__main__":
    init_db()
    seed_default_user()
