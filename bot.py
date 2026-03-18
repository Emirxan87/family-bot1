import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from handlers.callbacks import handle_callbacks
from handlers.calendar import calendar_menu, calendar_router
from handlers.expenses import expenses_menu, expenses_router
from handlers.family import family_menu, family_router
from handlers.memories import (
    memories_menu,
    memories_router,
    memory_location_handler,
    memory_photo_handler,
)
from handlers.settings import location_handler, settings_menu, settings_router
from handlers.shopping import shopping_menu, shopping_router
from handlers.start import help_command, start, to_main_menu
from keyboards.shopping import (
    BTN_ADD_MORE,
    BTN_MAIN_MENU_SHORT,
    BTN_NEW_LIST,
    BTN_OPEN_LIST,
)
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from states import (
    ADDING_EVENT_DATE,
    ADDING_EVENT_DATE_CUSTOM,
    ADDING_EVENT_PARTICIPANT,
    ADDING_EVENT_PARTICIPANT_CUSTOM,
    ADDING_EVENT_TIME,
    ADDING_EVENT_TIME_CUSTOM,
    ADDING_EVENT_TITLE,
    ADDING_EXPENSE_ACTOR,
    ADDING_EXPENSE_AMOUNT,
    ADDING_EXPENSE_CATEGORY,
    ADDING_EXPENSE_COMMENT,
    ADDING_EXPENSE_SUBCATEGORY,
    SELECTING_EXPENSE_STATS_PERIOD,
    ADDING_SHOPPING_ITEM,
    AWAITING_FAMILY_CUSTOM_ROLE,
    AWAITING_FAMILY_ROLE,
    INVITING_FAMILY_MEMBER,
    VIEWING_EVENTS_BY_DATE,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
states_repo = StatesRepo()

FAMILY_STATES = {INVITING_FAMILY_MEMBER, AWAITING_FAMILY_ROLE, AWAITING_FAMILY_CUSTOM_ROLE}

MENU_BUTTON_TEXTS = {
    "🛒 Покупки",
    "📅 Календарь",
    "💰 Расходы",
    "📸 Моменты",
    "👨‍👩‍👧‍👦 Семья",
    "⚙️ Ещё",
    "🏠 Главное меню",
    BTN_MAIN_MENU_SHORT,
    "🛒 Что купить",
    "📋 Мои списки",
    "📋 Открыть списки",
    "➕ Добавить товар",
    BTN_ADD_MORE,
    BTN_OPEN_LIST,
    BTN_NEW_LIST,
    "✅ Отметить всё купленным",
    "✅ Отметить несколько",
    "↩ Назад",
    "♻️ Вернуть всё в активные",
    "🧹 Очистить купленные",
    "🗑 Очистить список",
    "⬅️ Назад",
    "❌ Отмена",
    "✅ Подтвердить",
    "➕ Добавить событие",
    "📅 Сегодня",
    "📆 Сегодня",
    "🌤 Завтра",
    "📋 Ближайшие 7 дней",
    "🗓 По дате",
    "👨‍👩‍👧 Все семейные события",
    "📋 К событиям",
    "➕ Ещё событие",
    "🔔 Напоминание",
    "🏥 Врач",
    "🎂 День рождения",
    "🏫 Школа / садик",
    "💼 Работа",
    "🛒 Покупки / дела",
    "🚗 Поездка",
    "🧾 Платёж",
    "📌 Другое",
    "🗓 Выбрать дату",
    "Без времени",
    "🌅 Утро",
    "☀️ День",
    "🌆 Вечер",
    "⏰ Ввести время",
    "На меня",
    "На другого члена семьи",
    "👨‍👩‍👧 Общее",
    "➖ Расход",
    "➕ Поступление",
    "➕ Ещё расход",
    "➕ Ещё поступление",
    "📃 Последние операции",
    "📊 Статистика",
    "👤 Кто потратил",
    "👤 Кто получил",
    "💬 Комментарий",
    "📅 Сегодня",
    "🗓 7 дней",
    "📆 Месяц",
    "📊 Квартал",
    "📈 Год",
    "➕ Добавить момент",
    "🖼 Лента моментов",
    "⏭ Пропустить",
    "🧾 Активность семьи",
    "📍 Последние геопозиции",
    "➕ Создать семью",
    "🔗 Вступить по ссылке/коду",
    "🔑 Вступить по коду",
    "➕ Пригласить",
    "👥 Участники",
    "✏️ Роли",
    "🔑 Новый код и ссылка",
}

EXPENSE_STATS_PERIOD_BUTTONS = {"📅 Сегодня", "🗓 7 дней", "📆 Месяц", "📊 Квартал", "📈 Год"}


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    state, _ = states_repo.get_state(user_id)

    finance_states = {
        ADDING_EXPENSE_CATEGORY,
        ADDING_EXPENSE_SUBCATEGORY,
        ADDING_EXPENSE_AMOUNT,
        ADDING_EXPENSE_COMMENT,
        ADDING_EXPENSE_ACTOR,
        SELECTING_EXPENSE_STATS_PERIOD,
    }
    calendar_states = {
        ADDING_EVENT_TITLE,
        ADDING_EVENT_DATE,
        ADDING_EVENT_DATE_CUSTOM,
        ADDING_EVENT_TIME,
        ADDING_EVENT_TIME_CUSTOM,
        ADDING_EVENT_PARTICIPANT,
        ADDING_EVENT_PARTICIPANT_CUSTOM,
        VIEWING_EVENTS_BY_DATE,
    }
    if state in finance_states and text in MENU_BUTTON_TEXTS and not (
        state == SELECTING_EXPENSE_STATS_PERIOD and text in EXPENSE_STATS_PERIOD_BUTTONS
    ):
        states_repo.clear_state(user_id)
    if state == ADDING_SHOPPING_ITEM and (text in MENU_BUTTON_TEXTS or text.startswith("✅ Готово (")):
        states_repo.clear_state(user_id)
    if state in calendar_states and text in MENU_BUTTON_TEXTS and text not in {"❌ Отмена"}:
        states_repo.clear_state(user_id)

    if state == SELECTING_EXPENSE_STATS_PERIOD and text in EXPENSE_STATS_PERIOD_BUTTONS:
        await expenses_router(update, context)
        return

    if text == "🛒 Покупки":
        await shopping_menu(update, context)
    elif text == "📅 Календарь":
        await calendar_menu(update, context)
    elif text == "💰 Расходы":
        await expenses_menu(update, context)
    elif text == "📸 Моменты":
        await memories_menu(update, context)
    elif text == "👨‍👩‍👧‍👦 Семья":
        await family_menu(update, context)
    elif text == "⚙️ Ещё":
        await settings_menu(update, context)
    elif text == "🏠 Главное меню":
        await to_main_menu(update, context)
    elif text in {"➕ Создать семью", "🔗 Вступить по ссылке/коду", "🔑 Вступить по коду", "➕ Пригласить", "👥 Участники", "✏️ Роли", "🔑 Новый код и ссылка", "⬅️ Назад"}:
        await family_router(update, context)
    elif text in {
        "🛒 Что купить",
        "📋 Мои списки",
        "📋 Открыть списки",
        "➕ Добавить товар",
        BTN_ADD_MORE,
        BTN_OPEN_LIST,
        BTN_NEW_LIST,
        "✅ Отметить всё купленным",
        "✅ Отметить несколько",
        "↩ Назад",
        "♻️ Вернуть всё в активные",
        "🧹 Очистить купленные",
        "🗑 Очистить список",
        "⬅️ Назад",
        "❌ Отмена",
        "✅ Подтвердить",
        BTN_MAIN_MENU_SHORT,
    } or text.startswith("✅ Готово ("):
        await shopping_router(update, context)
    elif text in {
        "➕ Добавить событие",
        "📅 Сегодня",
        "📆 Сегодня",
        "🌤 Завтра",
        "📋 Ближайшие 7 дней",
        "🗓 По дате",
        "👨‍👩‍👧 Все семейные события",
        "📋 К событиям",
        "➕ Ещё событие",
        "🔔 Напоминание",
        "🏥 Врач",
        "🎂 День рождения",
        "🏫 Школа / садик",
        "💼 Работа",
        "🛒 Покупки / дела",
        "🚗 Поездка",
        "🧾 Платёж",
        "📌 Другое",
        "🗓 Выбрать дату",
        "Без времени",
        "🌅 Утро",
        "☀️ День",
        "🌆 Вечер",
        "⏰ Ввести время",
        "На меня",
        "На другого члена семьи",
        "👨‍👩‍👧 Общее",
    }:
        await calendar_router(update, context)
    elif text in {
        "➖ Расход",
        "➕ Поступление",
        "➕ Ещё расход",
        "➕ Ещё поступление",
        "📃 Последние операции",
        "📊 Статистика",
        "👤 Кто потратил",
        "👤 Кто получил",
        "💬 Комментарий",
        "📅 Сегодня",
        "🗓 7 дней",
        "📆 Месяц",
        "📊 Квартал",
        "📈 Год",
    }:
        await expenses_router(update, context)
    elif text in {"➕ Добавить момент", "🖼 Лента моментов", "⏭ Пропустить"}:
        await memories_router(update, context)
    elif text in {"🧾 Активность семьи", "📍 Последние геопозиции"}:
        await settings_router(update, context)
    else:
        if state in FAMILY_STATES:
            await family_router(update, context)
            return
        if state == ADDING_SHOPPING_ITEM or (state and state.startswith("shopping_")):
            await shopping_router(update, context)
            return
        if state in calendar_states:
            await calendar_router(update, context)
            return
        if state in finance_states:
            await expenses_router(update, context)
            return
        await family_router(update, context)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled Telegram handler error", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла внутренняя ошибка. Попробуйте ещё раз через пару секунд."
            )
        except Exception:
            logger.exception("Failed to send error message to user")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден BOT_TOKEN в переменных окружения.")
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, memory_photo_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.LOCATION, memory_location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_error_handler(on_error)

    print("Family bot is running")
    app.run_polling()


if __name__ == "__main__":
    main()
