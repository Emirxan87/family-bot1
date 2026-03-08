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
    category TEXT,
    description TEXT
)
""")

conn.commit()


def ensure_expenses_schema():
    cursor.execute("PRAGMA table_info(expenses)")
    columns = [row[1] for row in cursor.fetchall()]

    if "category" not in columns:
        cursor.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'Другое'")
        conn.commit()


ensure_expenses_schema()


CATEGORIES = [
    "🍎 Еда",
    "🚕 Транспорт",
    "👶 Дети",
    "🏠 Дом",
    "💊 Здоровье",
    "🎉 Развлечения",
    "📦 Другое",
]


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📋 Покупки", "💸 Расход"],
            ["👨‍👩‍👧 Семья", "💰 Итого"],
            ["📖 Расходы", "📊 Статистика"],
            ["❌ Удалить покупку", "🗑 Удалить расход"],
            ["ℹ️ Помощь"],
        ],
        resize_keyboard=True
    )


def get_category_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🍎 Еда", "🚕 Транспорт"],
            ["👶 Дети", "🏠 Дом"],
            ["💊 Здоровье", "🎉 Развлечения"],
            ["📦 Другое"],
            ["⬅️ Отмена"],
        ],
        resize_keyboard=True
    )


def normalize_category(text: str) -> str:
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


def get_user_family_id(telegram_id: int):
    cursor.execute("SELECT family_id FROM users WHERE telegram_id=?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None


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
        "SELECT amount, category, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
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
    for i, (amount, category, desc) in enumerate(rows, start=1):
        category = category or "Другое"
        text += f"{i}. {amount:.2f} — {category} — {desc}\n"

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

    text = "📊 Статистика по категориям:\n\n"
    total_sum = 0

    for category, amount in rows:
        category = category or "Другое"
        total_sum += amount or 0
        text += f"• {category} — {amount:.2f}\n"

    text += f"\n💰 Всего: {total_sum:.2f}"

    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Как пользоваться ботом:\n\n"
        "1. Нажми /start\n"
        "2. Чтобы добавить участника семьи, дай ему код и пусть он напишет /join 1234\n"
        "3. Чтобы добавить покупку, просто напиши:\n"
        "молоко\n\n"
        "4. Чтобы добавить расход, нажми кнопку 💸 Расход\n"
        "5. Выбери категорию\n"
        "6. Потом напиши сумму и описание:\n"
        "250 молоко\n\n"
        "7. Статистика покажет расходы по категориям"
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
        "SELECT id, amount, category, description FROM expenses WHERE family_id=? ORDER BY id DESC LIMIT 10",
        (family_id,)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Расходов нет", reply_markup=get_main_keyboard())
        return

    context.user_data["delete_mode"] = "expenses"
    context.user_data["expense_ids"] = [row[0] for row in rows]

    text = "🗑 Выбери номер расхода для удаления:\n\n"
    for i, (_, amount, category, desc) in enumerate(rows, start=1):
        category = category or "Другое"
        text += f"{i}. {amount:.2f} — {category} — {desc}\n"

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


async def handle_category_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        context.user_data.pop("waiting_for_category", None)
        context.user_data.pop("selected_category", None)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    if text in CATEGORIES:
        category = normalize_category(text)
        context.user_data["waiting_for_category"] = False
        context.user_data["waiting_for_expense_input"] = True
        context.user_data["selected_category"] = category

        await update.message.reply_text(
            f"Категория выбрана: {category}\n\nТеперь напиши сумму и описание.\nПример:\n250 молоко",
            reply_markup=get_main_keyboard()
        )
        return True

    if context.user_data.get("waiting_for_category"):
        await update.message.reply_text(
            "Выбери категорию кнопкой ниже",
            reply_markup=get_category_keyboard()
        )
        return True

    return False


async def handle_expense_input_after_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_expense_input"):
        return False

    text = (update.message.text or "").strip()

    if text == "⬅️ Отмена":
        context.user_data.pop("waiting_for_expense_input", None)
        context.user_data.pop("selected_category", None)
        await update.message.reply_text(
            "Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return True

    amount, description = parse_amount_and_description(text)
    if amount is None:
        await update.message.reply_text(
            "Неправильный формат.\nНапиши так:\n250 молоко",
            reply_markup=get_main_keyboard()
        )
        return True

    telegram_id = update.effective_user.id
    family_id = get_user_family_id(telegram_id)

    if not family_id:
        context.user_data.pop("waiting_for_expense_input", None)
        context.user_data.pop("selected_category", None)
        await update.message.reply_text(
            "Сначала нажми /start",
            reply_markup=get_main_keyboard()
        )
        return True

    category = context.user_data.get("selected_category", "Другое")

    cursor.execute(
        "INSERT INTO expenses (family_id, amount, category, description) VALUES (?,?,?,?)",
        (family_id, amount, category, description)
    )
    conn.commit()

    context.user_data.pop("waiting_for_expense_input", None)
    context.user_data.pop("selected_category", None)

    await update.message.reply_text(
        f"Расход добавлен: {amount:.2f} — {category} — {description}",
        reply_markup=get_main_keyboard()
    )
    return True


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    handled_delete = await handle_delete_number(update, context)
    if handled_delete:
        return

    handled_category = await handle_category_choice(update, context)
    if handled_category:
        return

    handled_expense_input = await handle_expense_input_after_category(update, context)
    if handled_expense_input:
        return

    if text == "📋 Покупки":
        await show_list(update, context)
        return

    if text == "💸 Расход":
        context.user_data["waiting_for_category"] = True
        context.user_data.pop("waiting_for_expense_input", None)
        context.user_data.pop("selected_category", None)

        await update.message.reply_text(
            "Выбери категорию расхода:",
            reply_markup=get_category_keyboard()
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

    if text == "📊 Статистика":
        await stats(update, context)
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

    await add_item(update, context)


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
