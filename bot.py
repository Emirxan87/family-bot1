import logging
import random
import sqlite3

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = "7925302773:AAHoe8mSYSVtNYL24qElXa9AcI9hI8YwsAA"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

conn = sqlite3.connect("family.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS families (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    family_id INTEGER,
    name TEXT,
    role TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shopping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    item TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER,
    amount REAL,
    description TEXT
)
""")

conn.commit()


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📋 Покупки", "💸 Расход"],
            ["👨‍👩‍👧 Семья", "💰 Итого"],
            ["📖 Расходы", "ℹ️ Помощь"],
            ["❌ Удалить покупку", "🗑 Удалить расход"],
        ],
        resize_keyboard=True
    )


def get_user_family_id(telegram_id: int):
    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def parse_amount(text: str):
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    user = cursor.fetchone()

    if user:
        await update.message.reply_text(
            "Вы уже в семье 👍\n\nВыберите действие в меню ниже.",
            reply_markup=get_main_keyboard()
        )
        return

    code = str(random.randint(1000, 9999))
    while True:
        cursor.execute("SELECT id FROM families WHERE code=?", (code,))
        if not cursor.fetchone():
            break
        code = str(random.randint(1000, 9999))

    cursor.execute("INSERT INTO families (code) VALUES (?)", (code,))
    family_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "parent")
    )
    conn.commit()

    await update.message.reply_text(
        f"Семья создана 👨‍👩‍👧\n\n"
        f"Код семьи: {code}\n\n"
        f"Пусть другие участники напишут:\n"
        f"/join {code}",
        reply_markup=get_main_keyboard()
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Напиши так: /join 1234",
            reply_markup=get_main_keyboard()
        )
        return

    telegram_id = update.effective_user.id
    name = update.effective_user.first_name or "Участник"
    code = context.args[0].strip()

    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    if cursor.fetchone():
        await update.message.reply_text(
            "Ты уже в семье 👍",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute("SELECT id FROM families WHERE code=?", (code,))
    fam = cursor.fetchone()

    if not fam:
        await update.message.reply_text(
            "Семья не найдена",
            reply_markup=get_main_keyboard()
        )
        return

    family_id = fam[0]

    cursor.execute(
        "INSERT INTO users (telegram_id, family_id, name, role) VALUES (?,?,?,?)",
        (telegram_id, family_id, name, "member")
    )
    conn.commit()

    await update.message.reply_text(
        "Ты присоединился к семье 👨‍👩‍👧",
        reply_markup=get_main_keyboard()
    )


async def family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute("SELECT name, role FROM users WHERE family_id=?", (family_id,))
    members = cursor.fetchall()

    text = "👨‍👩‍👧 Семья:\n\n"
    for name, role in members:
        role_text = "родитель" if role == "parent" else "участник"
        text += f"• {name} — {role_text}\n"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = (update.message.text or "").strip()

    family_id = get_user_family_id(telegram_id)
    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        "INSERT INTO shopping (family_id, item) VALUES (?,?)",
        (family_id, text)
    )
    conn.commit()

    await update.message.reply_text(
        f"Добавил в покупки: {text}",
        reply_markup=get_main_keyboard()
    )


async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        "SELECT item FROM shopping WHERE family_id=? ORDER BY id DESC",
        (family_id,)
    )
    items = cursor.fetchall()

    if not items:
        await update.message.reply_text(
            "Список покупок пуст",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📋 Покупки:\n\n"
    for i, item in enumerate(items, start=1):
        text += f"{i}. {item[0]}\n"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = (update.message.text or "").strip()

    family_id = get_user_family_id(telegram_id)
    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    amount, description = parse_amount(text)

    if amount is None:
        await add_item(update, context)
        return

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, description) VALUES (?,?,?)",
        (family_id, amount, description)
    )
    conn.commit()

    await update.message.reply_text(
        f"Расход добавлен: {amount:.2f} — {description}",
        reply_markup=get_main_keyboard()
    )


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
        "SELECT amount, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
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
    for i, (amount, desc) in enumerate(rows, start=1):
        text += f"{i}. {amount:.2f} — {desc}\n"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return

    cursor.execute(
        "SELECT SUM(amount) FROM expenses WHERE family_id=?",
        (family_id,)
    )
    total_sum = cursor.fetchone()[0] or 0

    await update.message.reply_text(
        f"💰 Всего потрачено: {total_sum:.2f}",
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Как пользоваться ботом:\n\n"
        "1. Нажми /start\n"
        "2. Чтобы добавить участника семьи, дай ему код и пусть он напишет /join 1234\n"
        "3. Чтобы добавить покупку, просто напиши:\n"
        "молоко\n\n"
        "4. Чтобы добавить расход, напиши:\n"
        "250 молоко\n\n"
        "5. Чтобы удалить покупку, нажми:\n"
        "❌ Удалить покупку\n"
        "и потом отправь номер\n\n"
        "6. Чтобы удалить расход, нажми:\n"
        "🗑 Удалить расход\n"
        "и потом отправь номер"
    )
    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def start_delete_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text("Сначала нажми /start", reply_markup=get_main_keyboard())
        return

    cursor.execute(
        "SELECT id, item FROM shopping WHERE family_id=? ORDER BY id DESC",
        (family_id,)
    )
    items = cursor.fetchall()

    if not items:
        await update.message.reply_text("Список покупок пуст", reply_markup=get_main_keyboard())
        return

    context.user_data["delete_mode"] = "shopping"
    context.user_data["shopping_ids"] = [row[0] for row in items]

    text = "❌ Выбери номер покупки для удаления:\n\n"
    for i, (_, item) in enumerate(items, start=1):
        text += f"{i}. {item}\n"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def start_delete_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        await update.message.reply_text("Сначала нажми /start", reply_markup=get_main_keyboard())
        return

    cursor.execute(
        "SELECT id, amount, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
        (family_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Расходов нет", reply_markup=get_main_keyboard())
        return

    context.user_data["delete_mode"] = "expenses"
    context.user_data["expense_ids"] = [row[0] for row in rows]

    text = "🗑 Выбери номер расхода для удаления:\n\n"
    for i, (_, amount, desc) in enumerate(rows, start=1):
        text += f"{i}. {amount:.2f} — {desc}\n"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def handle_delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if not text.isdigit():
        return False

    number = int(text)
    mode = context.user_data.get("delete_mode")

    if mode == "shopping":
        ids = context.user_data.get("shopping_ids", [])
        if number < 1 or number > len(ids):
            await update.message.reply_text("Неверный номер", reply_markup=get_main_keyboard())
            return True

        item_id = ids[number - 1]
        cursor.execute("DELETE FROM shopping WHERE id=?", (item_id,))
        conn.commit()

        context.user_data.pop("delete_mode", None)
        context.user_data.pop("shopping_ids", None)

        await update.message.reply_text("Покупка удалена ✅", reply_markup=get_main_keyboard())
        return True

    if mode == "expenses":
        ids = context.user_data.get("expense_ids", [])
        if number < 1 or number > len(ids):
            await update.message.reply_text("Неверный номер", reply_markup=get_main_keyboard())
            return True

        expense_id = ids[number - 1]
        cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()

        context.user_data.pop("delete_mode", None)
        context.user_data.pop("expense_ids", None)

        await update.message.reply_text("Расход удалён ✅", reply_markup=get_main_keyboard())
        return True

    return False


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    handled_delete = await handle_delete_number(update, context)
    if handled_delete:
        return

    if text == "📋 Покупки":
        await show_list(update, context)
        return

    if text == "💸 Расход":
        await update.message.reply_text(
            "Напиши расход так:\n250 продукты",
            reply_markup=get_main_keyboard()
        )
        return

    if text == "👨‍👩‍👧 Семья":
        await family(update, context)
        return

    if text == "💰 Итого":
        await total(update, context)
        return

    if text == "📖 Расходы":
        await show_expenses(update, context)
        return

    if text == "ℹ️ Помощь":
        await help_command(update, context)
        return

    if text == "❌ Удалить покупку":
        await start_delete_purchase(update, context)
        return

    if text == "🗑 Удалить расход":
        await start_delete_expense(update, context)
        return

    await add_expense(update, context)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("family", family))
    app.add_handler(CommandHandler("list", show_list))
    app.add_handler(CommandHandler("expenses", show_expenses))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
