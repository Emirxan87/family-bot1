from database import get_conn


class ExpensesRepo:
    def add_operation(
        self,
        family_id: int,
        created_by: int,
        actor_id: int | None,
        operation_type: str,
        amount: float,
        category: str,
        subcategory: str | None,
        comment: str | None,
    ) -> int:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses(
                    family_id,
                    created_by,
                    actor_id,
                    operation_type,
                    amount,
                    category,
                    subcategory,
                    comment,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (family_id, created_by, actor_id, operation_type, amount, category, subcategory, comment),
            )
            return int(cursor.lastrowid)

    def update_comment(self, expense_id: int, family_id: int, comment: str) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE expenses SET comment = ? WHERE id = ? AND family_id = ?",
                (comment, expense_id, family_id),
            )

    def update_actor(self, expense_id: int, family_id: int, actor_id: int | None) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE expenses SET actor_id = ? WHERE id = ? AND family_id = ?",
                (actor_id, expense_id, family_id),
            )

    def latest(self, family_id: int, limit: int = 10):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    e.*,
                    COALESCE(NULLIF(TRIM(creator.role_label), ''), 'Участник') AS creator_name,
                    COALESCE(NULLIF(TRIM(actor.role_label), ''), 'Участник') AS actor_name
                FROM expenses e
                JOIN users creator ON creator.telegram_id = e.created_by
                LEFT JOIN users actor ON actor.telegram_id = e.actor_id
                WHERE e.family_id = ?
                ORDER BY e.id DESC LIMIT ?
                """,
                (family_id, limit),
            ).fetchall()

    def aggregate_by_period(self, family_id: int, start_ts: str):
        with get_conn() as conn:
            totals = conn.execute(
                """
                SELECT
                    operation_type,
                    ROUND(COALESCE(SUM(amount), 0), 2) AS total
                FROM expenses
                WHERE family_id = ? AND datetime(created_at) >= datetime(?)
                GROUP BY operation_type
                """,
                (family_id, start_ts),
            ).fetchall()

            by_categories = conn.execute(
                """
                SELECT
                    operation_type,
                    category,
                    ROUND(SUM(amount), 2) AS total
                FROM expenses
                WHERE family_id = ? AND datetime(created_at) >= datetime(?)
                GROUP BY operation_type, category
                ORDER BY operation_type, total DESC
                """,
                (family_id, start_ts),
            ).fetchall()

            by_people = conn.execute(
                """
                SELECT
                    e.operation_type,
                    CASE WHEN e.actor_id IS NULL THEN 'Общее' ELSE COALESCE(NULLIF(TRIM(u.role_label), ''), 'Участник') END AS actor_name,
                    ROUND(SUM(e.amount), 2) AS total
                FROM expenses e
                LEFT JOIN users u ON u.telegram_id = e.actor_id
                WHERE e.family_id = ? AND datetime(e.created_at) >= datetime(?)
                GROUP BY e.operation_type, actor_name
                ORDER BY e.operation_type, total DESC
                """,
                (family_id, start_ts),
            ).fetchall()

            return totals, by_categories, by_people
