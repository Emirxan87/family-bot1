from database import get_conn

DEFAULT_LISTS = ["🛒 Общий", "🥦 Продукты", "💊 Аптека"]


class ShoppingRepo:
    def get_list_for_family(self, list_id: int, family_id: int):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM shopping_lists WHERE id = ? AND family_id = ?",
                (list_id, family_id),
            ).fetchone()

    def ensure_default_lists(self, family_id: int, created_by: int | None = None) -> None:
        with get_conn() as conn:
            for name in DEFAULT_LISTS:
                existing = conn.execute(
                    "SELECT id FROM shopping_lists WHERE family_id = ? AND name = ? LIMIT 1",
                    (family_id, name),
                ).fetchone()
                if existing:
                    continue

                conn.execute(
                    "INSERT INTO shopping_lists(family_id, name, created_by) VALUES (?, ?, ?)",
                    (family_id, name, created_by),
                )

    def get_lists(self, family_id: int):
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM shopping_lists WHERE family_id = ? ORDER BY id", (family_id,)
            ).fetchall()

    def add_item(self, list_id: int, title: str, user_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO shopping_items(list_id, title, added_by) VALUES (?, ?, ?)",
                (list_id, title, user_id),
            )
            return cur.lastrowid

    def get_list(self, list_id: int):
        with get_conn() as conn:
            return conn.execute("SELECT * FROM shopping_lists WHERE id = ?", (list_id,)).fetchone()

    def get_items(self, list_id: int):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT i.*,
                    COALESCE(NULLIF(TRIM(a.role_label), ''), 'Участник') AS added_name,
                    COALESCE(NULLIF(TRIM(b.role_label), ''), 'Участник') AS bought_name
                FROM shopping_items i
                LEFT JOIN users a ON a.telegram_id = i.added_by
                LEFT JOIN users b ON b.telegram_id = i.bought_by
                WHERE i.list_id = ?
                ORDER BY i.is_done, i.id DESC
                """,
                (list_id,),
            ).fetchall()

    def get_visible_items(self, list_id: int):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT i.*,
                    COALESCE(NULLIF(TRIM(a.role_label), ''), 'Участник') AS added_name,
                    COALESCE(NULLIF(TRIM(b.role_label), ''), 'Участник') AS bought_name, TRIM(i.title) AS display_title
                FROM shopping_items i
                LEFT JOIN users a ON a.telegram_id = i.added_by
                LEFT JOIN users b ON b.telegram_id = i.bought_by
                WHERE i.list_id = ?
                  AND TRIM(i.title) != ''
                  AND TRIM(i.title) != 'Без названия'
                ORDER BY i.is_done, i.id DESC
                """,
                (list_id,),
            ).fetchall()

    def get_family_active_items(self, family_id: int):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT i.*, l.family_id, l.name AS list_name,
                    COALESCE(NULLIF(TRIM(a.role_label), ''), 'Участник') AS added_name,
                    TRIM(i.title) AS display_title
                FROM shopping_items i
                JOIN shopping_lists l ON l.id = i.list_id
                LEFT JOIN users a ON a.telegram_id = i.added_by
                WHERE l.family_id = ?
                  AND i.is_done = 0
                  AND TRIM(i.title) != ''
                  AND TRIM(i.title) != 'Без названия'
                ORDER BY i.id DESC
                """,
                (family_id,),
            ).fetchall()

    def mark_item_done(self, family_id: int, item_id: int, user_id: int):
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE shopping_items
                SET is_done = 1, bought_by = ?, updated_at=CURRENT_TIMESTAMP
                WHERE id = ?
                  AND is_done = 0
                  AND list_id IN (
                      SELECT id FROM shopping_lists WHERE family_id = ?
                  )
                """,
                (user_id, item_id, family_id),
            )
            return cur.rowcount

    def mark_items_done(self, family_id: int, item_ids: list[int], user_id: int):
        if not item_ids:
            return 0
        placeholders = ",".join("?" for _ in item_ids)
        with get_conn() as conn:
            cur = conn.execute(
                f"""
                UPDATE shopping_items
                SET is_done = 1, bought_by = ?, updated_at=CURRENT_TIMESTAMP
                WHERE is_done = 0
                  AND id IN ({placeholders})
                  AND list_id IN (
                      SELECT id FROM shopping_lists WHERE family_id = ?
                  )
                """,
                [user_id, *item_ids, family_id],
            )
            return cur.rowcount

    def mark_all_family_done(self, family_id: int, user_id: int):
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE shopping_items
                SET is_done = 1, bought_by = ?, updated_at=CURRENT_TIMESTAMP
                WHERE is_done = 0
                  AND list_id IN (
                      SELECT id FROM shopping_lists WHERE family_id = ?
                  )
                """,
                (user_id, family_id),
            )
            return cur.rowcount

    def toggle_item(self, item_id: int, user_id: int):
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM shopping_items WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return None
            new_done = 0 if row["is_done"] else 1
            bought_by = user_id if new_done else None
            conn.execute(
                """
                UPDATE shopping_items
                SET is_done = ?, bought_by = ?, updated_at=CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_done, bought_by, item_id),
            )
            return {"item": row, "is_done": new_done}

    def mark_all_done(self, list_id: int, user_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE shopping_items
                SET is_done = 1, bought_by = ?, updated_at=CURRENT_TIMESTAMP
                WHERE list_id = ? AND is_done = 0
                """,
                (user_id, list_id),
            )
            return cur.rowcount

    def restore_all_active(self, list_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                """
                UPDATE shopping_items
                SET is_done = 0, bought_by = NULL, updated_at=CURRENT_TIMESTAMP
                WHERE list_id = ? AND is_done = 1
                """,
                (list_id,),
            )
            return cur.rowcount

    def clear_done(self, list_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM shopping_items WHERE list_id = ? AND is_done = 1",
                (list_id,),
            )
            return cur.rowcount

    def clear_list(self, list_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM shopping_items WHERE list_id = ?", (list_id,))
            return cur.rowcount

    def get_item_by_id(self, item_id: int):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT i.*, l.family_id, l.name AS list_name
                FROM shopping_items i
                JOIN shopping_lists l ON l.id = i.list_id
                WHERE i.id = ?
                """,
                (item_id,),
            ).fetchone()

    def get_item_for_family(self, item_id: int, family_id: int):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT i.*, l.family_id, l.name AS list_name
                FROM shopping_items i
                JOIN shopping_lists l ON l.id = i.list_id
                WHERE i.id = ? AND l.family_id = ?
                """,
                (item_id, family_id),
            ).fetchone()
