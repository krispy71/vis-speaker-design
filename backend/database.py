import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "speaker_design.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                type TEXT NOT NULL,
                fs_hz REAL,
                qts REAL,
                vas_liters REAL,
                xmax_mm REAL,
                sensitivity_db REAL,
                power_rms_w INTEGER,
                diameter_mm INTEGER,
                price_usd REAL,
                price_updated_date TEXT,
                datasheet_url TEXT,
                buy_url TEXT
            );

            CREATE TABLE IF NOT EXISTS driver_search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                driver_model TEXT NOT NULL,
                source_url TEXT,
                ts_params_json TEXT,
                price_usd REAL,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                phase TEXT NOT NULL DEFAULT 'intake',
                conversation_json TEXT NOT NULL DEFAULT '[]',
                design_brief_json TEXT,
                design_output_json TEXT,
                bom_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
