import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from keyboards.calendar import (
    calendar_menu_keyboard,
    event_date_keyboard,
    event_participant_keyboard,
    event_saved_actions_keyboard,
    event_time_keyboard,
    event_type_keyboard,
    members_keyboard,
)
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.calendar_service import CalendarService
from services.notification_service import NotificationService
from utils.display_name import preferred_display_name
from states import (
    ADDING_EVENT_DATE,
    ADDING_EVENT_DATE_CUSTOM,
    ADDING_EVENT_PARTICIPANT,
    ADDING_EVENT_PARTICIPANT_CUSTOM,
    ADDING_EVENT_TIME,
    ADDING_EVENT_TIME_CUSTOM,
    ADDING_EVENT_TITLE,
    VIEWING_EVENTS_BY_DATE,
)

logger = logging.getLogger(__name__)

users_repo = UsersRepo()
states_repo = StatesRepo()
calendar_service = CalendarService()
activity_service = ActivityService()
notify_service = NotificationService()

FAST_TYPE_SET = {
    "🏥 Врач",
    "🎂 День рождения",
    "🏫 Школа / садик",
    "💼 Работа",
    "🛒 Покупки / дела",
    "🚗 Поездка",
    "🧾 Платёж",
    "📌 Другое",
}


async def calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Календарь: выберите действие 👇", reply_markup=calendar_menu_keyboard())


