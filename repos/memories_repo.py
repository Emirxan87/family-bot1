from database import get_conn


class MemoriesRepo:
    def create_moment(
        self,
        family_id: int,
        user_id: int,
        photo_file_id: str,
        caption: str,
        latitude: float | None,
        longitude: float | None,
        city: str | None,
        place: str | None,
        weather: str | None,
        temperature: float | None,
    ) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO moments(
                    family_id, user_id, photo_file_id, caption,
                    latitude, longitude, city, place, weather, temperature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    family_id,
                    user_id,
                    photo_file_id,
                    caption,
                    latitude,
                    longitude,
                    city,
                    place,
                    weather,
                    temperature,
                ),
            )

    def latest(self, family_id: int, limit: int = 10):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT m.*, u.full_name
                FROM moments m JOIN users u ON u.telegram_id = m.user_id
                WHERE m.family_id = ?
                ORDER BY m.id DESC LIMIT ?
                """,
                (family_id, limit),
            ).fetchall()
