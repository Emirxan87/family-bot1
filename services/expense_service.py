from datetime import datetime, timedelta

from repos.expenses_repo import ExpensesRepo

PERIOD_LABELS = {
    "day": "сегодня",
    "week": "последние 7 дней",
    "month": "месяц",
    "quarter": "квартал",
    "year": "год",
}


class ExpenseService:
    def __init__(self):
        self.repo = ExpensesRepo()

    def add_operation(
        self,
        family_id: int,
        created_by: int,
        actor_id: int | None,
        operation_type: str,
        amount: float,
        category: str,
        subcategory: str | None = None,
        comment: str | None = None,
    ) -> int:
        return self.repo.add_operation(
            family_id,
            created_by,
            actor_id,
            operation_type,
            amount,
            category,
            subcategory,
            comment,
        )

    def update_comment(self, expense_id: int, family_id: int, comment: str) -> None:
        self.repo.update_comment(expense_id, family_id, comment)

    def update_actor(self, expense_id: int, family_id: int, actor_id: int | None) -> None:
        self.repo.update_actor(expense_id, family_id, actor_id)

    def latest_text(self, family_id: int) -> str:
        rows = self.repo.latest(family_id)
        if not rows:
            return "💳 Пока нет операций."

        lines = ["💳 Последние операции:"]
        for row in rows:
            icon = "➖" if row["operation_type"] == "expense" else "➕"
            actor = row["actor_name"] or "👨‍👩‍👧 Общее"
            sub = f" → {row['subcategory']}" if row["subcategory"] else ""
            comment = f" — {row['comment']}" if row["comment"] else ""
            lines.append(
                f"• {icon} {row['amount']:.2f} ₽ | {row['category']}{sub} | {actor}{comment}"
            )
        return "\n".join(lines)

    def stats_text(self, family_id: int, period: str) -> str:
        start_ts = self._period_start(period)
        totals, by_categories, by_people = self.repo.aggregate_by_period(family_id, start_ts)

        totals_map = {row["operation_type"]: row["total"] for row in totals}
        expenses = float(totals_map.get("expense", 0) or 0)
        incomes = float(totals_map.get("income", 0) or 0)
        balance = incomes - expenses

        lines = [
            f"📊 Статистика за {PERIOD_LABELS.get(period, period)}",
            f"• Расходы: {expenses:.2f} ₽",
            f"• Поступления: {incomes:.2f} ₽",
            f"• Баланс: {balance:+.2f} ₽",
        ]

        expense_categories = [row for row in by_categories if row["operation_type"] == "expense"]
        income_categories = [row for row in by_categories if row["operation_type"] == "income"]
        if expense_categories:
            lines.append("\nТоп расходов:")
            lines.extend([f"• {row['category']} — {row['total']:.2f} ₽" for row in expense_categories[:5]])
        if income_categories:
            lines.append("\nТоп поступлений:")
            lines.extend([f"• {row['category']} — {row['total']:.2f} ₽" for row in income_categories[:5]])

        expense_people = [row for row in by_people if row["operation_type"] == "expense"]
        income_people = [row for row in by_people if row["operation_type"] == "income"]
        if expense_people:
            lines.append("\nКто тратил:")
            lines.extend([f"• {row['actor_name']} — {row['total']:.2f} ₽" for row in expense_people])
        if income_people:
            lines.append("\nКто получал:")
            lines.extend([f"• {row['actor_name']} — {row['total']:.2f} ₽" for row in income_people])

        return "\n".join(lines)

    def _period_start(self, period: str) -> str:
        now = datetime.now()
        if period == "day":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        elif period == "quarter":
            start = now - timedelta(days=90)
        elif period == "year":
            start = now - timedelta(days=365)
        else:
            start = now - timedelta(days=30)
        return start.strftime("%Y-%m-%d %H:%M:%S")
