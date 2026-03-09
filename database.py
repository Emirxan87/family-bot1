import sqlite3
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                family_id INTEGER,
                full_name TEXT NOT NULL,
                username TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(telegram_id) ON DELETE SET NULL,
                UNIQUE(family_id, name)
            );

            CREATE TABLE IF NOT EXISTS shopping_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                added_by INTEGER,
                bought_by INTEGER,
                is_done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE,
                FOREIGN KEY (added_by) REFERENCES users(telegram_id) ON DELETE SET NULL,
                FOREIGN KEY (bought_by) REFERENCES users(telegram_id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT,
                is_family INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_states (
                telegram_id INTEGER PRIMARY KEY,
                state TEXT,
                payload TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                label TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS moments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                photo_file_id TEXT NOT NULL,
                caption TEXT,
                latitude REAL,
                longitude REAL,
                city TEXT,
                place TEXT,
                weather TEXT,
                temperature REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_users_family ON users(family_id);
            CREATE INDEX IF NOT EXISTS idx_shopping_lists_family ON shopping_lists(family_id);
            CREATE INDEX IF NOT EXISTS idx_shopping_items_list ON shopping_items(list_id, is_done);
            CREATE INDEX IF NOT EXISTS idx_events_family_date ON events(family_id, event_date);
            CREATE INDEX IF NOT EXISTS idx_expenses_family_created ON expenses(family_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_activity_family_created ON activity_log(family_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_locations_family_created ON locations(family_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_moments_family_created ON moments(family_id, created_at);
            """
        )
