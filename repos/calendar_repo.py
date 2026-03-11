from database import get_conn


class CalendarRepo:
    def add_event(
        self,
        family_id: int,
        creator_user_id: int,
        participant_user_id: int | None,
        title: str,
        event_type: str,
        event_date: str,
        event_time: str | None,
        is_family: int,
    ) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO events(
                    family_id,
                    created_by,
                    creator_user_id,
                    participant_user_id,
                    title,
                    event_type,
                    event_date,
                    event_time,
                    is_family
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    family_id,
                    creator_user_id,
                    creator_user_id,
                    participant_user_id,
                    title,
                    event_type,
                    event_date,
                    event_time,
                    is_family,
                ),
            )
            return cur.lastrowid

    def events_for_period(self, family_id: int, date_from: str, date_to: str):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    e.*,
                    creator.full_name AS creator_name,
                    participant.full_name AS participant_name
                FROM events e
                JOIN users creator ON creator.telegram_id = e.created_by
                LEFT JOIN users participant ON participant.telegram_id = e.participant_user_id
                WHERE e.family_id = ?
                  AND e.event_date BETWEEN ? AND ?
                ORDER BY e.event_date, COALESCE(e.event_time, '99:99'), e.id
                """,
                (family_id, date_from, date_to),
            ).fetchall()

    def events_for_date(self, family_id: int, event_date: str):
        return self.events_for_period(family_id, event_date, event_date)
