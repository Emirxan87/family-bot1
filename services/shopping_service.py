from repos.shopping_repo import ShoppingRepo


class ShoppingService:
    def __init__(self):
        self.repo = ShoppingRepo()

    def lists(self, family_id: int):
        self.repo.ensure_default_lists(family_id)
        return self.repo.get_lists(family_id)

    def add_item(self, list_id: int, title: str, user_id: int):
        cleaned = title.strip()
        if not cleaned:
            return None
        return self.repo.add_item(list_id, cleaned, user_id)

    def get_visible_items(self, list_id: int):
        return self.repo.get_visible_items(list_id)

    def render_list(self, list_id: int) -> str:
        lst = self.repo.get_list(list_id)
        items = self.repo.get_visible_items(list_id)
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
            lines.append(f"{mark} {i['display_title']}{suffix}")
        return "\n".join(lines)

    def toggle_item(self, item_id: int, user_id: int):
        self.repo.toggle_item(item_id, user_id)
        return self.repo.get_item_by_id(item_id)

    def mark_all_done(self, list_id: int, user_id: int) -> int:
        return self.repo.mark_all_done(list_id, user_id)

    def restore_all_active(self, list_id: int) -> int:
        return self.repo.restore_all_active(list_id)

    def clear_done(self, list_id: int) -> int:
        return self.repo.clear_done(list_id)

    def clear_list(self, list_id: int) -> int:
        return self.repo.clear_list(list_id)
