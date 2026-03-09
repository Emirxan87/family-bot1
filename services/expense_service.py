from repos.expenses_repo import ExpensesRepo


class ExpenseService:
    def __init__(self):
        self.repo = ExpensesRepo()

    def add_expense(self, family_id: int, user_id: int, amount: float, category: str, comment: str):
        self.repo.add_expense(family_id, user_id, amount, category, comment)

    def latest_text(self, family_id: int) -> str:
        rows = self.repo.latest(family_id)
        if not rows:
            return "💰 Пока нет расходов."
        lines = ["💰 Последние расходы:"]
        for r in rows:
            comment = f" — {r['comment']}" if r["comment"] else ""
            lines.append(f"• {r['full_name']}: {r['amount']:.2f} ₽ [{r['category']}] {comment}")
        return "\n".join(lines)

    def summary_text(self, family_id: int) -> str:
        total, by_cat = self.repo.summary(family_id)
        lines = [f"💳 Итого расходов: {total:.2f} ₽", "По категориям:"]
        lines.extend([f"• {row['category']}: {row['t']:.2f} ₽" for row in by_cat])
        return "\n".join(lines)
