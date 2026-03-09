from datetime import datetime

from repos.calendar_repo import CalendarRepo


class CalendarService:
    def __init__(self):
        self.repo = CalendarRepo()

    def add_event(self, family_id: int, user_id: int, title: str, date_str: str, time_str: str | None, is_family: int = 1):
        self.repo.add_event(family_id, user_id, title, date_str, time_str, is_family)

    def today_text(self, family_id: int) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        events = self.repo.events_for_date(family_id, today)
        if not events:
            return "📅 На сегодня событий нет."
        lines = ["📅 События на сегодня:"]
        for e in events:
            time = e["event_time"] or "в течение дня"
            scope = "семейное" if e["is_family"] else "личное"
            lines.append(f"• {time} — {e['title']} ({e['full_name']}, {scope})")
        return "\n".join(lines)
