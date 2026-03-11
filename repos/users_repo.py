import logging
import sqlite3

from database import get_conn


logger = logging.getLogger(__name__)


class UsersRepo:
    def _ensure_users_full_name_column(self, conn) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "full_name" in columns:
            return

        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")

        if "username" in columns:
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

        logger.warning("Applied runtime fallback migration: users.full_name")

    def upsert_user(self, telegram_id: int, full_name: str, username: str | None) -> None:
        with get_conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (telegram_id, full_name, username)
                    VALUES (?, ?, ?)
                    ON CONFLICT(telegram_id) DO UPDATE SET
                        full_name=excluded.full_name,
                        username=excluded.username
                    """,
                    (telegram_id, full_name, username),
                )
            except sqlite3.OperationalError as exc:
                if "no column named full_name" not in str(exc).lower():
                    raise

                logger.warning("users.full_name is missing during upsert; applying fallback migration")
                self._ensure_users_full_name_column(conn)
                conn.execute(
                    """
                    INSERT INTO users (telegram_id, full_name, username)
                    VALUES (?, ?, ?)
                    ON CONFLICT(telegram_id) DO UPDATE SET
                        full_name=excluded.full_name,
                        username=excluded.username
                    """,
                    (telegram_id, full_name, username),
                )

    def get_user(self, telegram_id: int):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()

    def set_family(self, telegram_id: int, family_id: int) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET family_id = ? WHERE telegram_id = ?",
                (family_id, telegram_id),
            )

    def list_family_members(self, family_id: int):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE family_id = ? ORDER BY full_name", (family_id,)
            ).fetchall()
