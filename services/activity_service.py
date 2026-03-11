from repos.activity_repo import ActivityRepo


class ActivityService:
    def __init__(self):
        self.repo = ActivityRepo()

    def log(self, family_id: int, actor_id: int, action_type: str, details: str) -> None:
        self.repo.add(family_id, actor_id, action_type, details)

    def latest_text(self, family_id: int) -> str:
        rows = self.repo.latest(family_id)
        if not rows:
            return "Пока активность пустая."
        lines = ["🧾 Последние действия:"]
        for row in rows:
            lines.append(f"• {row['actor_name']}: {row['details']}")
        return "\n".join(lines)
