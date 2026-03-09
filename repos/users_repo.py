from database import get_conn


class UsersRepo:
    def upsert_user(self, telegram_id: int, full_name: str, username: str | None) -> None:
        with get_conn() as conn:
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
