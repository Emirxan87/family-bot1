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
from keyboards.main_menu import main_menu_keyboard
from repos.states_repo import StatesRepo
from states import ADDING_SHOPPING_ITEM

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
states_repo = StatesRepo()

MENU_BUTTON_TEXTS = {
    "🛒 Покупки",
    "📅 Календарь",
    "💰 Расходы",
    "📸 Моменты",
    "👨‍👩‍👧‍👦 Семья",
    "⚙️ Ещё",
    "🏠 Главное меню",
    "📋 Мои списки",
    "➕ Добавить товар",
    "➕ Добавить событие",
    "📆 Сегодня",
    "➕ Добавить расход",
    "📃 Последние расходы",
    "📊 Сводка",
    "➕ Добавить момент",
    "🖼 Лента моментов",
    "⏭ Пропустить",
    "🧾 Активность семьи",
    "📍 Последние геопозиции",
    "➕ Создать семью",
    "🔑 Вступить по коду",
    "👥 Участники",
}


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    state, _ = states_repo.get_state(user_id)

    if state == ADDING_SHOPPING_ITEM and text in MENU_BUTTON_TEXTS:
        states_repo.clear_state(user_id)

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
    elif text in {"➕ Создать семью", "🔑 Вступить по коду", "👥 Участники"}:
        await family_router(update, context)
    elif text in {"📋 Мои списки", "➕ Добавить товар"}:
        await shopping_router(update, context)
    elif text in {"➕ Добавить событие", "📆 Сегодня"}:
        await calendar_router(update, context)
    elif text in {"➕ Добавить расход", "📃 Последние расходы", "📊 Сводка"}:
        await expenses_router(update, context)
    elif text in {"➕ Добавить момент", "🖼 Лента моментов", "⏭ Пропустить"}:
        await memories_router(update, context)
    elif text in {"🧾 Активность семьи", "📍 Последние геопозиции"}:
        await settings_router(update, context)
    else:
        await family_router(update, context)
        await shopping_router(update, context)
        await calendar_router(update, context)
        await expenses_router(update, context)
        await memories_router(update, context)
        await settings_router(update, context)


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
