from database import get_conn


class ExpensesRepo:
    def add_expense(self, family_id: int, user_id: int, amount: float, category: str, comment: str) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO expenses(family_id, created_by, amount, category, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (family_id, user_id, amount, category, comment),
            )

    def latest(self, family_id: int, limit: int = 10):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT e.*, u.full_name
                FROM expenses e JOIN users u ON u.telegram_id = e.created_by
                WHERE e.family_id = ?
                ORDER BY e.id DESC LIMIT ?
                """,
                (family_id, limit),
            ).fetchall()

    def summary(self, family_id: int):
        with get_conn() as conn:
            total = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS t FROM expenses WHERE family_id = ?",
                (family_id,),
            ).fetchone()["t"]
            by_cat = conn.execute(
                """
                SELECT category, ROUND(SUM(amount), 2) AS t
                FROM expenses
                WHERE family_id = ?
                GROUP BY category
                ORDER BY t DESC
                """,
                (family_id,),
            ).fetchall()
            return total, by_cat
