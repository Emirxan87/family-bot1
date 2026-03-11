import logging
from datetime import datetime, timedelta

from repos.calendar_repo import CalendarRepo

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self):
        self.repo = CalendarRepo()

    def add_event(
        self,
        family_id: int,
        creator_user_id: int,
        participant_user_id: int | None,
        title: str,
        event_type: str,
        date_str: str,
        time_str: str | None,
        is_family: int,
    ) -> int:
        return self.repo.add_event(
            family_id,
            creator_user_id,
            participant_user_id,
            title,
            event_type,
            date_str,
            time_str,
            is_family,
        )

    def events_text_for_date(self, family_id: int, date_str: str, title: str) -> str:
        events = self.repo.events_for_date(family_id, date_str)
        if not events:
            return f"{title}\nНа этот день событий нет."
        return self._format_events(events, title)

    def today_text(self, family_id: int) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.events_text_for_date(family_id, today, "📅 Сегодня")

    def tomorrow_text(self, family_id: int) -> str:
        date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return self.events_text_for_date(family_id, date_str, "🌤 Завтра")

    def upcoming_week_text(self, family_id: int) -> str:
        start = datetime.now().date()
        end = start + timedelta(days=6)
        events = self.repo.events_for_period(family_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if not events:
            logger.info("Calendar period view: no events for family_id=%s", family_id)
            return "📋 Ближайшие 7 дней\nСобытий пока нет."
        logger.info("Calendar period view: family_id=%s, events=%s", family_id, len(events))
        return self._format_events(events, "📋 Ближайшие 7 дней")

    def all_family_events_text(self, family_id: int) -> str:
        start = datetime.now().date()
        end = start + timedelta(days=30)
        events = self.repo.events_for_period(family_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        family_events = [e for e in events if e["is_family"] == 1]
        if not family_events:
            return "👨‍👩‍👧 Ближайшие семейные события\nПока нет запланированных семейных событий."
        return self._format_events(family_events, "👨‍👩‍👧 Ближайшие семейные события")

    def saved_event_summary(self, event: dict) -> str:
        event_time = event["event_time"] or "без времени"
        participant = event.get("participant_label") or "не указан"
        return (
            "✅ Событие сохранено\n"
            f"• Что: {event['title']}\n"
            f"• Дата: {event['event_date']}\n"
            f"• Время: {event_time}\n"
            f"• Участник: {participant}"
        )

    def _format_events(self, events, header: str) -> str:
        lines = [header]
        current_date = None
        for e in events:
            if e["event_date"] != current_date:
                current_date = e["event_date"]
                lines.append("")
                lines.append(self._human_date(current_date))
            event_time = e["event_time"] or "Без времени"
            participant = "Общее" if e["is_family"] else (e["participant_name"] or e["creator_name"])
            lines.append(f"- {event_time} — {e['title']} — {participant}")
        return "\n".join(lines)

    def _human_date(self, date_str: str) -> str:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        if date_obj == today:
            return "Сегодня"
        if date_obj == today + timedelta(days=1):
            return "Завтра"
        return date_obj.strftime("%d.%m.%Y")
