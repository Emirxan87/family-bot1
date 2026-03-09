from repos.shopping_repo import ShoppingRepo


class ShoppingService:
    def __init__(self):
        self.repo = ShoppingRepo()

    def lists(self, family_id: int):
        self.repo.ensure_default_lists(family_id)
        return self.repo.get_lists(family_id)

    def add_item(self, list_id: int, title: str, user_id: int):
        return self.repo.add_item(list_id, title.strip(), user_id)

    def render_list(self, list_id: int) -> str:
        lst = self.repo.get_list(list_id)
        items = self.repo.get_items(list_id)
        if not lst:
            return "Список не найден."
        lines = [f"🛒 {lst['name']}"]
        if not items:
            lines.append("Пока пусто — добавьте первую покупку.")
            return "\n".join(lines)
        for i in items:
            mark = "✅" if i["is_done"] else "⬜"
            who = i["bought_name"] if i["is_done"] else i["added_name"]
            suffix = f" ({who})" if who else ""
            lines.append(f"{mark} {i['title']}{suffix}")
        return "\n".join(lines)

    def toggle_item(self, item_id: int, user_id: int):
        self.repo.toggle_item(item_id, user_id)
        return self.repo.get_item_by_id(item_id)
