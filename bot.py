import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
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

TOKEN = "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я не понял, что нужно сделать.\n\n"
        "Выбери действие в меню.",
        reply_markup=get_main_keyboard()
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

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

    if text == "🛒 Что купить?":
        await show_all_shopping(update, context)
        return

    if text == "➕ Добавить покупки":
        await start_add_shopping(update, context)
        return

    if text == "🏪 Магазин":
        await show_store_view(update, context)
        return

    if text == "💊 Аптека":
        await show_pharmacy_view(update, context)
        return

    if text == "📦 Онлайн":
        await show_online_view(update, context)
        return

    if text == "✅ Куплено":
        await start_mark_done(update, context)
        return

    if text == "🧹 Очистить купленное":
        await start_clear_done(update, context)
        return

    if text == "💸 Расход":
        await start_expense(update, context)
        return

    if text == "📖 Расходы":
        await show_expenses(update, context)
        return

    if text == "📊 Статистика":
        await stats(update, context)
        return

    if text == "💰 Итого":
        await total(update, context)
        return

    if text == "📅 Мой день":
        await show_my_day(update, context)
        return

    if text == "👨‍👩‍👧 День семьи":
        await show_family_day(update, context)
        return

    if text == "➕ Событие":
        await start_add_event(update, context)
        return

    if text == "👨‍👩‍👧 Семья":
        await family(update, context)
        return

    if text == "ℹ️ Помощь":
        await help_command(update, context)
        return

    await unknown_text(update, context)


def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("family", family))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("expenses", show_expenses))
    app.add_handler(CommandHandler("total", total))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
