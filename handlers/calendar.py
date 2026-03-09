from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from keyboards.calendar import calendar_menu_keyboard
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from repos.users_repo import UsersRepo
from services.activity_service import ActivityService
from services.calendar_service import CalendarService
from services.notification_service import NotificationService
from states import ADDING_EVENT_DATE, ADDING_EVENT_TIME, ADDING_EVENT_TITLE

users_repo = UsersRepo()
states_repo = StatesRepo()
calendar_service = CalendarService()
activity_service = ActivityService()
notify_service = NotificationService()


async def calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Календарь 📅", reply_markup=calendar_menu_keyboard())


async def calendar_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    user = users_repo.get_user(user_id)
    if not user or not user["family_id"]:
        await update.message.reply_text("Сначала присоединитесь к семье.", reply_markup=main_menu_keyboard())
        return
    state, payload = states_repo.get_state(user_id)

    if text == "➕ Добавить событие":
        states_repo.set_state(user_id, ADDING_EVENT_TITLE, {})
        await update.message.reply_text("Введите название события:")
        return
    if text == "📆 Сегодня":
        await update.message.reply_text(calendar_service.today_text(user["family_id"]))
        return
    if text == "🏠 Главное меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())
        return

    if state == ADDING_EVENT_TITLE:
        payload["title"] = text
        states_repo.set_state(user_id, ADDING_EVENT_DATE, payload)
        await update.message.reply_text("Введите дату в формате ГГГГ-ММ-ДД")
    elif state == ADDING_EVENT_DATE:
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Нужен формат ГГГГ-ММ-ДД")
            return
        payload["event_date"] = text
        states_repo.set_state(user_id, ADDING_EVENT_TIME, payload)
        await update.message.reply_text("Введите время ЧЧ:ММ или '-' если не важно")
    elif state == ADDING_EVENT_TIME:
        event_time = None if text == "-" else text
        calendar_service.add_event(
            user["family_id"], user_id, payload["title"], payload["event_date"], event_time, is_family=1
        )
        states_repo.clear_state(user_id)
        activity_service.log(user["family_id"], user_id, "event_add", f"создал(а) событие «{payload['title']}»")
        await notify_service.notify_family(
            context.bot,
            user["family_id"],
            user_id,
            f"📅 {user['full_name']} добавил(а) событие: {payload['title']} ({payload['event_date']})",
        )
        await update.message.reply_text("Событие добавлено ✅", reply_markup=calendar_menu_keyboard())
