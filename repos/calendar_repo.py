from database import get_conn


class CalendarRepo:
    def add_event(self, family_id: int, user_id: int, title: str, event_date: str, event_time: str, is_family: int) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO events(family_id, created_by, title, event_date, event_time, is_family)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (family_id, user_id, title, event_date, event_time, is_family),
            )

    def events_for_date(self, family_id: int, event_date: str):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT e.*, u.full_name
                FROM events e JOIN users u ON u.telegram_id = e.created_by
                WHERE e.family_id = ? AND e.event_date = ?
                ORDER BY COALESCE(e.event_time, '99:99')
                """,
                (family_id, event_date),
            ).fetchall()
