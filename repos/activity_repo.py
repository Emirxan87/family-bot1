from database import get_conn


class ActivityRepo:
    def add(self, family_id: int, actor_id: int, action_type: str, details: str) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO activity_log (family_id, actor_id, action_type, details)
                VALUES (?, ?, ?, ?)
                """,
                (family_id, actor_id, action_type, details),
            )

    def latest(self, family_id: int, limit: int = 10):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT a.*, COALESCE(NULLIF(TRIM(u.role_label), ''), 'Участник') AS actor_name
                FROM activity_log a
                JOIN users u ON u.telegram_id = a.actor_id
                WHERE a.family_id = ?
                ORDER BY a.id DESC
                LIMIT ?
                """,
                (family_id, limit),
            ).fetchall()
