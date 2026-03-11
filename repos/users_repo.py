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

    def update_role(self, telegram_id: int, role_key: str, role_label: str) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET role_key = ?, role_label = ? WHERE telegram_id = ?",
                (role_key, role_label, telegram_id),
            )

    def set_admin(self, telegram_id: int, is_admin: bool) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET is_admin = ? WHERE telegram_id = ?",
                (1 if is_admin else 0, telegram_id),
            )

    def remove_from_family(self, telegram_id: int) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET family_id = NULL, is_admin = 0 WHERE telegram_id = ?",
                (telegram_id,),
            )

    def list_family_members(self, family_id: int):
        if not family_id:
            return []
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE family_id = ? ORDER BY is_admin DESC, full_name", (family_id,)
            ).fetchall()

    def get_family_member(self, family_id: int, telegram_id: int):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE family_id = ? AND telegram_id = ?",
                (family_id, telegram_id),
            ).fetchone()
