import logging
import os
import re

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import init_db
from keyboards import get_main_keyboard

from handlers.family import start, join, family, help_command
from handlers.shopping import (
    handle_shopping_section_choice,
    handle_shopping_items_input,
    handle_mark_done_scope,
    handle_clear_done_scope,
    handle_quick_shopping_input,
    show_all_shopping,
    start_add_shopping,
    show_store_view,
    show_pharmacy_view,
    show_online_view,
    start_mark_done,
    start_clear_done,
)
from handlers.expenses import (
    handle_expense_category_choice,
    handle_expense_input,
    show_expenses,
    stats,
    total,
    start_expense,
)
from handlers.calendar import (
    start_add_event,
    handle_event_date,
    handle_event_start,
    handle_event_end,
    handle_event_title,
    show_my_day,
    show_family_day,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def normalize_text(value: str) -> str:
    return (value or "").strip()


def normalize_command_text(value: str) -> str:
    text = normalize_text(value).lower()

    text = re.sub(r"^[^\wа-яё]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я не понял, что нужно сделать.\n\nВыбери действие в меню.",
        reply_markup=get_main_keyboard(),
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = normalize_text(update.message.text)
    text = normalize_command_text(raw_text)

    # Пошаговые сценарии
    if await handle_shopping_section_choice(update, context):
        return

    if await handle_shopping_items_input(update, context):
        return

    if await handle_mark_done_scope(update, context):
        return

    if await handle_clear_done_scope(update, context):
        return

    if await handle_expense_category_choice(update, context):
        return

    if await handle_expense_input(update, context):
        return

    if await handle_event_date(update, context):
        return

    if await handle_event_start(update, context):
        return

    if await handle_event_end(update, context):
        return

    if await handle_event_title(update, context):
        return

    # Главное меню
    if text == "что купить?":
        await show_all_shopping(update, context)
        return

    if text == "добавить покупки":
        await start_add_shopping(update, context)
        return

    if text == "магазин":
        await show_store_view(update, context)
        return

    if text == "аптека":
        await show_pharmacy_view(update, context)
        return

    if text == "онлайн":
        await show_online_view(update, context)
        return

    if text == "куплено":
        await start_mark_done(update, context)
        return

    if text == "очистить купленное":
        await start_clear_done(update, context)
        return

    if text == "расход":
        await start_expense(update, context)
        return

    if text == "расходы":
        await show_expenses(update, context)
        return

    if text == "статистика":
        await stats(update, context)
        return

    if text == "итого":
        await total(update, context)
        return

    if text == "мой день":
        await show_my_day(update, context)
        return

    if text == "день семьи":
        await show_family_day(update, context)
        return

    if text == "событие":
        await start_add_event(update, context)
        return

    if text == "семья":
        await family(update, context)
        return

    if text == "помощь":
        await help_command(update, context)
        return

    # Быстрое добавление покупок обычным текстом
    if await handle_quick_shopping_input(update, context):
        return

    await unknown_text(update, context)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден BOT_TOKEN. Добавь его в Railway Variables.")

    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("family", family))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("expenses", show_expenses))
    application.add_handler(CommandHandler("total", total))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    print("Бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main()
