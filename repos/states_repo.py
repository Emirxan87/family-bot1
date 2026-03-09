import json

from database import get_conn


class StatesRepo:
    def set_state(self, telegram_id: int, state: str, payload: dict | None = None) -> None:
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_states(telegram_id, state, payload, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_id) DO UPDATE SET
                  state=excluded.state,
                  payload=excluded.payload,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (telegram_id, state, payload_json),
            )

    def get_state(self, telegram_id: int) -> tuple[str | None, dict]:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT state, payload FROM user_states WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
        if not row:
            return None, {}
        return row["state"], json.loads(row["payload"] or "{}")

    def clear_state(self, telegram_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM user_states WHERE telegram_id = ?", (telegram_id,))
