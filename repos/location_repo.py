from database import get_conn


class LocationRepo:
    def save(self, family_id: int, user_id: int, lat: float, lon: float, label: str | None = None):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO locations(family_id, user_id, latitude, longitude, label)
                VALUES (?, ?, ?, ?, ?)
                """,
                (family_id, user_id, lat, lon, label),
            )

    def latest_family(self, family_id: int, limit: int = 10):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT l.*, u.full_name
                FROM locations l JOIN users u ON u.telegram_id = l.user_id
                WHERE l.family_id = ?
                ORDER BY l.id DESC LIMIT ?
                """,
                (family_id, limit),
            ).fetchall()
