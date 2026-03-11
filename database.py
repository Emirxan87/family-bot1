import sqlite3
import logging
from contextlib import contextmanager

from config import DB_PATH


logger = logging.getLogger(__name__)


@contextmanager
def get_conn():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
    applied_migrations: list[str],
) -> None:
    if not _table_exists(conn, table_name):
        return
    if _column_exists(conn, table_name, column_name):
        return

    conn.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )
    applied_migrations.append(f"{table_name}.{column_name}")


def _ensure_timestamp_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    applied_migrations: list[str],
) -> None:
    """
    Безопасно добавляет timestamp-колонку в существующую SQLite таблицу.
    Нельзя использовать DEFAULT CURRENT_TIMESTAMP в ALTER TABLE,
    поэтому добавляем колонку без default и заполняем существующие строки отдельно.
    """
    if not _table_exists(conn, table_name):
        return
    if _column_exists(conn, table_name, column_name):
        return

    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")
    conn.execute(
        f"UPDATE {table_name} SET {column_name} = CURRENT_TIMESTAMP WHERE {column_name} IS NULL"
    )
    applied_migrations.append(f"{table_name}.{column_name}")


def _ensure_users_full_name(conn: sqlite3.Connection, applied_migrations: list[str]) -> None:
    if not _table_exists(conn, "users"):
        return

    users_has_username = _column_exists(conn, "users", "username")
    users_has_full_name = _column_exists(conn, "users", "full_name")

    if not users_has_full_name:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        applied_migrations.append("users.full_name")

    if users_has_username:
        conn.execute(
            """
            UPDATE users
            SET full_name = COALESCE(NULLIF(username, ''), 'Участник семьи')
            WHERE full_name IS NULL OR TRIM(full_name) = ''
            """
        )
    else:
        conn.execute(
            """
            UPDATE users
            SET full_name = 'Участник семьи'
            WHERE full_name IS NULL OR TRIM(full_name) = ''
            """
        )


def _run_migrations(conn: sqlite3.Connection) -> list[str]:
    applied_migrations: list[str] = []

    # shopping_items (legacy compatibility)
    _ensure_column(conn, "shopping_items", "added_by", "INTEGER", applied_migrations)
    _ensure_column(conn, "shopping_items", "bought_by", "INTEGER", applied_migrations)
    _ensure_column(conn, "shopping_items", "is_done", "INTEGER NOT NULL DEFAULT 0", applied_migrations)
    _ensure_timestamp_column(conn, "shopping_items", "updated_at", applied_migrations)
    _ensure_timestamp_column(conn, "shopping_items", "created_at", applied_migrations)

    # users
    _ensure_column(conn, "users", "username", "TEXT", applied_migrations)
    _ensure_users_full_name(conn, applied_migrations)
    _ensure_timestamp_column(conn, "users", "created_at", applied_migrations)

    # shopping_lists
    _ensure_column(conn, "shopping_lists", "created_by", "INTEGER", applied_migrations)
    _ensure_timestamp_column(conn, "shopping_lists", "created_at", applied_migrations)

    # events
    _ensure_column(conn, "events", "event_time", "TEXT", applied_migrations)
    _ensure_column(conn, "events", "is_family", "INTEGER NOT NULL DEFAULT 1", applied_migrations)
    _ensure_timestamp_column(conn, "events", "created_at", applied_migrations)

    # expenses
    _ensure_column(conn, "expenses", "comment", "TEXT", applied_migrations)
    _ensure_timestamp_column(conn, "expenses", "created_at", applied_migrations)

    # activity_log
    _ensure_column(conn, "activity_log", "details", "TEXT", applied_migrations)
    _ensure_timestamp_column(conn, "activity_log", "created_at", applied_migrations)

    # user_states
    _ensure_column(conn, "user_states", "payload", "TEXT", applied_migrations)
    _ensure_timestamp_column(conn, "user_states", "updated_at", applied_migrations)

    # locations
    _ensure_column(conn, "locations", "label", "TEXT", applied_migrations)
    _ensure_timestamp_column(conn, "locations", "created_at", applied_migrations)

    # moments
    _ensure_column(conn, "moments", "caption", "TEXT", applied_migrations)
    _ensure_column(conn, "moments", "latitude", "REAL", applied_migrations)
    _ensure_column(conn, "moments", "longitude", "REAL", applied_migrations)
    _ensure_column(conn, "moments", "city", "TEXT", applied_migrations)
    _ensure_column(conn, "moments", "place", "TEXT", applied_migrations)
    _ensure_column(conn, "moments", "weather", "TEXT", applied_migrations)
    _ensure_column(conn, "moments", "temperature", "REAL", applied_migrations)
    _ensure_timestamp_column(conn, "moments", "created_at", applied_migrations)

    return applied_migrations


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _log_schema_health(conn: sqlite3.Connection) -> None:
    expected_columns = {
        "users": {"telegram_id", "family_id", "full_name", "username", "created_at"},
        "shopping_lists": {"id", "family_id", "name", "created_by", "created_at"},
        "shopping_items": {"id", "list_id", "title", "added_by", "bought_by", "is_done", "created_at", "updated_at"},
        "events": {"id", "family_id", "created_by", "title", "event_date", "event_time", "is_family", "created_at"},
        "expenses": {"id", "family_id", "created_by", "amount", "category", "comment", "created_at"},
        "activity_log": {"id", "family_id", "actor_id", "action_type", "details", "created_at"},
        "user_states": {"telegram_id", "state", "payload", "updated_at"},
        "locations": {"id", "family_id", "user_id", "latitude", "longitude", "label", "created_at"},
        "moments": {"id", "family_id", "user_id", "photo_file_id", "caption", "latitude", "longitude", "city", "place", "weather", "temperature", "created_at"},
    }

    for table_name, expected in expected_columns.items():
        actual = _table_columns(conn, table_name)
        if not actual:
            logger.warning("Schema check: table '%s' not found", table_name)
            continue
        missing = sorted(expected - actual)
        if missing:
            logger.warning("Schema check: table '%s' is missing columns: %s", table_name, ", ".join(missing))

    users_columns = sorted(_table_columns(conn, "users"))
    logger.info("users schema columns: %s", ", ".join(users_columns))


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
            """
        )

        applied_migrations = _run_migrations(conn)
        if applied_migrations:
            logger.info("Applied SQLite migrations: %s", ", ".join(applied_migrations))
        else:
            logger.info("Applied SQLite migrations: none")

        _log_schema_health(conn)

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_users_family
            ON users(family_id);

            CREATE INDEX IF NOT EXISTS idx_shopping_lists_family
            ON shopping_lists(family_id);

            CREATE INDEX IF NOT EXISTS idx_shopping_items_list
            ON shopping_items(list_id, is_done);

            CREATE INDEX IF NOT EXISTS idx_events_family_date
            ON events(family_id, event_date);

            CREATE INDEX IF NOT EXISTS idx_expenses_family_created
            ON expenses(family_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_activity_family_created
            ON activity_log(family_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_locations_family_created
            ON locations(family_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_moments_family_created
            ON moments(family_id, created_at);
            """
        )

        conn.commit()