async def calendar_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return

    if text == "📆 Сегодня":
        text = "📅 Сегодня"

    state, payload = states_repo.get_state(user_id)

    if text == "❌ Отмена":
        states_repo.clear_state(user_id)
        await update.message.reply_text("Добавление события отменено.", reply_markup=calendar_menu_keyboard())
        return

    if text == "➕ Добавить событие":
        logger.info("Start add event flow: user_id=%s family_id=%s", user_id, user["family_id"])
        states_repo.set_state(user_id, ADDING_EVENT_TITLE, {})
        await update.message.reply_text("Шаг 1/4. Что за событие?\nВыберите быстрый тип или введите свой текст.", reply_markup=event_type_keyboard())
        return
    if text == "📅 Сегодня":
        await update.message.reply_text(calendar_service.today_text(user["family_id"]))
        return
    if text == "🌤 Завтра":
        await update.message.reply_text(calendar_service.tomorrow_text(user["family_id"]))
        return
    if text == "📋 Ближайшие 7 дней":
        await update.message.reply_text(calendar_service.upcoming_week_text(user["family_id"]))
        return
    if text == "👨‍👩‍👧 Все семейные события":
        await update.message.reply_text(calendar_service.all_family_events_text(user["family_id"]))
        return
    if text == "🗓 По дате":
        states_repo.set_state(user_id, VIEWING_EVENTS_BY_DATE, {})
        await update.message.reply_text("Введите дату в формате ГГГГ-ММ-ДД")
        return
    if text == "📋 К событиям":
        states_repo.clear_state(user_id)
        await update.message.reply_text("Календарь", reply_markup=calendar_menu_keyboard())
        return
    if text == "🔔 Напоминание":
        await update.message.reply_text("Скоро добавим удобные напоминания для событий 🙌", reply_markup=calendar_menu_keyboard())
        return
    if text == "🏠 Главное меню":
        states_repo.clear_state(user_id)
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
        return

    if state == ADDING_EVENT_TITLE:
        if not text:
            await update.message.reply_text("Введите название события или выберите готовый тип.", reply_markup=event_type_keyboard())
            return
        payload["title"] = text
        payload["event_type"] = text if text in FAST_TYPE_SET else "📌 Другое"
        states_repo.set_state(user_id, ADDING_EVENT_DATE, payload)
        await update.message.reply_text("Шаг 2/4. Когда событие?", reply_markup=event_date_keyboard())
        return

    if state == ADDING_EVENT_DATE:
        if text == "📅 Сегодня":
            payload["event_date"] = datetime.now().strftime("%Y-%m-%d")
        elif text == "🌤 Завтра":
            payload["event_date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif text == "🗓 Выбрать дату":
            states_repo.set_state(user_id, ADDING_EVENT_DATE_CUSTOM, payload)
            await update.message.reply_text("Введите дату в формате ГГГГ-ММ-ДД")
            return
        else:
            await update.message.reply_text("Выберите дату кнопкой или нажмите «🗓 Выбрать дату».", reply_markup=event_date_keyboard())
            return
        states_repo.set_state(user_id, ADDING_EVENT_TIME, payload)
        await update.message.reply_text("Шаг 3/4. Во сколько?", reply_markup=event_time_keyboard())
        return

    if state == ADDING_EVENT_DATE_CUSTOM:
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            logger.warning("Date parse failed: user_id=%s value=%s", user_id, text)
            await update.message.reply_text("Неверная дата. Формат: ГГГГ-ММ-ДД")
            return
        payload["event_date"] = text
        states_repo.set_state(user_id, ADDING_EVENT_TIME, payload)
        await update.message.reply_text("Шаг 3/4. Во сколько?", reply_markup=event_time_keyboard())
        return

    if state == ADDING_EVENT_TIME:
        mapping = {
            "Без времени": None,
            "🌅 Утро": "09:00",
            "☀️ День": "14:00",
            "🌆 Вечер": "19:00",
        }
        if text in mapping:
            payload["event_time"] = mapping[text]
        elif text == "⏰ Ввести время":
            states_repo.set_state(user_id, ADDING_EVENT_TIME_CUSTOM, payload)
            await update.message.reply_text("Введите время в формате ЧЧ:ММ")
            return
        else:
            await update.message.reply_text("Выберите вариант времени кнопкой.", reply_markup=event_time_keyboard())
            return
        states_repo.set_state(user_id, ADDING_EVENT_PARTICIPANT, payload)
        await update.message.reply_text("Шаг 4/4. Для кого событие?", reply_markup=event_participant_keyboard())
        return

    if state == ADDING_EVENT_TIME_CUSTOM:
        try:
            datetime.strptime(text, "%H:%M")
        except ValueError:
            logger.warning("Time parse failed: user_id=%s value=%s", user_id, text)
            await update.message.reply_text("Неверное время. Формат: ЧЧ:ММ")
            return
        payload["event_time"] = text
        states_repo.set_state(user_id, ADDING_EVENT_PARTICIPANT, payload)
        await update.message.reply_text("Шаг 4/4. Для кого событие?", reply_markup=event_participant_keyboard())
        return

    if state == ADDING_EVENT_PARTICIPANT:
        if text == "На меня":
            payload["is_family"] = 0
            payload["participant_user_id"] = user_id
            payload["participant_label"] = "Я"
        elif text == "👨‍👩‍👧 Общее":
            payload["is_family"] = 1
            payload["participant_user_id"] = None
            payload["participant_label"] = "Общее"
        elif text == "На другого члена семьи":
            members = [m for m in users_repo.list_family_members(user["family_id"]) if m["telegram_id"] != user_id]
            if not members:
                await update.message.reply_text("Других участников пока нет. Выберите «На меня» или «Общее».", reply_markup=event_participant_keyboard())
                return
            payload["member_map"] = {preferred_display_name(m): m["telegram_id"] for m in members}
            states_repo.set_state(user_id, ADDING_EVENT_PARTICIPANT_CUSTOM, payload)
            await update.message.reply_text("Выберите участника:", reply_markup=members_keyboard(list(payload["member_map"].keys())))
            return
        else:
            await update.message.reply_text("Выберите, для кого событие.", reply_markup=event_participant_keyboard())
            return
        await _save_event(update, context, user, payload)
        return

    if state == ADDING_EVENT_PARTICIPANT_CUSTOM:
        member_map = payload.get("member_map", {})
        participant_id = member_map.get(text)
        if not participant_id:
            await update.message.reply_text("Выберите участника кнопкой.", reply_markup=members_keyboard(list(member_map.keys())))
            return
        payload["is_family"] = 0
        payload["participant_user_id"] = participant_id
        payload["participant_label"] = text
        await _save_event(update, context, user, payload)
        return

    if state == VIEWING_EVENTS_BY_DATE:
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            logger.warning("Date parse failed in list by date: user_id=%s value=%s", user_id, text)
            await update.message.reply_text("Неверная дата. Формат: ГГГГ-ММ-ДД")
            return
        states_repo.clear_state(user_id)
        await update.message.reply_text(
            calendar_service.events_text_for_date(user["family_id"], text, f"🗓 События на {text}")
        )


async def _save_event(update: Update, context: ContextTypes.DEFAULT_TYPE, user, payload: dict):
    event_id = calendar_service.add_event(
        family_id=user["family_id"],
        creator_user_id=user["telegram_id"],
        participant_user_id=payload.get("participant_user_id"),
        title=payload["title"],
        event_type=payload.get("event_type", "📌 Другое"),
        date_str=payload["event_date"],
        time_str=payload.get("event_time"),
        is_family=payload.get("is_family", 1),
    )
    logger.info("Event saved: id=%s family_id=%s creator=%s", event_id, user["family_id"], user["telegram_id"])
    activity_service.log(user["family_id"], user["telegram_id"], "event_add", f"создал(а) событие «{payload['title']}»")
    await notify_service.notify_family(
        context.bot,
        user["family_id"],
        user["telegram_id"],
        f"📅 {preferred_display_name(user)} добавил(а) событие: {payload['title']} ({payload['event_date']})",
    )
    states_repo.clear_state(user["telegram_id"])
    await update.message.reply_text(
        calendar_service.saved_event_summary(payload),
        reply_markup=event_saved_actions_keyboard(include_reminder=True),
    )
