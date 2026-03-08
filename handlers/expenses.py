from telegram import Update
from telegram.ext import ContextTypes

from database import cursor, conn, get_user_family_id
from keyboards import (
    EXPENSE_CATEGORIES,
    get_main_keyboard,
    get_expense_category_keyboard,
    get_cancel_keyboard,
)


def normalize_expense_category(text: str) -> str:
    if text.startswith("🍎"):
        return "Еда"
    if text.startswith("🚕"):
        return "Транспорт"
    if text.startswith("👶"):
        return "Дети"
    if text.startswith("🏠"):
        return "Дом"
    if text.startswith("💊"):
        return "Здоровье"
    if text.startswith("🎉"):
        return "Развлечения"
    return "Другое"


def parse_amount_and_description(text: str):
    parts = text.strip().split()
    if len(parts) < 2:
        return None, None

    raw = parts[0].replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        return None, None

    description = " ".join(parts[1:]).strip()
    if amount <= 0 or not description:
        return None, None

    return amount, description


def clear_expense_modes(context: ContextTypes.DEFAULT_TYPE):
    for key in [
        "waiting_for_expense_category",
        "waiting_for_expense_input",
        "selected_expense_category",
    ]:
        context.user_data.pop(key, None)


async def start_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_expense_modes(context)
    context.user_data["waiting_for_expense_category"] = True

    await update.message.reply_text(
        "Выбери категорию расхода:",
        reply_markup=get_expense_category_keyboard()
    )


async def handle_expense_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_expense_category"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_expense_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if text not in EXPENSE_CATEGORIES:
        await update.message.reply_text(
            "Выбери категорию кнопкой ниже",
            reply_markup=get_expense_category_keyboard()
        )
        return True

    category = normalize_expense_category(text)
    context.user_data["waiting_for_expense_category"] = False
    context.user_data["waiting_for_expense_input"] = True
    context.user_data["selected_expense_category"] = category

    await update.message.reply_text(
        f"Категория выбрана: {category}\n\n"
        f"Теперь напиши сумму и описание.\n"
        f"Пример:\n250 молоко",
        reply_markup=get_cancel_keyboard()
    )
    return True


async def handle_expense_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_expense_input"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        clear_expense_modes(context)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    amount, description = parse_amount_and_description(text)
    if amount is None:
        await update.message.reply_text(
            "Неправильный формат.\nНапиши так:\n250 молоко",
            reply_markup=get_cancel_keyboard()
        )
        return True

    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        clear_expense_modes(context)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    category = context.user_data.get("selected_expense_category", "Другое")

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, category, description) VALUES (?, ?, ?, ?)",
        (family_id, amount, category, description)
    )
    conn.commit()

    clear_expense_modes(context)

    await update.message.reply_text(
        f"Расход добавлен: {amount:.2f} — {category} — {description}",
        reply_markup=get_main_keyboard()
    )
    return True


async def show_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        """
        SELECT amount, category, description
        FROM expenses
        WHERE family_id=?
        ORDER BY id DESC
        LIMIT 15
        """,
        (family_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "Расходов нет",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📖 Последние расходы:\n\n"
    for amount, category, description in rows:
        text += f"• {amount:.2f} — {category} — {description}\n"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        """
        SELECT category, SUM(amount)
        FROM expenses
        WHERE family_id=?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        """,
        (family_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "Пока нет данных для статистики",
            reply_markup=get_main_keyboard()
        )
        return

    total_sum = 0.0
    text = "📊 Статистика по категориям:\n\n"

    for category, amount in rows:
        total_sum += amount or 0
        text += f"• {category} — {amount:.2f}\n"

    text += f"\n💰 Всего: {total_sum:.2f}"

    await update.message.reply_text(
        text,
        reply_markup=get_main_keyboard()
    )


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute("SELECT SUM(amount) FROM expenses WHERE family_id=?", (family_id,))
    total_sum = cursor.fetchone()[0] or 0

    await update.message.reply_text(
        f"💰 Всего потрачено: {total_sum:.2f}",
        reply_markup=get_main_keyboard()
    )
